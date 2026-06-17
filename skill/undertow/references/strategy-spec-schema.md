# Strategy-spec output contract

The skill's deliverable is one JSON object. Field-by-field:

| Path | Type | Meaning |
|------|------|---------|
| `skill` | string | always `"undertow"` |
| `as_of` | ISO-8601 | UTC timestamp of the read |
| `token` / `timeframe` | string | resolved symbol; horizon (`1d`/`7d`/`30d`/`90d`) |
| `regime.label` | enum | `TREND` \| `RANGE` |
| `regime.macro_trend` | enum | `bull` \| `bear` (close vs macro EMA) |
| `regime.skill_hub_regime` | string | raw label from `detect_market_regime` (or `unavailable`) |
| `regime.efficiency_ratio` | number | Kaufman ER in [0,1] (if computed) |
| `stress.S` | number | composite positioning-stress score (signed) |
| `stress.reading` | enum | `neutral`/`frothy`/`euphoric`/`fearful`/`capitulation` |
| `stress.components` | object | `z_fng`, `z_funding`, `z_stretch` (the z-scored inputs) |
| `stress.weights` | object | weights actually used (after any renormalization) |
| `stress.surface` | object | `fear_greed` (0–100); `social_kol` (live-only, optional) |
| `stress.undertow` | object | `funding_bps_7d`, `oi_change_pct_7d` (live; OI is enhancement) |
| `decision.stance` | enum | `long` \| `reduce` \| `flat` \| `short` |
| `decision.target_position` | number | fraction of capital in [−1, 1] (negative = short) |
| `decision.entry` / `exit` | string | human-readable trigger conditions |
| `decision.risk` | object | `max_position`, `vol_target_annual`, `drawdown_guard`, `cost_bps_one_way` |
| `enhancements_live_only` | object | `social_kol`, `oi_dark_flow`, `on_chain` — flagged not-backtested |
| `backtest_provenance` | object | pointer to `strategy-params.json → backtest_headline` |
| `disclaimer` | string | research artifact, not investment advice |

### Mapping stance ⇄ target_position
- `long`  : target_position ≥ +0.5
- `reduce`: 0 < target_position < 0.5 (trimmed in froth)
- `flat`  : target_position ≈ 0 (stepped aside)
- `short` : target_position < 0 (only bear-regime froth)

### Invariants
- `|target_position| ≤ max_position` (≤ 1.0 — never levered).
- If any backtested-core input is missing, its z-term is dropped and `stress.weights` reflects the
  renormalized set.
- `enhancements_live_only` values must never enter `stress.S` (they have no backtested history).
