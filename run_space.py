"""Send a photo to one of the free Hugging Face Spaces and save the result.

    python run_space.py sun_direction photos/03_concrete_block.jpg right --sun 90 --height 30
    python run_space.py qwen_3d photos/01_villa.jpg left --sun 270 --height 30
    python run_space.py kontext photos/02_living_room.jpg back_left --prompt "..."

--sun is where the sun sits compared to the camera.
sun_direction: -180 to 180 (0 behind the camera, 90 right, -90 left, 180 behind the building)
qwen_3d: 0 to 315 in 45 degree steps (0 front, 90 right, 270 left)

Run `hf auth login` first, otherwise the free quota runs out after a few images.
"""
import argparse
import base64
import csv
import io
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from gradio_client import Client, handle_file
from huggingface_hub import get_token
from PIL import Image

SPACES = {
    "sun_direction": "linoyts/sun-direction-flux2-klein",
    "qwen_3d": "prithivMLmods/Qwen-Image-Edit-3D-Lighting-Control",
    "kontext": "black-forest-labs/FLUX.1-Kontext-Dev",
}


def sun_ball(rotation, elevation, intensity=1.5, size=512):
    """Draw the lit gray ball the Sun-Direction LoRA uses as its light reference.

    The Space renders this with Three.js in the browser, so this is the same scene in numpy.
    """
    gray = (0x8a / 255) ** 2.2
    camera = np.array([0.0, 6.0, 8.0])
    forward = np.array([0.0, -0.5, 0.0]) - camera
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    t = np.tan(np.radians(35 / 2))
    v, u = np.mgrid[0:size, 0:size]
    px, py = (2 * (u + 0.5) / size - 1) * t, (1 - 2 * (v + 0.5) / size) * t
    rays = forward + px[..., None] * right + py[..., None] * up
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)

    a, e = np.radians(rotation), np.radians(elevation)
    sun = np.array([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)])

    def hit_sphere(origin, directions):
        b = (origin * directions).sum(-1)
        d = b ** 2 - ((origin ** 2).sum(-1) - 1)
        return np.where(d > 0, -b - np.sqrt(np.maximum(d, 0)), np.inf)

    t_sphere = hit_sphere(camera, rays)
    t_floor = np.where(rays[..., 1] < 0, (-1 - camera[1]) / rays[..., 1], np.inf)
    on_sphere = t_sphere < t_floor
    t_hit = np.where(on_sphere, t_sphere, t_floor)
    point = camera + rays * np.where(np.isinf(t_hit), 0, t_hit)[..., None]
    normal = np.where(on_sphere[..., None], point, [0.0, 1.0, 0.0])
    color = np.where(on_sphere, (0xcc / 255) ** 2.2, gray)
    light = np.maximum((normal * sun).sum(-1), 0)
    shadow = (hit_sphere(point + normal * 1e-3, sun[None, None]) < np.inf) & ~on_sphere
    pixels = color * (0.2 + intensity * light * ~shadow)
    pixels = np.where(np.isinf(t_hit), gray, pixels)
    return Image.fromarray((np.clip(pixels, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).convert("RGB")


def ball_state(rotation, elevation, intensity=1.5):
    buffer = io.BytesIO()
    sun_ball(rotation, elevation, intensity).save(buffer, "PNG")
    png = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    return json.dumps({"rotation": rotation, "elevation": elevation, "intensity": intensity, "png": png})


def run(tool, photo, args):
    client = Client(SPACES[tool], token=get_token(), verbose=False)
    if tool == "sun_direction":
        result = client.predict(handle_file(str(photo)), ball_state(args.sun, args.height),
                                args.prompt, True, args.seed, False, api_name="/relight")
        return result[0][1]
    if tool == "qwen_3d":
        width, height = client.predict(handle_file(str(photo)), api_name="/update_dimensions_on_upload")
        result = client.predict(handle_file(str(photo)), args.sun, args.height, args.seed, False,
                                1.0, 4, height, width, api_name="/infer_lighting_edit")
        return result[0]
    result = client.predict(handle_file(str(photo)), args.prompt, args.seed, False, 2.5, 28, api_name="/infer")
    return result[0]["path"] if isinstance(result[0], dict) else result[0]


def log_time(tool, photo, trial, seconds, sun, height, prompt):
    path = Path("results/timings.csv")
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";").writerow([datetime.now().isoformat(timespec="seconds"), tool, photo, trial,
                                               round(seconds, 1), sun, height, prompt])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tool", choices=SPACES)
    parser.add_argument("photo", type=Path)
    parser.add_argument("trial", help="short name for this try, like left")
    parser.add_argument("--sun", type=float, default=90)
    parser.add_argument("--height", type=float, default=30)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    start = time.time()
    temp_file = run(args.tool, args.photo, args)
    seconds = time.time() - start

    folder = Path("results") / args.tool
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{args.photo.stem}__{args.trial}.png"
    Image.open(temp_file).convert("RGB").save(output)
    shutil.rmtree(Path(temp_file).parent, ignore_errors=True)
    log_time(args.tool, args.photo.stem, args.trial, seconds, args.sun, args.height, args.prompt)
    print(f"{output}  ({seconds:.1f} s, queue included)")


if __name__ == "__main__":
    main()
