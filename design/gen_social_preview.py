from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1280, 640
CANVAS_BG = (244, 247, 242, 255)
PANEL_BG = (253, 255, 252, 255)
PANEL_BORDER = (126, 154, 98, 255)
TITLE_COLOR = (28, 42, 27, 255)
TEXT_COLOR = (45, 62, 42, 255)
ACCENT = (108, 166, 63, 255)
ACCENT_LIGHT = (165, 210, 130, 255)

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "neight.ico"
OUT_PATH = ROOT / "social-preview-neight.png"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/SFNS.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
        )

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)

    return ImageFont.load_default()


def draw_round_rect(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def load_icon(size: int) -> Image.Image:
    with Image.open(ICON_PATH) as icon:
        icon = icon.convert("RGBA")
        return icon.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), CANVAS_BG)
    draw = ImageDraw.Draw(img)

    # Atmospheric background glow.
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((760, -80, 1380, 560), fill=(185, 221, 146, 100))
    glow_draw.ellipse((-220, 290, 500, 900), fill=(145, 190, 108, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(42))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    panel_margin_x = 56
    panel_margin_y = 42
    panel_box = (panel_margin_x, panel_margin_y, WIDTH - panel_margin_x, HEIGHT - panel_margin_y)
    draw_round_rect(draw, panel_box, radius=28, fill=PANEL_BG, outline=PANEL_BORDER, width=6)

    # Decorative lines inspired by GitHub's social card safe area template.
    draw.line((82, 118, WIDTH - 82, 118), fill=(153, 182, 126, 160), width=2)
    draw.line((82, HEIGHT - 118, WIDTH - 82, HEIGHT - 118), fill=(153, 182, 126, 160), width=2)

    left = 122
    top = 140

    icon = load_icon(176)
    img.alpha_composite(icon, (left, top))

    title_font = load_font(94, bold=True)
    subtitle_font = load_font(44, bold=True)
    body_font = load_font(36, bold=False)
    badge_font = load_font(30, bold=True)

    text_x = left + 210
    draw.text((text_x, top + 8), "Neight", font=title_font, fill=TITLE_COLOR)
    draw.text((text_x, top + 112), "Write into the night. Notepad, reimagined.", font=subtitle_font, fill=ACCENT)

    body = "Built to feel at home on both Windows 11 and Mac OS."
    draw.text((left, top + 250), body, font=body_font, fill=TEXT_COLOR)

    badge_y = top + 330
    win_badge = (left, badge_y, left + 320, badge_y + 82)
    mac_badge = (left + 344, badge_y, left + 664, badge_y + 82)

    draw_round_rect(draw, win_badge, radius=18, fill=(231, 241, 222, 255), outline=(133, 171, 102, 255), width=3)
    draw_round_rect(draw, mac_badge, radius=18, fill=(231, 241, 222, 255), outline=(133, 171, 102, 255), width=3)

    draw.text((win_badge[0] + 28, win_badge[1] + 23), "Windows 11", font=badge_font, fill=TITLE_COLOR)
    draw.text((mac_badge[0] + 56, mac_badge[1] + 23), "Mac OS", font=badge_font, fill=TITLE_COLOR)

    # Free & Open Source callout - bottom right
    oss_font = load_font(32, bold=True)
    draw.text((WIDTH - 420, HEIGHT - 110), "Free & Open Source", font=oss_font, fill=ACCENT)

    # Bottom-right app mark.
    mark = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)
    md.ellipse((22, 22, 218, 218), fill=(108, 166, 63, 56), outline=(108, 166, 63, 150), width=3)
    md.ellipse((68, 68, 172, 172), fill=ACCENT_LIGHT)
    md.ellipse((102, 78, 186, 162), fill=PANEL_BG)
    mark = mark.filter(ImageFilter.GaussianBlur(0.4))
    img.alpha_composite(mark, (WIDTH - 320, HEIGHT - 290))

    img.save(OUT_PATH)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
