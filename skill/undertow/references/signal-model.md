# Signal model — full math

All transforms are **causal** (trailing windows only). Sign convention everywhere: **positive =
froth** (greed / crowded longs / stretched), **negative = capitulation** (fear / washed out).

## 1. Component z-scores

For a raw series `x` (Fear & Greed, funding, or price-stretch), the causal z-score is

```
z_t = (x_t − mean(x[t−W+1 .. t])) / std(x[t−W+1 .. t])      # W = z_window_days (default 90)
```

In the **backtest** this rolling window is recomputed every day (no look-ahead). In the **live
skill** there is no multi-year MCP history, so z-score the single live reading against the snapshot
baselines instead:

```
z = (x_live − baseline.mean) / baseline.std                  # baselines in strategy-params.json
```

Inputs:
- `z(FearGreed)` — market-wide CMC Fear & Greed (0–100). Baseline key `fng_market`.
- `z(funding)`   — daily perp funding (sum of the day's 8h prints). Baseline key `funding[SYMBOL]`.
- `z(price_stretch)` — `stretch = (close − EMA_span(close)) / EMA_span(close)`, `span =
  stretch_ema_span` (30). Baseline key `stretch[SYMBOL]`.

## 2. Positioning-stress score

```
S = w_fng·z(FearGreed) + w_funding·z(funding) + w_stretch·z(price_stretch)
```

Weights from `composite.weights` (tuned on the training split only, frozen out-of-sample). If an
input is unavailable, drop its term and renormalize the remaining weights to sum to 1.

Reading bands: `|S|<0.5` neutral · `0.5–1.5` frothy(+)/fearful(−) · `>1.5` euphoric(+)/capitulation(−).

## 3. Regime filter R

- **Kaufman Efficiency Ratio** over `er_window` (20): `ER = |close_t − close_{t−n}| /
  Σ|close_i − close_{i−1}|`, in [0,1]. `ER > er_threshold` (0.30) ⇒ **TREND**, else **RANGE**.
- **Macro filter (bull/bear):** `close > EMA(macro_ema=50)` ⇒ bull, else bear.
- **Live:** prefer `detect_market_regime` → `market_regime` for an attributable label
  (`trend_expansion`→TREND; `range_chop`/`mixed_transition`→RANGE; `overheated_longs`/
  `liquidation_stress` = stress states that reinforce a froth/fear `S`).

## 4. Position from (S, R)

```
froth_pos = max(tanh(S/s_scale), 0)      # only froth trims longs
fear      = max(−tanh(S/s_scale), 0)

if bull:
    if TREND: raw = 1 − trend_froth_haircut·froth_pos          # ride, trim froth
    else:     raw = clip(range_long_base − range_tilt·tanh(S/s_scale), 0, 1)   # fade froth / buy fear
else:  # bear
    if TREND: raw = −short_bear·froth_pos                      # step aside, light froth short
    else:     raw = clip(dip_bear·fear − short_bear·froth_pos, −range_short_cap, range_short_cap)
```

## 5. Vol targeting, caps, risk

```
scalar    = min(target_daily_vol / realized_vol, 1.0)         # de-risk only; never levers up
position  = clip(raw · scalar, −max_position, +max_position)
```

- `target_daily_vol = target_vol_annual / sqrt(365)`.
- Drawdown guard: halve the position while the sleeve drawdown is worse than `drawdown_guard`.
- Costs: charge `cost_bps_one_way` on `|Δposition|` each rebalance.
- No look-ahead: the position decided at the close of day *t* is applied to day *t+1*'s return.

All constants: `strategy-params.json → decision_rules`.
