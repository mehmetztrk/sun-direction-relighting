"""Run the Sun-Direction LoRA (FLUX.2 Klein 4B) on my own GPU.

    python run_local.py              run everything in TRIES
    python run_local.py --only villa_angles
    python run_local.py --limit 1    quick test

Works on a 12 GB card, but slowly, because part of the model has to sit in system RAM.
Results go to results/sun_4b_local, and the overcast step is saved to results/_overcast.
"""
import argparse
import sys
import time
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

from run_space import log_time, sun_ball

BASE_MODEL = "black-forest-labs/FLUX.2-klein-4B"
LORA = "eric-venti-seeds/Sun-Direction-Lora-Flux2Klein4B"
LORA_FILE = "Sun_direction_LoRA_Flux_2_Klein_4b_v1.safetensors"
TRIGGER = "match the sun direction from the reference"
OVERCAST = "make it an overcast day, remove the shadows"
STEPS, GUIDANCE, PIXELS = 4, 1.0, 1024 * 1024
OVERCAST_SEED, SEED = 161, 42

KEEP_COLOR_OUTSIDE = "clear blue sky, warm natural sunlight, same colors and materials as the original"
KEEP_COLOR_INSIDE = "warm natural sunlight, same furniture colors and materials as the original"
HARD_SUN = "strong direct sunlight, hard sharp shadows, " + KEEP_COLOR_OUTSIDE
SUNSET = "low orange sunset light, long dark shadows, same materials as the original"

VILLA, ROOM, BLOCK = "01_villa", "02_living_room", "03_concrete_block"

# (group, photo, trial, sun rotation, sun height, ball brightness, extra prompt)
TRIES = [
    ("first_run", BLOCK, "right", 90, 30, 1.5, ""),
    ("first_run", VILLA, "left", -90, 30, 1.5, ""),
    ("first_run", ROOM, "back_left", -135, 25, 1.5, ""),
    ("first_run", BLOCK, "right_color", 90, 30, 1.5, KEEP_COLOR_OUTSIDE),
    ("first_run", VILLA, "left_color", -90, 30, 1.5, KEEP_COLOR_OUTSIDE),
    ("first_run", ROOM, "back_left_color", -135, 25, 1.5, KEEP_COLOR_INSIDE),
    ("villa_angles", VILLA, "sun_front", 0, 35, 3.0, HARD_SUN),
    ("villa_angles", VILLA, "sun_back", 180, 25, 3.0, HARD_SUN),
    ("villa_angles", VILLA, "sun_left", -90, 25, 3.0, HARD_SUN),
    ("villa_angles", VILLA, "sun_right", 90, 25, 3.0, HARD_SUN),
    ("villa_angles", VILLA, "sun_top", 0, 85, 3.0, HARD_SUN),
    ("villa_angles", VILLA, "sunset_left", -90, 8, 3.0, SUNSET),
    ("villa_low_sun", VILLA, "sun_left_low", -100, 12, 3.0, HARD_SUN),
    ("villa_low_sun", VILLA, "sun_right_low", 100, 12, 3.0, HARD_SUN),
    ("villa_low_sun", VILLA, "sunset_right", 90, 8, 3.0, SUNSET),
]


def resize_to_1mp(image):
    w, h = image.size
    scale = (PIXELS / (w * h)) ** 0.5
    return image.convert("RGB").resize((round(w * scale / 16) * 16, round(h * scale / 16) * 16), Image.LANCZOS)


def generate(pipe, images, prompt, size, seed):
    return pipe(image=images, prompt=prompt, width=size[0], height=size[1], num_inference_steps=STEPS,
                guidance_scale=GUIDANCE, generator=torch.Generator("cuda").manual_seed(seed)).images[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="run one group from TRIES")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    tries = [t for t in TRIES if args.only in (None, t[0])][:args.limit]
    pipe = Flux2KleinPipeline.from_pretrained(BASE_MODEL, torch_dtype=torch.bfloat16)
    pipe.load_lora_weights(LORA, weight_name=LORA_FILE, adapter_name="sun")
    pipe.enable_model_cpu_offload()

    results = Path("results/sun_4b_local")
    overcast_dir = Path("results/_overcast")
    results.mkdir(parents=True, exist_ok=True)
    overcast_dir.mkdir(exist_ok=True)

    for _, photo, trial, rotation, height, brightness, prompt in tries:
        scene = resize_to_1mp(Image.open(f"photos/{photo}.jpg"))
        torch.cuda.reset_peak_memory_stats()
        start = time.time()

        # the LoRA wants a flat, shadowless image, so make one first and reuse it
        overcast_file = overcast_dir / f"{photo}__overcast.png"
        if overcast_file.exists():
            overcast = Image.open(overcast_file).convert("RGB")
        else:
            pipe.disable_lora()
            overcast = generate(pipe, [scene], OVERCAST, scene.size, OVERCAST_SEED)
            overcast.save(overcast_file)

        pipe.enable_lora()
        ball = sun_ball(rotation, height, brightness).resize((1024, 1024), Image.LANCZOS)
        result = generate(pipe, [overcast, ball], TRIGGER + (", " + prompt if prompt else ""), scene.size, SEED)
        seconds = time.time() - start

        output = results / f"{photo}__{trial}.png"
        result.save(output)
        log_time("sun_4b_local", photo, trial, seconds, rotation, height, prompt)
        print(f"{output}  {seconds:.1f} s, peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB", flush=True)


if __name__ == "__main__":
    main()
