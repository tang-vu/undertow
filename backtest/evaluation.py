"""Out-of-sample evaluation: train-only weight tuning + expanding walk-forward.

Two independent OOS protocols, both reported:
  1. Simple split  : tune weights on the first TRAIN_FRAC of dates, freeze, evaluate on the rest.
  2. Walk-forward  : re-tune on an expanding window every WF_REFIT_EVERY days; stitch the
                     never-seen blocks into one continuous OOS curve. This is the headline.

Weight tuning maximizes portfolio Sharpe on the *training* window only — never the test window.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from config import WEIGHT_GRID, ANN, TRAIN_FRAC, WF_MIN_TRAIN_DAYS, WF_REFIT_EVERY
from strategy import run_sleeve, portfolio_returns, default_params


def _sharpe(net: pd.Series) -> float:
    net = net.fillna(0.0)
    std = net.std()
    return float(net.mean() / std * np.sqrt(ANN)) if std > 0 else -np.inf


def portfolio_net(data: dict[str, pd.DataFrame], weights, params) -> pd.Series:
    """Full-history equal-weight portfolio net-return series for one weight vector."""
    sleeves = {sym: run_sleeve(df, weights, params) for sym, df in data.items()}
    port = portfolio_returns(sleeves)
    return port.set_index("date")["net"]


def all_dates(data: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex([])
    for df in data.values():
        idx = idx.union(pd.DatetimeIndex(df["date"]))
    return idx.sort_values()


def tune_weights(data, params, lo, hi) -> tuple[tuple, list]:
    """Grid-search weights maximizing portfolio Sharpe on dates in [lo, hi). Returns best + board."""
    board = []
    for w in WEIGHT_GRID:
        net = portfolio_net(data, w, params)
        mask = (net.index >= lo) & (net.index < hi)
        board.append((w, _sharpe(net[mask])))
    board.sort(key=lambda x: x[1], reverse=True)
    return board[0][0], board


def simple_split(data, params):
    """Tune on first TRAIN_FRAC, freeze, evaluate train vs test. Returns dict of artifacts."""
    dates = all_dates(data)
    boundary = dates[int(len(dates) * TRAIN_FRAC)]
    best_w, board = tune_weights(data, params, dates[0], boundary)
    net = portfolio_net(data, best_w, params)
    return {
        "boundary": boundary,
        "weights": best_w,
        "scoreboard": board,
        "net_full": net,
        "net_train": net[net.index < boundary],
        "net_test": net[net.index >= boundary],
    }


def walk_forward(data, params):
    """Expanding-window refit; stitch OOS blocks into one continuous net-return series."""
    dates = all_dates(data)
    if len(dates) <= WF_MIN_TRAIN_DAYS + 1:
        return pd.Series(dtype=float), []
    pieces, log = [], []
    start_i = WF_MIN_TRAIN_DAYS
    while start_i < len(dates):
        end_i = min(start_i + WF_REFIT_EVERY, len(dates))
        lo, hi = dates[start_i], dates[end_i - 1]
        best_w, _ = tune_weights(data, params, dates[0], lo)
        net = portfolio_net(data, best_w, params)
        block = net[(net.index >= lo) & (net.index <= hi)]
        pieces.append(block)
        log.append({"from": str(lo.date()), "to": str(hi.date()), "weights": [round(x, 3) for x in best_w]})
        start_i = end_i
    wf = pd.concat(pieces).sort_index()
    wf = wf[~wf.index.duplicated(keep="first")]
    return wf, log
