# Undertow — DoraHacks submission

**Track 2 (Strategy Skills)** · also targeting **Best Use of Agent Hub**
**Tagline:** *Trade the gap between what the crowd feels and how it's positioned.*

---

## ⎘ COPY-PASTE FOR DORAHACKS (fill the form with these)

**Project name:** `Undertow`

**One-liner:** `An LLM Strategy Skill that trades the divergence between surface crypto sentiment (Fear & Greed) and sub-surface positioning (perp funding, open interest, price stretch), conditioned on market regime — emitting a backtested, agent-ready strategy spec wired live to the CoinMarketCap Agent Hub.`

**Track / prize:** `Track 2 — Strategy Skills` + special prize `Best Use of Agent Hub`

**Short description (summary field):**
```
Undertow reads two layers of the market — what the crowd FEELS (CMC Fear & Greed, social heat) versus
how it is POSITIONED (perp funding extremity, open-interest change, price stretch from trend) — and
switches strategy by regime (trend vs range). It is authored as a CoinMarketCap SKILL.md and emits a
structured, agent-ready strategy spec: regime label, a positioning-stress score S, entry/exit/sizing
rules, and risk parameters.

The walk-forward backtest (BTC/ETH/BNB/SOL/XRP, daily, 2019–2026, trading costs + slippage modeled,
weights tuned on the train split only) delivers Bitcoin-like total return with LESS THAN HALF the
max drawdown (−33% vs −77%) and ~1.8× the Sharpe over the full cycle (1.34 vs 0.76), and beats a
naive Fear & Greed contrarian outright. We report the result honestly, including where buy-and-hold
edges out on raw return in a post-cycle-top window.

It is agent-native and exercises ALL FOUR CoinMarketCap Agent Hub surfaces: live data over MCP,
keyless pay-per-request over x402 (verified real HTTP 402 challenge), the official CMC CLI (installed
& run), and orchestration of CMC's own Skill Hub services (detect_market_regime,
perp_contract_analysis) via find_skill — the deepest available Agent-Hub integration.
```

**Links to paste:**
- Code repo: `https://github.com/tang-vu/undertow`
- Demo video: `<YouTube/Loom link — see below>`
- Live demo page (in repo): `demo/index.html`

**Tags:** `trading-strategy` `coinmarketcap` `agent-hub` `mcp` `x402` `backtest` `crypto` `llm-skill` `regime-switching`

---

## ⎘ YOUTUBE — title & description

**Title:** `Undertow — a CoinMarketCap Agent Skill that trades sentiment vs positioning`

**Description:**
```
Undertow is an LLM Strategy Skill for the CoinMarketCap AI Agent Hub. It trades the divergence
between what the crowd FEELS (Fear & Greed, social heat) and how it is POSITIONED (perp funding,
open interest, price stretch from trend), conditioned on market regime.

Given {token, timeframe} it emits a backtested, agent-ready strategy spec: regime, a positioning-
stress score, entry/exit/sizing, and risk.

Out-of-sample (BTC/ETH/BNB/SOL/XRP, 2019–2026, costs modeled): Bitcoin-like return with less than
half the drawdown, ~1.8× the Sharpe over the full cycle — and it beats a naive Fear & Greed
contrarian outright.

Agent-native across all four CMC Agent Hub surfaces: live data over MCP and the CMC CLI,
pay-per-request over x402 (real HTTP 402 on Base), and orchestration of CoinMarketCap's own Skill
Hub services via find_skill.

Code: https://github.com/tang-vu/undertow
Built for the BNB × CoinMarketCap × Trust Wallet Hackathon — Track 2 + Best Use of Agent Hub.
Research artifact, not investment advice.

0:00 Thesis — surface sentiment vs the undertow
0:23 The Skill — live stress + regime → strategy spec
0:36 Out-of-sample edge — half the drawdown
0:58 Agent Hub — MCP · x402 · CLI · Skills
```

---

## Problem

Retail crypto reacts to **surface sentiment** — Fear & Greed, trending narratives, social hype — but
the moves that hurt build **underneath**: crowded perp leverage, rising open interest, price stretched
far from trend. Most "strategy" skills are indicator mashups that re-skin RSI/MACD. None reads the
*divergence* between surface mood and sub-surface positioning, and none adapts that read to whether
the market is trending or ranging.

## Solution

**Undertow** is an LLM Skill (in CoinMarketCap's official SKILL.md format) that:
1. Pulls two layers of signal from the CMC Agent Hub — **surface** (Fear & Greed, social/KOL) and
   **undertow** (funding extremity, open-interest change, price stretch).
2. Compresses them into a single **positioning-stress score `S`** (causal z-scores; `S>0` = froth,
   `S<0` = capitulation).
3. Classifies the **regime `R`** (TREND vs RANGE + bull/bear) — live, via the Skill Hub's
   `detect_market_regime`.
4. Applies **regime-switching logic** — fade froth in ranges, ride trends, step aside in down-trends,
   buy capitulation on dips — with vol-targeted, no-leverage sizing and modeled costs.
5. Emits a structured, agent-ready **strategy spec (JSON)**: regime, stress reading, entry/exit/sizing,
   risk params, and the out-of-sample backtest provenance behind the rules.

## Why it's original

It's a *meta-strategy* on **positioning vs sentiment divergence, conditioned on regime** — not an
indicator mashup. And it's a *meta-skill*: it **orchestrates CMC's own hosted Skill-Hub services**
(`detect_market_regime`, `perp_contract_analysis`, `assess_volatility_expansion_risk`,
`altcoin_kol_sentiment`) rather than only calling raw data endpoints.

## Results (reproducible, OOS, costs modeled)

BTC/ETH/BNB/SOL/XRP daily 2019→2026; weights tuned on train only; walk-forward = strict OOS.

- **Full cycle:** ~the same total return as BTC (**+533% vs +550%**) with **less than half the
  drawdown (−33% vs −77%)**, **~1.8× the Sharpe (1.34 vs 0.76)**, **>2× the Calmar (0.94 vs 0.42)**.
- **Walk-forward OOS (2021 top → 2026):** halves drawdown vs buy-and-hold, **wins on Calmar**, and
  **beats the naive Fear & Greed contrarian on every metric** (which loses −53%).
- **Honest caveat:** over the post-cycle-top window Undertow trails buy-and-hold on *raw* Sharpe/return
  (avoiding the −77% crash also forgoes the cheapest V-recovery re-entry). The win is risk-adjusted —
  comparable return, far less pain, and survivability. We report it straight.

## Best Use of Agent Hub (all four surfaces, verified live 2026-06-17)

- **MCP:** real Streamable-HTTP / JSON-RPC client (`agent_hub/mcp_client.py`) — live 12-tool handshake.
- **x402:** keyless connect to `…/x402/mcp`; `agent_hub/x402_demo.py` triggers a **real HTTP 402**
  challenge and prints the EIP-3009 USDC-on-Base settlement params ($0.01/call).
- **CMC CLI:** official `cmc` v0.1.0 installed & run; `agent_hub/cmc_cli_demo.sh` previews the exact
  global-metrics / historical / derivatives endpoints (keyless `--dry-run`) — terminal-native access.
- **Skill Hub:** `find_skill` → `execute_skill` orchestration of CMC's evidence services; a real
  captured response ships in `agent_hub/fixtures/`.
- **Authored Skill:** `skill/undertow/SKILL.md` in CMC's exact format, `find_skill`-discoverable.

→ MCP + x402 + CLI + Skills (authored *and* orchestrated): the full Agent Hub, each wired for real.

## Tech

Python backtest (pandas/numpy/matplotlib), no-key data (Binance, alternative.me) for reproducibility,
self-contained HTML demo (inline SVG, no deps), dependency-light MCP client (`requests`).

## Reproduce

```bash
cd backtest && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python run_backtest.py            # identical numbers from the committed snapshot
python ../agent_hub/undertow_live.py --demo --token BTCUSDT   # emits the strategy spec, no creds
python ../agent_hub/x402_demo.py                # real x402 402-challenge
```
Open `demo/index.html` in any browser.

## What we did NOT do (honesty)

No fabricated history for live-only fields (OI/social/on-chain are flagged enhancements, excluded from
the backtested core). No look-ahead (causal z-scores, train-only tuning, shifted positions). No
leverage. No cherry-picked window. No 400% overfit curve.

## Links

- Repo: https://github.com/tang-vu/undertow
- Demo video: `video/undertow_demo.mp4` (84s, narrated) — *upload to YouTube/Loom and paste the link here*
- Live demo page: `demo/index.html`

---

## 60–90s demo video script

| t | shot | line |
|---|---|---|
| 0–15s | stress dial flips euphoric while a funding gauge stays crowded | "Crypto sentiment screams on the surface. The risk builds underneath. Undertow trades that gap." |
| 15–35s | drop `skill/undertow` into a CMC Skills dir; ask *"undertow read on BTC"*; show the JSON spec | "It's a Skill in CMC's format. Ask it, and it emits a full strategy spec — regime, stress, stance, risk." |
| 35–55s | equity chart (same return, half drawdown) + walk-forward table + annotated 2021-top / COVID divergences | "Backtested out-of-sample, costs modeled: Bitcoin's return with half the drawdown — and it laps the naive contrarian." |
| 55–75s | run `x402_demo.py` (real 402) and `detect_market_regime` via the Skill Hub | "It's agent-native: pays per call over x402, and orchestrates CMC's own Skill-Hub services." |
| 75–90s | logo + repo link | "Reproducible. Honest. Agent-native. Undertow." |

*Research/competition artifact, not investment advice.*
