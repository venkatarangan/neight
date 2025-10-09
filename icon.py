# pip install Pillow
from PIL import Image, ImageDraw, ImageFilter

# Icon parameters
SIZE = 1024  # Base size for crisp downscaling
BG = (0, 0, 0, 0)
ORANGE = (249, 115, 22, 255)   # Tailwind orange-500
ORANGE_DARK = (234, 88, 12, 255)  # orange-600
ORANGE_LIGHT = (253, 186, 116, 255)  # orange-300
WHITE = (255, 255, 255, 255)
GRAY = (203, 213, 225, 255)  # slate-300
GRAY_DARK = (100, 116, 139, 255)  # slate-500

# Create base with transparency
img = Image.new("RGBA", (SIZE, SIZE), BG)
draw = ImageDraw.Draw(img)

# Helper to draw rounded rectangle with shadow
def rounded_rect(image, xy, radius, fill, shadow=False, shadow_offset=(0, 8), shadow_blur=24, shadow_color=(0,0,0,100)):
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    rect_layer = Image.new("RGBA", (w, h), (0,0,0,0))
    rl_draw = ImageDraw.Draw(rect_layer)
    rl_draw.rounded_rectangle((0,0,w,h), radius=radius, fill=fill)
    if shadow:
        sh_layer = Image.new("RGBA", (w, h), (0,0,0,0))
        sh_draw = ImageDraw.Draw(sh_layer)
        sh_draw.rounded_rectangle((0,0,w,h), radius=radius, fill=shadow_color)
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
        image.alpha_composite(sh_layer, (x0 + shadow_offset[0], y0 + shadow_offset[1]))
    image.alpha_composite(rect_layer, (x0, y0))

pad = int(SIZE * 0.08)
# Background rounded square
rounded_rect(img, (pad, pad, SIZE - pad, SIZE - pad), radius=int(SIZE*0.12), fill=ORANGE, shadow=True)

# Inner subtle glossy overlay at top
overlay = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
ov = ImageDraw.Draw(overlay)
top_h = int(SIZE * 0.35)
ov.rounded_rectangle((pad, pad, SIZE - pad, pad + top_h), radius=int(SIZE*0.12), fill=(255,255,255,30))
img = Image.alpha_composite(img, overlay)

# Notepad page
inset = int(SIZE * 0.16)
page_radius = int(SIZE * 0.06)
page_box = (pad + inset, pad + inset, SIZE - pad - inset, SIZE - pad - inset)
rounded_rect(img, page_box, radius=page_radius, fill=WHITE, shadow=True, shadow_offset=(0,6), shadow_blur=18, shadow_color=(0,0,0,80))

# Page header strip
x0, y0, x1, y1 = page_box
header_h = int((y1 - y0) * 0.14)
header_box = (x0, y0, x1, y0 + header_h)
rounded_rect(img, header_box, radius=page_radius, fill=ORANGE_LIGHT)

# Spiral rings
rings = 6
ring_r = int(header_h * 0.22)
ring_gap = (x1 - x0 - 2*pad) // (rings - 1)
for i in range(rings):
    cx = x0 + pad + i * ring_gap
    cy = y0 + header_h // 2
    # Shadow ring
    draw.ellipse((cx - ring_r, cy - ring_r + 2, cx + ring_r, cy + ring_r + 2), fill=(0,0,0,40))
    # Metal ring
    draw.ellipse((cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r), fill=(230, 232, 235, 255), outline=(180, 184, 190, 255), width=2)

# Ruled lines on the page
line_left = x0 + int((x1 - x0) * 0.08)
line_right = x1 - int((x1 - x0) * 0.08)
line_top = y0 + header_h + int((y1 - y0) * 0.06)
line_spacing = int((y1 - line_top) * 0.12)
for y in range(line_top, y1 - int((y1 - y0) * 0.10), line_spacing):
    draw.line((line_left, y, line_right, y), fill=GRAY, width=max(1, SIZE//256))

# A subtle pencil glyph at bottom-right for identity
p_pad = int((x1 - x0) * 0.06)
p_len = int((x1 - x0) * 0.28)
px1 = x1 - p_pad
py1 = y1 - p_pad
px0 = px1 - p_len
py0 = py1 - int(p_len * 0.18)
# Pencil body
draw.rounded_rectangle((px0, py0, px1, py1), radius=int(p_len*0.08), fill=ORANGE_DARK)
# Pencil tip
tip_w = int(p_len * 0.18)
tri = [(px1 - tip_w, py0), (px1, (py0+py1)//2), (px1 - tip_w, py1)]
draw.polygon(tri, fill=(255, 236, 200, 255), outline=(180,140,100,255))
# Graphite
g_tip = [(px1 - tip_w//2, (py0+py1)//2 - tip_w//6), (px1, (py0+py1)//2), (px1 - tip_w//2, (py0+py1)//2 + tip_w//6)]
draw.polygon(g_tip, fill=(90,90,90,255))

# Corner fold on page
fold = int((x1 - x0) * 0.10)
fold_tri = Image.new("RGBA", (fold, fold), (0,0,0,0))
ft = ImageDraw.Draw(fold_tri)
ft.polygon([(0,0), (fold,0), (fold,fold)], fill=(245, 245, 245, 255))
ft.line([(0,0),(fold,fold)], fill=(220,220,220,255), width=max(1, SIZE//256))
img.alpha_composite(fold_tri.rotate(180), (x1 - fold, y1 - fold))

# Export ICO with multiple sizes for crispness
ico_sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256),(512,512)]

# Ensure opaque background inside the orange rounded square to avoid halo on dark themes
# Composite over a fully transparent canvas already done; keep as is for ICO with alpha.

ico_path = 'neight.ico'
img.save(ico_path, format='ICO', sizes=ico_sizes)

print(f"Created {ico_path} with sizes: {ico_sizes}")