"""Minimal CoinMarketCap MCP client over Streamable HTTP (JSON-RPC 2.0).

Verified live on 2026-06-17 against:
  - https://mcp.coinmarketcap.com/mcp        (needs header X-CMC-MCP-API-KEY)
  - https://mcp.coinmarketcap.com/x402/mcp   (no key; tool CALLS are pay-per-request via x402)

initialize + tools/list work on the x402 endpoint with no key — handy for connectivity checks.
Tool *calls* on x402 require a signed USDC payment (see x402_demo.py). On the keyed endpoint,
tool calls work directly once X-CMC-MCP-API-KEY is set.

No SDK dependency — just `requests`. Handles both application/json and text/event-stream replies
and the optional Mcp-Session-Id handshake.
"""
from __future__ import annotations
import os
import json
import requests

PLAIN_ENDPOINT = "https://mcp.coinmarketcap.com/mcp"
X402_ENDPOINT = "https://mcp.coinmarketcap.com/x402/mcp"


class CmcMcpClient:
    def __init__(self, endpoint: str = PLAIN_ENDPOINT, api_key: str | None = None, timeout: int = 40):
        self.endpoint = endpoint
        self.api_key = api_key or os.environ.get("CMC_MCP_API_KEY")
        self.timeout = timeout
        self.session_id: str | None = None
        self._id = 0
        self._s = requests.Session()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.api_key:
            h["X-CMC-MCP-API-KEY"] = self.api_key
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    @staticmethod
    def _parse(resp: requests.Response) -> dict:
        if "event-stream" in resp.headers.get("Content-Type", ""):
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    try:
                        return json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
            return {"_raw": resp.text[:500]}
        try:
            return resp.json()
        except ValueError:
            return {"_raw": resp.text[:500], "_status": resp.status_code}

    def _rpc(self, method: str, params: dict | None = None, notify: bool = False) -> dict | None:
        payload = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._id += 1
            payload["id"] = self._id
        if params is not None:
            payload["params"] = params
        resp = self._s.post(self.endpoint, headers=self._headers(), json=payload, timeout=self.timeout)
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        if resp.status_code == 402:                      # x402 payment required
            return {"_status": 402, "_payment_required": self._parse(resp)}
        if notify:
            return None
        return self._parse(resp)

    def initialize(self) -> dict:
        out = self._rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "undertow", "version": "1.0"},
        })
        self._rpc("notifications/initialized", notify=True)
        return out

    def list_tools(self) -> list[dict]:
        out = self._rpc("tools/list") or {}
        return out.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}}) or {}

    @staticmethod
    def tool_text(call_result: dict) -> str:
        """Extract the text payload from an MCP tool result envelope."""
        content = call_result.get("result", {}).get("content", [])
        return "".join(c.get("text", "") for c in content if c.get("type") == "text")


if __name__ == "__main__":
    # Connectivity smoke test against the x402 endpoint (no key, no payment for initialize/list).
    c = CmcMcpClient(endpoint=X402_ENDPOINT)
    init = c.initialize()
    print("initialize:", json.dumps(init.get("result", init))[:200])
    tools = c.list_tools()
    print(f"tools/list: {len(tools)} tools")
    for t in tools:
        print("  -", t.get("name"))
