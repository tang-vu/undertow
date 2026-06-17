"""x402 pay-per-request demo for CoinMarketCap data - no API key, USDC on Base.

x402 lets an autonomous agent pay $0.01 USDC per request instead of holding an API key. This script
demonstrates the path end to end:

  1. Connect to the x402 MCP endpoint (initialize + tools/list) - works with NO key, NO payment.
  2. Attempt a tool CALL - the server requires payment; we surface whatever it returns.
  3. Print the documented EIP-3009 `transferWithAuthorization` settlement parameters so a funded
     Base wallet can complete the call.

Completing a real paid call needs a funded Base wallet (USDC + a little ETH for gas) and the x402
client to sign the authorization. Default run is a safe dry-run (no funds required).

Refs: official cmc-x402 skill; https://x402.org ; https://github.com/coinbase/x402
"""
from __future__ import annotations
import json
from mcp_client import CmcMcpClient, X402_ENDPOINT

# From the official cmc-x402 skill (references/payment-details.md), verified values:
X402_PAYMENT = {
    "network": "Base (eip155:8453)",
    "asset": "USDC",
    "usdc_contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "pay_to": "0x271189c860DB25bC43173B0335784aD68a680908",
    "amount_smallest_unit": "10000",          # $0.01 USDC (6 decimals)
    "method": "EIP-3009 transferWithAuthorization",
    "eip712_domain": {"name": "USD Coin", "version": "2"},
    "max_timeout_seconds": 30,
}


def main():
    print("=" * 68)
    print("STEP 1 - connect to x402 MCP (no key, no payment)")
    print("        ", X402_ENDPOINT)
    c = CmcMcpClient(endpoint=X402_ENDPOINT)
    init = c.initialize()
    server = init.get("result", {}).get("serverInfo", {})
    print("  handshake OK:", json.dumps(server))
    tools = c.list_tools()
    print(f"  {len(tools)} tools available via x402:", ", ".join(t["name"] for t in tools[:6]), "...")

    print("\nSTEP 2 - attempt a tool call (payment required on x402)")
    res = c.call_tool("get_crypto_quotes_latest", {"symbol": "BTC"})
    if res.get("_status") == 402:
        print("  -> HTTP 402 Payment Required (expected). Challenge:")
        print("    ", json.dumps(res.get("_payment_required"))[:400])
    else:
        txt = c.tool_text(res) or json.dumps(res)
        print("  -> server response (first 300 chars):", txt[:300])
        print("     (If this returned data, the endpoint settled or allowed a free probe.)")

    print("\nSTEP 3 - settlement parameters for a funded Base wallet (EIP-3009)")
    for k, v in X402_PAYMENT.items():
        print(f"  {k:22s}: {v}")
    print("\n  To complete a paid call: sign a USDC transferWithAuthorization for the amount above")
    print("  and resend with the PAYMENT-SIGNATURE header. Pay-on-success only - failed calls cost $0.")
    print("  TS one-liner path: `npm i @x402/axios @x402/evm viem` then createX402AxiosClient(...).")


if __name__ == "__main__":
    main()
