"""Data acquisition + caching for the Undertow backtest.

Free, no-API-key sources only, so a judge reproduces identical numbers with zero credentials:
  - Daily OHLCV  : Binance spot klines
  - Funding rate : Binance USDT-M perp funding (8h prints -> daily)
  - Fear & Greed : alternative.me (market-wide, daily, since 2018)

All raw pulls are cached to data_cache/*.csv and committed to the repo for determinism.
Pass refresh=True (CLI: --refresh) to re-pull live and overwrite the snapshot.
"""
from __future__ import annotations
import os
import time
import datetime as dt
import pandas as pd
import requests

from config import (
    DATA_DIR, DATA_START, DATA_END, MIN_HISTORY_DAYS,
)

KLINES_HOSTS = ["https://api.binance.com", "https://data-api.binance.vision"]
FAPI_HOST = "https://fapi.binance.com"
FNG_URL = "https://api.alternative.me/fng/?limit=0&format=json"
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "undertow-backtest/1.0"})


def _ms(date_str: str) -> int:
    return int(dt.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def _get(url: str, params: dict, tries: int = 4) -> list:
    for i in range(tries):
        try:
            r = _SESSION.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            time.sleep(1.0 + i)
        except requests.RequestException:
            time.sleep(1.0 + i)
    raise RuntimeError(f"GET failed after {tries} tries: {url} {params}")


def _fetch_klines(symbol: str) -> pd.DataFrame:
    """Daily OHLCV, paged in 1000-candle chunks across all KLINES_HOSTS as fallback."""
    start, end = _ms(DATA_START), _ms(DATA_END) + 86_400_000
    rows, cur = [], start
    host = KLINES_HOSTS[0]
    while cur < end:
        params = {"symbol": symbol, "interval": "1d", "startTime": cur, "endTime": end, "limit": 1000}
        data = None
        for h in KLINES_HOSTS:
            try:
                data = _get(f"{h}/api/v3/klines", params)
                host = h
                break
            except RuntimeError:
                continue
        if not data:
            break
        rows.extend(data)
        cur = data[-1][0] + 86_400_000
        time.sleep(0.25)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "openTime", "open", "high", "low", "close", "volume", "closeTime",
        "qv", "trades", "tbv", "tqv", "ignore"])
    df["date"] = pd.to_datetime(df["openTime"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    df = df[["date", "open", "high", "low", "close", "volume"]].astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float})
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def _fetch_funding(symbol: str) -> pd.DataFrame:
    """Perp funding (8h) paged forward, aggregated to a daily sum (total daily funding)."""
    start, end = _ms(DATA_START), _ms(DATA_END) + 86_400_000
    rows, cur = [], start
    while cur < end:
        params = {"symbol": symbol, "startTime": cur, "endTime": end, "limit": 1000}
        try:
            data = _get(f"{FAPI_HOST}/fapi/v1/fundingRate", params)
        except RuntimeError:
            break
        if not data:
            break
        rows.extend(data)
        if len(data) < 1000:
            break
        cur = data[-1]["fundingTime"] + 1
        time.sleep(0.25)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    df["fundingRate"] = df["fundingRate"].astype(float)
    daily = df.groupby("date", as_index=False)["fundingRate"].sum().rename(columns={"fundingRate": "funding"})
    return daily.sort_values("date").reset_index(drop=True)


def _fetch_fng() -> pd.DataFrame:
    data = _get(FNG_URL, {})
    recs = data["data"] if isinstance(data, dict) else data
    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s", utc=True).dt.tz_localize(None).dt.normalize()
    df["fng"] = df["value"].astype(float)
    return df[["date", "fng"]].sort_values("date").reset_index(drop=True)


def _cached(name: str, builder, refresh: bool) -> pd.DataFrame:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, name)
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path, parse_dates=["date"])
    df = builder()
    if not df.empty:
        df.to_csv(path, index=False)
    return df


def load_dataset(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Return {symbol: daily df[date, close, ret, funding, fng]} for assets with enough history."""
    fng = _cached("fng.csv", _fetch_fng, refresh)
    out: dict[str, pd.DataFrame] = {}
    from config import UNIVERSE
    for sym in UNIVERSE:
        ohlcv = _cached(f"klines_{sym}.csv", lambda s=sym: _fetch_klines(s), refresh)
        funding = _cached(f"funding_{sym}.csv", lambda s=sym: _fetch_funding(s), refresh)
        if ohlcv.empty or funding.empty:
            print(f"  [skip] {sym}: missing OHLCV or funding")
            continue
        df = ohlcv[["date", "close"]].merge(funding, on="date", how="left").merge(fng, on="date", how="left")
        df = df[(df["date"] >= DATA_START) & (df["date"] <= DATA_END)].copy()
        df["funding"] = df["funding"].ffill()
        df["fng"] = df["fng"].ffill()
        df = df.dropna(subset=["close", "funding", "fng"]).reset_index(drop=True)
        df["ret"] = df["close"].pct_change()
        if len(df) < MIN_HISTORY_DAYS:
            print(f"  [skip] {sym}: only {len(df)} days (< {MIN_HISTORY_DAYS})")
            continue
        out[sym] = df
        print(f"  [ok]   {sym}: {len(df)} days  {df['date'].iloc[0].date()} -> {df['date'].iloc[-1].date()}")
    if not out:
        raise RuntimeError("No assets loaded — check network / cache.")
    return out
