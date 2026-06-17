"""Generate a 1280x720 YouTube thumbnail for the Undertow demo (Pillow only).

Bold, high-contrast, readable at small size: title + tagline + the punchy stat + Agent Hub surfaces,
with the demo's stress-dial crop for visual interest. Output video/assets/thumbnail.png.

    python video/build_thumbnail.py
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "assets", "demo_full.png")
OUT = os.path.join(ROOT, "assets", "thumbnail.png")
W, H = 1280, 720
INK = (232, 244, 248); MUT = (150, 180, 195); TEAL = (25, 195, 200); GOLD = (247, 147, 26); BG = (6, 20, 29)
FONTS = {"black": "C:/Windows/Fonts/seguibl.ttf", "bold": "C:/Windows/Fonts/segoeuib.ttf",
         "reg": "C:/Windows/Fonts/segoeui.ttf"}


def font(size, w="reg"):
    p = FONTS.get(w, FONTS["reg"])
    return ImageFont.truetype(p if os.path.exists(p) else FONTS["reg"], size)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(H):  # gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(6 + 6 * (1 - t)), int(20 + 18 * (1 - t)), int(29 + 24 * (1 - t))))

    # Right: stress-dial crop from the demo for visual interest.
    try:
        demo = Image.open(DEMO).convert("RGB")
        dial = demo.crop((70, 300, 660, 600))            # dial card header + gauge + value (no clutter)
        r = 360 / dial.height
        dial = dial.resize((int(dial.width * r), 360), Image.LANCZOS)
        img.paste(dial, (W - dial.width - 50, 190))
    except Exception:
        pass

    # Left: title + tagline.
    d.text((60, 70), "UNDERTOW", font=font(96, "black"), fill=TEAL)
    d.line([(64, 175), (560, 175)], fill=(20, 70, 90), width=4)
    d.multiline_text((64, 200), "Trade sentiment\nvs positioning", font=font(60, "bold"), fill=INK, spacing=8)

    # Punchy stat box.
    d.rounded_rectangle([60, 360, 660, 520], 18, fill=(12, 40, 52))
    d.text((84, 380), "≈ Bitcoin's return", font=font(40, "bold"), fill=INK)
    d.text((84, 432), "HALF the drawdown", font=font(46, "black"), fill=TEAL)

    # Footer: Agent Hub surfaces + hackathon.
    d.text((64, 600), "CoinMarketCap Agent Hub", font=font(34, "bold"), fill=GOLD)
    d.text((64, 648), "MCP · x402 · CLI · Skills", font=font(30, "reg"), fill=MUT)

    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
