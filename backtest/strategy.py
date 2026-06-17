"""Regime-switching decision logic, vol-targeted sizing, costs, and a causal drawdown guard.

The mapping from the positioning-stress score S to a position depends on the regime R:
  - RANGE  -> mean-reversion: fade the crowd. Froth (S>0) -> short; capitulation (S<0) -> long.
  - TREND  -> momentum: ride the EMA trend; use froth only to TRIM size (risk), never to flip.
Sizing is proportional to signal strength and inverse to realized volatility (vol targeting).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from config import (
    S_SCALE, ER_THRESHOLD, TREND_FROTH_HAIRCUT, RANGE_LONG_BASE, RANGE_TILT, RANGE_SHORT_CAP,
    SHORT_BEAR, DIP_BEAR, TARGET_VOL_ANNUAL, MAX_POS, DD_GUARD, COST_BPS, ANN,
)
from signals import stress_score


def default_params() -> dict:
    return {"er_threshold": ER_THRESHOLD}


def compute_target_positions(df: pd.DataFrame, s: pd.Series, params: dict) -> pd.Series:
    """Target position per day from stress S and regime R (vectorized), in [-MAX_POS, MAX_POS].

    Regime-switching, anchored to a causal macro-trend filter (close vs ema_macro) so the book
    never naked-shorts the primary up-trend:

      TREND : momentum. Up -> long, trimmed when froth aligns (late-move risk).
              Down -> flat, with at most a light froth-driven defensive short (SHORT_BEAR).
      RANGE : mean-reversion. Up -> base long, sell froth / buy fear around RANGE_LONG_BASE.
              Down -> flat (DIP_BEAR=0 => no knife-catching) with a light froth short.
    """
    er_thr = params["er_threshold"]
    is_trend = (df["er"] > er_thr).to_numpy()
    up = (df["close"] > df["ema_macro"]).to_numpy()         # macro-trend filter (causal, responsive)
    froth = np.tanh(s.to_numpy() / S_SCALE)                  # [-1,1]; + = frothy, - = fearful
    froth_pos = np.maximum(froth, 0.0)                       # froth magnitude
    fear_pos = np.maximum(-froth, 0.0)                       # capitulation magnitude

    trend_pos = np.where(
        up,
        1.0 - TREND_FROTH_HAIRCUT * froth_pos,             # frothy bull -> trim toward 0.5
        -SHORT_BEAR * froth_pos,                            # down-trend -> flat, light froth short
    )
    range_pos = np.where(
        up,
        np.clip(RANGE_LONG_BASE - RANGE_TILT * froth, 0.0, 1.0),          # bull range: sell froth / buy fear
        np.clip(DIP_BEAR * fear_pos - SHORT_BEAR * froth_pos, -RANGE_SHORT_CAP, RANGE_SHORT_CAP),
    )
    raw = pd.Series(np.where(is_trend, trend_pos, range_pos), index=df.index)

    # Vol targeting: de-risk turmoil only — scalar capped at 1.0 so calm up-trends stay fully invested
    # and the book never uses leverage. High realized vol shrinks the position.
    target_daily_vol = TARGET_VOL_ANNUAL / np.sqrt(ANN)
    scalar = (target_daily_vol / df["rv"]).clip(upper=1.0)
    pos = (raw * scalar).clip(-MAX_POS, MAX_POS).fillna(0.0)
    return pos


def run_sleeve(df: pd.DataFrame, weights, params: dict, cost_bps: float = COST_BPS) -> pd.DataFrame:
    """Single-asset sleeve. Returns a frame with date, net return, held position, regime.

    No look-ahead: the position decided at the close of day t is held during day t+1, and the
    drawdown guard at day t uses equity only through day t. Costs charged on position change.
    """
    s = stress_score(df, weights)
    target = compute_target_positions(df, s, params).to_numpy()
    ret = df["ret"].to_numpy()
    n = len(df)
    cost = cost_bps / 1e4

    net = np.zeros(n)
    held_arr = np.zeros(n)
    eq, peak, prev_held = 1.0, 1.0, 0.0
    for t in range(n - 1):
        guard = 0.5 if (eq / peak - 1.0) <= -DD_GUARD else 1.0
        held = float(np.clip(target[t] * guard, -MAX_POS, MAX_POS))
        r_next = ret[t + 1]
        if not np.isfinite(r_next):
            r_next = 0.0
        turn = abs(held - prev_held)
        nr = held * r_next - cost * turn
        net[t + 1] = nr
        held_arr[t + 1] = held
        eq *= (1.0 + nr)
        peak = max(peak, eq)
        prev_held = held

    out = pd.DataFrame({
        "date": df["date"].to_numpy(),
        "ret": ret,
        "S": s.to_numpy(),
        "er": df["er"].to_numpy(),
        "regime": np.where(df["er"].to_numpy() > params["er_threshold"], "TREND", "RANGE"),
        "held": held_arr,
        "net": net,
    })
    return out


def portfolio_returns(sleeves: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Equal-weight the per-asset net returns across assets available each day."""
    frames = [s.set_index("date")["net"].rename(sym) for sym, s in sleeves.items()]
    wide = pd.concat(frames, axis=1).sort_index()
    port = wide.mean(axis=1, skipna=True).fillna(0.0)
    return pd.DataFrame({"date": port.index, "net": port.to_numpy()})


def fng_contrarian_returns(df: pd.DataFrame, cost_bps: float = COST_BPS) -> pd.Series:
    """Naive single-signal baseline: long-only Fear & Greed contrarian, vol-targeted, same costs.

    Buy fear, step to cash on greed (fng<=20 -> full long, fng>=60 -> flat) — the standard,
    fair interpretation of an F&G contrarian. No regime, no funding, no stretch. This isolates
    the value added by Undertow's regime-switching + positioning (undertow) layer.
    """
    pos = ((60.0 - df["fng"]) / 40.0).clip(0.0, 1.0)
    target_daily_vol = TARGET_VOL_ANNUAL / np.sqrt(ANN)
    scalar = (target_daily_vol / df["rv"]).clip(upper=3.0)
    target = (pos * scalar).clip(-MAX_POS, MAX_POS).fillna(0.0).to_numpy()
    ret = df["ret"].to_numpy()
    n = len(df)
    cost = cost_bps / 1e4
    net = np.zeros(n)
    prev = 0.0
    for t in range(n - 1):
        held = target[t]
        r_next = ret[t + 1] if np.isfinite(ret[t + 1]) else 0.0
        net[t + 1] = held * r_next - cost * abs(held - prev)
        prev = held
    return pd.Series(net, index=df["date"])
