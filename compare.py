"""Compare every result against its original photo.

    python compare.py

Results must be named results/<tool>/<photo>__<trial>.png.
Writes side by side images and two csv files to results/_report.

The scores only help me sort results. A result can score well and still look wrong,
so I always check the images too. Things it tracks:
    structure  did edges and details stay the same (0 to 1)
    light      how much the brightness pattern changed (higher = stronger change)
    scale      1.00 means the model kept the framing
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORK_SIZE = 1024
WINDOW = 7
MIN_TEXTURE = 0.02  # ignore flat areas like sky and plain walls
EDGE_TOLERANCE = 2
SCALES = np.arange(0.80, 1.205, 0.01)
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
FIELDS = ["tool", "photo", "trial", "structure_raw", "structure", "scale", "edges", "light_ev",
          "exposure_ev", "shift_px", "aspect_change_pct", "warning"]


def load(path, size=None):
    image = Image.open(path).convert("RGB")
    if size is None:
        scale = WORK_SIZE / max(image.size)
        size = (round(image.width * scale), round(image.height * scale))
    return image.resize(size, Image.LANCZOS)


def luminance(image):
    return np.asarray(image, dtype=np.float64).dot([0.2126, 0.7152, 0.0722]) / 255


def box(a, r):
    k = 2 * r + 1
    summed = np.pad(a, r + 1, mode="edge").cumsum(0).cumsum(1)
    out = summed[k:, k:] - summed[:-k, k:] - summed[k:, :-k] + summed[:-k, :-k]
    return out[:a.shape[0], :a.shape[1]] / (k * k)


def blur(a, r):
    for _ in range(3):
        a = box(a, r)
    return a


def local_match(a, b, r=WINDOW):
    """Local correlation. It ignores brightness changes, so new light alone doesn't lower it."""
    mean_a, mean_b = box(a, r), box(b, r)
    var_a = np.maximum(box(a * a, r) - mean_a ** 2, 0)
    var_b = np.maximum(box(b * b, r) - mean_b ** 2, 0)
    cov = box(a * b, r) - mean_a * mean_b
    bottom = np.sqrt(var_a * var_b)
    match = np.divide(cov, bottom, out=np.zeros_like(cov), where=bottom > 1e-8)
    return np.clip(match, -1, 1), np.sqrt(var_a)


def edges(a):
    gy, gx = np.gradient(box(a, 1))
    g = np.hypot(gx, gy)
    return g > np.percentile(g, 90)


def edge_score(a, b, r=EDGE_TOLERANCE):
    ea, eb = edges(a), edges(b)
    near_a, near_b = box(ea.astype(float), r) > 0, box(eb.astype(float), r) > 0
    precision = (eb & near_a).sum() / max(eb.sum(), 1)
    recall = (ea & near_b).sum() / max(ea.sum(), 1)
    return 2 * precision * recall / max(precision + recall, 1e-8)


def find_shift(a, b):
    gy_a, gx_a = np.gradient(box(a, 1))
    gy_b, gx_b = np.gradient(box(b, 1))
    product = np.fft.rfft2(np.hypot(gx_a, gy_a)) * np.conj(np.fft.rfft2(np.hypot(gx_b, gy_b)))
    peak = np.fft.irfft2(product / np.maximum(np.abs(product), 1e-8), s=a.shape)
    dy, dx = np.unravel_index(peak.argmax(), peak.shape)
    dy = dy - a.shape[0] if dy > a.shape[0] / 2 else dy
    dx = dx - a.shape[1] if dx > a.shape[1] / 2 else dx
    return int(dx), int(dy)


def align(image, scale, dx, dy):
    w, h = image.size
    s = 1 / scale
    return image.transform((w, h), Image.AFFINE,
                           (s, 0, w / 2 * (1 - s) - s * dx, 0, s, h / 2 * (1 - s) - s * dy), Image.BILINEAR)


def best_alignment(before, after):
    """Some models zoom or shift the picture. Undo that first so the score is fair."""
    a = luminance(before)
    _, texture = local_match(a, a)
    mask = texture > MIN_TEXTURE
    best, fit = -1.0, (1.0, 0, 0)
    for scale in SCALES:
        b = luminance(align(after, scale, 0, 0))
        dx, dy = find_shift(a, b)
        score = local_match(a, np.roll(b, (dy, dx), (0, 1)))[0][mask].mean()
        if score > best:
            best, fit = score, (float(scale), dx, dy)
    return float(best), fit


def light_map(a, b):
    r = max(a.shape) // 40
    difference = blur(np.log2(b + 0.02), r) - blur(np.log2(a + 0.02), r)
    return difference - difference.mean(), float(difference.mean())


def measure(before, after, original_size):
    a, b = luminance(before), luminance(after)
    match, texture = local_match(a, b)
    mask = texture > MIN_TEXTURE
    light, exposure = light_map(a, b)
    aspect = abs(original_size[0] / original_size[1] / (before.width / before.height) - 1) * 100
    structure, fit = best_alignment(before, after)
    scores = {
        "structure_raw": match[mask].mean(),
        "structure": structure,
        "scale": fit[0],
        "edges": edge_score(a, b),
        "light_ev": light.std(),
        "exposure_ev": exposure,
        "shift_px": float(np.hypot(*find_shift(a, b))),
        "aspect_change_pct": aspect,
        "warning": "aspect ratio changed" if aspect > 1 else "",
    }
    return scores, blur(np.where(mask, 1 - match, 0), 2), light, fit


def color_ab(image):
    """Lab color without brightness, since brightness is supposed to change."""
    rgb = np.asarray(image, dtype=np.float64) / 255
    rgb = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = rgb @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    f = xyz / [0.9505, 1.0, 1.089]
    f = np.where(f > 0.008856, np.cbrt(f), 7.787 * f + 16 / 116)
    return np.stack([500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def measure_objects(before, aligned, regions):
    w, h = before.size
    ab_a, ab_b = color_ab(before), color_ab(aligned)
    a, b = luminance(before), luminance(aligned)
    out = {}
    for name, (x0, y0, x1, y1) in regions.items():
        area = slice(round(y0 * h), round(y1 * h)), slice(round(x0 * w), round(x1 * w))
        match, texture = local_match(a[area], b[area])
        out[name] = {"color_change": float(np.linalg.norm(ab_a[area].mean((0, 1)) - ab_b[area].mean((0, 1)))),
                     "shift_px": float(np.hypot(*find_shift(a[area], b[area]))),
                     "structure": float(match[texture > MIN_TEXTURE].mean())}
    return out


def change_panel(after, difference):
    gray = luminance(after)[..., None].repeat(3, 2) * 0.6 + 0.2
    alpha = np.clip(difference / 0.6, 0, 1)[..., None]
    rgb = gray * (1 - alpha) + np.array([0.9, 0.05, 0.05]) * alpha
    return Image.fromarray((rgb * 255).astype(np.uint8))


def light_panel(light):
    d = np.clip(light / 2, -1, 1)[..., None]
    rgb = 1 - np.maximum(d, 0) * [0, 1, 1] - np.maximum(-d, 0) * [1, 1, 0]
    return Image.fromarray((rgb * 255).astype(np.uint8))


def font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def side_by_side(before, rows, path):
    width = 420
    height = round(width * before.height / before.width)
    gap, title = 6, 26
    canvas = Image.new("RGB", (width * 4 + gap * 3, (height + title * 2 + gap) * len(rows)), "white")
    draw = ImageDraw.Draw(canvas)
    text = font(14)
    labels = ["Before", "After", "What changed (red)", "Light (red brighter, blue darker)"]
    y = 0
    for name, scores, panels in rows:
        summary = (f"{name}   structure {scores['structure']:.2f}   light {scores['light_ev']:.2f}   "
                   f"scale {scores['scale']:.2f}   {scores['warning']}")
        draw.text((4, y + 5), summary, fill="black", font=text)
        y += title
        for i, (panel, label) in enumerate(zip([before] + panels, labels)):
            x = i * (width + gap)
            draw.text((x + 4, y + 5), label, fill="#555555", font=text)
            canvas.paste(panel.resize((width, height), Image.LANCZOS), (x, y + title))
        y += title + height + gap
    canvas.save(path, quality=90)


def find_results(results):
    found = []
    for folder in sorted(p for p in results.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in EXTENSIONS and "__" in path.stem:
                photo, trial = path.stem.split("__", 1)
                found.append((folder.name, photo, trial, path))
    return found


def save_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: round(v, 3) if isinstance(v, float) else v for k, v in row.items()})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    photos = {p.stem: p for p in Path("photos").iterdir() if p.suffix.lower() in EXTENSIONS}
    regions_by_photo = json.loads(Path("photos/regions.json").read_text(encoding="utf-8"))
    results = find_results(Path("results"))
    report = Path("results/_report")
    report.mkdir(exist_ok=True)

    all_scores, object_scores = [], []
    for stem, photo in sorted(photos.items()):
        before = load(photo)
        regions = regions_by_photo.get(stem, {})
        rows = []
        for tool, photo_name, trial, path in results:
            if photo_name != stem:
                continue
            after = load(path, before.size)
            scores, change, light, fit = measure(before, after, Image.open(path).size)
            all_scores.append({"tool": tool, "photo": stem, "trial": trial, **scores})
            rows.append((f"{tool} / {trial}", scores, [after, change_panel(after, change), light_panel(light)]))
            if regions:
                for name, values in measure_objects(before, align(after, *fit), regions).items():
                    object_scores.append({"tool": tool, "photo": stem, "trial": trial, "object": name, **values})
            print(f"{stem} / {tool} / {trial}: structure {scores['structure']:.2f}, light {scores['light_ev']:.2f}")
        if rows:
            side_by_side(before, rows, report / f"{stem}_comparison.jpg")

    save_csv(report / "scores.csv", FIELDS, all_scores)
    save_csv(report / "objects.csv", ["tool", "photo", "trial", "object", "color_change", "shift_px", "structure"],
             object_scores)


if __name__ == "__main__":
    main()
