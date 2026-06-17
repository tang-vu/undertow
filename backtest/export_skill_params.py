"""Export the frozen strategy parameters + normalization baselines for the live Skill.

The live Undertow Skill cannot recompute multi-year rolling z-scores from MCP (which returns only
live values). So we snapshot the backtest's reference mean/std for each signal and the frozen
weights/thresholds into skill/undertow/references/strategy-params.json. The Skill reads these to
z-score a LIVE reading against historical norms — making the live agent a faithful real-time
instance of the backtested spec.

Run after run_backtest.py:  python export_skill_params.py
"""
from __future__ import annotations
import os
import json
import config
from data import load_dataset
from signals import add_signals

SKILL_REF = os.path.join(config.ROOT, "..", "skill", "undertow", "references")


def _ms(x):
    return {"mean": round(float(x.mean()), 8), "std": round(float(x.std()), 8)}


def main():
    data = {sym: add_signals(df) for sym, df in load_dataset().items()}
    btc = next((k for k in data if k.startswith("BTC")), list(data)[0])

    baselines = {
        "fng_market": _ms(data[btc]["fng"]),          # F&G is market-wide (same series for all)
        "funding": {sym: _ms(df["funding"]) for sym, df in data.items()},
        "stretch": {sym: _ms(df["stretch"]) for sym, df in data.items()},
        "stretch_ema_span": config.EMA_STRETCH_SPAN,
    }

    results_path = os.path.join(config.OUTPUT_DIR, "results.json")
    headline = {}
    if os.path.exists(results_path):
        r = json.load(open(results_path))
        m = r["metrics"]
        keep = ("sharpe", "sortino", "max_drawdown", "total_return", "calmar")
        headline = {k: {kk: m[k].get(kk) for kk in keep}
                    for k in ("strategy_walk_forward", "btc_buy_hold_wf", "fng_contrarian_wf",
                              "strategy_full", "btc_buy_hold_full")}
        weights = r["meta"]["frozen_weights"]
    else:
        weights = {"w_fng": 1 / 3, "w_funding": 1 / 3, "w_stretch": 1 / 3}

    params = {
        "version": "1.0",
        "generated_from_window": [config.DATA_START, config.DATA_END],
        "assets_calibrated": list(data.keys()),
        "composite": {
            "formula": "S = w_fng*z(fng) + w_funding*z(funding) + w_stretch*z(price_stretch)",
            "weights": weights,
            "z_window_days": config.Z_WINDOW,
            "sign_convention": "S>0 = froth (greed / crowded longs / stretched); S<0 = capitulation (fear)",
            "note": "Backtest uses strictly causal rolling z-scores; the live Skill z-scores a live "
                    "reading against these snapshot baselines as a real-time approximation.",
        },
        "normalization_baselines": baselines,
        "regime": {
            "macro_filter": "close vs EMA{} (bull/bear)".format(config.MACRO_EMA),
            "er_window": config.ER_WINDOW,
            "er_threshold": config.ER_THRESHOLD,
            "labels": ["TREND", "RANGE"],
            "skill_hub_service": "detect_market_regime -> {trend_expansion, range_chop, overheated_longs, "
                                 "liquidation_stress, mixed_transition}",
        },
        "decision_rules": {
            "s_scale": config.S_SCALE,
            "trend_froth_haircut": config.TREND_FROTH_HAIRCUT,
            "range_long_base": config.RANGE_LONG_BASE,
            "range_tilt": config.RANGE_TILT,
            "range_short_cap": config.RANGE_SHORT_CAP,
            "short_bear": config.SHORT_BEAR,
            "dip_bear": config.DIP_BEAR,
            "target_vol_annual": config.TARGET_VOL_ANNUAL,
            "max_position": config.MAX_POS,
            "drawdown_guard": config.DD_GUARD,
            "cost_bps_one_way": config.COST_BPS,
        },
        "backtest_headline": headline,
    }

    os.makedirs(SKILL_REF, exist_ok=True)
    out = os.path.join(SKILL_REF, "strategy-params.json")
    with open(out, "w") as f:
        json.dump(params, f, indent=2)
    print(f"wrote {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
