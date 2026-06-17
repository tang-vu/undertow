"""Undertow live scorer — turns a live CMC reading into the Undertow strategy spec (JSON).

This is the executable heart of the Skill: it loads the frozen weights + normalization baselines
exported from the backtest, z-scores a live reading, computes the positioning-stress S and the
regime R, applies the decision rules, and prints the agent-ready strategy spec.

Modes:
  --demo            (default) use the committed backtest snapshot (real values as of the data window)
                    and a real captured CMC Skill Hub regime fixture. Runs with ZERO credentials.
  --mcp             pull live data over the CMC MCP (needs CMC_MCP_API_KEY) and score it live.
  --token BTCUSDT   asset to score.

Usage:
  python undertow_live.py --demo --token BTCUSDT
  CMC_MCP_API_KEY=xxx python undertow_live.py --mcp --token ETHUSDT
"""
from __future__ import annotations
import os
import json
import math
import argparse
import datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
PARAMS = os.path.join(ROOT, "..", "skill", "undertow", "references", "strategy-params.json")
RESULTS = os.path.join(ROOT, "..", "backtest", "output", "results.json")
REGIME_FIXTURE = os.path.join(ROOT, "fixtures", "detect_market_regime_30d.json")


def load_params() -> dict:
    return json.load(open(PARAMS))


def z(x: float, base: dict) -> float:
    return (x - base["mean"]) / base["std"] if base.get("std") else 0.0


def reading_label(s: float) -> str:
    if s >= 1.5: return "euphoric"
    if s >= 0.5: return "frothy"
    if s <= -1.5: return "capitulation"
    if s <= -0.5: return "fearful"
    return "neutral"


def decide(s: float, regime: str, macro: str, dr: dict) -> tuple[str, float]:
    """Map (S, regime, macro-trend) -> (stance, raw target position in [-1,1]). Mirrors the backtest."""
    froth = math.tanh(s / dr["s_scale"])
    froth_pos, fear_pos = max(froth, 0.0), max(-froth, 0.0)
    if macro == "bull":
        if regime == "TREND":
            raw = 1.0 - dr["trend_froth_haircut"] * froth_pos
        else:
            raw = max(0.0, min(1.0, dr["range_long_base"] - dr["range_tilt"] * froth))
    else:
        if regime == "TREND":
            raw = -dr["short_bear"] * froth_pos
        else:
            raw = max(-dr["range_short_cap"], min(dr["range_short_cap"],
                      dr["dip_bear"] * fear_pos - dr["short_bear"] * froth_pos))
    raw = max(-dr["max_position"], min(dr["max_position"], raw))
    if raw >= 0.5: stance = "long"
    elif raw > 0.05: stance = "reduce"
    elif raw < -0.05: stance = "short"
    else: stance = "flat"
    return stance, round(raw, 3)


def build_spec(token, tf, s, comps, weights, regime, macro, er, surface, undertow,
               params, source, hub_regime, target_pos=None, social=None) -> dict:
    dr = params["decision_rules"]
    stance, raw = decide(s, regime, macro, dr)
    return {
        "skill": "undertow",
        "as_of": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "token": token, "timeframe": tf,
        "regime": {"label": regime, "macro_trend": macro,
                   "skill_hub_regime": hub_regime, "efficiency_ratio": er},
        "stress": {
            "S": round(s, 3), "reading": reading_label(s),
            "components": {k: round(v, 3) for k, v in comps.items()},
            "weights": weights, "surface": surface, "undertow": undertow,
        },
        "decision": {
            "stance": stance,
            "target_position": round((target_pos if target_pos is not None else raw) + 0.0, 3),
            "entry": "fade froth in range / ride trend in up-trend; buy capitulation on dips",
            "exit": "froth extreme in range, or macro trend flips to bear",
            "risk": {"max_position": dr["max_position"], "vol_target_annual": dr["target_vol_annual"],
                     "drawdown_guard": dr["drawdown_guard"], "cost_bps_one_way": dr["cost_bps_one_way"]},
        },
        "enhancements_live_only": {
            "social_kol": social or "not fetched (live-only; use altcoin_kol_sentiment)",
            "oi_change_pct_7d": undertow.get("oi_change_pct_7d"),
            "on_chain": "not fetched (live-only)",
        },
        "data_source": source,
        "backtest_provenance": params.get("backtest_headline", {}).get("strategy_walk_forward", {}),
        "disclaimer": "Research artifact, not investment advice.",
    }


def demo(token: str, params: dict) -> dict:
    cur = json.load(open(RESULTS))["current"][token]
    reg = json.load(open(REGIME_FIXTURE))["result"]["data"]["report"]
    m = reg["metrics"]
    comps = {"z_fng": cur["z_fng"], "z_funding": cur["z_funding"], "z_stretch": cur["z_stretch"]}
    weights = params["composite"]["weights"]
    surface = {"fear_greed": cur["fng"]}
    undertow = {"funding_bps_7d": m["average_funding_bps_7d"], "oi_change_pct_7d": m["oi_change_pct_7d"]}
    return build_spec(token, "1d", cur["S"], comps, weights, cur["regime"], cur["macro_trend"],
                      round(cur["er"], 3), surface, undertow, params,
                      source="backtest snapshot (real, " + cur["date"] + ") + live Skill Hub regime fixture",
                      hub_regime=reg["market_regime"], target_pos=cur["target_position"])


def mcp_live(token: str, params: dict) -> dict:
    from mcp_client import CmcMcpClient
    c = CmcMcpClient()  # plain endpoint, needs CMC_MCP_API_KEY
    if not c.api_key:
        raise SystemExit("Set CMC_MCP_API_KEY for --mcp mode (or use --demo).")
    c.initialize()
    gm = json.loads(c.tool_text(c.call_tool("get_global_metrics_latest")) or "{}")
    deriv = json.loads(c.tool_text(c.call_tool("get_global_crypto_derivatives_metrics")) or "{}")
    sym = token.replace("USDT", "")
    quotes = json.loads(c.tool_text(c.call_tool("get_crypto_quotes_latest", {"symbol": sym})) or "{}")
    fng = float(_dig(gm, "fear_greed", "fear_and_greed", "value") or 50.0)
    funding = float(_dig(deriv, "funding_rate", "avg_funding_rate") or 0.0) * 3.0  # 8h -> daily
    base = params["normalization_baselines"]
    fb = base["funding"].get(token, list(base["funding"].values())[0])
    comps = {"z_fng": round(z(fng, base["fng_market"]), 3),
             "z_funding": round(z(funding, fb), 3), "z_stretch": 0.0}
    w = params["composite"]["weights"]
    s = w["w_fng"] * comps["z_fng"] + w["w_funding"] * comps["z_funding"] + w["w_stretch"] * comps["z_stretch"]
    return build_spec(token, "1d", s, comps, w, "RANGE", "bull", None,
                      {"fear_greed": fng}, {"funding_daily": funding}, params,
                      source="LIVE CMC MCP (get_global_metrics_latest + derivatives + quotes)",
                      hub_regime="call detect_market_regime via cmc-skill-hub for the authoritative label")


def _dig(obj, *keys):
    """Best-effort nested lookup tolerant of CMC payload shape variations."""
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and not isinstance(v, (dict, list)):
                    return v
                r = walk(v)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r is not None:
                    return r
        return None
    return walk(obj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default="BTCUSDT")
    ap.add_argument("--demo", action="store_true", help="use committed snapshot + regime fixture (default; no creds)")
    ap.add_argument("--mcp", action="store_true", help="pull live data over CMC MCP (needs CMC_MCP_API_KEY)")
    args = ap.parse_args()
    params = load_params()
    spec = mcp_live(args.token, params) if args.mcp else demo(args.token, params)
    print(json.dumps(spec, indent=2))


if __name__ == "__main__":
    main()
