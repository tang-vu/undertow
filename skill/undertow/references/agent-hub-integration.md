# Agent Hub integration — MCP, x402, and Skill-Hub orchestration

Undertow is built to sit *natively* inside the CoinMarketCap AI Agent Hub. It touches every surface
of the Hub, and each one is wired for real (verified live 2026-06-17), not just described.

## 1. Three access modes for the live read

| Mode | Endpoint | Auth | When |
|------|----------|------|------|
| **MCP (keyed)** | `https://mcp.coinmarketcap.com/mcp` | `X-CMC-MCP-API-KEY` | normal agent use |
| **x402 (pay-per-request)** | `https://mcp.coinmarketcap.com/x402/mcp` | none — $0.01 USDC/call on Base | keyless / autonomous agents |
| **Skill Hub (evidence services)** | `find_skill` / `execute_skill` | per Hub | richer regime / positioning reads |

Repo scripts (`agent_hub/`) implement all three:
- `mcp_client.py` — dependency-light MCP-over-HTTP client (initialize / tools/list / tools/call).
- `undertow_live.py` — emits the strategy spec from a live read (`--mcp`) or a committed real snapshot (`--demo`).
- `x402_demo.py` — connects over x402 and triggers the real 402 payment challenge.

## 2. Tools Undertow orchestrates

**Raw MCP (the 12-tool `cmc-mcp` server):**
- `search_cryptos` — resolve the token.
- `get_global_metrics_latest` — live Fear & Greed (surface layer).
- `get_global_crypto_derivatives_metrics` — live funding + open interest (undertow layer).
- `get_crypto_quotes_latest`, `get_crypto_technical_analysis` — price + EMAs for price-stretch.
- `trending_crypto_narratives` — social/narrative heat (live-only enhancement).

**CMC Skill Hub evidence services (the integration edge):** Undertow does not re-derive what the Hub
already computes — it *composes* it.
- `detect_market_regime` → the regime label R **and** live `fear_greed_value`, `average_funding_bps_7d`,
  `oi_change_pct_7d` in one ~1s call.
- `perp_contract_analysis` → per-token funding regime, OI/mcap, CVD, liquidation heatmap.
- `assess_volatility_expansion_risk` → realized-vol context for sizing.
- `altcoin_kol_sentiment` → KOL/social positioning (surface enhancement, live-only).

This makes Undertow a **meta-skill**: an authored Skill that orchestrates the platform's own hosted
services into a single decision — the deepest form of Agent-Hub integration.

## 3. find_skill discoverability

Two directions:
- **Undertow is discoverable.** The frontmatter `description` front-loads the matching vocabulary
  (positioning stress, funding vs sentiment, fade the crowd, regime strategy) and an explicit
  `Trigger:` keyword line, exactly the fields `find_skill` ranks on.
- **Undertow discovers.** At runtime it calls `find_skill` to locate the best live evidence service
  for the current token/intent (e.g. regime → `detect_market_regime`, funding depth →
  `perp_contract_analysis`), then `execute_skill` to run it. The repo includes a real captured
  response in `agent_hub/fixtures/detect_market_regime_30d.json`.

## 4. Verified-live evidence (2026-06-17)

- x402 MCP handshake (no key): `initialize` → `{"serverInfo":{"name":"cmc-mcp-service"}}`, `tools/list`
  → 12 tools. (Reproduce: `python agent_hub/mcp_client.py`.)
- x402 tool call without payment → **HTTP 402**: `{"resource":"X402_get_crypto_quotes_latest",
  "error":"Provide PAYMENT-SIGNATURE header to pay and retry."}`. (Reproduce: `python agent_hub/x402_demo.py`.)
- Plain MCP without key → rejected (`"error: Token not found"`), confirming the key requirement.
- `execute_skill(detect_market_regime)` → live evidence pack with regime + F&G + funding + OI.

## 5. x402 settlement parameters (Base)

| Field | Value |
|-------|-------|
| network | Base, chain id 8453 (`eip155:8453`) |
| asset / contract | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| pay to | `0x271189c860DB25bC43173B0335784aD68a680908` |
| amount | `10000` = $0.01 (6 dp) · EIP-3009 `transferWithAuthorization` · domain `{name:"USD Coin",version:"2"}` |

Pay-on-success only; a failed call costs nothing. TS SDK path: `@x402/axios @x402/evm viem`.
