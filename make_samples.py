"""Make the sample images used in the README."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, BAR = 620, 408, 28


def sheet(items, columns, output):
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (WIDTH * columns, (HEIGHT + BAR) * rows), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("arial.ttf", 18)
    for i, (path, label) in enumerate(items):
        x, y = (i % columns) * WIDTH, (i // columns) * (HEIGHT + BAR)
        draw.text((x + 6, y + 4), label, fill="#1f2933", font=font)
        canvas.paste(Image.open(path).convert("RGB").resize((WIDTH - 4, HEIGHT), Image.LANCZOS), (x + 2, y + BAR))
    Path(output).parent.mkdir(exist_ok=True)
    canvas.save(output, quality=88)


local = "results/sun_4b_local/01_villa__"
sheet([("photos/01_villa.jpg", "Original"), (local + "sun_front.png", "Sun behind the camera"),
       (local + "sun_back.png", "Sun behind the building"), (local + "sun_top.png", "Sun straight above"),
       (local + "sun_left_low.png", "Low sun from the left"), (local + "sun_right_low.png", "Low sun from the right"),
       (local + "sunset_left.png", "Sunset on the left"), (local + "sunset_right.png", "Sunset on the right")],
      2, "docs/villa_sun_angles.jpg")

block = "03_concrete_block__right"
sheet([("photos/03_concrete_block.jpg", "Original"), (f"results/sun_4b_local/{block}_color.png", "Sun-Direction 4B"),
       (f"results/qwen_3d/{block}.png", "Qwen 3D Lighting (added flower pots)"),
       (f"results/kontext/{block}.png", "Kontext (shadow didn't move)")], 2, "docs/tools_side_by_side.jpg")

room = "02_living_room__back_left"
sheet([("photos/02_living_room.jpg", "Original"), (f"results/sun_direction/{room}.png", "Sun-Direction 9B (furniture changed)"),
       (f"results/kontext/{room}.png", "Kontext (new view, all orange)"),
       (f"results/transfer_sun_direction/{room}.png", "My light transfer (objects safe, weak light)")],
      2, "docs/living_room.jpg")
print("done")
