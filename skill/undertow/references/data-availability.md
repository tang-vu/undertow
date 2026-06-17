# Data availability — backtestable vs live-only

Verified 2026-06-17. This split is load-bearing: the **core backtest runs only on signals with real
multi-year history**; everything else is a live-only *enhancement*, never given fabricated history.

| Signal | Used for | History (verified) | Source |
|--------|----------|--------------------|--------|
| Price OHLCV | core | 9+ yr daily | Binance spot klines (free, no key) |
| Fear & Greed | core | daily since 2018-02-01 | alternative.me (free); CMC `get_global_metrics_latest` live |
| Perp funding | core | since 2019-09-10 (BTC) | Binance `/fapi/v1/fundingRate` (free); CMC derivatives live |
| Open interest | **enhancement** | free history ~30 days only | CMC `get_global_crypto_derivatives_metrics` / `perp_contract_analysis` (live) |
| Social / KOL heat | **enhancement** | no queryable daily history | `altcoin_kol_sentiment`, `trending_crypto_narratives` (live) |
| On-chain / DEX flow | **enhancement** | shallow / rate-limited | CMC DEX, Bitquery (live) |

## Rules

1. The composite `S` in the backtest uses **only** Fear & Greed + funding + price stretch.
2. Open-interest change, social/KOL heat, and on-chain flow are returned in the spec's
   `enhancements_live_only` block, clearly labelled, and **never** folded into the backtested `S`.
3. Never fabricate history for an enhancement to make it "backtestable".
4. Live mode may still *display* enhancements (e.g., `oi_change_pct_7d` from `detect_market_regime`)
   as confirming/contradicting context for a human — as long as the provenance is honest.

See the repo's `docs/agent-hub-notes.md` for the full ground-truth map and `backtest/` for the
reproducible harness.
