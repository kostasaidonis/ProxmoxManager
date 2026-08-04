"""Generate the Proxmox Quick Connect application icon (quick.ico).

Distinct from the main app icon: a lightning bolt inside a monitor screen,
on a deep-teal gradient background with cyan accent.
"""
from PIL import Image, ImageDraw


def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = size // 10
    radius = size // 6

    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(15, 32, 39, 255),
    )

    # Monitor screen outline
    sx0 = margin + size // 7
    sy0 = margin + size // 7
    sx1 = size - margin - size // 7
    sy1 = int(size * 0.62)
    screen_r = max(2, size // 18)
    d.rounded_rectangle(
        [sx0, sy0, sx1, sy1],
        radius=screen_r,
        outline=(0, 210, 255, 255),
        width=max(2, size // 30),
    )

    # Monitor stand
    stand_w = size // 8
    stand_h = size // 14
    stand_x0 = (size - stand_w) // 2
    stand_y0 = sy1 + max(2, size // 40)
    d.rounded_rectangle(
        [stand_x0, stand_y0, stand_x0 + stand_w, stand_y0 + stand_h],
        radius=max(1, stand_h // 4),
        fill=(0, 210, 255, 220),
    )
    # base
    base_w = size // 4
    base_h = max(2, size // 24)
    base_x0 = (size - base_w) // 2
    base_y0 = stand_y0 + stand_h
    d.rounded_rectangle(
        [base_x0, base_y0, base_x0 + base_w, base_y0 + base_h],
        radius=max(1, base_h // 3),
        fill=(0, 210, 255, 220),
    )

    # Lightning bolt inside screen
    cx = (sx0 + sx1) // 2
    cy = (sy0 + sy1) // 2
    bolt_h = int((sy1 - sy0) * 0.55)
    bolt_w = bolt_h // 2

    bolt_pts = [
        (cx + bolt_w // 2, cy - bolt_h // 2),
        (cx - bolt_w // 4, cy),
        (cx + bolt_w // 8, cy),
        (cx - bolt_w // 2, cy + bolt_h // 2),
        (cx + bolt_w // 4, cy),
        (cx - bolt_w // 8, cy),
    ]
    d.polygon(bolt_pts, fill=(0, 210, 255, 255))

    return img


sizes = [16, 32, 48, 64, 128, 256]
icons = [make_icon(s) for s in sizes]
icons[0].save(
    "quick.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
print("quick.ico created")