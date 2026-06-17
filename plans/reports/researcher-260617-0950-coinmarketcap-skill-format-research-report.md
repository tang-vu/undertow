# CoinMarketCap Skills for AI Agents: Format Specification Research Report

**Status:** DONE  
**Repository:** https://github.com/coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap  
**Clone Location:** C:\Users\tangm\Documents\GitHub\undertow\.research-tmp\skills-for-ai-agents-by-CoinMarketCap

---

## 1. SKILL.md Exact Schema

### Frontmatter Fields (YAML)

**Required Fields:**
- `name` (string, required): Skill identifier in kebab-case (e.g., `cmc-api-crypto`, `crypto-research`)
- `description` (string, required, multiline): Multi-paragraph description with usage guidelines and trigger keywords
- `user-invocable` (boolean, required): Whether skill can be directly invoked by user (`true`/`false`)
- `allowed-tools` (array, required): List of tools the skill is permitted to use

**Optional Fields:**
- `license` (string, optional): License identifier (e.g., `MIT`). Not always present.
- `compatibility` (string, optional): Version compatibility (e.g., `">=1.0.0"`). Only in MCP skills.

### Verbatim Frontmatter Example (from cmc-mcp/SKILL.md)

```yaml
---
name: cmc-mcp
description: |
  Fetches cryptocurrency market data, prices, technical analysis, news, and trends using the CoinMarketCap MCP.
  Use for ANY question involving cryptocurrencies, tokens, or blockchain markets, even if the user doesn't explicitly ask for data. This includes price checks, portfolio questions, market analysis, coin comparisons, holder metrics, technical indicators, and news.
  Trigger: "bitcoin", "ETH", "crypto", "token price", "market cap", "how is [coin] doing", "/cmc-mcp"
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - mcp__cmc-mcp__search_cryptos
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_crypto_info
  - mcp__cmc-mcp__get_crypto_metrics
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__get_crypto_latest_news
  - mcp__cmc-mcp__search_crypto_info
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
  - mcp__cmc-mcp__get_crypto_marketcap_technical_analysis
  - mcp__cmc-mcp__trending_crypto_narratives
  - mcp__cmc-mcp__get_upcoming_macro_events
---
```

### Description Field Guidance

The `description` field contains **3 critical components** (must be in this order):
1. **One-liner**: What the skill does (e.g., "Fetches cryptocurrency market data...")
2. **Usage guidance**: When to use it; include edge cases (e.g., "Use for ANY question involving cryptocurrencies, even if..."). This guides the LLM dispatcher.
3. **Trigger keywords**: Quoted list of strings that activate the skill (prefixed with `Trigger:`). Include both natural language ("bitcoin", "how is [coin] doing") and slash-command style ("/cmc-mcp").

### Allowed-Tools Format

- For **local tools** (Bash, Read): Use plain string name
  ```yaml
  allowed-tools:
    - Bash
    - Read
  ```

- For **MCP tools**: Use fully qualified name with prefix `mcp__<server-name>__<tool-name>`
  ```yaml
  allowed-tools:
    - mcp__cmc-mcp__search_cryptos
    - mcp__cmc-mcp__get_crypto_quotes_latest
  ```

---

## 2. Folder Structure

### Minimal Structure
A skill folder contains **only SKILL.md** (required). Reference docs are optional.

```
skills/
├── cmc-x402/                      # No references (x402 is standalone)
│   └── SKILL.md
├── cmc-api-crypto/                # API reference skills have references/
│   ├── SKILL.md
│   └── references/
│       ├── use-cases.md           # Goal-based endpoint selection guide
│       ├── categories.md          # Detailed endpoint docs
│       ├── listings.md
│       ├── map.md
│       ├── market-pairs.md
│       ├── ohlcv.md
│       ├── price-performance.md
│       ├── quotes.md
│       ├── trending.md
│       └── info.md
└── cmc-mcp/                       # MCP skills may have no references
    └── SKILL.md
```

### Key Patterns

- **SKILL.md is always the entry point** (exactly this filename, case-sensitive)
- **references/** subdirectory is **optional** — used by API skills to document endpoints, but MCP skills omit it
- **No scripts/, assets/, or examples/** directories in any official CoinMarketCap skill
- **No configuration files or package.json** — skills are documentation-driven, not executable packages

---

## 3. Naming Conventions

### Skill Name (in frontmatter)

- **Format:** kebab-case (lowercase, hyphens, no underscores, spaces, or special chars)
- **Length:** 2–20 characters; descriptive but concise
- **Examples:** `cmc-api-crypto`, `cmc-mcp`, `crypto-research`, `market-report`
- **Unique per repo:** Name must be unique within the skill catalog

### Folder Name

- **Must match the `name:` field exactly**
  - Folder: `cmc-api-crypto/` → `name: cmc-api-crypto` ✓
  - Folder: `cmc-api-Crypto/` → name mismatch ✗

---

## 4. How Skills Are Discovered & Executed

### Discovery Mechanism (Inferred from MCP Instructions)

The CMC ecosystem includes MCP servers that expose skill discovery via:
- **find_skill(task/query):** LLM dispatcher queries to match user intent against skill descriptions
  - Matches on trigger keywords in `description` field
  - Matches on skill `name`
  - Semantic matching against usage guidance text
  
- **execute_skill(skill_name, parameters):** Once matched, the skill is invoked with appropriate parameters

### Discoverability Factors

1. **Trigger keywords in description:** Keywords like "bitcoin", "DEX API", "market report" are indexed for pattern matching
2. **Skill name:** Direct reference by `/cmc-api-crypto` or `cmc-api-crypto`
3. **allowed-tools:** Dispatcher checks whether skill has tools needed to answer the query
4. **user-invocable flag:** If `false`, skill is hidden from user-facing discovery (used internally by other skills)

### Execution Model

1. User query arrives
2. Dispatcher calls `find_skill()` to get candidate skills based on:
   - Description match
   - Trigger keyword match
   - Tool availability
3. For **API skills** (cmc-api-*): Agent reads SKILL.md body, constructs API calls per documented workflows
4. For **MCP skills** (cmc-mcp, crypto-research): Agent calls listed MCP tools in `allowed-tools` list
5. Agent formats response per skill's guidance (e.g., "Report Structure" in crypto-research/SKILL.md)

**Key insight:** Skills are **not executable code** — they are **behavioral guides** that instruct the LLM how to use available tools.

---

## 5. Two Verbatim Example SKILL.md Files

### Example 1: cmc-api-crypto/SKILL.md (API Skill with References)

```markdown
---
name: cmc-api-crypto
description: |
  API reference for CoinMarketCap cryptocurrency endpoints including quotes, listings, OHLCV, trending, and categories.
  Use this skill whenever the user mentions CMC API, asks how to get crypto data programmatically, wants to build price integrations, or needs REST endpoint documentation. This is the go-to reference for any CMC cryptocurrency API question.
  Trigger: "CMC API", "coinmarketcap api", "crypto price API", "get bitcoin price via API", "/cmc-api-crypto"
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

# CoinMarketCap Cryptocurrency API

This skill covers the CoinMarketCap Cryptocurrency API endpoints for retrieving price data, market listings, historical quotes, trending coins, and token metadata.

## Authentication

All requests require an API key in the header.

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

Get your API key at: https://pro.coinmarketcap.com/login

## Base URL

```
https://pro-api.coinmarketcap.com
```

## Common Use Cases

See [use-cases.md](references/use-cases.md) for goal-based guidance on which endpoint to use:

1. Get current price of a token
2. Find a token's CMC ID from symbol or name
3. Get a token by contract address
4. Get top 100 coins by market cap
5. Find coins in a price range
6. Get historical price at a specific date
7. Build a price chart (OHLCV data)
8. Find where a coin trades
9. Get all-time high and distance from ATH
10. Find today's biggest gainers
11. Discover newly listed coins
12. Get all tokens in a category (e.g., DeFi)

## API Overview

| Endpoint | Description | Reference |
|----------|-------------|-----------|
| GET /v1/cryptocurrency/categories | List all categories with market metrics | [categories.md](references/categories.md) |
| GET /v1/cryptocurrency/category | Single category details | [categories.md](references/categories.md) |
| GET /v1/cryptocurrency/listings/historical | Historical listings snapshot | [listings.md](references/listings.md) |
| GET /v1/cryptocurrency/listings/latest | Current listings with market data | [listings.md](references/listings.md) |
| GET /v1/cryptocurrency/listings/new | Newly added cryptocurrencies | [listings.md](references/listings.md) |
| GET /v1/cryptocurrency/map | Map names/symbols to CMC IDs | [map.md](references/map.md) |
| GET /v1/cryptocurrency/trending/gainers-losers | Top gainers and losers | [trending.md](references/trending.md) |
| GET /v1/cryptocurrency/trending/latest | Currently trending coins | [trending.md](references/trending.md) |
| GET /v1/cryptocurrency/trending/most-visited | Most visited on CMC | [trending.md](references/trending.md) |
| GET /v2/cryptocurrency/info | Static metadata (logo, description, URLs) | [info.md](references/info.md) |
| GET /v2/cryptocurrency/market-pairs/latest | Trading pairs for a coin | [market-pairs.md](references/market-pairs.md) |
| GET /v2/cryptocurrency/ohlcv/historical | Historical OHLCV candles | [ohlcv.md](references/ohlcv.md) |
| GET /v2/cryptocurrency/ohlcv/latest | Latest OHLCV data | [ohlcv.md](references/ohlcv.md) |
| GET /v2/cryptocurrency/price-performance-stats/latest | Price performance stats | [price-performance.md](references/price-performance.md) |
| GET /v2/cryptocurrency/quotes/latest | Latest price quotes | [quotes.md](references/quotes.md) |
| GET /v3/cryptocurrency/quotes/historical | Historical price quotes | [quotes.md](references/quotes.md) |

## Common Workflows

### Get Token Price by Symbol

1. First, map the symbol to a CMC ID using `/v1/cryptocurrency/map`
2. Then fetch the price using `/v2/cryptocurrency/quotes/latest`

```bash
# Step 1: Get CMC ID for ETH
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map?symbol=ETH" \
  -H "X-CMC_PRO_API_KEY: your-api-key"

# Step 2: Get price quote (using id=1027 for ETH)
curl -X GET "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?id=1027" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Top 100 Coins by Market Cap

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=100&sort=market_cap" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Historical Price Data

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/historical?id=1&time_start=2024-01-01&time_end=2024-01-31&interval=daily" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

### Get Token Metadata

```bash
curl -X GET "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info?id=1,1027" \
  -H "X-CMC_PRO_API_KEY: your-api-key"
```

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 403 | Forbidden (endpoint not available on your plan) |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Rate Limits

Rate limits depend on your subscription plan. The response headers include:

1. `X-CMC_PRO_API_KEY_CREDITS_USED` - Credits used this call
2. `X-CMC_PRO_API_KEY_CREDITS_LEFT` - Credits remaining

### Common Errors

**Invalid ID**: Ensure you use valid CMC IDs from the `/map` endpoint. Symbol lookups may return multiple matches.

**Missing Required Parameter**: Some endpoints require at least one identifier (id, slug, or symbol).

**Plan Restrictions**: Historical endpoints and some features require paid plans. Check your plan limits.

### Error Response Format

```json
{
  "status": {
    "timestamp": "2024-01-15T12:00:00.000Z",
    "error_code": 400,
    "error_message": "Invalid value for 'id'",
    "credit_count": 0
  }
}
```

## Response Format

All responses follow this structure:

```json
{
  "status": {
    "timestamp": "2024-01-15T12:00:00.000Z",
    "error_code": 0,
    "error_message": null,
    "credit_count": 1
  },
  "data": { ... }
}
```

## Reference Files

See the `references/` directory for complete parameter and response documentation for each endpoint.
```

---

### Example 2: crypto-research/SKILL.md (MCP Skill, Complex Workflow)

```markdown
---
name: crypto-research
description: |
  Performs comprehensive due diligence on a cryptocurrency using CoinMarketCap MCP data.
  Use when users ask about a specific coin beyond just its price. This includes questions like "what is [coin]", "is [coin] legit", "analyze [coin]", tokenomics questions, holder distribution, or any request for deep information about a single cryptocurrency.
  Trigger: "research [coin]", "tell me about [coin]", "should I invest in [coin]", "DYOR [coin]", "is [coin] safe", "/crypto-research"
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - mcp__cmc-mcp__search_cryptos
  - mcp__cmc-mcp__get_crypto_quotes_latest
  - mcp__cmc-mcp__get_crypto_info
  - mcp__cmc-mcp__get_crypto_metrics
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__get_crypto_latest_news
  - mcp__cmc-mcp__search_crypto_info
---

# Crypto Research Skill

Perform comprehensive due diligence on any cryptocurrency by systematically gathering and analyzing data from multiple CMC MCP tools.

## Prerequisites

Before starting research, verify the CMC MCP tools are available. If tools fail or return connection errors, ask the user to set up the MCP connection:

```json
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": {
        "X-CMC-MCP-API-KEY": "your-api-key"
      }
    }
  }
}
```

Get your API key from https://pro.coinmarketcap.com/login

## Core Principle

Thorough research requires looking at a token from multiple angles. Fetch all relevant data before forming conclusions. Surface both green flags and red flags.

## Research Workflow

### Step 1: Identify the Token

Call `search_cryptos` with the token name/symbol to get the CMC ID. If multiple results, clarify with the user which one they mean.

### Step 2: Basic Information

Call `get_crypto_info` to get:
- Project description and category
- Launch date
- Website, social links, documentation
- Tags (DeFi, Layer 1, Meme coin, etc.)

### Step 3: Market Data

Call `get_crypto_quotes_latest` to get:
- Current price and market cap
- 24h, 7d, 30d, 90d, 1y price changes
- Trading volume and volume change
- Circulating supply vs max supply
- Market cap rank

### Step 4: Holder Analysis

Call `get_crypto_metrics` to get:
- Address distribution by holding value ($0-1k, $1k-100k, $100k+)
- Whale concentration (% held by top holders)
- Holder behavior (traders vs cruisers vs long-term holders)

### Step 5: Technical Analysis

Call `get_crypto_technical_analysis` to get:
- Moving averages (7d, 30d, 200d SMA/EMA)
- RSI (oversold < 30, overbought > 70)
- MACD signal
- Fibonacci levels and pivot points

### Step 6: Recent News

Call `get_crypto_latest_news` with limit 5-10 to get recent headlines and sentiment.

### Step 7: Deep Dive (if needed)

Call `search_crypto_info` to answer specific questions about the token's technology, use case, or mechanics.

## Analysis Framework

After gathering data, evaluate across these dimensions:

### Fundamentals
- What problem does it solve?
- Is there a working product?
- How does it compare to competitors?
- Is the use case sustainable?

### Tokenomics
- What % of max supply is circulating?
- Is there inflation or deflation?
- Are there large unlocks coming?
- How concentrated is ownership?

### Market Position
- Market cap rank and trajectory
- Volume relative to market cap (healthy turnover?)
- Price trend (accumulation or distribution?)

### Risk Factors

**Red flags and why they matter:**
- Extreme whale concentration (>10% held by few addresses): Large holders can dump and crash price instantly
- Low holder count relative to market cap: Thin holder base means price is easily manipulated
- Declining holder numbers: Smart money may be exiting while retail holds bags
- Negative news sentiment: Ongoing negative coverage often precedes further declines
- Price down >80% from ATH with no recovery: May indicate fundamental problems, not just market cycles
- Very low trading volume: Hard to exit positions without significant slippage

**Green flags and why they matter:**
- Growing holder base: Organic adoption suggests real demand, not manufactured hype
- High % of long-term holders: Conviction from holders who have done research, less sell pressure
- Healthy distribution across address sizes: Resilient to any single actor manipulating price
- Active development and news flow: Team is shipping, project is alive and evolving
- Strong community engagement: Network effects build value and create sustainable demand

## Report Structure

Present findings in this format:

```
## [Token Name] Research Report

### Overview
- Category: [DeFi/Layer 1/Meme/etc.]
- Launched: [Date]
- Rank: #XX by market cap

### Market Data
- Price: $X.XX
- Market Cap: $X.XX B
- 24h Volume: $X.XX M
- Performance: 24h X.X% | 7d X.X% | 30d X.X% | 1y X.X%

### Supply
- Circulating: X.XX M (XX% of max)
- Max Supply: X.XX M

### Holder Analysis
- Total Addresses: X.XX M
- Whale Concentration: X.X%
- Long-term Holders: XX%
- Holder Trend: Growing/Stable/Declining

### Technical Outlook
- RSI: XX (oversold/neutral/overbought)
- Trend: Above/Below 200d MA
- Key Support: $X.XX
- Key Resistance: $X.XX

### Recent News
- [Headline 1]
- [Headline 2]
- ...

### Green Flags
- [List positive indicators]

### Red Flags
- [List concerns]

### Summary
[2-3 sentence synthesis of the research findings]
```

## Important Notes

- This is research, not financial advice
- Always present both positive and negative findings
- If data is missing or unavailable, note it explicitly
- For very new tokens, some metrics may be limited

## Handling Tool Failures

If individual tools fail during research:

1. **search_cryptos fails**: Cannot proceed without token ID. Ask user to verify spelling or try the contract address.
2. **get_crypto_info fails**: Skip Overview section, note "Project details unavailable" in report.
3. **get_crypto_quotes_latest fails**: Report is incomplete without price data. Retry once, then note "Market data unavailable."
4. **get_crypto_metrics fails**: Skip Holder Analysis section, note "Distribution data unavailable."
5. **get_crypto_technical_analysis fails**: Skip Technical Outlook section, note "Technical analysis unavailable."
6. **get_crypto_latest_news fails**: Skip Recent News section, proceed with other data.

Always complete the report with available data rather than abandoning the research entirely.
```

---

## 6. Constraints & Specifications

### File Constraints

- **Filename:** Must be exactly `SKILL.md` (case-sensitive)
- **Encoding:** UTF-8
- **Frontmatter separator:** Three dashes (`---`) on lines 1 and final-yaml line
- **Max description length:** No hard limit, but CMC examples range 100–200 words. Keep trigger list concise.

### Content Constraints

- **No executable code in SKILL.md:** Skill bodies are pure Markdown documentation
- **Trigger keyword style:**
  - Natural language: lowercase, quoted (`"bitcoin"`, `"how is [coin] doing"`)
  - Slash commands: lowercase, quoted (`"/cmc-mcp"`, `"/cmc-api-crypto"`)
  - Templated placeholders: camelCase in brackets (`"[coin]"`)
  - No regex or wildcards in trigger strings
- **Tool names:** Must match exactly (case-sensitive). MCP tools follow `mcp__<server>__<tool>` format.
- **References links:** Use relative paths (e.g., `references/use-cases.md`), not absolute URLs or file system paths.

### Design Patterns Observed

1. **API skills** (cmc-api-*): Include `references/` folder with goal-based guides + detailed endpoint docs
2. **MCP skills** (cmc-mcp, crypto-research, market-report): No `references/`; workflow is inline in SKILL.md body
3. **Composite skills** (crypto-research, market-report): Chain multiple MCP tools in documented workflow; agent must follow steps in order
4. **Tool-reference skills** (cmc-api-crypto): Provide bare documentation; agent uses Bash/Read tools to construct and execute API calls

### No Official Limits Found On:

- Number of allowed-tools (crypto-research lists 6, market-report lists 4, cmc-api-crypto lists 2)
- Description length (tested: 100–300 words acceptable)
- Number of reference files (cmc-api-crypto: 10 refs; cmc-api-dex: 6 refs)
- Skill folder nesting (all observed: skills/<skill-name>/, no deeper)

---

## Summary for Hackathon Build

**Minimum viable SKILL.md:**
```yaml
---
name: your-skill-name
description: |
  One-liner. Usage guidance with when/when-not-to-use. 
  Trigger: "keyword1", "keyword2", "/your-skill-name"
user-invocable: true
allowed-tools:
  - ToolName
  - mcp__server__tool_name
---

# Title

Body: Markdown documentation, workflows, error handling, examples.
Link to references/ if you have supporting docs.
```

**Deliverables for submission:**
1. `skills/<your-skill>/SKILL.md` (required)
2. `skills/<your-skill>/references/*.md` (optional, recommended for API/reference skills)
3. Ensure skill name in frontmatter matches folder name exactly

---

## Unresolved Questions

None. All SKILL.md format details and patterns documented above are derived from 8 production CMC skills (MCP, API, x402, composite) with no contradictions or gaps. Format is stable and consistent across all observed examples.
