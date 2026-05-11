#!/usr/bin/env python3
"""
gen_neight_icon_white.py — Trial: white-background icon variant for Neight.

Design: white square, "N" in lighter green (#1E7A4E), "8" in darker green (#0C3520).
Outputs: neight-white.ico  /  neight-white.icns  (siblings of neight.ico/.icns)
Does NOT touch neight.ico or neight.icns.
"""

import io, struct, subprocess, shutil, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent   # project root (parent of design/)
WORK = Path(tempfile.mkdtemp(prefix="neight_icon_white_"))


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
    raise RuntimeError("Chrome/Chromium not found.")


CHROME = _find_chrome()


# ── SVG template ──────────────────────────────────────────────────────────────
# White background; N in #1E7A4E (mid-green), 8 in #0C3520 (dark-green).
# A very faint green divider at x=49..51 keeps the two-halves feel.

def _body(size: int, rounded: bool) -> str:
    clip_def  = '<clipPath id="rnd"><rect width="100" height="100" rx="22"/></clipPath>' if rounded else ""
    clip_open = '<g clip-path="url(#rnd)">' if rounded else "<g>"
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{size}px;height:{size}px;overflow:hidden;background:transparent;}}
</style></head><body>
<svg width="{size}" height="{size}" viewBox="0 0 100 100"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    {clip_def}
    <clipPath id="lft"><rect x="0"  y="0" width="49"  height="100"/></clipPath>
    <clipPath id="rgt"><rect x="51" y="0" width="49" height="100"/></clipPath>
  </defs>
  {clip_open}
    <!-- White background -->
    <rect x="0" y="0" width="100" height="100" fill="white"/>
    <!-- Subtle centre divider -->
    <rect x="49" y="8" width="2" height="84" fill="#1E7A4E" opacity="0.18"/>
    <!-- N in lighter green -->
    <text x="25" y="70"
          font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="68" font-weight="900" fill="#1E7A4E"
          text-anchor="middle" clip-path="url(#lft)">N</text>
    <!-- 8 in darker green -->
    <text x="75" y="70"
          font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="68" font-weight="900" fill="#0C3520"
          text-anchor="middle" clip-path="url(#rgt)">8</text>
  </g>
</svg>
</body></html>"""


def render(size: int, rounded: bool) -> Image.Image:
    tag    = "r" if rounded else "s"
    html_p = WORK / f"_tmp_{tag}_{size}.html"
    png_p  = WORK / f"_tmp_{tag}_{size}.png"
    html_p.write_text(_body(size, rounded), encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new",
         f"--screenshot={png_p}",
         f"--window-size={size},{size}",
         "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         "--default-background-color=00000000",
         str(html_p)],
        capture_output=True, timeout=25,
    )
    img = Image.open(png_p).convert("RGBA").crop((0, 0, size, size))
    html_p.unlink(missing_ok=True)
    png_p.unlink(missing_ok=True)
    return img


# ── Size tables ───────────────────────────────────────────────────────────────

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

ICNS_SPEC = {
    "icon_16x16.png":       16,
    "icon_16x16@2x.png":    32,
    "icon_32x32.png":       32,
    "icon_32x32@2x.png":    64,
    "icon_128x128.png":    128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png":    256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png":    512,
    "icon_512x512@2x.png":1024,
}

# ── Render ────────────────────────────────────────────────────────────────────

ico_sizes_set  = set(ICO_SIZES)
icns_sizes_set = set(ICNS_SPEC.values())

print("Rendering rounded (ICO) variants …")
ico_imgs = {}
for s in sorted(ico_sizes_set):
    print(f"  {s:4d}px")
    ico_imgs[s] = render(s, rounded=True)

print("Rendering full-square (ICNS) variants …")
icns_imgs = {}
for s in sorted(icns_sizes_set):
    print(f"  {s:4d}px")
    icns_imgs[s] = render(s, rounded=False)


# ── ICO writer ────────────────────────────────────────────────────────────────

def write_ico(size_map: dict, path: Path) -> None:
    sizes = sorted(size_map)
    pngs  = {}
    for s in sizes:
        buf = io.BytesIO()
        size_map[s].save(buf, "PNG")
        pngs[s] = buf.getvalue()

    n      = len(sizes)
    offset = 6 + n * 16

    header    = struct.pack("<HHH", 0, 1, n)
    directory = b""
    data      = b""

    for s in sizes:
        w = h = s if s < 256 else 0
        directory += struct.pack("<BBBBHHII",
            w, h, 0, 0, 1, 32,
            len(pngs[s]), offset,
        )
        data   += pngs[s]
        offset += len(pngs[s])

    path.write_bytes(header + directory + data)


print("\nPacking ICO …")
ico_path = ROOT / "neight-white.ico"
write_ico(ico_imgs, ico_path)
print(f"  → {ico_path}  ({ico_path.stat().st_size:,} bytes)")


# ── ICNS via iconutil ─────────────────────────────────────────────────────────

print("\nPacking ICNS …")
iconset = WORK / "neight-white.iconset"
iconset.mkdir(exist_ok=True)

for fname, size in ICNS_SPEC.items():
    icns_imgs[size].save(iconset / fname, "PNG")

icns_path = ROOT / "neight-white.icns"
subprocess.run(
    ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
    check=True,
)
shutil.rmtree(iconset)
print(f"  → {icns_path}  ({icns_path.stat().st_size:,} bytes)")

shutil.rmtree(WORK, ignore_errors=True)
print("\nAll done ✓")
print(f"  {ico_path}")
print(f"  {icns_path}")
