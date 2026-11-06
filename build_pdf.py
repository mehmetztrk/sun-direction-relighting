"""Build the PDF report from the images in results/.

    python compare.py
    python build_pdf.py
"""
import io
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import compare

OUTPUT = "Mehmet_Ozturk_sun_direction_report.pdf"
REPO = "https://github.com/mehmetztrk/sun-direction-relighting"
PAGE_WIDTH = A4[0] - 28 * mm
DARK, GRAY, LINE, SOFT = (colors.HexColor(c) for c in ("#1f2933", "#52606d", "#d5dae0", "#f1f3f5"))

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")


def style(name, font="Arial", color=DARK, **kw):
    return ParagraphStyle(name, fontName=font, textColor=color, **kw)


TITLE = style("title", "Arial-Bold", fontSize=19, leading=23, spaceAfter=1 * mm)
SUB = style("sub", color=GRAY, fontSize=10, leading=13, spaceAfter=3 * mm)
H1 = style("h1", "Arial-Bold", fontSize=13, leading=16, spaceBefore=4 * mm, spaceAfter=1.2 * mm)
H2 = style("h2", "Arial-Bold", fontSize=10.5, leading=13, spaceBefore=2.5 * mm, spaceAfter=1 * mm)
BODY = style("body", fontSize=10, leading=14, spaceAfter=1.6 * mm)
BULLET = style("bullet", fontSize=10, leading=13.5, leftIndent=4 * mm, spaceAfter=1 * mm)
CELL = style("cell", fontSize=9, leading=11.5)
CELL_B = style("cell_b", "Arial-Bold", fontSize=9, leading=11.5)
CAPTION = style("caption", "Arial-Bold", fontSize=9, leading=11, spaceBefore=1 * mm)
NOTE = style("note", color=GRAY, fontSize=8.5, leading=10.5)


def text(body, s=BODY):
    return Paragraph(body, s)


def bullets(items):
    return [Paragraph(item, BULLET, bulletText="•") for item in items]


def table(rows, widths):
    t = Table([[text(str(c), CELL_B if i == 0 else CELL) for c in row] for i, row in enumerate(rows)],
              colWidths=[w * PAGE_WIDTH for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def picture(image, width, max_height=None):
    if not isinstance(image, PILImage.Image):
        image = PILImage.open(image).convert("RGB")
    image = image.copy()
    image.thumbnail((1300, 1300), PILImage.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=86)
    buffer.seek(0)
    height = width * image.height / image.width
    if max_height and height > max_height:
        width, height = width * max_height / height, max_height
    return Image(buffer, width, height)


def grid(items, columns=2, max_height=None):
    """items: (image path, caption, note). Big pictures with a short note under each."""
    width = PAGE_WIDTH / columns
    cells = [[picture(path, width - 6, max_height), text(caption, CAPTION), text(note, NOTE)]
             for path, caption, note in items]
    rows = [cells[i:i + columns] for i in range(0, len(cells), columns)]
    if len(rows[-1]) < columns:
        rows[-1] += [""] * (columns - len(rows[-1]))
    t = Table(rows, colWidths=[width] * columns)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def r(tool, photo, trial):
    return f"results/{tool}/{photo}__{trial}.png"


def intro():
    return [
        text("Moving the sun in architecture photos", TITLE),
        text(f"Mehmet Ozturk &nbsp;|&nbsp; Task for MyArchitectAI &nbsp;|&nbsp; "
             f'<a href="{REPO}" color="#1a5fb4">{REPO.replace("https://", "")}</a>', SUB),
        text("The short version", H1),
        text("I wanted to change where the sun comes from in a photo without changing the building. Nothing I tried "
             "does this perfectly. The best tool for outdoor shots was the Sun-Direction LoRA: it really moves the "
             "sun, and on the villa you can clearly see front, back, top and sunset light. But it still changes some "
             "materials, and indoors it changes the furniture. So I would launch it for exteriors only, with an "
             "automatic check in front of it."),
        text("What I used and why", H1),
        table([
            ["Tool", "Why I picked it", "How I ran it"],
            ["Sun-Direction LoRA (9B, then 4B)", "The only image tool I found made just for moving the sun", "Free Hugging Face Space, then on my own RTX 4070"],
            ["Qwen 3D Lighting", "You pick a light direction, and it can try interiors", "Free Hugging Face Space"],
            ["FLUX.1 Kontext", "A normal text-edit model, to see how far a plain prompt gets", "Free Hugging Face Space"],
            ["Light transfer (my own script)", "To keep the original pixels and only copy the new light", "Python, on my own computer"],
        ], [0.31, 0.42, 0.27]),
        text("How I used them", H1),
        *bullets([
            "I took three real photos from Unsplash: a villa, a concrete apartment block and a living room.",
            "I asked each tool to move the sun, then put every result next to the original.",
            "I wrote small Python scripts to send the photos, save the results and compare them.",
            "To judge a result I asked three things: did the light really change, did the building stay the same, "
            "and did single objects like the sofa stay the same? A score helped me sort results, but the final call was by eye.",
        ]),
        text("Time and cost per image", H1),
        table([
            ["Tool", "Time", "Cost for me"],
            ["Sun-Direction 9B (Space)", "20 to 26 s", "$0"],
            ["Sun-Direction 4B (my RTX 4070)", "73 to 116 s", "$0"],
            ["Qwen 3D Lighting (Space)", "6.5 to 17 s", "$0"],
            ["FLUX.1 Kontext (Space)", "31 to 45 s", "$0"],
        ], [0.5, 0.25, 0.25]),
        text("Space times include waiting in the queue. My 4B runs were slow because the model didn't fully fit on my 12 GB card.", NOTE),
    ]


def villa_angles():
    v = "01_villa"
    return [
        PageBreak(),
        text("The villa: sun from different sides", H1),
        text("This is the best result of the project. Same photo, same model, only the sun position changes. "
             "The reflections on the pool and the shadows on the walls change with it."),
        picture("photos/01_villa.jpg", PAGE_WIDTH, 78 * mm),
        text("Original photo", CAPTION),
        Spacer(1, 2 * mm),
        grid([
            (r("sun_4b_local", v, "sun_front"), "Sun behind the camera", "Flat, even light on the front of the house."),
            (r("sun_4b_local", v, "sun_back"), "Sun behind the building", "You can see the sun in the sky, and the walls fall into shade."),
            (r("sun_4b_local", v, "sun_top"), "Sun straight above", "Short, hard shadows under the overhangs."),
            (r("sun_4b_local", v, "sun_left_low"), "Low sun from the left", "Lower sun gives longer shadows across the terrace."),
        ], max_height=62 * mm),
        PageBreak(),
        grid([
            (r("sun_4b_local", v, "sun_right_low"), "Low sun from the right", "Now the right wall lights up. Left and right are still the closest pair."),
            (r("sun_4b_local", v, "sun_left"), "Higher sun from the left", "My first try at this angle. Softer than the low sun."),
            (r("sun_4b_local", v, "sun_right"), "Higher sun from the right", "Same here. Left and right looked too similar, so I lowered the sun."),
            (r("sun_4b_local", v, "sunset_left"), "Sunset on the left", "Biggest change of all. The sky went dark and orange."),
            (r("sun_4b_local", v, "sunset_right"), "Sunset on the right", "I asked for right, but the orange sky stayed on the left. A miss."),
        ], max_height=60 * mm),
        text("What still goes wrong here: the steel sculpture starts to look like stone, the pool loses its strong turquoise, "
             "and the wall tile lines get softer. So it's a nice picture, but not a true copy of the building.", BODY),
    ]


def photo_page(title, photo, trial, items, note):
    return [PageBreak(), text(title, H1), picture(f"photos/{photo}.jpg", PAGE_WIDTH * 0.62, 72 * mm),
            text(f"Original photo. Goal: {note}", CAPTION), Spacer(1, 2 * mm), grid(items, max_height=61 * mm)]


def first_tries():
    v, b, l = "01_villa", "03_concrete_block", "02_living_room"
    return (
        photo_page("Villa: first tries with each tool", v, "left", [
            (r("sun_direction", v, "left"), "Sun-Direction 9B", "The sun moved, but the colors and pool went gray."),
            (r("qwen_3d", v, "left"), "Qwen 3D Lighting", "Soft haze on the left. It also zoomed the picture."),
            (r("kontext", v, "left"), "FLUX.1 Kontext", "Almost nothing changed. The sun stayed where it was."),
            (r("sun_4b_local", v, "left_color"), "Sun-Direction 4B + color prompt", "Colors came back. This led to the angle tests."),
        ], "move the sun to the left.")
        + photo_page("Concrete block", b, "right", [
            (r("sun_direction", b, "right"), "Sun-Direction 9B", "Sun moved, but beige concrete turned gray."),
            (r("qwen_3d", b, "right"), "Qwen 3D Lighting", "Old shadow stayed. It zoomed out and added flower pots."),
            (r("kontext", b, "right"), "FLUX.1 Kontext", "Diagonal shadow did not move."),
            (r("sun_4b_local", b, "right_color"), "Sun-Direction 4B + color prompt", "Blue sky, moved sun, paler concrete. It added a tree."),
        ], "move the sun to the right.")
        + photo_page("Living room", l, "back_left", [
            (r("sun_direction", l, "back_left"), "Sun-Direction 9B", "Sofa, table, rug and the view outside all changed."),
            (r("qwen_3d", l, "back_left"), "Qwen 3D Lighting", "Furniture stayed, but it zoomed in and put sun on the window wall, which can't happen."),
            (r("kontext", l, "back_left"), "FLUX.1 Kontext", "Nice sunset, but all orange, the view is new and the sun is on the wrong side."),
            (r("sun_4b_local", l, "back_left_color"), "Sun-Direction 4B + color prompt", "Good light, but rug and armchair colors changed, plus an extra ceiling light."),
        ], "low sun from the back left, through the windows.")
    )


def light_transfer_page():
    b, l = "03_concrete_block", "02_living_room"
    return [
        PageBreak(),
        text("My own try: copy only the light", H1),
        text("Since the models kept redrawing things, I kept the original photo and copied only the brightness change "
             "from a model's result. Objects stayed perfect, but the sun didn't really move. The old hard shadow on "
             "the concrete block is still there, and sharper settings added bright halos around edges."),
        grid([
            (r("transfer_sun_direction", b, "right"), "Concrete, smooth setting", "Objects are safe. The light barely changed."),
            (r("transfer_sharp_sun_direction", b, "right"), "Concrete, sharp setting", "Old shadow stayed, with a bright halo on the roof."),
            (r("transfer_sun_direction", l, "back_left"), "Living room, smooth setting", "Furniture is untouched. Soft light change."),
            (r("transfer_sharp_sun_direction", l, "back_left"), "Living room, sharp setting", "More light, but halos and a ghost ring on the floor."),
        ], max_height=62 * mm),
    ]


def object_page():
    photo = "02_living_room"
    regions = json.loads(Path("photos/regions.json").read_text(encoding="utf-8"))[photo]
    rows = [("armchair", "Armchair"), ("sofa", "Sofa"), ("coffee_table", "Coffee table"),
            ("rug_left_end", "Rug, left end"), ("rug_front_edge", "Rug, front edge")]
    columns = [("sun_direction", "back_left", "Sun 9B"), ("sun_4b_local", "back_left_color", "Sun 4B"),
               ("qwen_3d", "back_left", "Qwen"), ("kontext", "back_left", "Kontext"),
               ("transfer_sun_direction", "back_left", "Light transfer")]
    before = compare.load(Path(f"photos/{photo}.jpg"))
    w, h = before.size
    images = [("Original", before)]
    for tool, trial, name in columns:
        after = compare.load(r(tool, photo, trial), before.size)
        images.append((name, compare.align(after, *compare.best_alignment(before, after)[1])))
    size = PAGE_WIDTH / 3
    body = [PageBreak(), text("Object check in the living room", H1),
            text("This is the check that changed my mind. The overall score looked fine, but when I looked closely, "
                 "the armchair lost its color, the table changed and the rug got smaller. "
                 "Black areas are parts that fell outside that tool's frame.")]
    for key, label in rows:
        x0, y0, x1, y1 = regions[key]
        area = (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h))
        cells = [[picture(image.crop(area).resize((image.crop(area).width * 2, image.crop(area).height * 2), PILImage.LANCZOS),
                          size - 4, 34 * mm), text(name, NOTE)] for name, image in images]
        t = Table([cells[:3], cells[3:]], colWidths=[size] * 3)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        body += [text(label, H2), t]
        if key == "sofa":
            body.append(PageBreak())
    return body


def closing():
    return [
        PageBreak(),
        text("Errors I ran into", H1),
        table([
            ["What happened", "What I did"],
            ["Several Hugging Face demos were paused or crashing", "Found other Spaces that worked"],
            ["The free GPU quota ran out after three images", "Logged in to Hugging Face"],
            ["Login looked fine, but the saved token was invalid", "Found the problem and logged in again in the browser"],
            ["Sun-Direction needed 150 s of quota and I had 147 s left", "Moved the tests to my own GPU"],
            ["The 9B model doesn't fit on my 12 GB card", "Switched to the smaller 4B, which also has a better license"],
            ["Sun-Direction needs a light ball drawn in the browser", "Rewrote the ball in Python"],
            ["Windows console crashed on special characters", "Forced UTF-8 output in the scripts"],
            ["My first score went to almost zero when a model zoomed", "Added automatic alignment before scoring"],
            ["Kontext got the best score for barely changing anything", "Stopped trusting one number, and scored the light separately"],
            ["The score missed the changed furniture", "Added the object check"],
            ["I thought the gray colors came from the overcast step", "Saved that step and saw it was the LoRA pass. A color prompt helped"],
            ["Villa left and right sun looked the same", "Used a brighter ball, a stronger prompt and a lower sun"],
            ["Sunset on the right still glowed on the left", "Left it in as a failure. Sunset direction isn't reliable yet"],
            ["Light transfer left the old shadows in place", "Kept it as a safety idea, not the final answer"],
        ], [0.56, 0.44]),
        text("What I would put in production", H1),
        text("I'd run the Sun-Direction 4B LoRA on a serverless GPU that only runs when someone uses it, and offer it for exteriors "
             "only. After generating, an automatic check compares the result to the original and tries again if the building changed."),
        table([
            ["Option", "Cost per image", "Speed", "My take"],
            ["Own serverless GPU (RTX 4090)", "About $0.01, or $0.02 with a retry", "About 20 to 26 s", "My pick"],
            ["Always-on GPU", "About $650 a month", "Same, no cold start", "Only above about 16,000 images a month"],
            ["Hosted Kontext or Qwen API", "$0.02 to $0.05", "Not measured", "Open versions failed this task"],
        ], [0.31, 0.27, 0.18, 0.24]),
        text("These cost and speed numbers are estimates from RunPod prices and my 9B Space times. I did not test 4B on that GPU.", NOTE),
        text("What could make it better", H1),
        *bullets([
            "<b>Test more photos:</b> try at least 30 exteriors and see how often a result passes. I only tried three photos, each with one seed.",
            "<b>Protect the materials:</b> mask glass, metal and water, so that the model can't turn steel into stone.",
            "<b>Use depth:</b> get a depth map of the photo and calculate real shadows from the true sun position.",
            "<b>Mix both worlds:</b> combine the model's new shadows with the original textures, so we get real light and real materials.",
            "<b>Train for interiors:</b> a LoRA trained on rooms, or use masks to lock the furniture.",
            "<b>Make it faster:</b> test a bigger GPU, since my card was short on memory. Your API averages 13.4 s, and mine is slower.",
            "<b>Add a real sun control:</b> let the user drag the sun on a dome, with the date, time and location of the building.",
            "<b>Test renders too:</b> I only used real photos here, but your users upload renders.",
        ]),
        text(f'All code, images and failed tries are on GitHub: <a href="{REPO}" color="#1a5fb4">{REPO}</a>', BODY),
        text("Photos from Unsplash: framesforyourheart, Clay Banks, Valentin Gerardi.", NOTE),
    ]


def page_number(canvas, doc):
    canvas.setFont("Arial", 8)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, str(doc.page))


def main():
    story = intro() + villa_angles() + first_tries() + object_page() + light_transfer_page() + closing()
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=13 * mm, title="Moving the sun in architecture photos", author="Mehmet Ozturk")
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(OUTPUT)


if __name__ == "__main__":
    main()
