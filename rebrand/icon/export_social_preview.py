"""One-off generator for the GitHub social preview image (1280x640).
Composites Wisp's existing icon mark with wordmark + tagline on the brand
palette. Not part of build.py's pipeline -- this is a repo-metadata asset,
not something that ships in the browser.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "social-preview.png"

W, H = 1280, 640
BG = "#29286A"
ACCENT = "#A5F3FC"
WHITE = "#FFFFFF"

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

icon = Image.open(HERE / "wisp.png").convert("RGBA")
icon_size = 220
icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
icon_x = 140
icon_y = (H - icon_size) // 2
img.paste(icon, (icon_x, icon_y), icon)

text_x = icon_x + icon_size + 60

title_font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 96)
tagline_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 34)

title = "Wisp"
title_bbox = draw.textbbox((0, 0), title, font=title_font)
title_h = title_bbox[3] - title_bbox[1]

tagline = "A privacy-hardened browser, built on LibreWolf"
tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
tagline_h = tagline_bbox[3] - tagline_bbox[1]

gap = 24
block_h = title_h + gap + tagline_h
block_y = (H - block_h) // 2

draw.text((text_x, block_y - title_bbox[1]), title, font=title_font, fill=WHITE)
draw.text(
    (text_x, block_y + title_h + gap - tagline_bbox[1]),
    tagline,
    font=tagline_font,
    fill=ACCENT,
)

img.save(OUT)
print(f"wrote {OUT} ({img.size[0]}x{img.size[1]})")
