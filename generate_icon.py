"""Generate the ProxmoxManager application icon (app.ico)."""
from PIL import Image, ImageDraw, ImageFont

def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded rectangle background — dark charcoal
    margin = size // 10
    radius = size // 6
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(26, 26, 26, 255),
    )

    # Magnifying glass circle (cyan accent)
    cx = size // 2
    cy = int(size * 0.42)
    r = int(size * 0.22)
    ring = max(2, size // 32)
    d.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(0, 120, 212, 255),
        width=ring,
    )

    # Server rack bars inside the lens
    bar_w = int(r * 1.1)
    bar_h = max(2, size // 20)
    gap = max(1, size // 40)
    start_y = cy - bar_h - gap // 2
    for i in range(3):
        y = start_y + i * (bar_h + gap)
        x0 = cx - bar_w // 2
        d.rounded_rectangle(
            [x0, y, x0 + bar_w, y + bar_h],
            radius=max(1, bar_h // 3),
            fill=(232, 232, 232, 220),
        )

    # Magnifying glass handle (bottom-right diagonal)
    hl = int(size * 0.18)
    hw = max(2, size // 24)
    hx0 = cx + int(r * 0.7)
    hy0 = cy + int(r * 0.7)
    hx1 = hx0 + hl
    hy1 = hy0 + hl
    d.line(
        [hx0, hy0, hx1, hy1],
        fill=(0, 120, 212, 255),
        width=hw,
    )
    # Round the handle endpoints
    d.ellipse(
        [hx0 - hw // 2, hy0 - hw // 2, hx0 + hw // 2, hy0 + hw // 2],
        fill=(0, 120, 212, 255),
    )
    d.ellipse(
        [hx1 - hw // 2, hy1 - hw // 2, hx1 + hw // 2, hy1 + hw // 2],
        fill=(0, 120, 212, 255),
    )

    # Green status dot (top-right corner)
    dot_r = size // 12
    dx = size - margin - dot_r - 2
    dy = margin + dot_r + 2
    d.ellipse(
        [dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
        fill=(76, 175, 80, 255),
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