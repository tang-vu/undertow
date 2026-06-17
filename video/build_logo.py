"""Generate a 480x480 BUIDL logo for Undertow (Pillow). Two opposed waves = surface vs undertow,
with the wordmark. Output video/assets/logo.png.

    python video/build_logo.py
"""
from __future__ import annotations
import os, math
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "assets", "logo.png")
S = 480
TEAL = (25, 195, 200); BLUE = (90, 150, 210); INK = (232, 244, 248); BG = (6, 20, 29)
FB = "C:/Windows/Fonts/seguibl.ttf"


def wave(d, y0, amp, phase, color, width):
    pts = []
    for x in range(40, S - 40):
        t = (x - 40) / (S - 80)
        y = y0 + amp * math.sin(2 * math.pi * 1.6 * t + phase)
        pts.append((x, y))
    d.line(pts, fill=color, width=width, joint="curve")


def main():
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    for y in range(S):  # radial-ish vertical gradient
        t = abs(y - S / 2) / (S / 2)
        d.line([(0, y), (S, y)], fill=(int(6 + 8 * (1 - t)), int(20 + 16 * (1 - t)), int(29 + 22 * (1 - t))))
    d.rounded_rectangle([6, 6, S - 6, S - 6], 48, outline=(20, 70, 90), width=3)

    # surface wave (light, calm) + undertow wave (teal, stronger, opposite phase)
    wave(d, 196, 16, 0.0, BLUE, 6)
    wave(d, 250, 30, math.pi, TEAL, 12)
    # downward "pull" arrow hinting the undertow
    d.polygon([(S // 2 - 16, 300), (S // 2 + 16, 300), (S // 2, 332)], fill=TEAL)

    font = ImageFont.truetype(FB if os.path.exists(FB) else "arial.ttf", 52)
    d.text((S // 2, 392), "UNDERTOW", font=font, fill=TEAL, anchor="mm")
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    d.text((S // 2, 430), "sentiment  vs  positioning", font=small, fill=(150, 180, 195), anchor="mm")

    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
