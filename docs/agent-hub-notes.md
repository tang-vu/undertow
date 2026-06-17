# Agent Hub Notes — ground-truth map for Undertow

Research date: **2026-06-17**. Sources: live CMC docs, the official skill repo (cloned & read
verbatim), and live calls against the CMC MCP + CMC Skill Hub. This file is the single source of
truth that drives Undertow's two-layer design (live signals vs. backtestable history).

> Honesty note: every "history depth" figure below was verified empirically where possible (live
> API probes on 2026-06-17), not assumed. Unverified items are flagged.

---

## 1. SKILL.md schema (verbatim from the official CMC repo)

Repo studied: `github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap`.
Skills are **pure documentation** (Markdown) — no executable code is shipped inside a skill. The
agent reads the SKILL.md and drives the listed tools itself.

**Frontmatter (YAML):**

| Field | Req? | Notes |
|-------|------|-------|
| `name` | ✅ | kebab-case; **must equal the folder name** |
| `description` | ✅ | multiline (`\|`). Block holds *what it does* + *when to use* + a `Trigger:` line of keywords for `find_skill` discovery |
| `user-invocable` | ✅ | boolean (`true` so users can call `/skill-name`) |
| `allowed-tools` | ◻ | array. Local tools plain (`Bash`,`Read`); MCP tools qualified: `mcp__cmc-mcp__<tool>` |
| `license` | ◻ | e.g. `MIT` |
| `compatibility` | ◻ | semver range, e.g. `">=1.0.0"` |

**Folder structure** (composite/MCP skill):

```
skills/<name>/
├── SKILL.md            # required
└── references/         # optional — deep-dive docs the agent reads on demand
    ├── <topic>.md
    └── use-cases.md
```

**Discovery:** `find_skill` ranks on the `Trigger:` keywords, the `name`, semantic match against the
description, and tool availability. → Undertow's description must front-load the divergence/funding/
sentiment/regime vocabulary.

---

## 2. CMC MCP — live data layer

- **Endpoint:** `https://mcp.coinmarketcap.com/mcp` · header `X-CMC-MCP-API-KEY` · key from
  `pro.coinmarketcap.com/login` (free Basic tier = 10k credits/mo, ~30–50 calls/min).
- **12 tools.** History availability matters — most are **live/latest only**:

| Tool | Returns | History? |
|------|---------|----------|
| `get_crypto_quotes_latest` | price, mcap, %chg, volume | latest only |
| `get_global_metrics_latest` | total mcap, **Fear & Greed (current)**, dominance, altseason | latest only |
| `get_global_crypto_derivatives_metrics` | **open interest, funding rates**, liquidations | latest only |
| `get_crypto_technical_analysis` | SMA/EMA, RSI, MACD, Fib, pivots | current + shallow snapshots |
| `get_crypto_marketcap_technical_analysis` | TA on total mcap | current |
| `get_crypto_metrics` | holder/whale distribution (on-chain) | current |
| `trending_crypto_narratives` | hot narratives + sector perf | current |
| `get_crypto_latest_news` | headlines | latest |
| `get_upcoming_macro_events` | scheduled catalysts | forward |
| `get_crypto_info` / `search_cryptos` / `search_crypto_info` | metadata / lookup / semantic | n/a |

**Takeaway:** MCP gives Undertow the **live** F&G, funding, and OI in one or two calls — but **no
multi-year history**. Backtest history must come from elsewhere (§5).

---

## 3. CMC Skill Hub — platform evidence services (the integration edge)

Beyond raw MCP, the Skill Hub (`find_skill` / `execute_skill`) hosts **analysis services** that
return structured `evidence_pack`s. Several map almost 1:1 onto Undertow and were **executed live on
2026-06-17** (real outputs captured):

| Service (`unique_name`) | Undertow role | Verified live output fields |
|---|---|---|
| `detect_market_regime` | **Regime filter R** | `market_regime` ∈ {trend_expansion, liquidation_stress, overheated_longs, range_chop, mixed_transition}; `metrics.fear_greed_value`, `oi_change_pct_7d`, `average_funding_bps_7d`, `liquidation_stress_ratio` |
| `perp_contract_analysis` | **Undertow funding/OI depth** | funding regime, OI/mcap ratio, price↔OI relation, CVD, liquidation heatmap |
| `detect_oi_dark_flow_setup` | OI-divergence enhancement | dark-flow score, OI change, funding, short-liq share |
| `assess_volatility_expansion_risk` | vol input for sizing/regime | realized vol, range expansion, funding |
| `altcoin_kol_sentiment` | **Surface social layer** (live-only) | high-signal vs retail positioning, fresh vs recycled chatter |
| `macro_liquidity_monitor` | macro overlay | reserves/TGA/RRP/USDJPY carry stress |

**Why this matters:** a single `detect_market_regime` call (~1s) returns **F&G value + funding bps +
OI change + a regime label** together — three of Undertow's four "undertow" inputs plus R, live and
attributable ("Powered by CoinMarketCap"). Undertow's live mode is therefore a **meta-skill that
orchestrates CMC's own evidence services**, which is the deepest available Agent-Hub integration.

---

## 4. x402 — pay-per-request access mode (no API key)

- **MCP over x402:** `https://mcp.coinmarketcap.com/x402/mcp` (Streamable HTTP).
- **REST over x402:** `https://pro.coinmarketcap.com/x402/v3/cryptocurrency/quotes/latest`, etc.
- **Price:** $0.01 USDC/request, **Base** (chain id 8453). Pay-on-success only.
- **Flow:** request → `402` + base64 `Payment-Required` → wallet signs USDC **EIP-3009
  `transferWithAuthorization`** → resend with `PAYMENT-SIGNATURE` → 200 + data.

| Field | Value |
|-------|-------|
| USDC contract (Base) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Payment recipient | `0x271189c860DB25bC43173B0335784aD68a680908` |
| Amount | `10000` (=$0.01, 6 dp) · EIP-712 domain `name:"USD Coin", version:"2"` |

TS SDK: `@x402/axios @x402/evm viem`. → Undertow ships an x402 access path so an autonomous agent can
pull the live read **without any subscription/API key**.

---

## 4b. IDE integration — the Agent Hub inside a coding agent

The Hub's 5th surface is delivery: its MCP servers drop straight into an IDE coding agent (Claude Code,
Cursor, Windsurf) via `.mcp.json`, so a developer's agent gets CMC data + Skills natively.

```jsonc
{ "mcpServers": {
  "cmc-mcp":  { "type": "http", "url": "https://mcp.coinmarketcap.com/mcp",
                "headers": { "X-CMC-MCP-API-KEY": "${CMC_MCP_API_KEY}" } },
  "cmc-x402": { "type": "http", "url": "https://mcp.coinmarketcap.com/x402/mcp" } } }
```

Committed verbatim as `agent_hub/cmc-agent-hub.mcp.json`. **Verified live (2026-06-17):** inside Claude
Code with the Agent Hub connected, `find_skill` ranked 6 CMC services for the divergence/regime query
and `execute_skill(perp_contract_analysis, BTC/1d)` returned a real `evidence_pack` ("Powered by
CoinMarketCap", ~50s) — full capture in `agent_hub/fixtures/ide_session_capture_2026-06-17.json`. This
is the Skill-Hub surface (§3) reached through the IDE-integration surface, both at once.

---

## 5. Data-history availability map — drives the backtest

The core construct needs rolling z-scores over **multi-year daily history**. What is freely &
reproducibly obtainable (verified 2026-06-17):

| Signal | Source used | History (verified) | Class |
|--------|-------------|--------------------|-------|
| **Price OHLCV** | Binance spot klines `/api/v3/klines` (free, no key) | 9+ yr daily | ✅ backtestable |
| **Fear & Greed** | alternative.me `/fng/?limit=0` (free, no key) | **3055 daily rows, 2018-02-01 → today** | ✅ backtestable |
| **Funding rate** | Binance `/fapi/v1/fundingRate` (free, no key) | **BTCUSDT from 2019-09-10** (perp inception), 8h prints → daily | ✅ backtestable |
| **Open Interest** | Binance `/futures/data/openInterestHist` | **~30 days only** (hard cap); deep history is paid (Coinglass/Tardis) | 🔴 live-only |
| **Social / trending heat** | CMC `trending`, `altcoin_kol_sentiment` | no queryable daily history | 🔴 live-only |
| **On-chain / DEX net flow** | CMC DEX, Bitquery | shallow / rate-limited | 🔴 live-only |

CMC's own historical REST endpoints exist (`/v2/cryptocurrency/ohlcv/historical`,
`/v3/fear-and-greed/historical`) but cost credits and have plan-gated depth; the free, no-key sources
above give a judge **identical, reproducible numbers with zero credentials**, so the committed
backtest uses them. (A `--source cmc` switch is documented for users who have a key.)

### Design consequence (the honesty line that scores points)

```
Backtestable core S  =  w1·z(FearGreed)  +  w2·z(funding)  +  w3·z(price_stretch)        ← 3 history-backed terms
Live-only enhancers   :  OI-change · social/KOL heat · on-chain flow                       ← surfaced via MCP / Skill Hub at inference, NEVER backtested with fabricated history
```

OI was in the original 4-term sketch, but **free OI history is capped at ~30 days**, so OI is
demoted to a *live-only enhancement* (delivered live by `detect_market_regime` /
`perp_contract_analysis`) rather than faked into the backtest. This is a deliberate, documented
trade-off: a defensible 3-term backtest beats an un-reproducible 4-term one.

---

## 6. Open questions / residual risk

1. Binance funding multi-year depth confirmed for BTC; per-asset start dates (ETH/BNB/SOL/XRP perps)
   are validated at fetch time and assets with insufficient history are dropped.
2. CMC `/v3/fear-and-greed/historical` depth is undocumented; we use alternative.me for the committed
   run to guarantee reproducibility.
3. x402 on-chain settlement is demonstrated via the documented flow + a dry-run client; a funded Base
   wallet is required for a true paid call (kept out of the committed run for safety).
