---
name: undertow
description: |
  Reads the divergence between SURFACE crowd sentiment (Fear & Greed, social heat) and the
  POSITIONING FORCES beneath it (perp funding extremity, open-interest change, price stretch from
  trend), conditioned on market regime, and emits a backtestable, agent-ready trading strategy spec
  for a token. Use when a user wants a regime-aware entry/exit/sizing plan, a "is the crowd offside"
  read, a positioning-stress or funding-vs-sentiment divergence check, or a structured strategy spec
  rather than a raw price quote.
  Trigger: "undertow", "positioning stress", "is the crowd offside", "funding vs sentiment",
  "fade the crowd", "regime strategy for [coin]", "stress score for [coin]", "should I fade greed on
  [coin]", "crowded longs [coin]", "/undertow"
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - Read
  - mcp__cmc-mcp__search_cryptos
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__trending_crypto_narratives
  - mcp__cmc-skill-hub__find_skill
  - mcp__cmc-skill-hub__execute_skill
---

# Undertow — positioning-stress strategy spec

**Thesis:** the edge is the gap between what the crowd *feels* (surface sentiment) and how it is
*positioned* (the undertow beneath), read through the lens of the current market regime. When the
surface is euphoric while leverage is crowded and price is stretched, the tide is set to pull the
other way — and the right response depends on whether the market is trending or ranging.

This skill turns `{token, timeframe}` into a **structured, backtestable strategy spec** (JSON):
regime label, a positioning-stress reading, an entry/exit/sizing plan, risk parameters, and the
out-of-sample backtest provenance behind the rules.

## Prerequisites

Two MCP connections. Verify both are reachable; if a tool errors, ask the user to configure it.

```json
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": { "X-CMC-MCP-API-KEY": "your-api-key" }
    },
    "cmc-skill-hub": {
      "url": "https://mcp.coinmarketcap.com/mcp"
    }
  }
}
```

Get an API key from https://pro.coinmarketcap.com/login. No-API-key access is possible via the x402
path (`https://mcp.coinmarketcap.com/x402/mcp`, $0.01 USDC/request on Base) — see
`references/agent-hub-integration.md`.

First, **`Read` the file `references/strategy-params.json`** — it holds the frozen weights, the
z-score normalization baselines, the regime thresholds, and the decision constants, all derived from
the out-of-sample backtest. Every number the skill uses comes from there.

## The signal model

Two layers, then a regime switch.

**Surface (what the crowd feels):**
- CMC Fear & Greed Index — multi-year daily history → part of the backtested core.
- Social / KOL narrative heat — live-only → a labelled *enhancement*, never backtested.

**Undertow (how the crowd is positioned):**
- Perp **funding** extremity — crowded leverage. Backtested core.
- Price **stretch** from trend (z-score of price vs its EMA). Backtested core.
- **Open-interest** change — live-only enhancement (free OI history is ~30 days; see data honesty).

**Positioning-stress score `S`** (causal z-scores; sign convention: `S > 0` = froth/greed/crowded
long, `S < 0` = capitulation/fear):

```
S = w_fng·z(FearGreed) + w_funding·z(funding) + w_stretch·z(price_stretch)
```

Weights were tuned on the training split only and frozen for the out-of-sample test (see
`strategy-params.json → composite.weights`).

**Regime `R`:** TREND vs RANGE from the Kaufman efficiency ratio, plus a causal macro filter
(`close` vs the macro EMA) for bull/bear. The CMC Skill Hub service `detect_market_regime`
provides a live, attributable regime label and the live funding / OI / Fear-&-Greed metrics in one
call — use it as the primary live source for `R` and the undertow inputs.

## Workflow

### Step 1 — Resolve the token
Call `search_cryptos` with the name/symbol to get the CMC id, name, symbol.

### Step 2 — Pull the live regime + undertow (one call)
Call `execute_skill` with `unique_name: "detect_market_regime"` (`time_window` matched to the user's
horizon: `1d`/`7d`/`30d`/`90d`). Read from its evidence pack:
- `report.market_regime` → map to TREND (`trend_expansion`) vs RANGE (`range_chop`,
  `mixed_transition`) vs stress states (`overheated_longs`, `liquidation_stress`).
- `report.metrics.fear_greed_value`, `average_funding_bps_7d`, `oi_change_pct_7d`.

For a per-token funding/OI deep read, also call `execute_skill` →
`unique_name: "perp_contract_analysis"` (`symbol`, `timeframe`). For vol context call
`assess_volatility_expansion_risk`.

### Step 3 — Pull the surface
- Fear & Greed (market-wide): from Step 2's `fear_greed_value`, or `get_global_metrics_latest`.
- Price & stretch inputs: `get_crypto_quotes_latest` (price) and `get_crypto_technical_analysis`
  (EMAs) for the price-vs-EMA stretch.
- Social heat (enhancement, label as live-only): `execute_skill` →
  `unique_name: "altcoin_kol_sentiment"` (`symbol`), or `trending_crypto_narratives`.

### Step 4 — Compute S
For each live input `x`, z-score it against the snapshot baseline in `strategy-params.json`:
`z = (x − baseline.mean) / baseline.std`. Use `fng_market` for Fear & Greed, and the per-asset
`funding` / `stretch` baselines. Combine with the frozen weights to get `S`. Classify the reading:
`|S|<0.5` neutral · `0.5–1.5` frothy/fearful · `>1.5` euphoric/capitulation (sign gives direction).

### Step 5 — Apply the decision logic (regime switch)
See the table below. Produce a target position, an entry/exit, and risk parameters.

### Step 6 — Emit the strategy spec
Return the JSON in **Output schema** below. That JSON *is* the deliverable.

## Decision logic

| Regime (R) | Stress (S) | Action | Sizing |
|------------|-----------|--------|--------|
| **RANGE** + bull | euphoric (S≫0) | **fade**: trim longs toward flat | size ↓ as S↑ |
| **RANGE** + bull | fearful (S≪0) | **add**: buy the dip toward full long | size ∝ \|S\|, ÷ vol |
| **RANGE** + bear | euphoric | light defensive short (capped) | small |
| **RANGE** + bear | fearful | **flat** (no knife-catching) | 0 |
| **TREND** + bull | any | **ride** the trend long; trim only at froth extremes | vol-targeted ~full |
| **TREND** + bear | any | **step aside** (flat); light froth short only | small |

- **Sizing:** position ∝ signal strength and **inverse to realized volatility** (vol targeting toward
  `target_vol_annual`); the vol scalar is capped at 1.0 → **never levered**.
- **Risk:** hard `max_position` cap; a drawdown guard halves exposure past `drawdown_guard`; the
  backtest charges `cost_bps_one_way` of turnover (fees + slippage).

## Output schema

```json
{
  "skill": "undertow",
  "as_of": "<ISO-8601 UTC>",
  "token": "BTC", "timeframe": "1d",
  "regime": { "label": "RANGE|TREND", "macro_trend": "bull|bear",
              "skill_hub_regime": "range_chop", "efficiency_ratio": 0.36 },
  "stress": {
    "S": -0.13,
    "reading": "neutral|frothy|euphoric|fearful|capitulation",
    "components": { "z_fng": -0.06, "z_funding": -0.20, "z_stretch": -0.58 },
    "weights": { "w_fng": 0.5, "w_funding": 0.5, "w_stretch": 0.0 },
    "surface": { "fear_greed": 23, "social_kol": "<live-only, optional>" },
    "undertow": { "funding_bps_7d": 22.4, "oi_change_pct_7d": 8.1 }
  },
  "decision": {
    "stance": "long|reduce|flat|short",
    "target_position": 0.0,
    "entry": "<condition>", "exit": "<condition>",
    "risk": { "max_position": 1.0, "vol_target_annual": 1.0,
              "drawdown_guard": 0.28, "cost_bps_one_way": 10 }
  },
  "enhancements_live_only": { "social_kol": "...", "oi_dark_flow": "...", "on_chain": "..." },
  "backtest_provenance": { "see": "references/strategy-params.json → backtest_headline" },
  "disclaimer": "Research artifact, not investment advice."
}
```

## Backtest provenance (be honest)

The rules above are not hand-waved — they come from a reproducible walk-forward backtest on BTC/ETH/
BNB/SOL/XRP daily data (2019–2026), costs + slippage modeled, weights tuned on train only. Headline
numbers live in `strategy-params.json → backtest_headline`. Honest summary: over the full cycle
Undertow's Sharpe beats BTC buy-and-hold and it more than **halves max drawdown**; it decisively
beats a naive Fear-&-Greed contrarian; over a post-cycle-top window it trades some raw return for far
lower drawdown (higher Calmar). State this plainly — do not overclaim.

## Data honesty

- **Backtested core** (multi-year history): Fear & Greed, funding, price stretch.
- **Live-only enhancements** (no reliable free history → never backtested, always labelled): social /
  KOL heat, open-interest change, on-chain / DEX flow. Surface them in `enhancements_live_only`.
- Never fabricate history for a live-only field. See `references/data-availability.md`.

## Handling tool failures

1. `search_cryptos` fails → cannot resolve token; ask the user to confirm symbol/slug.
2. `detect_market_regime` fails → fall back to `get_global_metrics_latest` (Fear & Greed) +
   `get_global_crypto_derivatives_metrics` (funding/OI) and compute regime from
   `get_crypto_technical_analysis` EMAs; mark `regime.skill_hub_regime: "unavailable"`.
3. Any undertow input missing → drop its term from `S`, renormalize weights, and note it in the spec.
4. Always emit the spec with whatever is available rather than abandoning the request.

## References

- [signal-model.md](references/signal-model.md) — full math for S, the regime filter, and sizing.
- [strategy-spec-schema.md](references/strategy-spec-schema.md) — field-by-field output contract.
- [agent-hub-integration.md](references/agent-hub-integration.md) — MCP, x402, and Skill-Hub orchestration.
- [data-availability.md](references/data-availability.md) — backtestable vs live-only, with sources.
- [strategy-params.json](references/strategy-params.json) — frozen weights, baselines, thresholds, backtest headline.
