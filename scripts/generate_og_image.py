#!/usr/bin/env python3
"""
Generate og-image.png for THE MCFD FILES.
1200x630, dark background, key stats.
Output: frontend/public/og-image.png
Run: python3 scripts/generate_og_image.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (10, 10, 10)
RED = (220, 60, 60)
RED_DIM = (140, 30, 30)
WHITE = (255, 255, 255)
GRAY = (120, 120, 120)
GRAY_LIGHT = (180, 180, 180)
AMBER = (251, 191, 36)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Top red accent bar
draw.rectangle([0, 0, W, 5], fill=RED)

# Bottom bar
draw.rectangle([0, H - 60, W, H], fill=(20, 8, 8))

# Try to load a system monospace font; fall back to default
def load_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/CourierNew.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

font_tiny   = load_font(16)
font_small  = load_font(22)
font_med    = load_font(32)
font_large  = load_font(56)
font_xl     = load_font(72)

# Eyebrow label
draw.text((60, 50), "PUBLIC ACCOUNTABILITY RECORD · PC 19700", font=font_small, fill=RED)

# Title
draw.text((60, 100), "THE MCFD FILES", font=font_xl, fill=WHITE)

# Subtitle
draw.text((60, 190), "British Columbia, Canada · Trial: May 19–21, 2026", font=font_med, fill=GRAY_LIGHT)

# Divider line
draw.rectangle([60, 250, W - 60, 252], fill=RED_DIM)

# Stats row
stats = [
    ("$175,041.32", "Documented\ntaxpayer cost"),
    ("23", "Sworn statement\ncontradictions"),
    ("906 vs 1,792", "FOI pages\ndisclosed vs stated"),
    ("PC 19700", "BC Provincial\nCourt case"),
]

col_w = (W - 120) // 4
for i, (val, label) in enumerate(stats):
    x = 60 + i * col_w
    draw.text((x, 275), val, font=font_med, fill=AMBER)
    for j, line in enumerate(label.split("\n")):
        draw.text((x, 320 + j * 24), line, font=font_tiny, fill=GRAY)

# Second divider
draw.rectangle([60, 400, W - 60, 401], fill=(40, 40, 40))

# Bottom detail line
draw.text((60, 420), "OIPC Complaint INV-F-26-00220 active · FOI gap confirmed", font=font_small, fill=GRAY)
draw.text((60, 455), "All figures derived from BC government-published rates and sworn court documents.", font=font_tiny, fill=(80, 80, 80))
draw.text((60, 485), "#BCPolitics  #MCFD  #FreeNadia  #ChildProtection", font=font_small, fill=(100, 60, 60))

# Bottom bar text
draw.text((60, H - 42), "themcfdfiles.ca/share", font=font_med, fill=GRAY_LIGHT)
draw.text((W - 340, H - 42), "Pro Patria · Open Record", font=font_small, fill=(80, 80, 80))

# Output path
out_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "og-image.png")
img.save(out_path, "PNG", optimize=True)
print(f"OG image saved: {out_path}  ({W}x{H})")
