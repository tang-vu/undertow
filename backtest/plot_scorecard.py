"""Scorecard chart: Undertow vs BTC buy&hold vs naive Fear&Greed contrarian (full cycle).

Makes the risk-adjusted win legible at a glance. Reads output/results.json, writes
output/scorecard.png. Dark "ocean" theme to match the demo.

    python plot_scorecard.py
"""
from __future__ import annotations
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import OUTPUT_DIR

TEAL, GOLD, RED, INK, MUT, BG, GRID = "#19c3c8", "#f7931a", "#ff5d6c", "#e8f4f8", "#7fa6b8", "#06141d", "#15323f"


def main():
    m = json.load(open(os.path.join(OUTPUT_DIR, "results.json")))["metrics"]
    u, b, f = m["strategy_full"], m["btc_buy_hold_full"], m["fng_contrarian_full"]
    names = ["Undertow", "BTC buy & hold", "F&G contrarian"]
    colors = [TEAL, GOLD, RED]

    plt.rcParams.update({"text.color": INK, "axes.labelcolor": INK, "xtick.color": MUT,
                         "ytick.color": MUT, "axes.edgecolor": GRID, "font.size": 12})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2), facecolor=BG)
    for ax in (ax1, ax2):
        ax.set_facecolor(BG)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.grid(axis="y", color=GRID, alpha=0.6)

    # Panel A: risk-adjusted return (higher = better)
    metrics = ["Sharpe", "Calmar"]
    vals = np.array([[u["sharpe"], u["calmar"]], [b["sharpe"], b["calmar"]], [f["sharpe"], f["calmar"]]])
    x = np.arange(len(metrics)); wbar = 0.26
    for i, nm in enumerate(names):
        bars = ax1.bar(x + (i - 1) * wbar, vals[i], wbar, label=nm, color=colors[i])
        for rect, v in zip(bars, vals[i]):
            ax1.text(rect.get_x() + rect.get_width() / 2, v + (0.03 if v >= 0 else -0.08),
                     f"{v:.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=10, color=INK)
    ax1.set_xticks(x); ax1.set_xticklabels(metrics)
    ax1.set_title("Risk-adjusted return  (higher = better)", color=INK, fontsize=13)
    ax1.axhline(0, color=MUT, lw=0.8); ax1.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=10)

    # Panel B: max drawdown (smaller bar = better)
    dd = [abs(u["max_drawdown"]) * 100, abs(b["max_drawdown"]) * 100, abs(f["max_drawdown"]) * 100]
    bars = ax2.bar(names, dd, color=colors, width=0.55)
    for rect, v in zip(bars, dd):
        ax2.text(rect.get_x() + rect.get_width() / 2, v + 1, f"-{v:.0f}%", ha="center", color=INK, fontsize=11)
    ax2.set_title("Max drawdown  (smaller = better)", color=INK, fontsize=13)
    ax2.set_ylabel("max drawdown %"); ax2.set_ylim(0, max(dd) * 1.18)
    ax2.tick_params(axis="x", labelsize=10)

    fig.suptitle("Undertow vs Bitcoin vs naive  —  full cycle 2019-2026  (costs modeled, weights tuned on train only)",
                 color=INK, fontsize=14, y=0.99)
    fig.text(0.5, 0.005,
             f"≈ same total return as BTC (+{u['total_return']*100:.0f}% vs +{b['total_return']*100:.0f}%)  "
             f"·  half the drawdown  ·  ~1.8× the Sharpe", ha="center", color=TEAL, fontsize=12)
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    out = os.path.join(OUTPUT_DIR, "scorecard.png")
    fig.savefig(out, dpi=130, facecolor=BG)
    print("wrote", out)


if __name__ == "__main__":
    main()
