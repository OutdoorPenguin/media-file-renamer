# make_icon.py
# Generates the CDL Extractor app icon and converts to .icns

import subprocess
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.run([
        '/Users/racelhmcintire/PycharmProjects/Claude/.venv/bin/pip',
        'install', 'Pillow'
    ])
    from PIL import Image, ImageDraw, ImageFont

def draw_icon(size):
    """Draws the CDL Extractor icon at the given size."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = size * 0.08
    r = size * 0.18

    # Background rounded rect
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=int(r),
        fill=(26, 26, 26, 255)
    )

    # CDL label
    label_y = size * 0.18
    font_size = max(int(size * 0.12), 8)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", font_size)
    except:
        font = ImageFont.load_default()

    d.text(
        (size / 2, label_y),
        "CDL",
        font=font,
        fill=(102, 102, 102, 255),
        anchor="mm"
    )

    # Waveform
    cx = size / 2
    cy = size / 2
    w = size * 0.65
    step = w / 8

    points = [
        (cx - w/2,          cy - size*0.12),
        (cx - w/2 + step,   cy - size*0.12),
        (cx - w/2 + step,   cy + size*0.12),
        (cx - w/2 + step*2, cy + size*0.12),
        (cx - w/2 + step*2, cy - size*0.18),
        (cx - w/2 + step*3, cy - size*0.18),
        (cx - w/2 + step*3, cy + size*0.07),
        (cx - w/2 + step*4, cy + size*0.07),
        (cx - w/2 + step*4, cy - size*0.10),
        (cx + w/2,          cy - size*0.10),
    ]

    lw = max(int(size * 0.025), 1)
    for i in range(len(points) - 1):
        d.line([points[i], points[i+1]], fill=(229, 9, 20, 255), width=lw)

    # Start and end dots
    dot_r = lw * 1.5
    d.ellipse([
        points[0][0] - dot_r, points[0][1] - dot_r,
        points[0][0] + dot_r, points[0][1] + dot_r
    ], fill=(229, 9, 20, 255))
    d.ellipse([
        points[-1][0] - dot_r, points[-1][1] - dot_r,
        points[-1][0] + dot_r, points[-1][1] + dot_r
    ], fill=(229, 9, 20, 255))

    # Bottom red line
    line_y = size * 0.72
    lpad = size * 0.18
    d.line(
        [(lpad, line_y), (size - lpad, line_y)],
        fill=(229, 9, 20, 255),
        width=lw
    )

    return img

# --- Generate all required icon sizes ---
iconset = Path("CDL_Extractor.iconset")
iconset.mkdir(exist_ok=True)

sizes = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}

for filename, size in sizes.items():
    img = draw_icon(size)
    img.save(iconset / filename)
    print(f"Generated {filename}")

# --- Convert to .icns ---
result = subprocess.run(
    ["iconutil", "-c", "icns", str(iconset)],
    capture_output=True, text=True
)

if result.returncode == 0:
    print("\n✅ CDL_Extractor.icns created successfully!")
else:
    print(f"\n❌ Error: {result.stderr}")