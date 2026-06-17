"""Performance metrics. Annualization uses 365 (crypto trades every day)."""
from __future__ import annotations
import numpy as np
import pandas as pd

from config import ANN


def equity_curve(net: pd.Series) -> pd.Series:
    return (1.0 + net.fillna(0.0)).cumprod()


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def perf_metrics(net: pd.Series, held: pd.Series | None = None) -> dict:
    """Core stats from a daily net-return series. held (optional) drives turnover/exposure."""
    net = net.fillna(0.0)
    n = len(net)
    if n == 0:
        return {}
    eq = equity_curve(net)
    total_return = float(eq.iloc[-1] - 1.0)
    years = n / ANN
    cagr = float(eq.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and eq.iloc[-1] > 0 else float("nan")
    mean, std = net.mean(), net.std()
    sharpe = float(mean / std * np.sqrt(ANN)) if std > 0 else float("nan")
    downside = net[net < 0].std()
    sortino = float(mean / downside * np.sqrt(ANN)) if downside and downside > 0 else float("nan")
    mdd = max_drawdown(eq)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else float("nan")
    active = net[net != 0.0]
    win_rate = float((active > 0).mean()) if len(active) else float("nan")
    out = {
        "total_return": total_return,
        "cagr": cagr,
        "ann_vol": float(std * np.sqrt(ANN)),
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "win_rate": win_rate,
        "n_days": int(n),
    }
    if held is not None:
        h = held.fillna(0.0)
        out["avg_turnover"] = float(h.diff().abs().mean())
        out["avg_exposure"] = float(h.abs().mean())
        out["pct_long"] = float((h > 0).mean())
        out["pct_short"] = float((h < 0).mean())
    return out


def buy_and_hold(ret: pd.Series) -> pd.Series:
    """Net return series for a fully-invested long-only position (no costs, single entry)."""
    return ret.fillna(0.0)
