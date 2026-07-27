"""Generate the ProxmoxManager application icon (app.ico)."""
from PIL import Image, ImageDraw, ImageFont

def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded rectangle background — dark blue
    margin = size // 10
    radius = size // 6
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(13, 71, 161, 255),  # Material Blue 800
    )

    # Server rack bars (white, representing VMs)
    bar_w = size // 3
    bar_h = size // 14
    gap = size // 28
    start_y = size // 3
    for i in range(3):
        y = start_y + i * (bar_h + gap)
        x0 = (size - bar_w) // 2
        d.rounded_rectangle(
            [x0, y, x0 + bar_w, y + bar_h],
            radius=bar_h // 3,
            fill=(255, 255, 255, 230),
        )

    # Green status dot (top-right)
    dot_r = size // 10
    cx, cy = size - margin - dot_r, margin + dot_r
    d.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=(76, 175, 80, 255),  # Material Green 500
    )

    return img

# Generate multiple sizes and save as ICO
sizes = [16, 32, 48, 64, 128, 256]
icons = [make_icon(s) for s in sizes]
icons[0].save(
    "app.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
print("app.ico created")