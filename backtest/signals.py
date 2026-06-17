"""Signal construction. Every transform here is CAUSAL (trailing windows only) — the
single most important property for an honest backtest. Nothing uses future information.

Sign convention for the stress score S: POSITIVE = "froth" (greed / crowded longs / stretched),
NEGATIVE = "capitulation" (fear / crowded shorts / washed out). The decision layer fades positive
S in range regimes and rides trends otherwise.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from config import (
    Z_WINDOW, EMA_STRETCH_SPAN, EMA_FAST, EMA_SLOW, MACRO_EMA, ER_WINDOW, RV_WINDOW,
)


def rolling_z(x: pd.Series, window: int = Z_WINDOW) -> pd.Series:
    """Trailing z-score using only data up to and including t (no look-ahead)."""
    mean = x.rolling(window, min_periods=window // 2).mean()
    std = x.rolling(window, min_periods=window // 2).std()
    return (x - mean) / std.replace(0.0, np.nan)


def efficiency_ratio(close: pd.Series, window: int = ER_WINDOW) -> pd.Series:
    """Kaufman Efficiency Ratio in [0,1]: ~1 = clean trend, ~0 = choppy range."""
    direction = (close - close.shift(window)).abs()
    volatility = close.diff().abs().rolling(window).sum()
    return (direction / volatility.replace(0.0, np.nan)).clip(0.0, 1.0)


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Attach z-scored components, the composite-ready columns, regime inputs, and realized vol."""
    df = df.copy()

    # --- Surface layer: crowd sentiment (Fear & Greed) ---
    df["z_fng"] = rolling_z(df["fng"])

    # --- Undertow layer: positioning forces beneath ---
    df["z_funding"] = rolling_z(df["funding"])
    ema_stretch = df["close"].ewm(span=EMA_STRETCH_SPAN, adjust=False).mean()
    df["stretch"] = (df["close"] - ema_stretch) / ema_stretch
    df["z_stretch"] = rolling_z(df["stretch"])

    # --- Regime inputs ---
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    df["ema_macro"] = df["close"].ewm(span=MACRO_EMA, adjust=False).mean()
    df["trend_dir"] = np.sign(df["ema_fast"] - df["ema_slow"])
    df["er"] = efficiency_ratio(df["close"])

    # --- Realized volatility (for vol targeting) ---
    df["rv"] = df["ret"].rolling(RV_WINDOW, min_periods=RV_WINDOW // 2).std()

    return df


def stress_score(df: pd.DataFrame, weights: tuple[float, float, float]) -> pd.Series:
    """Composite positioning-stress S from the three history-backed z-scores.

    weights = (w_fng, w_funding, w_stretch). Components missing early in the sample are
    treated as 0 contribution (fillna 0) so S is defined once any window warms up.
    """
    w_fng, w_funding, w_stretch = weights
    z_fng = df["z_fng"].fillna(0.0)
    z_funding = df["z_funding"].fillna(0.0)
    z_stretch = df["z_stretch"].fillna(0.0)
    return w_fng * z_fng + w_funding * z_funding + w_stretch * z_stretch
