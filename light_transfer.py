"""Take only the light from a model's result and put it on the original photo.

The models keep redrawing furniture and materials, so this keeps the original pixels
and just copies a smoothed brightness change from the result.

    python light_transfer.py
    python light_transfer.py --tool sun_direction --radius 3 --epsilon 0.05 --prefix transfer_sharp

Spoiler: objects stay perfect, but old hard shadows don't go away.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import compare

RADIUS = 12
EPSILON = 0.002
MAX_EV = 2.0


def guided_filter(guide, p, r, eps):
    mean_guide, mean_p = compare.box(guide, r), compare.box(p, r)
    var = compare.box(guide * guide, r) - mean_guide ** 2
    cov = compare.box(guide * p, r) - mean_guide * mean_p
    a = cov / (var + eps)
    b = mean_p - a * mean_guide
    return compare.box(a, r) * guide + compare.box(b, r)


def light_ratio(before, after, radius=RADIUS, epsilon=EPSILON):
    _, fit = compare.best_alignment(before, after)
    aligned = compare.align(after, *fit)
    valid = np.asarray(compare.align(Image.new("RGB", after.size, "white"), *fit), dtype=np.float64)[..., 0] / 255

    log_before = np.log2(compare.luminance(before) + 0.02)
    log_after = np.log2(compare.luminance(aligned) + 0.02)
    ratio = (log_after - log_before) * (valid > 0.99)
    ratio = guided_filter(log_before / 6, ratio, radius, epsilon)
    return np.clip(ratio * compare.blur(valid, 8), -MAX_EV, MAX_EV)


def apply_light(photo, ratio):
    full = Image.open(photo).convert("RGB")
    scaled = Image.fromarray(ratio.astype(np.float32), "F").resize(full.size, Image.BICUBIC)
    rgb = (np.asarray(full, dtype=np.float64) / 255) ** 2.2
    out = rgb * (2.0 ** np.asarray(scaled, dtype=np.float64))[..., None]
    return Image.fromarray((np.clip(out, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tool", help="only use results from this tool")
    parser.add_argument("--radius", type=int, default=RADIUS)
    parser.add_argument("--epsilon", type=float, default=EPSILON)
    parser.add_argument("--prefix", default="transfer")
    args = parser.parse_args()

    photos = {p.stem: p for p in Path("photos").iterdir() if p.suffix.lower() in compare.EXTENSIONS}
    for tool, photo, _, path in compare.find_results(Path("results")):
        if tool.startswith("transfer") or photo not in photos or args.tool not in (None, tool):
            continue
        before = compare.load(photos[photo])
        ratio = light_ratio(before, compare.load(path, before.size), args.radius, args.epsilon)
        folder = Path("results") / f"{args.prefix}_{tool}"
        folder.mkdir(exist_ok=True)
        apply_light(photos[photo], ratio).save(folder / path.name)
        print(folder / path.name)


if __name__ == "__main__":
    main()
