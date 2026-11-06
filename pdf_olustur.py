"""Teslim PDF'ini sonuclar/ klasöründeki denemelerden üretir.

Çalıştırma:
    python karsilastir.py
    python pdf_olustur.py

Gerekenler: reportlab, pillow
"""
import csv
import io
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import karsilastir as k

CIKTI = "MyArchitectAI_sun_direction_report.pdf"
GENISLIK = A4[0] - 30 * mm
KOYU, GRI, CIZGI, ACIK = colors.HexColor("#1f2933"), colors.HexColor("#52606d"), colors.HexColor("#cbd2d9"), colors.HexColor("#f0f2f5")

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")


def stil(ad, **k):
    return ParagraphStyle(ad, fontName=k.pop("fontName", "Arial"), textColor=k.pop("textColor", KOYU),
                          alignment=TA_LEFT, **k)


BASLIK = stil("baslik", fontName="Arial-Bold", fontSize=16, leading=19, spaceAfter=1 * mm)
ALT = stil("alt", fontSize=8.5, leading=11, textColor=GRI, spaceAfter=2 * mm)
H1 = stil("h1", fontName="Arial-Bold", fontSize=10.5, leading=13, spaceBefore=2.4 * mm, spaceAfter=0.8 * mm)
METIN = stil("metin", fontSize=9, leading=11.8, spaceAfter=1 * mm)
MADDE = stil("madde", fontSize=9, leading=11.6, leftIndent=3.5 * mm, bulletIndent=0, spaceAfter=0.5 * mm)
HUCRE = stil("hucre", fontSize=8, leading=9.8)
HUCRE_B = stil("hucre_b", fontName="Arial-Bold", fontSize=8, leading=9.8)
ETIKET = stil("etiket", fontName="Arial-Bold", fontSize=7.6, leading=9.2)
NOT = stil("not", fontSize=7.2, leading=8.8, textColor=GRI)


def p(metin, s=METIN):
    return Paragraph(metin, s)


def maddeler(liste):
    return [Paragraph(m, MADDE, bulletText="•") for m in liste]


def tablo(satirlar, genislikler, kucuk=False):
    t = Table([[p(str(h), HUCRE_B if i == 0 else HUCRE) for h in s] for i, s in enumerate(satirlar)],
              colWidths=[g * GENISLIK for g in genislikler], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACIK), ("LINEBELOW", (0, 0), (-1, -1), 0.3, CIZGI),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5), ("TOPPADDING", (0, 0), (-1, -1), 1.6 if kucuk else 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 if kucuk else 2.2),
    ]))
    return t


def resim(yol, genislik, en_fazla=None):
    g = PILImage.open(yol).convert("RGB")
    g.thumbnail((1000, 1000), PILImage.LANCZOS)
    tampon = io.BytesIO()
    g.save(tampon, "JPEG", quality=82)
    tampon.seek(0)
    yukseklik = genislik * g.height / g.width
    if en_fazla and yukseklik > en_fazla:
        genislik, yukseklik = genislik * en_fazla / yukseklik, en_fazla
    return Image(tampon, genislik, yukseklik)


def metrikler():
    with open("sonuclar/_rapor/metrikler.csv", encoding="utf-8-sig", newline="") as f:
        return {(s["arac"], s["gorsel"], s["deneme"]): s for s in csv.DictReader(f, delimiter=";")}


GORSELLER = [
    ("01_dis_cephe_villa", "sol", "Villa exterior", "Sun moved to the left of the image"),
    ("03_dis_cephe_beton_bina", "sag", "Concrete apartment block", "Sun moved to the right of the image"),
    ("02_ic_mekan_oturma_odasi", "arka_sol", "Living room", "Low sun from the back left, through the windows"),
]

DENEMELER = [
    ("sun_direction", "", "Sun-Direction 9B (Space)"),
    ("qwen_3d", "", "Qwen 3D Lighting (Space)"),
    ("kontext", "", "FLUX.1 Kontext (Space)"),
    ("yerel_4b", "", "Sun-Direction 4B, no prompt (RTX 4070)"),
    ("yerel_4b", "_renk", "Sun-Direction 4B, color prompt (RTX 4070)"),
    ("aktarim_sun_direction", "", "Light transfer from Sun 9B, smooth"),
    ("aktarim_keskin_sun_direction", "", "Light transfer from Sun 9B, sharp"),
    ("aktarim_qwen_3d", "", "Light transfer from Qwen, smooth"),
    ("aktarim_kontext", "", "Light transfer from Kontext, smooth"),
]

NOTLAR = {
    ("01_dis_cephe_villa", "sun_direction"): "Sun moved. Colors and pool turned gray.",
    ("01_dis_cephe_villa", "qwen_3d"): "Haze on the left. Reframed, aspect changed.",
    ("01_dis_cephe_villa", "kontext"): "Sun not moved. Slightly more saturated.",
    ("01_dis_cephe_villa", "yerel_4b_renk"): "Best sun here. Steel sculpture looks like stone, facade warmer.",
    ("03_dis_cephe_beton_bina", "sun_direction"): "Sun moved. Beige concrete turned gray, sky pale.",
    ("03_dis_cephe_beton_bina", "qwen_3d"): "Old shadow stays. Reframed. Added flower pots.",
    ("03_dis_cephe_beton_bina", "kontext"): "Old shadow unchanged. Harsher texture, frame shifted.",
    ("03_dis_cephe_beton_bina", "yerel_4b"): "Sun moved. Concrete faded, clouds and tree added.",
    ("03_dis_cephe_beton_bina", "yerel_4b_renk"): "Blue sky back, concrete paler. Tree still added.",
    ("03_dis_cephe_beton_bina", "aktarim_sun_direction"): "Objects intact. Old shadow stays, sun not moved.",
    ("03_dis_cephe_beton_bina", "aktarim_keskin_sun_direction"): "Old shadow stays. Bright halo along the roof.",
    ("02_ic_mekan_oturma_odasi", "sun_direction"): "Sofa, table, rug and view changed. Odd ring shadow.",
    ("02_ic_mekan_oturma_odasi", "qwen_3d"): "Objects kept. Reframed. Impossible sun patch on window wall.",
    ("02_ic_mekan_oturma_odasi", "kontext"): "Orange cast, view replaced, sun on the wrong side.",
    ("02_ic_mekan_oturma_odasi", "yerel_4b_renk"): "Good light. Rug, armchair and view changed, extra ceiling light.",
    ("02_ic_mekan_oturma_odasi", "aktarim_sun_direction"): "Objects intact. Light change is weak.",
    ("02_ic_mekan_oturma_odasi", "aktarim_keskin_sun_direction"): "Objects intact. Halos and a ghost ring.",
}


def resim_sayfasi(gorsel, deneme, ad, hedef, m):
    w = (GENISLIK - 8) / 3
    cizim_yuk = 41 * mm
    hucreler = [[resim(f"gorseller/{gorsel}.jpg", w - 4, cizim_yuk), p("Original", ETIKET), p(hedef, NOT)]]
    for arac, ek, etiket in DENEMELER:
        klasor = Path("sonuclar") / arac
        yol = klasor / f"{gorsel}__{deneme}{ek}.png"
        o = m[(arac, gorsel, deneme + ek)]
        olcum = f"Structure {float(o['yapi_hizali']):.2f}, light {float(o['isik_degisimi_ev']):.2f} EV"
        notu = NOTLAR.get((gorsel, arac + ek))
        hucreler.append([resim(yol, w - 4, cizim_yuk), p(etiket, ETIKET), p(olcum + (". " + notu if notu else ""), NOT)])
    hucreler.append([resim(f"sonuclar/_ara/{gorsel}__bulutlu.png", w - 4, cizim_yuk),
                     p("Intermediate overcast step, 4B", ETIKET), p("Input to the Sun-Direction pass.", NOT)])
    hucreler.append([p("", NOT)])
    satirlar = [hucreler[i:i + 3] for i in range(0, 12, 3)]
    t = Table([[c for c in s] for s in satirlar], colWidths=[w] * 3)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [p(f"Before and after: {ad}", H1), t]


def nesne_sayfasi():
    """Oturma odasındaki objeleri özgün ve hizalanmış sonuçlarla yan yana gösterir."""
    gorsel = "02_ic_mekan_oturma_odasi"
    bolgeler = json.loads(Path("gorseller/bolgeler.json").read_text(encoding="utf-8"))[gorsel]
    satirlar = [("koltuk_sol", "Armchair"), ("koltuk_sag", "Sofa"), ("sehpa", "Coffee table"),
                ("hali_sol_uc", "Rug, left end"), ("hali_on_kenar", "Rug, front edge")]
    sutunlar = [("sun_direction", "arka_sol", "Sun 9B"), ("yerel_4b", "arka_sol_renk", "Sun 4B, color"),
                ("qwen_3d", "arka_sol", "Qwen"), ("kontext", "arka_sol", "Kontext"),
                ("aktarim_sun_direction", "arka_sol", "Transfer")]
    once = k.yukle(Path(f"gorseller/{gorsel}.jpg"))
    g, y = once.size
    goruntuler = [("Original", once)]
    for arac, deneme, ad in sutunlar:
        sonra = k.yukle(Path("sonuclar") / arac / f"{gorsel}__{deneme}.png", once.size)
        _, hiza = k.hizali_yapi(once, sonra)
        goruntuler.append((ad, k.hizala(sonra, *hiza)))
    w = GENISLIK / 7
    bas = [p("", ETIKET)] + [p(ad, ETIKET) for ad, _ in goruntuler]
    govde = [bas]
    for bolge, ad in satirlar:
        x0, y0, x1, y1 = bolgeler[bolge]
        kutu_px = (round(x0 * g), round(y0 * y), round(x1 * g), round(y1 * y))
        satir = [p(ad, ETIKET)]
        for _, goruntu in goruntuler:
            tampon = io.BytesIO()
            kirpinti = goruntu.crop(kutu_px)
            kirpinti.save(tampon, "JPEG", quality=88)
            tampon.seek(0)
            satir.append(Image(tampon, w - 3, (w - 3) * kirpinti.height / kirpinti.width))
        govde.append(satir)
    t = Table(govde, colWidths=[w] * 7)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 1.5), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, 0), (-1, -1), 0.3, CIZGI)]))
    return [PageBreak(), p("Living room object check", H1),
            p("Same crop in every column, after correcting each result's scale and shift. Black areas fell outside "
              "that tool's frame. The transfer column keeps the original pixels, but it also has the weakest light change.", NOT),
            Spacer(1, 2 * mm), t]


def ilk_sayfa():
    return [
        p("Changing sun direction without breaking the building", BASLIK),
        p("Mehmet Ozturk. Task report for MyArchitectAI. Tests run on 6 November 2026.", ALT),
        p("Bottom line", H1),
        p("No tool I tested moves the sun cleanly and also keeps the scene intact. The closest is the "
          "Sun-Direction LoRA on exteriors. I would pilot its Apache-2.0 4B version on exteriors only, behind "
          "automatic checks, and would not ship interiors yet."),
        p("What I found", H1),
        p("Options fall into three groups: LoRAs trained for lighting, general edit models, and commercial apps. "
          "I found only two built directly for sun position, and several public demos were paused or crashing. "
          "The full list is on page 2."),
        p("What I tried", H1),
        p("I ran three tools on three real photos, then repeated the best one on my own GPU in its "
          "license-safe version. Space times include queue and upload. Cost was $0."),
        tablo([
            ["Tool", "Sun moved?", "Scene kept?", "Time per image"],
            ["Sun-Direction 9B (Space)", "Yes on exteriors", "Framing kept. Colors turned gray", "20.5 to 26 s"],
            ["Sun-Direction 4B + color prompt (my RTX 4070)", "Yes on exteriors", "Color mostly back. Some materials changed, objects added", "81 to 103 s*"],
            ["Qwen 3D Lighting (Space)", "Partly. Old shadows stay", "Reframed 16 to 19%. Added flower pots", "6.5 to 17 s"],
            ["FLUX.1 Kontext (Space)", "No on exteriors", "Best structure, because little changed", "31.5 to 45 s"],
        ], [0.32, 0.2, 0.33, 0.15], True),
        p("*Partly offloaded to system RAM, so this is not production speed.", NOT),
        p("What went wrong", H1),
        *maddeler([
            "<b>Interiors:</b> every tool failed differently. Sun-Direction changed the sofa color, the table and the rug size. "
            "Kontext replaced the outside view. Qwen put a sun patch on the window wall, which is physically impossible.",
            "<b>Added content:</b> models invented flower pots, clouds, a tree and a ceiling light.",
            "<b>My first score misled me:</b> Kontext scored best because it barely changed the light, and the overall "
            "score missed the furniture changes. I also blamed the wrong step for the gray colors at first.",
            "<b>Light transfer:</b> applying only the model's light to the original kept every object, but old hard "
            "shadows stayed and halos appeared.",
        ]),
        p("How I decided which result is better", H1),
        p("I did not rank by one number. Each result had to pass three checks: the light really changed, the structure "
          "survived after correcting scale and shift, and individual objects survived in before and after crops. "
          "The numbers narrow the choice, but the final call is visual."),
        p("What I would put in production", H1),
        p("<b>Self-hosted serverless GPU</b> running the 4B LoRA with a color prompt, then color correction, automatic "
          "structure checks with retry, and 4K upscaling. <b>Estimated cost:</b> about $0.01 per image, or $0.02 with one "
          "retry, using RunPod's RTX 4090 at $1.34 per hour. <b>Estimated speed:</b> 20 to 26 s, based on 9B timings. "
          "Neither figure was measured for 4B on that GPU. Hosted Qwen and Kontext APIs cost $0.02 to $0.05 per image, "
          "but their open versions failed this task in my tests. An always-on GPU costs about $650 a month and only makes sense "
          "above roughly 16,000 images a month."),
        p("My next step would be to test 4B on at least 30 exteriors and measure how often a result passes the checks. "
          "This was one seed on three images, so these are failure patterns, not reliable rates."),
    ]


def piyasa_sayfasi(m):
    satirlar = [["Image", "Tool", "Structure", "Scale", "Light (EV)"]]
    adlar = {"01_dis_cephe_villa": "Villa", "03_dis_cephe_beton_bina": "Concrete", "02_ic_mekan_oturma_odasi": "Living room"}
    for gorsel, deneme, _, _ in GORSELLER:
        for arac, ek, etiket in DENEMELER[:5]:
            o = m[(arac, gorsel, deneme + ek)]
            satirlar.append([adlar[gorsel], etiket, f"{float(o['yapi_hizali']):.2f}", f"{float(o['olcek']):.2f}",
                             f"{float(o['isik_degisimi_ev']):.2f}"])
    return [
        PageBreak(),
        p("What is on the market", H1),
        tablo([
            ["Option", "Type", "One line"],
            ["Sun-Direction LoRA (FLUX.2 Klein)", "Open LoRA", "Trained for sun rotation and elevation on exteriors, using a rendered light ball. 4B is Apache-2.0; the 9B base is non-commercial."],
            ["Qwen-Edit Multi-Angle Lighting", "Open LoRA", "Eight directions plus above and below, by text. Author says some angles are uncontrolled."],
            ["Qwen-Edit Relight, Light Migration", "Open LoRA", "Relight from text, or copy the lighting of a reference image."],
            ["FLUX.1 Kontext", "Open weights, API", "General text editing. Dev weights are non-commercial; Pro is $0.04 per image on fal."],
            ["LTX-2.3 Relight IC-LoRA", "Open LoRA, video", "Sun direction and hardness for exterior video only."],
            ["IC-Light", "Open model", "Older SD 1.5 relighter with conflicting license labels."],
            ["Nano Banana family", "Commercial API", "Prompt-based editing, from $0.0336 per 1K image."],
            ["fal relighting", "Commercial API", "$0.04 per image. Underlying model not confirmed."],
            ["Magnific, Krea, Clipdrop", "Commercial apps", "Subscriptions. No evidence of architecture-specific relighting found."],
            ["LBM Relighting, UniRelight", "Ruled out", "LBM relights a foreground object and is non-commercial. UniRelight is non-commercial video."],
        ], [0.27, 0.15, 0.58], True),
        p("Measured results", H1),
        p("Structure is local correlation with the original after correcting scale and shift, from 0 to 1. Scale is "
          "the correction needed; 1.00 means the framing held. Light is the spatial change in brightness. A high "
          "structure score alone means little if the light barely changed.", NOT),
        Spacer(1, 1 * mm),
        tablo(satirlar, [0.14, 0.5, 0.12, 0.12, 0.12], True),
        p("Light transfer, which keeps the original pixels, scored 0.94 to 1.00 for structure but only 0.04 to 0.20 EV for "
          "light. Those images are on the next pages.", NOT),
    ]


def sorun_sayfasi():
    return [
        PageBreak(),
        p("Appendix: problems log", H1),
        p("Tools and access", H1),
        tablo([
            ["Problem", "Effect", "What I did"],
            ["Two Qwen Relight Spaces paused or crashing, Multi-Angle Space crashing", "First choices unusable", "Switched to Qwen 3D Lighting Control"],
            ["Second Sun-Direction Space crashing", "Only one working mirror", "Used the linoyts Space"],
            ["Anonymous ZeroGPU limit after three attempts", "Six planned runs failed", "Logged in with a Hugging Face account"],
            ["Saved Hugging Face token was invalid", "Runs still failed after login", "Diagnosed it, logged in again through the browser"],
            ["Sun-Direction reserves 150 s per run", "Color runs refused with 147 s left", "Moved those tests to my RTX 4070"],
            ["Klein 9B is too large for a 12 GB card", "Could not repeat the Space run locally", "Used 4B, which is also the license-safe one"],
            ["Local 4B needs offloading to system RAM", "81 to 116 s per image", "Recorded as a local test, not production speed"],
            ["Sun-Direction needs a ball image made in the browser", "No direct API call", "Recreated the ball scene in Python"],
            ["Openverse rate-limited image search", "Partial search results", "Used Unsplash instead"],
            ["OpenAI pricing refused access, BFL prices came back blank", "No first-party prices for those", "Left out of cost figures"],
            ["Google pricing page read only partly", "Figures less certain", "Marked as checked from a summary"],
        ], [0.46, 0.25, 0.29], True),
        p("Decisions that changed", H1),
        tablo([
            ["First position", "What changed"],
            ["LBM was a candidate", "Dropped: it relights a foreground object and is non-commercial"],
            ["Free API credits were expected", "None shown on Google, fal or Replicate"],
            ["A render was one of the three test images", "Replaced with a real photo, so renders remain untested"],
            ["The villa was chosen for hard shadows", "Its shadows are softer than expected and it is heavily processed"],
            ["Sun-Direction looked like the clear winner", "Changed after the interior object check"],
            ["Gray colors seemed to come from the overcast pass", "Saved that image. Color survived it, so the LoRA pass is the cause"],
            ["The 9B model seemed the one to recommend", "Replaced by 4B because 9B is non-commercial"],
            ["Qwen reframing might have been my size settings", "Same result at the Space's own sizes"],
            ["Light transfer might solve everything", "Objects were kept, but the sun did not really move on exteriors"],
            ["Smooth transfer was the first setting", "Light barely changed. The sharper setting added halos"],
        ], [0.45, 0.55], True),
        p("Measurement problems", H1),
        tablo([
            ["Problem", "Fix or status"],
            ["Structure score fell near zero on reframed images", "Added scale and shift alignment"],
            ["Kontext scored best while barely changing the light", "Score light change separately"],
            ["Score could not separate a correct shadow from an added object", "Read the difference map by eye"],
            ["Overall score missed the sofa, table and rug changes", "Added per-object crops and measurements"],
            ["Color check ignores brightness, so dark to light gray scores low", "Not fixed. Crops are checked by eye"],
            ["Position check gave a 1 px table shift while its shape had changed", "Use object structure and crops"],
        ], [0.6, 0.4], True),
        Spacer(1, 2 * mm),
        p("Photo credits, Unsplash: framesforyourheart, Clay Banks, Valentin Gerardi. All attempts are kept in the "
          "project's sonuclar folder, including a repeat Qwen run at the Space's sizes that gave the same result.", NOT),
    ]


def sayfa_no(c, d):
    c.setFont("Arial", 7.5)
    c.setFillColor(GRI)
    c.drawRightString(A4[0] - 15 * mm, 8 * mm, str(d.page))


def main():
    m = metrikler()
    govde = ilk_sayfa() + piyasa_sayfasi(m)
    for gorsel, deneme, ad, hedef in GORSELLER:
        govde += [PageBreak()] + resim_sayfasi(gorsel, deneme, ad, hedef, m)
    govde += nesne_sayfasi() + sorun_sayfasi()
    belge = SimpleDocTemplate(CIKTI, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=11 * mm,
                              bottomMargin=12 * mm, title="Changing sun direction without breaking the building",
                              author="Mehmet Ozturk", subject="MyArchitectAI task report")
    belge.build(govde, onFirstPage=sayfa_no, onLaterPages=sayfa_no)
    print(CIKTI)


if __name__ == "__main__":
    main()
