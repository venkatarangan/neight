# Modified Neighty notepad icon generator using the green color palette from the favicon.
# Design retained: night background, moon accent, and notepad layout with green tones.

from PIL import Image, ImageDraw, ImageFilter

# Parameters
SIZE = 1024
BG = (0, 0, 0, 0)

# Green palette from favicon
GREENS = [
    (109, 166, 64, 255),   # #6DA640
    (140, 194, 110, 255),  # #8CC26E
    (109, 167, 64, 255),   # #6DA740
    (140, 193, 110, 255),  # #8CC16E
    (108, 166, 63, 255),   # #6CA63F
    (108, 165, 63, 255),   # #6CA53F
    (110, 167, 65, 255),   # #6EA741
    (139, 192, 109, 255),  # #8BC06D
    (139, 191, 108, 255),  # #8BBF6C
    (109, 166, 63, 255),   # #6DA63F
]

# Assign functional colors from the green palette
NIGHT = GREENS[4]                # Slightly darker green for background
MOON = (255, 225, 160, 255)      # Warm moonlight (kept same)
PAGE = (245, 246, 250, 255)      # Notepad page
PAGE_LINE = (200, 205, 220, 255)
HEADER = GREENS[1]               # Light green header bar
HIGHLIGHT = (255, 255, 255, 30)  # Soft glow overlay
ACCENT = GREENS[0]               # Rich medium green for pen/accent

# Create base
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

# Background (green square with glow)
rounded_rect(img, (pad, pad, SIZE - pad, SIZE - pad), radius=int(SIZE*0.12), fill=NIGHT, shadow=True)

# Subtle glow to simulate moonlight
overlay = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
ov = ImageDraw.Draw(overlay)
ov.ellipse((SIZE*0.45, SIZE*0.1, SIZE*1.1, SIZE*0.8), fill=(255,255,255,40))
img = Image.alpha_composite(img, overlay)

# Notepad page
inset = int(SIZE * 0.16)
page_radius = int(SIZE * 0.06)
page_box = (pad + inset, pad + inset, SIZE - pad - inset, SIZE - pad - inset)
rounded_rect(img, page_box, radius=page_radius, fill=PAGE, shadow=True, shadow_offset=(0,6), shadow_blur=18, shadow_color=(0,0,0,80))

# Header (light green header bar)
x0, y0, x1, y1 = page_box
header_h = int((y1 - y0) * 0.14)
header_box = (x0, y0, x1, y0 + header_h)
rounded_rect(img, header_box, radius=page_radius, fill=HEADER)

# Ruled lines on notepad
line_left = x0 + int((x1 - x0) * 0.08)
line_right = x1 - int((x1 - x0) * 0.08)
line_top = y0 + header_h + int((y1 - y0) * 0.06)
line_spacing = int((y1 - line_top) * 0.12)
for y in range(line_top, y1 - int((y1 - y0) * 0.10), line_spacing):
    draw.line((line_left, y, line_right, y), fill=PAGE_LINE, width=max(1, SIZE//256))

# Moon in corner
moon_r = int(SIZE * 0.12)
mx = SIZE - int(SIZE * 0.28)
my = pad + int(SIZE * 0.22)
draw.ellipse((mx - moon_r, my - moon_r, mx + moon_r, my + moon_r), fill=MOON)
# Crescent shadow
draw.ellipse((mx - moon_r*0.7, my - moon_r, mx + moon_r*0.7, my + moon_r), fill=NIGHT)

# Pen/accent stripe at bottom
pen_len = int((x1 - x0) * 0.28)
pen_w = int(pen_len * 0.10)
pen_x0 = x0 + int((x1 - x0) * 0.10)
pen_y0 = y1 - int((y1 - y0) * 0.15)
pen_x1 = pen_x0 + pen_len
pen_y1 = pen_y0 + pen_w
draw.rounded_rectangle((pen_x0, pen_y0, pen_x1, pen_y1), radius=int(pen_w/2), fill=ACCENT)

# Gentle gradient overlay for depth
grad = Image.new("L", (1, SIZE))
for y in range(SIZE):
    grad.putpixel((0,y), int(255 * (y/SIZE) * 0.5))
grad = grad.resize((SIZE, SIZE))
grad_overlay = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
grad_overlay.putalpha(grad)
img = Image.alpha_composite(img, grad_overlay)

# Export ICO
ico_sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256),(512,512)]
ico_path = "neight_green.ico"
img.save(ico_path, format="ICO", sizes=ico_sizes)

ico_path

