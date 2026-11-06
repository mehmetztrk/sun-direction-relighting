"""Build the PDF report from the images in results/.

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
DARK, GRAY, LINE = (colors.HexColor(c) for c in ("#1f2933", "#52606d", "#d5dae0"))
VILLA, BLOCK, ROOM = "01_villa", "03_concrete_block", "02_living_room"

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")


def style(name, font="Arial", color=DARK, **kw):
    return ParagraphStyle(name, fontName=font, textColor=color, **kw)


TITLE = style("title", "Arial-Bold", fontSize=20, leading=24, spaceAfter=1 * mm)
SUB = style("sub", color=GRAY, fontSize=10, leading=13, spaceAfter=4 * mm)
H1 = style("h1", "Arial-Bold", fontSize=14, leading=17, spaceBefore=4 * mm, spaceAfter=1.5 * mm)
H2 = style("h2", "Arial-Bold", fontSize=10.5, leading=13, spaceBefore=2 * mm, spaceAfter=0.8 * mm)
BODY = style("body", fontSize=10.5, leading=14.5, spaceAfter=1.8 * mm)
BULLET = style("bullet", fontSize=10.5, leading=14, leftIndent=4 * mm, spaceAfter=1 * mm)
LABEL = style("label", "Arial-Bold", fontSize=9, leading=11, spaceBefore=0.8 * mm)
NOTE = style("note", color=GRAY, fontSize=9, leading=11)


def text(body, s=BODY):
    return Paragraph(body, s)


def bullets(items):
    return [Paragraph(item, BULLET, bulletText="•") for item in items]


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


def grid(items, columns=2, max_height=62 * mm):
    """items: (image, label, note)"""
    width = PAGE_WIDTH / columns
    cells = [[picture(image, width - 6, max_height), text(label, LABEL), text(note, NOTE)]
             for image, label, note in items]
    rows = [cells[i:i + columns] for i in range(0, len(cells), columns)]
    rows[-1] += [""] * (columns - len(rows[-1]))
    t = Table(rows, colWidths=[width] * columns)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 1),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def r(tool, photo, trial):
    return f"results/{tool}/{photo}__{trial}.png"


def original(photo):
    return f"photos/{photo}.jpg"


def start():
    return [
        text("Moving the sun in architecture photos", TITLE),
        text(f'Mehmet Ozturk &nbsp;|&nbsp; <a href="{REPO}" color="#1a5fb4">{REPO.replace("https://", "")}</a>', SUB),
        text("What I did", H1),
        text("I tried to change where the sun comes from in a photo without changing the building. "
             "I took three real photos from Unsplash (a villa, a concrete block and a living room) and tried three "
             "AI models on them. I also wrote one small script of my own."),
        text("Results in one look", H1),
        *bullets([
            "<b>Sun-Direction LoRA:</b> the best one. It really moves the sun on exteriors, but it changes some materials.",
            "<b>Qwen 3D Lighting:</b> fast and keeps the colors, but it zooms the photo and old shadows stay.",
            "<b>FLUX.1 Kontext:</b> keeps the building, but the sun doesn't move on exteriors.",
            "<b>My light transfer script:</b> furniture stays perfect, but the light barely changes.",
            "<b>Interiors:</b> nothing worked well enough yet.",
        ]),
        text("Time and cost", H1),
        *bullets([
            "Sun-Direction: 20 to 26 s on a free Hugging Face Space, 73 to 116 s on my RTX 4070",
            "Qwen 3D Lighting: 6.5 to 17 s on a free Space",
            "FLUX.1 Kontext: 31 to 45 s on a free Space",
            "Everything cost me $0. Space times include the queue.",
        ]),
        text("What I would ship", H1),
        text("The Sun-Direction 4B model on a serverless GPU, for exteriors only, with an automatic check that retries "
             "if the building changes. My estimate is about $0.01 to $0.02 per image and 20 to 26 s. That estimate uses "
             "RunPod prices and my Space times. I did not test it on that GPU."),
    ]


def sun_direction():
    v = "sun_4b_local"
    return [
        PageBreak(),
        text("1. Sun-Direction LoRA", H1),
        text("<b>What I did:</b> this model is made for moving the sun. You give it a small picture of a lit ball and it "
             "copies that light. I first ran it on a free Space, then on my own GPU with the smaller 4B version, because "
             "4B has a license that allows commercial use. I also added a color prompt, and for the villa a stronger sun."),
        picture(original(VILLA), PAGE_WIDTH, 72 * mm),
        text("Villa, original", LABEL),
        Spacer(1, 2 * mm),
        grid([
            (r(v, VILLA, "sun_front"), "Sun behind the camera", "Even light on the front."),
            (r(v, VILLA, "sun_back"), "Sun behind the building", "The sun shows in the sky and walls go into shade."),
            (r(v, VILLA, "sun_top"), "Sun straight above", "Short, hard shadows under the overhangs."),
            (r(v, VILLA, "sunset_left"), "Sunset on the left", "The biggest change."),
        ]),
        PageBreak(),
        grid([
            (r(v, VILLA, "sun_left_low"), "Low sun from the left", "Long shadows across the terrace."),
            (r(v, VILLA, "sun_right_low"), "Low sun from the right", "Left and right are the closest pair."),
            (original(BLOCK), "Concrete block, original", "Sun comes from the left."),
            (r(v, BLOCK, "right_color"), "Sun moved to the right", "Blue sky, paler concrete. It added a tree."),
            (original(ROOM), "Living room, original", ""),
            (r(v, ROOM, "back_left_color"), "Low sun from the back left", "Good light, but rug, armchair and window view changed."),
        ], max_height=58 * mm),
        text("Result", H2),
        text("Good on exteriors. You can clearly see where the sun is. Not good enough on interiors, and the model was not trained on them."),
        text("Problems", H2),
        *bullets([
            "Colors turned gray until I added a color prompt.",
            "The steel sculpture looks like stone, and the pool loses color.",
            "It adds things like a tree and clouds.",
            "When I asked for a sunset on the right, the orange sky stayed on the left.",
        ]),
    ]


def tool_page(number, name, tool, did, trials, result, problems):
    rows = []
    labels = {VILLA: "Villa", BLOCK: "Concrete block", ROOM: "Living room"}
    for photo, trial, note in trials:
        rows += [(original(photo), f"{labels[photo]}, original", ""), (r(tool, photo, trial), "Result", note)]
    return [PageBreak(), text(f"{number}. {name}", H1), text(f"<b>What I did:</b> {did}"),
            grid(rows, max_height=56 * mm), text("Result", H2), text(result), text("Problems", H2), *bullets(problems)]


def object_page():
    regions = json.loads(Path("photos/regions.json").read_text(encoding="utf-8"))[ROOM]
    rows = [("armchair", "Armchair"), ("sofa", "Sofa"), ("coffee_table", "Table"), ("rug_left_end", "Rug")]
    columns = [("sun_direction", "back_left", "Sun 9B"), ("sun_4b_local", "back_left_color", "Sun 4B"),
               ("qwen_3d", "back_left", "Qwen"), ("kontext", "back_left", "Kontext"),
               ("transfer_sun_direction", "back_left", "Transfer")]
    before = compare.load(Path(original(ROOM)))
    w, h = before.size
    images = [("Original", before)]
    for tool, trial, name in columns:
        after = compare.load(r(tool, ROOM, trial), before.size)
        images.append((name, compare.align(after, *compare.best_alignment(before, after)[1])))

    width = PAGE_WIDTH / 7
    data = [[""] + [text(name, LABEL) for name, _ in images]]
    for key, label in rows:
        x0, y0, x1, y1 = regions[key]
        area = (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h))
        data.append([text(label, LABEL)] + [picture(image.crop(area), width - 3) for _, image in images])
    t = Table(data, colWidths=[width] * 7)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 1.5), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE)]))
    return [PageBreak(), text("Furniture check", H1),
            text("I compared each object up close, and this showed what the overall picture hid. "
                 "Black areas fell outside that model's frame."), t]


def ending():
    return [
        PageBreak(),
        text("Problems along the way", H1),
        *bullets([
            "Some free Hugging Face demos were paused or crashing, so I found others.",
            "The free GPU quota ran out quickly, so I moved the Sun-Direction tests to my own computer.",
            "The bigger 9B model doesn't fit on my 12 GB card, so I used 4B.",
            "My first score was misleading. Kontext scored best because it barely changed anything, so I checked by eye too.",
        ]),
        text("What can be improved", H1),
        *bullets([
            "Test on at least 30 exteriors, since three photos isn't many.",
            "Protect glass, metal and water with masks, so they don't change.",
            "Use a depth map to work out real shadows from the sun position.",
            "Combine the model's new shadows with the original textures.",
            "Use masks or a room-trained model to lock furniture in interiors.",
            "Test on a bigger GPU to get closer to your 13.4 s average.",
            "Let the user drag the sun, or pick a date, time and location.",
            "Test on renders too, since I only used real photos.",
        ]),
        text("Other models worth trying", H1),
        *bullets([
            "<b>Sun-Direction v2:</b> the author says it's in progress, with no overcast step and control over light hardness and color.",
            "<b>Qwen Light Migration:</b> copies the light from a reference photo, so you could use a real sunset photo.",
            "<b>Qwen Edit 2511 with LightingRemap:</b> you paint color blocks at the edge of the image to set the light. Still an alpha.",
            "<b>Nano Banana (Gemini):</b> paid prompt-based editing from about $0.03 per image.",
            "<b>FLUX.2 Edit and Seedream Edit:</b> newer paid edit models on fal.",
            "<b>GPT Image 2:</b> OpenAI's edit model. I couldn't confirm its price.",
            "<b>LTX-2.3 Relight:</b> sets sun direction for exterior video, so it could also suit a time-of-day feature.",
            "<b>HELIOS:</b> a research project with sun angle control from GPS. I couldn't confirm that its code is public.",
        ]),
        text(f'Code and all tries, including the failed ones: <a href="{REPO}" color="#1a5fb4">{REPO}</a>', BODY),
        text("Photos from Unsplash: framesforyourheart, Clay Banks, Valentin Gerardi.", NOTE),
    ]


def page_number(canvas, doc):
    canvas.setFont("Arial", 8)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, str(doc.page))


def main():
    story = start() + sun_direction()
    story += tool_page(2, "Qwen 3D Lighting", "qwen_3d",
                       "I used a free Space. You pick the light direction with an angle.",
                       [(VILLA, "left", "Haze on the left, and the photo got zoomed."),
                        (BLOCK, "right", "Old shadow stayed. It added flower pots."),
                        (ROOM, "back_left", "Furniture stayed. The sun patch on the window wall can't happen.")],
                       "Fast and keeps colors, but the light doesn't really move.",
                       ["It zooms the photo by 16 to 19 percent every time.", "Old shadows stay, and it adds objects."])
    story += tool_page(3, "FLUX.1 Kontext", "kontext",
                       "I used a free Space and asked in plain text: change only the lighting, keep the building.",
                       [(VILLA, "left", "Almost nothing changed."),
                        (BLOCK, "right", "The diagonal shadow did not move."),
                        (ROOM, "back_left", "Nice sunset, but all orange, with a new view.")],
                       "It keeps the building, but it doesn't move the sun on exteriors.",
                       ["Inside, the sun appeared on the wrong side and the window view changed.",
                        "The open version is non-commercial."])
    story += [PageBreak(), text("4. My light transfer script", H1),
              text("<b>What I did:</b> the models kept redrawing things, so I kept the original photo and copied only "
                   "the brightness change from a model's result."),
              grid([(original(BLOCK), "Concrete block, original", ""),
                    (r("transfer_sun_direction", BLOCK, "right"), "Result", "The old shadow is still there."),
                    (original(ROOM), "Living room, original", ""),
                    (r("transfer_sun_direction", ROOM, "back_left"), "Result", "Furniture is safe, and the light change is weak.")],
                   max_height=50 * mm),
              text("Result", H2), text("Objects stay perfect, but the sun doesn't really move."),
              text("Problems", H2), *bullets(["Old hard shadows stay.", "Sharper settings add bright halos around objects."])]
    story += object_page() + ending()
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=13 * mm, title="Moving the sun in architecture photos", author="Mehmet Ozturk")
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(OUTPUT)


if __name__ == "__main__":
    main()
