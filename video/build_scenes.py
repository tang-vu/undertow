"""Compose 1920x1080 video scenes for the Undertow demo (Pillow only, no external services).

Sources: the headless-Chrome demo screenshot (video/assets/demo_full.png) + the matplotlib equity
curve (backtest/output/equity_curve.png). Outputs video/scenes/scene_XX.png.

    python video/build_scenes.py
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "assets", "demo_full.png")
EQUITY = os.path.join(ROOT, "..", "backtest", "output", "equity_curve.png")
SCENES = os.path.join(ROOT, "scenes")
W, H = 1920, 1080

INK = (232, 244, 248); MUT = (127, 166, 184); TEAL = (25, 195, 200)
GOLD = (247, 147, 26); RED = (255, 93, 108); BLUE = (58, 155, 220); BG = (6, 20, 29)

FONTS = ["C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/segoeuib.ttf",
         "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]


def font(size, weight="reg"):
    order = {"black": ["seguibl", "arialbd"], "bold": ["segoeuib", "arialbd"],
             "reg": ["segoeui", "arial"]}[weight]
    for stem in order:
        for f in FONTS:
            if stem in f and os.path.exists(f):
                return ImageFont.truetype(f, size)
    return ImageFont.truetype(FONTS[-1], size)


def canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(H):  # subtle vertical gradient
        t = y / H
        c = (int(6 + 4 * (1 - t)), int(20 + 14 * (1 - t)), int(29 + 18 * (1 - t)))
        d.line([(0, y), (W, y)], fill=c)
    return img, d


def text(d, xy, s, fnt, fill=INK, anchor="la", spacing=10):
    d.multiline_text(xy, s, font=fnt, fill=fill, anchor=anchor, spacing=spacing)


def fit(img, box_w, box_h):
    r = min(box_w / img.width, box_h / img.height)
    return img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)


def paste_card(base, crop, top, max_h=720):
    """Center a cropped element below the caption area with a soft border."""
    el = fit(crop, 1740, max_h)
    x = (W - el.width) // 2
    panel = Image.new("RGB", (el.width + 24, el.height + 24), (14, 38, 50))
    base.paste(panel, (x - 12, top - 12))
    base.paste(el, (x, top))


def kicker(d, s, color=TEAL):
    text(d, (140, 86), s, font(26, "bold"), color)


# ---------- scenes ----------
def scene_title():
    img, d = canvas()
    text(d, (W // 2, 360), "UNDERTOW", font(150, "black"), TEAL, "mm")
    d.line([(W // 2 - 360, 470), (W // 2 + 360, 470)], fill=(20, 70, 90), width=3)
    text(d, (W // 2, 560),
         "Trade the gap between what the crowd feels\nand how it's positioned.",
         font(46, "reg"), INK, "mm", spacing=14)
    text(d, (W // 2, 720), "A CoinMarketCap AI-Agent Strategy Skill",
         font(30, "reg"), MUT, "mm")
    text(d, (W // 2, 770), "BNB × CoinMarketCap × Trust Wallet Hackathon",
         font(26, "reg"), (90, 120, 135), "mm")
    return img


def scene_thesis():
    img, d = canvas()
    kicker(d, "THE THESIS")
    text(d, (W // 2, 170), "Sentiment screams on the surface.\nThe risk builds underneath.",
         font(54, "bold"), INK, "mm", spacing=14)
    # two columns
    d.rounded_rectangle([140, 360, 930, 900], 18, fill=(14, 38, 50))
    d.rounded_rectangle([990, 360, 1780, 900], 18, fill=(14, 38, 50))
    text(d, (180, 410), "SURFACE", font(40, "black"), BLUE)
    text(d, (180, 480), "what the crowd feels", font(30, "reg"), MUT)
    text(d, (180, 560), "•  CMC Fear & Greed\n•  Social / KOL heat\n•  Trending narratives",
         font(34, "reg"), INK, spacing=22)
    text(d, (1030, 410), "UNDERTOW", font(40, "black"), TEAL)
    text(d, (1030, 480), "how it's positioned", font(30, "reg"), MUT)
    text(d, (1030, 560), "•  Perp funding extremity\n•  Open-interest change\n•  Price stretch from trend",
         font(34, "reg"), INK, spacing=22)
    text(d, (W // 2, 980), "When they diverge — conditioned on regime — the tide turns.",
         font(34, "reg"), GOLD, "mm")
    return img


def scene_live(demo):
    img, d = canvas()
    kicker(d, "THE SKILL — LIVE READ")
    text(d, (W // 2, 165), "Positioning-stress  S  +  regime  R  →  a full strategy spec",
         font(40, "bold"), INK, "mm")
    cards = demo.crop((40, 300, 1880, 815))   # dial + regime + edge cards
    paste_card(img, cards, 250, max_h=560)
    text(d, (W // 2, 880), "regime · stress reading · stance · sizing · risk — emitted as JSON",
         font(30, "reg"), MUT, "mm")
    return img


def scene_equity():
    img, d = canvas()
    kicker(d, "OUT-OF-SAMPLE BACKTEST")
    text(d, (W // 2, 165), "Bitcoin-like return — with half the drawdown",
         font(46, "bold"), INK, "mm")
    eq = Image.open(EQUITY).convert("RGB")
    eqf = fit(eq, 1500, 720)
    x = (W - eqf.width) // 2
    img.paste(eqf, (x, 250))
    text(d, (W // 2, 1010), "BTC/ETH/BNB/SOL/XRP · 2019–2026 · costs + slippage · walk-forward OOS",
         font(28, "reg"), MUT, "mm")
    return img


def scene_edge(demo):
    img, d = canvas()
    kicker(d, "THE EDGE")
    text(d, (470, 250), "−35%", font(150, "black"), TEAL, "mm")
    text(d, (470, 360), "max drawdown", font(34, "reg"), INK, "mm")
    text(d, (470, 410), "vs BTC −77%", font(30, "reg"), MUT, "mm")
    text(d, (470, 560), "1.34", font(110, "black"), TEAL, "mm")
    text(d, (470, 650), "full-cycle Sharpe", font(34, "reg"), INK, "mm")
    text(d, (470, 700), "vs BTC 0.76", font(30, "reg"), MUT, "mm")
    tbl = demo.crop((40, 1655, 1880, 2010))   # metrics table
    el = fit(tbl, 1000, 560)
    img.paste(el, (940, 300))
    text(d, (W // 2, 980), "Wins on Calmar & drawdown OOS · laps the naive Fear & Greed contrarian (−53%)",
         font(28, "reg"), MUT, "mm")
    return img


def scene_agenthub():
    img, d = canvas()
    kicker(d, "BEST USE OF AGENT HUB")
    text(d, (W // 2, 170), "Agent-native — verified live", font(50, "bold"), INK, "mm")
    rows = [
        (TEAL, "MCP", "real JSON-RPC client · live Fear & Greed, funding, OI, quotes"),
        (GOLD, "x402", "keyless pay-per-request · real HTTP 402 challenge · $0.01 USDC on Base"),
        (BLUE, "Skill Hub", "orchestrates detect_market_regime, perp_contract_analysis via find_skill"),
        (RED, "Authored Skill", "SKILL.md in CMC format · find_skill-discoverable"),
    ]
    y = 330
    for col, k, v in rows:
        d.rounded_rectangle([140, y, 1780, y + 130], 16, fill=(14, 38, 50))
        text(d, (180, y + 30), k, font(40, "black"), col)
        text(d, (560, y + 42), v, font(30, "reg"), INK)
        y += 158
    text(d, (W // 2, 1015),
         '402: "Provide PAYMENT-SIGNATURE header to pay and retry."  — captured live',
         font(26, "reg"), MUT, "mm")
    return img


def scene_close():
    img, d = canvas()
    text(d, (W // 2, 360), "Reproducible.  Honest.  Agent-native.",
         font(56, "bold"), INK, "mm")
    text(d, (W // 2, 520), "UNDERTOW", font(130, "black"), TEAL, "mm")
    d.line([(W // 2 - 320, 620), (W // 2 + 320, 620)], fill=(20, 70, 90), width=3)
    text(d, (W // 2, 700), "github.com/tang-vu/undertow", font(38, "reg"), TEAL, "mm")
    text(d, (W // 2, 770), "Research artifact, not investment advice.", font(26, "reg"), MUT, "mm")
    return img


def main():
    os.makedirs(SCENES, exist_ok=True)
    demo = Image.open(DEMO).convert("RGB")
    builders = [scene_title(), scene_thesis(), scene_live(demo), scene_equity(),
                scene_edge(demo), scene_agenthub(), scene_close()]
    for i, im in enumerate(builders, 1):
        p = os.path.join(SCENES, f"scene_{i:02d}.png")
        im.save(p)
        print("wrote", p)


if __name__ == "__main__":
    main()
