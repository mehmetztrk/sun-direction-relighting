"""Build the PDF report from the images in results/.

    python build_pdf.py
"""
import csv
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
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

import compare

OUTPUT = "Mehmet_Ozturk_sun_direction_report.pdf"
REPO = "https://github.com/mehmetztrk/sun-direction-relighting"
PAGE_WIDTH = A4[0] - 28 * mm
DARK, GRAY = colors.HexColor("#1f2933"), colors.HexColor("#52606d")
VILLA, BLOCK, ROOM = "01_villa", "03_concrete_block", "02_living_room"
ALIGNED = {}

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
    """items: (image, label, note), or None for an empty cell."""
    width = PAGE_WIDTH / columns
    cells = [item and [picture(item[0], width - 6, max_height), text(item[1], LABEL), text(item[2], NOTE)]
             for item in items]
    rows = [cells[i:i + columns] for i in range(0, len(cells), columns)]
    rows[-1] += [None] * (columns - len(rows[-1]))
    t = Table([[cell or "" for cell in row] for row in rows], colWidths=[width] * columns)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 1),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def r(tool, photo, trial):
    return f"results/{tool}/{photo}__{trial}.png"


def original(photo):
    return f"photos/{photo}.jpg"


def aligned(tool, photo, trial):
    """A result at full size, with the model's zoom and shift undone."""
    key = (tool, photo, trial)
    if key not in ALIGNED:
        small = compare.load(Path(original(photo)))
        fit = compare.best_alignment(small, compare.load(r(tool, photo, trial), small.size))[1]
        full = PILImage.open(original(photo)).convert("RGB")
        result = compare.load(r(tool, photo, trial), full.size)
        factor = full.width / small.width
        ALIGNED[key] = compare.align(result, fit[0], fit[1] * factor, fit[2] * factor)
    return ALIGNED[key]


def crop(image, box):
    if not isinstance(image, PILImage.Image):
        image = PILImage.open(image).convert("RGB")
    w, h = image.size
    return image.crop((round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)))


def start():
    return [
        text("Moving the sun in architecture photos", TITLE),
        text(f'Mehmet Ozturk &nbsp;|&nbsp; <a href="{REPO}" color="#1a5fb4">{REPO.replace("https://", "")}</a>', SUB),
        text("What I did", H1),
        *bullets([
            "I looked at what's out there: open models, LoRAs, paid APIs and apps.",
            "I picked three real photos from Unsplash: a villa, a concrete apartment block and a living room.",
            "I tried three models on all three photos: Sun-Direction, Qwen 3D Lighting and FLUX.1 Kontext.",
            "I used free Hugging Face demos first. When the free quota ran out, I ran Sun-Direction on my own RTX 4070.",
            "The models kept redrawing things, so I wrote my own script that copies only the light onto the original photo.",
            "I tested the villa with the sun in many positions, to see if the direction is really visible.",
        ]),
        text("How I judged the results", H1),
        text("I asked three simple questions: did the light really change, did the building stay the same, and did "
             "single objects like the sofa stay the same? I also used a small script that scores each result, but it "
             "missed some mistakes, so the final decision was always by eye."),
        text("Results in one look", H1),
        *bullets([
            "<b>Sun-Direction:</b> the best one. It really moves the sun on exteriors, but it changes some materials.",
            "<b>Qwen 3D Lighting:</b> fast and keeps the colors, but it zooms the photo and old shadows stay.",
            "<b>FLUX.1 Kontext:</b> keeps the building, but the sun doesn't move on exteriors.",
            "<b>My light transfer script:</b> furniture stays perfect, but the light barely changes.",
            "<b>Interiors:</b> nothing worked well enough yet.",
        ]),
        PageBreak(),
        text("Time and cost", H1),
        *bullets([
            "Sun-Direction: 20 to 26 s on a free Hugging Face Space, 73 to 116 s on my RTX 4070",
            "Qwen 3D Lighting: 6.5 to 24 s on a free Space",
            "FLUX.1 Kontext: 31 to 45 s on a free Space",
            "Everything cost me $0. Space times include the queue.",
        ]),
        text("What I would ship", H1),
        text("The Sun-Direction 4B model on a serverless GPU, for exteriors only, with an automatic check that retries "
             "if the building changes. My estimate is about $0.01 to $0.02 per image and 20 to 26 s. That estimate uses "
             "RunPod prices and my Space times. I did not test it on that GPU."),
        text("How I measured", H1),
        text("Every number here comes from my compare.py script. It helps me sort results, but it doesn't replace looking at them."),
        *bullets([
            "<b>Structure (0 to 1):</b> local correlation of brightness in a 15 x 15 pixel window, after undoing zoom and shift. "
            "Flat areas like sky are skipped. New shadows lower it too: fake hard shadows scored 0.92 to 0.96, so a low score isn't always damage.",
            "<b>Light change (EV):</b> how much the brightness pattern changed across the image, with the overall exposure change removed.",
            "<b>Scale:</b> the zoom needed to line the result up with the original. 1.00 means the framing held.",
            "<b>What it can't do:</b> it doesn't check if a shadow points the right way. That part was by eye.",
        ]),
        text("The three test photos", H1),
        grid([(original(VILLA), "Villa", "Glass, a pool and a steel sculpture. Lots of ways to go wrong."),
              (original(BLOCK), "Concrete block", "A strong diagonal shadow, so you can see if the sun really moved."),
              (original(ROOM), "Living room", "Light can only come through the windows, and there is a lot of furniture.")],
             max_height=52 * mm),
    ]


def pairs(number, name, did, rows):
    """One section per model: every photo next to its result, with what happened."""
    labels = {VILLA: "Villa", BLOCK: "Concrete block", ROOM: "Living room"}
    items = []
    for tool, photo, trial, title, note in rows:
        items += [(original(photo), f"{labels[photo]}, original", ""), (r(tool, photo, trial), title, note)]
    return [PageBreak(), text(f"{number}. {name}", H1), text(f"<b>What I did:</b> {did}"), grid(items, max_height=43 * mm)]


def ending_of(setup, result, problems):
    return [KeepTogether([text("Setup", H2), text(setup), text("Result", H2), text(result)]),
            text("Problems and why they happen", H2), *bullets(problems)]


def models():
    s9, s4, q, k = "sun_direction", "sun_4b_local", "qwen_3d", "kontext"
    story = pairs(1, "Sun-Direction (9B version, free demo)",
                  "this model is made just for moving the sun. You give it a picture of a lit ball, and it copies that "
                  "light. It first makes the photo look overcast, then adds the new sun.",
                  [(s9, VILLA, "left", "Sun moved to the left", "The sun moved, but the colors and the pool went gray."),
                   (s9, BLOCK, "right", "Sun moved to the right", "The sun moved, but beige concrete turned gray and the sky went pale."),
                   (s9, ROOM, "back_left", "Low sun from the back left", "The sofa, table, rug and the view outside all changed.")])
    story += ending_of(
        "FLUX.2 Klein 9B with the Sun-Direction LoRA, on a free ZeroGPU Space. It runs two passes at about 1 megapixel: "
        "an overcast pass without the LoRA, then a LoRA pass that gets the overcast image and the ball as references. "
        "4 steps, guidance 1.0, seed 42.",
        "On both exteriors the lit side of the building really changed. Light change was 0.37 to 0.49 EV and the framing "
        "held (scale 0.97 to 1.00). Structure was only 0.33 to 0.52, because the image is generated again rather than edited. "
        "Output is about 1264 wide, so detail from the 1536 px input is lost too.",
        ["<b>Color loss:</b> concrete and the pool went gray. On the 4B version I saved the overcast image and the color "
         "was still there, so the loss happens in the LoRA pass, not the overcast pass.",
         "<b>Interiors:</b> the author says the LoRA has no interior training data. It doesn't know light has to come "
         "through the windows, and it redrew the view, sofa, table and rug.",
         "<b>License:</b> the LoRA is Apache-2.0, but the 9B base model is non-commercial, so this version can't ship."])

    rows = [(VILLA, "left", "left_color", "Villa", "A lot of clouds appeared and everything is pale.",
             "The blue sky came back. The sculpture looks like stone."),
            (BLOCK, "right", "right_color", "Concrete block", "The sun moved, but the concrete faded and clouds appeared.",
             "Blue sky came back, but the concrete is paler and there's a new tree."),
            (ROOM, "back_left", "back_left_color", "Living room", "Nice light, but the view outside is new and the armchair is gray.",
             "Warmer light. Rug and armchair colors changed, and there's an extra ceiling light.")]
    items = []
    for photo, plain, color, name, plain_note, color_note in rows:
        items += [(original(photo), f"{name}, original", ""), (r(s4, photo, plain), "No prompt", plain_note),
                  (r(s4, photo, color), "With color prompt", color_note)]
    story += [PageBreak(), text("2. Sun-Direction (4B version, on my GPU)", H1),
              text("<b>What I did:</b> 4B is the smaller version, and it's the one that allows commercial use. "
                   "I ran it on my own RTX 4070, once with no prompt and once with a short prompt asking it to keep the colors."),
              grid(items, columns=3, max_height=42 * mm)]
    story += ending_of(
        "FLUX.2 Klein 4B (Apache-2.0) with its matching LoRA, on an RTX 4070 with 12 GB. Same two passes, 4 steps and "
        "guidance 1.0 through diffusers, with bfloat16 and model CPU offload. Peak GPU memory was 10.4 GB. Color prompt: "
        "<i>clear blue sky, warm natural sunlight, same colors and materials as the original</i>.",
        "The color prompt brought back the blue sky and warmer walls without hurting structure much "
        "(villa 0.29 to 0.31, block 0.52 to 0.48, room 0.48 to 0.49). It's a cheap fix, and this is the version I would "
        "build on, but only for exteriors.",
        ["<b>Materials:</b> steel turns to stone because nothing protects it. Every pixel is generated again.",
         "<b>Added objects:</b> the tree and wire on the concrete block are already there in the overcast pass. That pass is a "
         "plain edit with no LoRA, so the extra content starts before the sun is even moved.",
         "<b>Speed:</b> 73 to 116 s. The model doesn't fully fit in 12 GB, so parts move between RAM and GPU. Time on a "
         "bigger GPU is still unknown."])

    story += pairs(3, "Qwen 3D Lighting (free demo)", "you choose the light direction with an angle, and the model edits the photo.",
                   [(q, VILLA, "left", "Sun moved to the left", "Soft haze on the left, and the photo got zoomed."),
                    (q, BLOCK, "right", "Sun moved to the right", "The right wall got brighter, but the old shadow stayed and flower pots appeared."),
                    (q, ROOM, "back_left", "Low sun from the back left", "Furniture stayed, but the sun patch on the window wall can't happen.")])
    story += ending_of(
        "Qwen-Image-Edit on a free ZeroGPU Space. The Space turns the angle into a prompt such as "
        "<i>Light source from the Right</i>. 4 steps, guidance 1.0, output about 1024 wide.",
        "The fastest tool at 6.5 to 24 s, and it keeps colors best. Light change was 0.38 to 0.50 EV, but it's mostly brightness "
        "added on top of the old lighting. After undoing the zoom, structure was 0.43 to 0.60.",
        ["<b>Zoom:</b> scale came back 0.81 to 0.84 on all four tries, so the output doesn't line up with the original. "
         "Using the Space's own image size gave the same result, so it isn't caused by my settings.",
         "<b>Light is added, not moved:</b> old shadows stay. Direction is only a few words in a prompt, and the model doesn't "
         "use any depth or geometry. That's probably why it put a sun patch on the window wall.",
         "<b>Added objects:</b> flower pots appeared on the concrete block balcony."])

    story += pairs(4, "FLUX.1 Kontext (free demo)",
                   "this is a normal text edit model. I asked in plain text: change only the lighting and keep the building the same.",
                   [(k, VILLA, "left", "Sun moved to the left", "Almost nothing changed. Colors are a bit stronger."),
                    (k, BLOCK, "right", "Sun moved to the right", "The diagonal shadow did not move, and the frame shifted a little."),
                    (k, ROOM, "back_left", "Low sun from the back left", "Nice sunset, but everything is orange and the view is new.")])
    story += ending_of(
        "FLUX.1 Kontext [dev] on a free ZeroGPU Space. 28 steps, guidance 2.5, seed 42. It only takes text, so there's "
        "no real way to give it a direction.",
        "The best structure on exteriors (villa 0.95, block 0.81), but the weakest light change of the three models on those "
        "photos (0.24 and 0.31 EV). In this case a high score mostly means that little happened.",
        ["<b>No sun movement:</b> my guess is that <i>keep everything the same</i> beat <i>move the sun</i> in the prompt.",
         "<b>Interior:</b> a strong sunset, about 0.8 EV darker overall, but the sun landed on the wrong side and the outside view was replaced.",
         "<b>Frame shift:</b> the concrete block moved by about 38 px (scale 0.98).",
         "<b>License:</b> the dev weights are non-commercial, so a product would need the paid Pro API, which I did not test."])

    t9, ts, tq, tk = "transfer_sun_direction", "transfer_sharp_sun_direction", "transfer_qwen_3d", "transfer_kontext"
    rows = [(VILLA, "left", "Villa", "Slight glow at the edges, and the sun didn't move.", "Stronger glow along the edges.",
             "Almost the same as the original.", "Almost the same as the original."),
            (BLOCK, "right", "Concrete block", "The old shadow is still there.", "The old shadow stayed, with a bright halo on the roof.",
             "A small change on the right side.", "The shadow got a bit darker."),
            (ROOM, "back_left", "Living room", "Furniture is safe, and the light is soft.", "More light, but halos and a ghost ring on the floor.",
             "A small bright area on the left.", "The room got a bit darker.")]
    items = []
    for photo, trial, name, a, b, c, d in rows:
        items += [(original(photo), f"{name}, original", ""), (r(t9, photo, trial), "From Sun 9B, smooth", a),
                  (r(ts, photo, trial), "From Sun 9B, sharp", b), None, (r(tq, photo, trial), "From Qwen", c),
                  (r(tk, photo, trial), "From Kontext", d)]
    story += [PageBreak(), text("5. My light transfer script", H1),
              text("<b>What I did:</b> the models kept redrawing things, so I kept the original photo and copied only the "
                   "brightness change from each model's result."),
              grid(items, columns=3, max_height=38 * mm)]
    story += ending_of(
        "Align the result to the original, take the log2 brightness ratio, smooth it with a guided filter that uses the original as "
        "its guide, clip to 2 EV, scale it up and multiply in linear light. Smooth: radius 12, epsilon 0.002. "
        "Sharp: radius 3, epsilon 0.05. It runs on a CPU and keeps the full resolution.",
        "Objects are safe: structure 0.94 to 1.00, with no redrawn furniture. But light change falls to 0.04 to 0.20 EV, against "
        "0.24 to 0.61 for the models, so most of the new light is lost on the way.",
        ["<b>Old shadows stay:</b> erasing a hard shadow needs a sharp ratio exactly on the shadow edge. Smoothing blurs it, "
         "and the model's result doesn't line up well enough for a sharp ratio.",
         "<b>Halos:</b> with less smoothing, edges that don't match between the two images show up as bright lines.",
         "<b>Ghosts:</b> mistakes in the model's result come along too, like the ring shadow on the living room floor."])
    return story


def villa_angles():
    v, s4 = VILLA, "sun_4b_local"
    return [
        PageBreak(),
        text("6. Extra test: the villa with the sun in different spots", H1),
        text("<b>What I did:</b> my first villa results didn't show the sun direction clearly. So I gave Sun-Direction 4B "
             "a stronger sun and tried nine positions. I wanted to do the same with Qwen and Kontext, but the free quota ran "
             "out after one Qwen image, so this test is mostly one model."),
        grid([
            (original(VILLA), "Original", ""),
            (r(s4, v, "sun_front"), "Sun behind the camera", "Even light on the front."),
            (r(s4, v, "sun_back"), "Sun behind the building", "The sun shows in the sky and the walls go into shade."),
            (r(s4, v, "sun_top"), "Sun straight above", "Short, hard shadows under the overhangs."),
            (r(s4, v, "sun_left"), "Higher sun from the left", "Soft. Too close to the right side version."),
            (r(s4, v, "sun_right"), "Higher sun from the right", "So I lowered the sun for the next two."),
        ], max_height=60 * mm),
        PageBreak(),
        grid([
            (r(s4, v, "sun_left_low"), "Low sun from the left", "Long shadows across the terrace."),
            (r(s4, v, "sun_right_low"), "Low sun from the right", "The right wall lights up. Left and right are still the closest pair."),
            (r(s4, v, "sunset_left"), "Sunset on the left", "The biggest change of all."),
            (r(s4, v, "sunset_right"), "Sunset on the right", "A miss: I asked for the right, but the orange sky stayed on the left."),
            (r("qwen_3d", v, "sun_front"), "Qwen, sun behind the camera", "My one extra Qwen try. Colors are nice, but it's zoomed in a lot."),
        ], max_height=48 * mm),
        *ending_of(
            "Same 4B setup. I raised the ball brightness from 1.5 to 3.0, set sun height from 8 to 85 degrees, and added "
            "<i>strong direct sunlight, hard sharp shadows</i> to the prompt. The sunset shots used their own prompt.",
            "This is the best result of the project. You can tell where the sun is, especially from behind the building, "
            "from above and at sunset. Light change was 0.22 to 0.47 EV in daylight and 0.69 to 0.80 EV at sunset.",
            ["<b>Materials:</b> the sculpture looks like stone, the pool loses its turquoise and tile lines get softer. "
             "Structure dropped to 0.19 to 0.38 here, so stronger light costs more detail.",
             "<b>Left and right:</b> this is the closest pair. The camera sees two faces of the villa at an angle, so the difference is small.",
             "<b>Sunset direction:</b> the right side sunset stayed orange on the left. My guess is that the word <i>sunset</i> "
             "pulled the result toward one look, and the ball lost that fight."]),
    ]


def failures():
    def pair(photo, tool, trial, box, title, note, use_align=True):
        failed = aligned(tool, photo, trial) if use_align else r(tool, photo, trial)
        return [(crop(original(photo), box), "Original", ""), (crop(failed, box), title, note)]

    items = []
    items += pair(BLOCK, "qwen_3d", "right", (0.48, 0.60, 0.72, 0.78), "Qwen added flower pots", "There were no pots here.")
    items += pair(VILLA, "sun_4b_local", "left_color", (0.0, 0.56, 0.32, 0.96), "Sun 4B changed the sculpture", "Shiny steel now looks like stone.")
    items += pair(BLOCK, "sun_4b_local", "right_color", (0.72, 0.72, 1.0, 1.0), "Sun 4B added a tree", "This came from the overcast step.")
    items += pair(VILLA, "sun_direction", "left", (0.25, 0.6, 0.95, 1.0), "Sun 9B turned the pool gray", "The turquoise water is gone.")
    items += pair(ROOM, "sun_direction", "back_left", (0.28, 0.6, 0.88, 1.0), "Sun 9B redrew the table and rug", "Note the strange ring shadow on the floor.")
    items += pair(ROOM, "qwen_3d", "back_left", (0.0, 0.2, 0.4, 0.75), "Qwen's impossible sun patch", "Sun can't hit the wall that holds the windows.")
    items += pair(ROOM, "kontext", "back_left", (0.18, 0.15, 0.82, 0.62), "Kontext replaced the view", "A new outdoor scene, and the sun is on the wrong side.")
    items += pair(ROOM, "sun_4b_local", "back_left_color", (0.18, 0.15, 0.82, 0.62), "Sun 4B also replaced the view", "The hillside became trees and sky.")
    items += pair(BLOCK, "kontext", "right", (0.0, 0.3, 0.85, 1.0), "Kontext didn't move the shadow", "I asked for the sun on the right. Nothing moved.")
    items += pair(BLOCK, "transfer_sharp_sun_direction", "right", (0.15, 0.33, 0.62, 0.55), "My script left a halo", "See the bright line along the roof.", False)
    items += [(r("sun_4b_local", VILLA, "sunset_left"), "Asked for sunset on the left", "This one worked."),
              (r("sun_4b_local", VILLA, "sunset_right"), "Asked for sunset on the right", "The orange sky stayed on the left.")]
    per_page = 8
    story = []
    for first in range(0, len(items), per_page):
        story.append(PageBreak())
        if first == 0:
            story += [text("Failed results up close", H1),
                      text("These are the mistakes I want to be clear about. An architect would notice all of them.")]
        story.append(grid(items[first:first + per_page], max_height=52 * mm))
    return story


def furniture():
    regions = json.loads(Path("photos/regions.json").read_text(encoding="utf-8"))[ROOM]
    objects = [("Armchair", regions["armchair"], "Sun 9B and 4B lost the green color."),
               ("Sofa", regions["sofa"], "Sun 9B redrew it."),
               ("Coffee table", regions["coffee_table"], "Sun 9B made the top look white and changed the legs."),
               ("Rug", (0.0, 0.64, 1.0, 0.95), "Sun 9B and 4B made it smaller and changed its color.")]
    columns = [("sun_direction", "back_left", "Sun 9B"), ("sun_4b_local", "back_left_color", "Sun 4B"),
               ("qwen_3d", "back_left", "Qwen"), ("kontext", "back_left", "Kontext"),
               ("transfer_sun_direction", "back_left", "Light transfer")]
    images = [("Original", PILImage.open(original(ROOM)).convert("RGB"))]
    images += [(name, aligned(tool, ROOM, trial)) for tool, trial, name in columns]
    story = []
    for i, (name, box, note) in enumerate(objects):
        if i % 2 == 0:
            story.append(PageBreak())
        if i == 0:
            story += [text("Furniture check", H1),
                      text("I compared each object up close, and this showed what the overall picture hid. "
                           "Black areas fell outside that model's frame.")]
        story += [text(name, H2), text(note, NOTE),
                  grid([(crop(image, box), title, "") for title, image in images], columns=2 if name == "Rug" else 3, max_height=52 * mm)]
    return story


def score_table():
    with open("results/_report/scores.csv", encoding="utf-8", newline="") as f:
        scores = {(row["tool"], row["photo"], row["trial"]): row for row in csv.DictReader(f, delimiter=";")}

    def cell(tool, photo, trial):
        row = scores[(tool, photo, trial)]
        return f"{float(row['structure']):.2f} / {float(row['light_ev']):.2f} / {float(row['scale']):.2f}"

    def small(rows, widths):
        t = Table([[text(str(c), LABEL if i == 0 else NOTE) for c in row] for i, row in enumerate(rows)],
                  colWidths=[w * PAGE_WIDTH for w in widths])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        return t

    tools = [("Sun 9B", "sun_direction", ""), ("Sun 4B, no prompt", "sun_4b_local", ""),
             ("Sun 4B, color prompt", "sun_4b_local", "_color"), ("Qwen 3D Lighting", "qwen_3d", ""),
             ("FLUX.1 Kontext", "kontext", ""), ("Transfer from Sun 9B, smooth", "transfer_sun_direction", ""),
             ("Transfer from Sun 9B, sharp", "transfer_sharp_sun_direction", ""),
             ("Transfer from Qwen", "transfer_qwen_3d", ""), ("Transfer from Kontext", "transfer_kontext", "")]
    rows = [["Tool", "Villa", "Concrete block", "Living room"]]
    rows += [[name, cell(tool, VILLA, "left" + end), cell(tool, BLOCK, "right" + end), cell(tool, ROOM, "back_left" + end)]
             for name, tool, end in tools]
    angles = [("Behind the camera", "sun_front"), ("Behind the building", "sun_back"), ("Straight above", "sun_top"),
              ("Higher left", "sun_left"), ("Higher right", "sun_right"), ("Low left", "sun_left_low"),
              ("Low right", "sun_right_low"), ("Sunset left", "sunset_left"), ("Sunset right", "sunset_right")]
    angle_rows = [["Sun position", "Villa, Sun 4B"]] + [[name, cell("sun_4b_local", VILLA, trial)] for name, trial in angles]
    return [PageBreak(), text("All the numbers", H1),
            text("Each cell shows structure / light change in EV / scale. One seed per try, so treat these as a rough guide. "
                 "They're also in results/_report/scores.csv on GitHub."),
            small(rows, [0.37, 0.21, 0.21, 0.21]), text("Villa sun positions", H2), small(angle_rows, [0.37, 0.25]),
            text("Time per image", H2),
            *bullets(["Sun 9B on a free Space: 20.5 to 26 s, queue included", "Sun 4B on my RTX 4070: 73 to 116 s",
                      "Qwen on a free Space: 6.5 to 24 s, queue included", "Kontext on a free Space: 31.5 to 45 s, queue included"])]


def ending():
    return [
        PageBreak(),
        text("How I would build it", H1),
        *bullets([
            "<b>Model:</b> Sun-Direction 4B with a color prompt, because its base model and LoRA are both Apache-2.0.",
            "<b>Hosting:</b> a serverless GPU that only runs when someone uses it. An always-on RTX 4090 costs about $650 a month, "
            "which only beats a $0.04 API above about 16,000 images a month.",
            "<b>Cost:</b> RunPod serverless RTX 4090 is $1.34 an hour. At about 25 s per image that's about $0.01, or $0.02 with one retry.",
            "<b>Quality gate:</b> after generating, compare the result with the original and retry or reject it if the structure "
            "drops too far. I haven't tuned that threshold yet.",
            "<b>Risks:</b> I didn't test 4B on that GPU or measure cold starts, so the speed and cost above are estimates from 9B Space times.",
        ]),
        text("Problems along the way", H1),
        *bullets([
            "Some free Hugging Face demos were paused or crashing, so I found others.",
            "The free GPU quota ran out quickly, so I moved the Sun-Direction tests to my own computer.",
            "The bigger 9B model doesn't fit on my 12 GB card, so I used 4B.",
            "My saved Hugging Face token was invalid, so runs kept failing after I logged in. Logging in again through the browser fixed it.",
            "My first score was misleading. It fell near zero when a model zoomed, so I added alignment. Kontext still scored best "
            "because it barely changed anything, so I also check by eye.",
            "I thought the gray colors came from the overcast step. They came from the next step, so a color prompt helped.",
            "Sun-Direction needed 150 s of quota when I had 147 s left. That's what pushed me to run it locally.",
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
    story = start() + models() + villa_angles() + failures() + furniture() + score_table() + ending()
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm,
                            bottomMargin=13 * mm, title="Moving the sun in architecture photos", author="Mehmet Ozturk")
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(OUTPUT)


if __name__ == "__main__":
    main()
