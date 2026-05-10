#!/usr/bin/env python3
"""
gen_social_preview.py — GitHub / social-media banner for Neight · சொல்வெளி
Output: 1280 × 640 px PNG

Light background, green ruled lines, icon palette accents.
"""

import subprocess, shutil, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── Canvas ─────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 640

# ── Palette ────────────────────────────────────────────────────────────────
BG            = (245, 248, 243, 255)  # warm off-white, slight green tint
PANEL         = (253, 255, 252, 255)  # near-white panel
MID_GREEN     = (30,  122,  78, 255)  # #1E7A4E — icon light half
DARK_GREEN    = (12,   53,  32, 255)  # #0C3520 — icon dark half
TITLE_COLOR   = (18,   42,  26, 255)  # near-black green for headings
TEXT_COLOR    = (40,   72,  50, 255)  # body text
ACCENT        = (30,  122,  78, 255)  # same as MID_GREEN
ACCENT_DIM    = ( 80, 140, 100, 255)  # sub-tagline, credit
RULE          = ( 30, 122,  78,  55)  # ruled lines — visible but gentle
PANEL_BORDER  = (126, 172,  98, 255)  # panel outline
BADGE_BG      = (232, 242, 234, 255)  # light green chip
BADGE_BORDER  = ( 30, 122,  78, 200)
BADGE_TEXT    = (18,   42,  26, 255)

ROOT      = Path(__file__).resolve().parent.parent   # project root (parent of design/)
ICON_PATH = ROOT / "neight.ico"
OUT_PATH  = ROOT / "social-preview-neight.png"


def _find_chrome() -> str:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise RuntimeError("Chrome/Chromium not found. Install Google Chrome or ensure it is on PATH.")


CHROME = _find_chrome()


# ── Fonts ──────────────────────────────────────────────────────────────────

def _first_existing(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default(size=size)


_GILL = "/System/Library/Fonts/Supplemental/GillSans.ttc"


def font_bold(size: int) -> ImageFont.FreeTypeFont:
    if Path(_GILL).exists():
        return ImageFont.truetype(_GILL, size=size, index=1)   # Gill Sans Bold
    return _first_existing([
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ], size)


def font_semibold(size: int) -> ImageFont.FreeTypeFont:
    if Path(_GILL).exists():
        return ImageFont.truetype(_GILL, size=size, index=4)   # Gill Sans SemiBold
    return font_bold(size)


def font_regular(size: int) -> ImageFont.FreeTypeFont:
    if Path(_GILL).exists():
        return ImageFont.truetype(_GILL, size=size, index=0)   # Gill Sans Regular
    return _first_existing([
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ], size)


def font_tamil(size: int) -> ImageFont.FreeTypeFont:
    return _first_existing([
        str(Path.home() / "Library/Fonts/NotoSerifTamil-VariableFont_wdth,wght.ttf"),
        "/Library/Fonts/NotoSerifTamil-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifTamil-Regular.ttf",
    ], size)


def render_tamil(text: str, font_size: int, color: tuple) -> Image.Image:
    """Render Tamil text via Chrome headless — Pillow lacks HarfBuzz shaping."""
    r, g, b = color[:3]
    _tamil_candidates = [
        Path.home() / "Library/Fonts/NotoSerifTamil-VariableFont_wdth,wght.ttf",
        Path("/Library/Fonts/NotoSerifTamil-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSerifTamil-Regular.ttf"),
    ]
    font_path = next((p for p in _tamil_candidates if p.exists()), _tamil_candidates[0])
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
@font-face{{font-family:'NotoTamil';src:url('file://{font_path}');font-weight:400;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;display:inline-block;padding:4px 6px;}}
span{{font-family:'NotoTamil',serif;font-size:{font_size}px;font-weight:400;
      color:rgb({r},{g},{b});white-space:nowrap;line-height:1.4;}}
</style></head><body><span>{text}</span></body></html>"""

    _tmpdir = Path(tempfile.gettempdir())
    html_p  = _tmpdir / "_ta_preview.html"
    png_p   = _tmpdir / "_ta_preview.png"
    html_p.write_text(html, encoding="utf-8")
    est_w  = font_size * (len(text) + 4) * 2
    est_h  = font_size * 3
    subprocess.run(
        [CHROME, "--headless=new",
         f"--screenshot={png_p}",
         f"--window-size={est_w},{est_h}",
         "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         "--default-background-color=00000000",
         str(html_p)],
        capture_output=True, timeout=25,
    )
    rendered = Image.open(png_p).convert("RGBA")
    bbox = rendered.getbbox()
    if bbox:
        rendered = rendered.crop(bbox)
    html_p.unlink(missing_ok=True)
    png_p.unlink(missing_ok=True)
    return rendered


# ── Helpers ────────────────────────────────────────────────────────────────

def load_icon(size: int) -> Image.Image:
    with Image.open(ICON_PATH) as ic:
        return ic.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def ruled_lines(draw: ImageDraw.ImageDraw,
                x0: int, x1: int, y0: int, y1: int,
                step: int = 30) -> None:
    y = y0
    while y <= y1:
        draw.line([(x0, y), (x1, y)], fill=RULE, width=1)
        y += step


def badge(draw: ImageDraw.ImageDraw, x: int, y: int,
          label: str, f: ImageFont.FreeTypeFont) -> int:
    tw  = int(f.getlength(label))
    bw  = tw + 52
    bh  = 52
    box = (x, y, x + bw, y + bh)
    draw.rounded_rectangle(box, radius=13,
                           fill=BADGE_BG, outline=BADGE_BORDER, width=2)
    draw.text((x + bw // 2, y + bh // 2), label,
              font=f, fill=BADGE_TEXT, anchor="mm")
    return bw


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:

    # ── Base canvas ─────────────────────────────────────────────────────
    img  = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # ── White panel with green border ────────────────────────────────────
    PAD = 40
    draw.rounded_rectangle(
        [(PAD, PAD), (WIDTH - PAD, HEIGHT - PAD)],
        radius=28, fill=PANEL, outline=PANEL_BORDER, width=5,
    )

    # ── Vertical separator inside panel ─────────────────────────────────
    draw.line([(368, PAD + 48), (368, HEIGHT - PAD - 48)],
              fill=(*MID_GREEN[:3], 80), width=1)

    # ── LEFT ZONE — icon + name ──────────────────────────────────────────
    ICON_SZ = 180
    ix = PAD + (368 - PAD - ICON_SZ) // 2   # centred in left zone
    iy = (HEIGHT - ICON_SZ) // 2 - 30

    icon_img = load_icon(ICON_SZ)
    img.alpha_composite(icon_img, (ix, iy))

    # App name under icon — stacked vertically (inline Tamil overflows left zone)
    nm_en    = font_bold(28)
    en_text  = "Neight"
    en_w     = int(nm_en.getlength(en_text))
    left_w   = 368 - PAD         # usable left-zone width (328 px)
    ny       = iy + ICON_SZ + 20

    draw.text((PAD + (left_w - en_w) // 2, ny), en_text,
              font=nm_en, fill=TITLE_COLOR)

    ta_img = render_tamil("சொல்வெளி", 30, ACCENT)
    ta_x   = PAD + (left_w - ta_img.width) // 2
    img.alpha_composite(ta_img, (max(PAD, ta_x), ny + 40))

    # ── RIGHT ZONE — text ────────────────────────────────────────────────
    RX = 392   # right zone left margin
    RM = WIDTH - PAD - 44
    ty = PAD + 82

    # Tagline
    tl_font = font_bold(60)
    draw.text((RX, ty), "Write into the night.", font=tl_font, fill=TITLE_COLOR)

    # Sub-tagline
    sl_font = font_regular(33)
    draw.text((RX, ty + 76), "Notepad, reimagined.", font=sl_font, fill=ACCENT)

    # Horizontal rule
    draw.line([(RX, ty + 130), (RM, ty + 130)],
              fill=(*MID_GREEN[:3], 100), width=1)

    # Body
    body_font = font_regular(28)
    draw.text((RX, ty + 150),
              "Built to feel at home on both Windows and macOS.",
              font=body_font, fill=TEXT_COLOR)
    draw.text((RX, ty + 190),
              "For Writers and Engineers alike.",
              font=body_font, fill=TEXT_COLOR)

    # Platform badges
    badge_font = font_bold(23)
    badge_y    = ty + 262
    bx         = RX
    for label in ("Windows", "macOS"):
        bw  = badge(draw, bx, badge_y, label, badge_font)
        bx += bw + 16

    # Free & Open Source
    oss_font = font_bold(23)
    draw.text((RM, badge_y + 26), "Free & Open Source",
              font=oss_font, fill=ACCENT, anchor="rm")

    # Author credit
    credit_font = font_regular(20)
    draw.text((RX, HEIGHT - PAD - 44), "Download from neight.app",
              font=credit_font, fill=ACCENT_DIM)

    # ── Save ──────────────────────────────────────────────────────────────
    img.convert("RGB").save(OUT_PATH, quality=95)
    print(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
