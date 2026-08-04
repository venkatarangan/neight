#!/usr/bin/env python3
"""
Generate the PNG logo assets required by packaging/AppxManifest.xml.template
for the Microsoft Store (MSIX) package, from the existing neight.ico.

Run from anywhere; writes into packaging/msix_assets/Assets/.
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICO_PATH = ROOT / "neight.ico"
OUT_DIR = ROOT / "packaging" / "msix_assets" / "Assets"

# name -> (canvas width, canvas height, square logo size drawn inside it)
ASSETS = {
    "Square44x44Logo.png": (44, 44, 44),
    "Square71x71Logo.png": (71, 71, 71),
    "Square150x150Logo.png": (150, 150, 150),
    "Square310x310Logo.png": (310, 310, 310),
    "StoreLogo.png": (50, 50, 50),
    "Wide310x150Logo.png": (310, 150, 110),
}


def load_source_icon() -> Image.Image:
    im = Image.open(ICO_PATH)
    sizes = im.info.get("sizes", [im.size])
    largest = max(sizes, key=lambda wh: wh[0] * wh[1])
    im.size = largest
    im.load()
    return im.convert("RGBA")


def render(source: Image.Image, canvas_w: int, canvas_h: int, logo_size: int) -> Image.Image:
    logo = source.resize((logo_size, logo_size), Image.LANCZOS)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    x = (canvas_w - logo_size) // 2
    y = (canvas_h - logo_size) // 2
    canvas.paste(logo, (x, y), logo)
    return canvas


def main() -> None:
    if not ICO_PATH.exists():
        raise SystemExit(f"Source icon not found: {ICO_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = load_source_icon()
    print(f"Source: {ICO_PATH} ({source.size[0]}x{source.size[1]})")
    for filename, (cw, ch, logo_size) in ASSETS.items():
        img = render(source, cw, ch, logo_size)
        out_path = OUT_DIR / filename
        img.save(out_path, "PNG")
        print(f"  -> {out_path.relative_to(ROOT)}  ({cw}x{ch})")
    print("\nDone. These are placeholder-quality assets scaled from the app")
    print("icon — good enough for submission and testing. Replace with")
    print("hand-designed tile art later if desired.")


if __name__ == "__main__":
    main()
