"""Undertow backtest — one-command entry point.

    python run_backtest.py            # uses committed data snapshot (deterministic)
    python run_backtest.py --refresh  # re-pull live data and overwrite the snapshot

Outputs:
    output/results.json     metrics, equity curves, live snapshot, annotated divergences
    output/equity_curve.png walk-forward strategy vs benchmarks
"""
from __future__ import annotations
import os
import sys
import json
import math
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import OUTPUT_DIR, DATA_START, DATA_END, COST_BPS, TARGET_VOL_ANNUAL, SEED
import config
from data import load_dataset
from signals import add_signals
from strategy import run_sleeve, portfolio_returns, default_params, fng_contrarian_returns
from metrics import perf_metrics, equity_curve, buy_and_hold
from evaluation import simple_split, walk_forward, all_dates


def _clean(o):
    """Recursively make a structure JSON-safe (NaN/inf -> None, np types -> py)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _rebased(net: pd.Series) -> list:
    return [round(float(x), 5) for x in equity_curve(net).to_numpy()]


def benchmark_series(data: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """BTC buy&hold, equal-weight basket buy&hold, and F&G-contrarian portfolio net returns."""
    rets = {sym: df.set_index("date")["ret"] for sym, df in data.items()}
    basket = pd.concat(rets.values(), axis=1).mean(axis=1)
    btc_key = next((k for k in data if k.startswith("BTC")), list(data)[0])
    fng = pd.concat({sym: fng_contrarian_returns(df) for sym, df in data.items()}, axis=1).mean(axis=1)
    return {
        "btc_bh": buy_and_hold(rets[btc_key]),
        "basket_bh": buy_and_hold(basket),
        "fng_contrarian": fng,
    }


def divergence_examples(sleeve: pd.DataFrame, df: pd.DataFrame, k: int = 3) -> list:
    """Pick historical days where |S| was extreme and the forward 14d move reversed the crowd."""
    close = df.set_index("date")["close"]
    fwd = close.shift(-14) / close - 1.0
    s = sleeve.set_index("date")["S"]
    reg = sleeve.set_index("date")["regime"]
    j = pd.DataFrame({"S": s, "fwd14": fwd, "regime": reg}).dropna()
    hi, lo = j["S"].quantile(0.95), j["S"].quantile(0.05)
    froth = j[(j["S"] >= hi) & (j["fwd14"] < 0)].sort_values("S", ascending=False).head(k)
    fear = j[(j["S"] <= lo) & (j["fwd14"] > 0)].sort_values("S").head(k)
    rows = []
    for d, r in pd.concat([froth.head(2), fear.head(2)]).iterrows():
        kind = "euphoria faded" if r["S"] > 0 else "capitulation bought"
        rows.append({"date": str(pd.Timestamp(d).date()), "S": r["S"], "regime": r["regime"],
                     "fwd_14d_return": r["fwd14"], "note": kind})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-pull live data, overwrite snapshot")
    args = ap.parse_args()
    np.random.seed(SEED)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading data ...")
    data = load_dataset(refresh=args.refresh)
    data = {sym: add_signals(df) for sym, df in data.items()}
    params = default_params()

    print("Simple split (tune on train, freeze, test OOS) ...")
    ss = simple_split(data, params)
    best_w = ss["weights"]
    print(f"  frozen weights (w_fng,w_funding,w_stretch) = {tuple(round(x,3) for x in best_w)}")

    print("Walk-forward (expanding refit) ...")
    wf_net, wf_log = walk_forward(data, params)

    # Frozen-weight sleeves for reporting (held/regime/current snapshot/divergences).
    sleeves = {sym: run_sleeve(df, best_w, params) for sym, df in data.items()}
    held = pd.concat({sym: s.set_index("date")["held"] for sym, s in sleeves.items()}, axis=1).mean(axis=1)
    strat_full = ss["net_full"]

    bm = benchmark_series(data)
    boundary = ss["boundary"]
    wf_start = wf_net.index[0] if len(wf_net) else boundary

    def window(series, lo=None, hi=None):
        s = series.copy()
        if lo is not None:
            s = s[s.index >= lo]
        if hi is not None:
            s = s[s.index < hi]
        return s

    metrics = {
        # Headline OOS: continuous walk-forward, and benchmarks over the IDENTICAL window.
        "strategy_walk_forward": perf_metrics(wf_net),
        "btc_buy_hold_wf": perf_metrics(window(bm["btc_bh"], wf_start)),
        "basket_buy_hold_wf": perf_metrics(window(bm["basket_bh"], wf_start)),
        "fng_contrarian_wf": perf_metrics(window(bm["fng_contrarian"], wf_start)),
        # Simple split OOS (tune on train, freeze on test) + benchmarks over the test window.
        "strategy_test_oos": perf_metrics(ss["net_test"], window(held, boundary)),
        "btc_buy_hold_test": perf_metrics(window(bm["btc_bh"], boundary)),
        "basket_buy_hold_test": perf_metrics(window(bm["basket_bh"], boundary)),
        "fng_contrarian_test": perf_metrics(window(bm["fng_contrarian"], boundary)),
        # Full-period context (train portion is in-sample for the frozen weights).
        "strategy_full": perf_metrics(strat_full, held),
        "btc_buy_hold_full": perf_metrics(bm["btc_bh"]),
        "basket_buy_hold_full": perf_metrics(bm["basket_bh"]),
        "fng_contrarian_full": perf_metrics(bm["fng_contrarian"]),
    }

    # Walk-forward equity vs benchmarks, all rebased to 1.0 at WF start (fair like-for-like).
    wf_dates = wf_net.index
    eq_wf = {
        "dates": [str(d.date()) for d in wf_dates],
        "strategy": _rebased(wf_net),
        "btc_bh": _rebased(window(bm["btc_bh"], wf_start)),
        "basket_bh": _rebased(window(bm["basket_bh"], wf_start)),
        "fng_contrarian": _rebased(window(bm["fng_contrarian"], wf_start)),
    }

    # Current live-ready snapshot per asset (latest bar).
    current = {}
    for sym, s in sleeves.items():
        df = data[sym]
        last = df.iloc[-1]
        sl = s.iloc[-1]
        current[sym] = {
            "date": str(pd.Timestamp(last["date"]).date()),
            "close": float(last["close"]), "fng": float(last["fng"]),
            "funding": float(last["funding"]),
            "z_fng": float(last["z_fng"]), "z_funding": float(last["z_funding"]),
            "z_stretch": float(last["z_stretch"]),
            "S": float(sl["S"]), "regime": str(sl["regime"]),
            "macro_trend": "bull" if last["close"] > last["ema_macro"] else "bear",
            "er": float(last["er"]), "target_position": float(sl["held"]),
        }

    btc_key = next((k for k in data if k.startswith("BTC")), list(data)[0])
    results = {
        "meta": {
            "data_window": [DATA_START, DATA_END],
            "universe_requested": config.UNIVERSE,
            "assets_used": list(data.keys()),
            "frozen_weights": {"w_fng": best_w[0], "w_funding": best_w[1], "w_stretch": best_w[2]},
            "cost_bps_one_way": COST_BPS, "target_vol_annual": TARGET_VOL_ANNUAL,
            "train_test_boundary": str(boundary.date()),
            "walk_forward_start": str(pd.Timestamp(wf_start).date()),
        },
        "metrics": metrics,
        "equity_walk_forward": eq_wf,
        "walk_forward_log": wf_log,
        "tuning_scoreboard": [{"weights": [round(x, 3) for x in w], "train_sharpe": round(sh, 3)}
                              for w, sh in ss["scoreboard"]],
        "current": current,
        "divergence_examples": divergence_examples(sleeves[btc_key], data[btc_key]),
    }

    out_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(out_path, "w") as f:
        json.dump(_clean(results), f, indent=2)
    print(f"  wrote {out_path}")

    # Plot walk-forward equity vs benchmarks.
    plt.figure(figsize=(11, 6))
    x = pd.to_datetime(eq_wf["dates"])
    plt.plot(x, eq_wf["strategy"], label="Undertow (walk-forward OOS)", lw=2.2, color="#0aa")
    plt.plot(x, eq_wf["btc_bh"], label="BTC buy & hold", lw=1.3, color="#f7931a", alpha=0.9)
    plt.plot(x, eq_wf["basket_bh"], label="Basket buy & hold", lw=1.1, color="#888", alpha=0.8)
    plt.plot(x, eq_wf["fng_contrarian"], label="Fear&Greed contrarian (naive)", lw=1.1,
             color="#c33", alpha=0.7, ls="--")
    plt.yscale("log")
    plt.title("Undertow — walk-forward out-of-sample equity (rebased to 1.0)")
    plt.ylabel("growth of $1 (log)"); plt.legend(); plt.grid(alpha=0.25)
    plt.tight_layout()
    png = os.path.join(OUTPUT_DIR, "equity_curve.png")
    plt.savefig(png, dpi=130)
    print(f"  wrote {png}")

    # Console summary — apples-to-apples over the identical walk-forward window.
    print(f"\n=== WALK-FORWARD OOS  ({results['meta']['walk_forward_start']} -> {DATA_END}) ===")
    print(f"  {'series':22s} {'sharpe':>7s} {'sortino':>7s} {'maxDD':>7s} {'total':>7s} {'calmar':>7s}")
    for name, lbl in [("strategy_walk_forward", "Undertow"), ("btc_buy_hold_wf", "BTC buy&hold"),
                      ("basket_buy_hold_wf", "Basket buy&hold"), ("fng_contrarian_wf", "F&G contrarian")]:
        m = metrics[name]
        def f(k): v = m.get(k); return f"{v:7.2f}" if isinstance(v, (int, float)) else f"{'n/a':>7s}"
        print(f"  {lbl:22s} {f('sharpe')} {f('sortino')} {f('max_drawdown')} {f('total_return')} {f('calmar')}")
    fm = metrics["strategy_full"]
    print(f"  full-cycle Undertow Sharpe={fm.get('sharpe'):.2f} vs BTC {metrics['btc_buy_hold_full'].get('sharpe'):.2f}"
          f" | avg exposure {fm.get('avg_exposure'):.2f}")


if __name__ == "__main__":
    main()
