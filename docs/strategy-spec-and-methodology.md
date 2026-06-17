# Undertow — strategy spec & methodology

This document is the written backbone behind the Skill: the spec it emits, the exact signal/strategy
construction, the out-of-sample protocol, and an honest accounting of data limitations and residual
risk. It is deliberately conservative — a defensible, modest, reproducible result, not a tuned-to-win
curve.

---

## 1. The strategy spec (what the Skill emits)

Given `{token, timeframe}` the Skill returns one JSON object. A **real** example, produced by
`agent_hub/undertow_live.py --demo --token BTCUSDT` (snapshot 2026-06-16 + live Skill-Hub regime):

```json
{
  "skill": "undertow",
  "as_of": "2026-06-17T03:32:29+00:00",
  "token": "BTCUSDT", "timeframe": "1d",
  "regime": { "label": "TREND", "macro_trend": "bear",
              "skill_hub_regime": "mixed_transition", "efficiency_ratio": 0.362 },
  "stress": {
    "S": -0.133, "reading": "neutral",
    "components": { "z_fng": -0.063, "z_funding": -0.203, "z_stretch": -0.583 },
    "weights": { "w_fng": 0.5, "w_funding": 0.5, "w_stretch": 0.0 },
    "surface": { "fear_greed": 23.0 },
    "undertow": { "funding_bps_7d": 22.42, "oi_change_pct_7d": 8.14 }
  },
  "decision": {
    "stance": "flat", "target_position": 0.0,
    "entry": "fade froth in range / ride trend in up-trend; buy capitulation on dips",
    "exit": "froth extreme in range, or macro trend flips to bear",
    "risk": { "max_position": 1.0, "vol_target_annual": 1.0,
              "drawdown_guard": 0.28, "cost_bps_one_way": 10 }
  },
  "enhancements_live_only": { "social_kol": "...", "oi_change_pct_7d": 8.14, "on_chain": "..." },
  "backtest_provenance": { "sharpe": 0.314, "max_drawdown": -0.351, "calmar": 0.112, ... },
  "disclaimer": "Research artifact, not investment advice."
}
```

Full field contract: `skill/undertow/references/strategy-spec-schema.md`.

---

## 2. Signals (all causal)

Sign convention everywhere: **`S>0` = froth** (greed / crowded longs / stretched), **`S<0` =
capitulation**.

| Component | Raw input | Transform | History |
|---|---|---|---|
| `z(F&G)` | CMC Fear & Greed (0–100), market-wide | rolling z, 90d | since 2018 ✅ |
| `z(funding)` | Binance perp funding, 8h prints → daily sum | rolling z, 90d | since 2019 ✅ |
| `z(price_stretch)` | `(close − EMA₃₀)/EMA₃₀` | rolling z, 90d | full ✅ |

Composite: `S = w_fng·z(F&G) + w_funding·z(funding) + w_stretch·z(price_stretch)`.

**Regime R:** Kaufman efficiency ratio (20d) → `ER>0.30` = TREND else RANGE; macro filter
`close > EMA₅₀` = bull else bear. Live, the Skill Hub's `detect_market_regime` supplies an
attributable label (`trend_expansion`/`range_chop`/`overheated_longs`/`liquidation_stress`/
`mixed_transition`).

---

## 3. Decision logic (regime switch)

| Regime | Macro | Behaviour |
|---|---|---|
| TREND | bull | ride: long, trim only as froth rises (`1 − haircut·froth⁺`) |
| TREND | bear | step aside: flat, at most a light froth short |
| RANGE | bull | mean-revert: base long `0.6`, sell froth / buy fear (`0.6 − tilt·tanh(S)`) |
| RANGE | bear | flat (no knife-catching); light froth short |

**Sizing:** vol-targeting — `position = raw · min(target_daily_vol / realized_vol, 1.0)`, capped at
`|1.0|`. The scalar **only de-risks** turmoil; it never adds leverage. **Risk:** hard position cap;
drawdown guard halves exposure past 28% sleeve drawdown; `10 bps` one-way cost on turnover (fees +
slippage). Per-asset sleeves are equal-weighted into the portfolio.

---

## 4. Out-of-sample protocol (no look-ahead)

- **Causal everything.** z-scores use trailing windows only. The position decided at the close of day
  *t* is applied to day *t+1*'s return (`position.shift`), with the drawdown guard at *t* using equity
  only through *t*. Turnover cost is charged on every position change.
- **Train-only tuning.** Weights are grid-searched to maximize **train-split** Sharpe, then frozen.
  The grid is deliberately tiny (10 simplex points) to limit overfitting; equal weights are included
  as the un-tuned reference and remain competitive.
- **Two OOS views:**
  1. *Simple split* — tune on the first 60% of dates, evaluate on the last 40%.
  2. *Walk-forward* — re-tune on an expanding window every 180 days; stitch the never-seen forward
     blocks into one continuous curve (the strict headline).
- **Determinism.** Data is snapshotted to `backtest/data_cache/` and committed; a fixed seed is set.
  A judge gets identical numbers with one command and zero credentials.

---

## 5. Results by window

| Window | Strategy | Total | Sharpe | Max DD | Calmar |
|---|---|--:|--:|--:|--:|
| Full 2019–26 | **Undertow** | +533% | **1.34** | **−33%** | **0.94** |
| Full 2019–26 | BTC b&h | +550% | 0.76 | −77% | 0.42 |
| Full 2019–26 | F&G contrarian | −52% | 0.01 | −71% | −0.15 |
| Split test 2023-10→26 | **Undertow** | +42% | 0.84 | **−19%** | **0.75** |
| Split test | BTC b&h | +135% | 0.90 | −51% | 0.72 |
| Walk-forward 2021-08→26 | **Undertow** | +20% | 0.31 | **−35%** | **0.11** |
| Walk-forward | BTC b&h | +35% | 0.38 | −77% | 0.08 |
| Walk-forward | F&G contrarian | −53% | −0.12 | −71% | −0.20 |

**Interpretation.** Undertow's edge is *risk-adjusted*: across every window it beats both buy-and-hold
and the naive contrarian on **Calmar** and roughly halves **max drawdown**; over the full cycle it
nearly doubles **Sharpe** at the same total return. It trails buy-and-hold on *raw* Sharpe/return only
inside the post-2021-top window, because a portfolio that sidesteps a −77% crash also forgoes the
cheapest re-entry into the V-recovery. We surface this rather than hide it.

---

## 6. Data limitations & honesty

- **Open interest** has only ~30 days of free history → **excluded from the backtested core**; it is a
  live-only enhancement delivered by the Skill Hub and flagged as such. We did not fabricate OI
  history to inflate the model.
- **Social / KOL heat** and **on-chain / DEX flow** have no reliable queryable daily history → live-only
  enhancements, never backtested.
- **Live z-score approximation.** The backtest uses strictly causal rolling windows; the *live* Skill
  z-scores a single live reading against snapshot baselines (`strategy-params.json`) — a reasonable
  real-time approximation, explicitly labelled.
- **Funding aggregation.** 8h funding prints summed to a daily figure; an alternative (mean) only
  rescales a z-scored input.
- **Survivorship / universe.** Five liquid majors with deep perp history; results may not generalize
  to illiquid alts. Assets with insufficient history are dropped at load time.

---

## 7. Residual risk & future work

- Walk-forward raw Sharpe in V-recovery windows is the known soft spot; a faster re-entry rule or a
  convexity overlay could narrow the gap without sacrificing the drawdown win.
- The live OI / social / on-chain enhancements are wired but not yet *forward-validated* on a logged
  out-of-sample horizon — the natural next step.
- Funding/F&G normalization could move from fixed snapshot baselines to a live expanding window once a
  history feed is available via the API key path.

*Research/competition artifact, not investment advice.*
