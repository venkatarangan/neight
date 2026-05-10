#!/usr/bin/env python3
"""
Generate neight.ico (Windows) and neight.icns (macOS) for V6 Split-Halves icon.

ICO  → rounded corners + transparent outside  (Windows 10/11 taskbar)
ICNS → full-square fill, no pre-rounding       (macOS applies squircle mask)
"""

import io, struct, subprocess, shutil, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent   # project root (parent of design/)
WORK = Path(tempfile.mkdtemp(prefix="neight_icon_"))


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

# ── SVG templates ─────────────────────────────────────────────────────────

def _body(size: int, rounded: bool) -> str:
    clip_open  = '<g clip-path="url(#rnd)">' if rounded else "<g>"
    clip_def   = '<clipPath id="rnd"><rect width="100" height="100" rx="22"/></clipPath>' if rounded else ""
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
    <rect x="0"  y="0" width="49"  height="100" fill="#1E7A4E"/>
    <rect x="51" y="0" width="49" height="100"  fill="#0C3520"/>
    <rect x="49" y="0" width="2"  height="100"  fill="white" opacity="0.12"/>
    <text x="25" y="70"
          font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="68" font-weight="900" fill="white"
          text-anchor="middle" clip-path="url(#lft)">N</text>
    <text x="75" y="70"
          font-family="'Helvetica Neue',Arial,sans-serif"
          font-size="68" font-weight="900" fill="white"
          text-anchor="middle" clip-path="url(#rgt)">8</text>
  </g>
</svg>
</body></html>"""


def render(size: int, rounded: bool) -> Image.Image:
    tag      = "r" if rounded else "s"
    html_p   = WORK / f"_tmp_{tag}_{size}.html"
    png_p    = WORK / f"_tmp_{tag}_{size}.png"
    html_p.write_text(_body(size, rounded), encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new",
         f"--screenshot={png_p}",
         f"--window-size={size},{size}",
         "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         str(html_p)],
        capture_output=True, timeout=25,
    )
    img = Image.open(png_p).convert("RGBA").crop((0, 0, size, size))
    html_p.unlink(missing_ok=True)
    png_p.unlink(missing_ok=True)
    return img


# ── Size tables ───────────────────────────────────────────────────────────

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

ICNS_SPEC = {                          # filename → pixel dimension
    "icon_16x16.png":        16,
    "icon_16x16@2x.png":     32,
    "icon_32x32.png":        32,
    "icon_32x32@2x.png":     64,
    "icon_128x128.png":     128,
    "icon_128x128@2x.png":  256,
    "icon_256x256.png":     256,
    "icon_256x256@2x.png":  512,
    "icon_512x512.png":     512,
    "icon_512x512@2x.png": 1024,
}

# ── Render ────────────────────────────────────────────────────────────────

ico_sizes_set  = set(ICO_SIZES)
icns_sizes_set = set(ICNS_SPEC.values())
all_sizes      = sorted(ico_sizes_set | icns_sizes_set)

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


# ── ICO writer (PNG-in-ICO, ARGB, Vista+) ────────────────────────────────

def write_ico(size_map: dict, path: Path) -> None:
    """Pack a {size: PIL.Image} dict into a PNG-in-ICO file."""
    sizes = sorted(size_map)
    pngs  = {}
    for s in sizes:
        buf = io.BytesIO()
        size_map[s].save(buf, "PNG")
        pngs[s] = buf.getvalue()

    n      = len(sizes)
    offset = 6 + n * 16          # ICONDIR header + ICONDIRENTRY × n

    header    = struct.pack("<HHH", 0, 1, n)
    directory = b""
    data      = b""

    for s in sizes:
        w = h = s if s < 256 else 0   # ICO spec: 0 encodes 256
        directory += struct.pack("<BBBBHHII",
            w, h,           # width, height
            0,              # palette colours (0 = truecolour)
            0,              # reserved
            1,              # colour planes
            32,             # bits per pixel
            len(pngs[s]),   # byte size of image data
            offset,         # byte offset to image data
        )
        data   += pngs[s]
        offset += len(pngs[s])

    path.write_bytes(header + directory + data)


print("\nPacking ICO …")
ico_path = ROOT / "neight.ico"
write_ico(ico_imgs, ico_path)
print(f"  → {ico_path}  ({ico_path.stat().st_size:,} bytes)")


# ── ICNS via iconutil ─────────────────────────────────────────────────────

print("\nPacking ICNS …")
iconset = WORK / "neight.iconset"
iconset.mkdir(exist_ok=True)

for fname, size in ICNS_SPEC.items():
    icns_imgs[size].save(iconset / fname, "PNG")

icns_path = ROOT / "neight.icns"
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
