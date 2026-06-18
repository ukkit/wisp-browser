"""Renders Wisp's mono mark (indigo circle + white wisp glyph) and exports
wisp.ico (multi-res: 16/32/48/64/128/256) plus a 256px PNG for the README.

The glyph is the user-approved "favicon · mono" treatment from
wisp_browser_icon_concepts.svg: a constant-width S-curl (two cubic bezier
segments) stroked in white with round caps, on a full-bleed indigo circle.
Stroke thickness scales up at smaller sizes for legibility, following the
ratios demonstrated in that same concept file's own 48px/16px previews.

Drawn directly with Pillow (sampling the bezier and stamping overlapping
circles along it) rather than rasterizing SVG, since this dev box has no
native libcairo for cairosvg. See wisp.svg for the path-based source.

Run from the repo root: .venv/Scripts/python.exe rebrand/icon/export_ico.py
"""
from pathlib import Path
import struct

from PIL import Image, ImageDraw

INDIGO = (79, 70, 229, 255)  # #4F46E5
WHITE = (255, 255, 255, 255)

# Local path coords from wisp_browser_icon_concepts.svg's <path id="wisp">,
# split into its two cubic bezier segments (P0, C1, C2, P1).
SEG_A = ((50, 88), (30, 78), (28, 56), (46, 49))
SEG_B = ((46, 49), (64, 42), (66, 22), (50, 14))

# That concept's favicon-treatment group transform: translate(495,55) scale(0.9),
# applied before the path is drawn inside circle center=(540,100) r=70.
TX, TY, SCALE = 495, 55, 0.9
CX, CY, R = 540, 100, 70

SUPERSAMPLE = 8

# size -> stroke width as a fraction of icon size. 256/128/64 use the concept's
# own favicon ratio (stroke-width 9 * scale 0.9 / (2*70) ≈ 0.058); 48 and 16 use
# the thickened ratios the concept file itself demonstrates in its "at small
# sizes" previews (stroke-width 12 @ tile-scale 0.336/48px ≈ 0.084, stroke-width
# 20 @ tile-scale 0.112/16px ≈ 0.14); 32 interpolates between 48 and 16.
STROKE_FRACTIONS = {256: 0.058, 128: 0.058, 64: 0.058, 48: 0.084, 32: 0.10, 16: 0.14}
SIZES = sorted(STROKE_FRACTIONS)

OUT_DIR = Path(__file__).parent
ICO_PATH = OUT_DIR / "wisp.ico"
PNG_PATH = OUT_DIR / "wisp.png"

# Sizes LibreWolf bakes into omni.ja as chrome/browser/content/branding/icon<N>.png
# (the in-app wolf-logo shown on about:support, the Help menu, etc — a separate
# asset from the .exe icon that rcedit swaps). rebrand_strings.py reads these.
OMNI_ICON_DIR = OUT_DIR / "omni-icons"
OMNI_ICON_SIZES = [16, 32, 48, 64, 128]


def bezier(p0, c1, c2, p1, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p1[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p1[1]
    return x, y


def local_to_norm(x, y):
    """Local path coords -> normalized circle coords (-1..1 across the circle)."""
    cxp = TX + SCALE * x
    cyp = TY + SCALE * y
    return (cxp - CX) / R, (cyp - CY) / R


def sample_path(steps=300):
    pts = []
    for seg in (SEG_A, SEG_B):
        for i in range(steps + 1):
            x, y = bezier(*seg, i / steps)
            pts.append(local_to_norm(x, y))
    return pts


def draw_icon(size, stroke_frac):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size - 1, size - 1], fill=INDIGO)
    r = size * stroke_frac / 2
    for nx, ny in sample_path():
        px = size / 2 + nx * (size / 2)
        py = size / 2 + ny * (size / 2)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=WHITE)
    return img


def render_size(size):
    big = draw_icon(size * SUPERSAMPLE, STROKE_FRACTIONS[size])
    return big.resize((size, size), Image.LANCZOS)


def pack_ico(images_by_size, path):
    """Hand-rolled ICO writer (PNG-compressed entries, valid since Windows
    Vista) — needed because Pillow's own ICO writer resizes one source image
    for every requested size, which can't give small layers their own
    (thicker-stroke) artwork the way render_size does per size.
    """
    import io

    entries = []
    blobs = []
    offset = 6 + 16 * len(images_by_size)
    for size in sorted(images_by_size):
        buf = io.BytesIO()
        images_by_size[size].save(buf, format="PNG")
        data = buf.getvalue()
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entries.append(struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset))
        blobs.append(data)
        offset += len(data)

    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(images_by_size)))
        for e in entries:
            f.write(e)
        for b in blobs:
            f.write(b)


def main():
    images = {size: render_size(size) for size in SIZES}
    pack_ico(images, ICO_PATH)
    images[256].save(PNG_PATH)
    print(f"wrote {ICO_PATH} ({len(images)} sizes: {sorted(images)})")
    print(f"wrote {PNG_PATH}")

    OMNI_ICON_DIR.mkdir(exist_ok=True)
    for size in OMNI_ICON_SIZES:
        out = OMNI_ICON_DIR / f"icon{size}.png"
        images[size].save(out)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
