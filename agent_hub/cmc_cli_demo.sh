#!/bin/sh
# CMC CLI access path for Undertow — the 4th CoinMarketCap Agent Hub surface (MCP · x402 · CLI · Skills).
#
# The official CMC CLI (github.com/openCMC/CoinMarketCap-CLI, `cmc`) gives terminal-native, scriptable
# access to the same data Undertow needs. This script proves the wiring with keyless --dry-run previews,
# then (with CMC_API_KEY) pulls the real inputs the Undertow scorer consumes.
#
# Install:  curl -sSfL https://raw.githubusercontent.com/openCMC/CoinMarketCap-CLI/main/install.sh | sh
# Auth:     export CMC_API_KEY=your-free-key   (https://pro.coinmarketcap.com/login)
# Run:      sh agent_hub/cmc_cli_demo.sh

set -e
CMC="${CMC_BIN:-cmc}"
command -v "$CMC" >/dev/null 2>&1 || CMC="$HOME/.local/bin/cmc"   # default install location

echo "== CMC CLI $($CMC --version 2>/dev/null) =="

echo
echo "1) Global metrics (Fear & Greed + dominance)  — request preview (keyless --dry-run):"
"$CMC" metrics --dry-run -o json

echo
echo "2) BTC daily history (price-stretch input)     — request preview (keyless --dry-run):"
"$CMC" history --id 1 --days 90 --dry-run -o json

echo
echo "3) Derivatives pairs (funding/OI context)      — request preview (keyless --dry-run):"
"$CMC" pairs 1 --category derivatives --limit 20 --dry-run -o json 2>/dev/null || \
  echo "   (pairs preview unavailable in this CLI build; metrics+history cover the backtested core)"

if [ -n "${CMC_API_KEY:-}" ]; then
  echo
  echo "== CMC_API_KEY detected -> pulling LIVE data and exporting for the Undertow scorer =="
  "$CMC" metrics -o json --export "$(dirname "$0")/cli_metrics.json" >/dev/null 2>&1 || "$CMC" metrics -o json
  "$CMC" history --id 1 --days 90 -o json --export "$(dirname "$0")/cli_btc_history.csv" >/dev/null 2>&1 || true
  echo "   wrote cli_metrics.json / cli_btc_history.csv — feed these into undertow_live.py to z-score live."
else
  echo
  echo "== Set CMC_API_KEY to fetch live data (above are keyless request previews). =="
  echo "   The CLI surfaces the same quotes / global-metrics / historical endpoints Undertow uses,"
  echo "   so the strategy spec can be produced in a pure terminal / automation workflow."
fi
