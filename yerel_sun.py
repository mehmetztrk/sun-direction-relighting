"""Sun-Direction LoRA'nın FLUX.2 Klein 4B sürümünü kendi GPU'nda çalıştırır.

Çalıştırma:
    python yerel_sun.py            aşağıdaki tüm denemeler
    python yerel_sun.py --sinir 1  yalnızca ilk deneme

Sonuçlar sonuclar/yerel_4b/ altına, bulutlu ara görseller sonuclar/_ara/ altına yazılır.
Süreler sonuclar/sureler.csv dosyasına eklenir.

Gerekenler: torch (CUDA), diffusers, transformers, accelerate, peft, gradio_client, pillow
"""
import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

from calistir import isik_topu

TABAN = "black-forest-labs/FLUX.2-klein-4B"
LORA = "eric-venti-seeds/Sun-Direction-Lora-Flux2Klein4B"
LORA_DOSYA = "Sun_direction_LoRA_Flux_2_Klein_4b_v1.safetensors"
TETIK = "match the sun direction from the reference"
BULUTLU = "make it an overcast day, remove the shadows"
ADIM, REHBER, TOPLAM_PIKSEL = 4, 1.0, 1024 * 1024
BULUT_TOHUM, TOHUM = 161, 42

RENK_DIS = "clear blue sky, warm natural sunlight, same colors and materials as the original"
RENK_IC = "warm natural sunlight, same furniture colors and materials as the original"
VILLA, ODA, BETON = "01_dis_cephe_villa", "02_ic_mekan_oturma_odasi", "03_dis_cephe_beton_bina"

# (görsel, deneme, güneş yönü, yükseklik, ek prompt, bulutlu adım)
DENEMELER = [
    (BETON, "sag", 90, 30, "", True),
    (VILLA, "sol", -90, 30, "", True),
    (ODA, "arka_sol", -135, 25, "", True),
    (BETON, "sag_renk", 90, 30, RENK_DIS, True),
    (VILLA, "sol_renk", -90, 30, RENK_DIS, True),
    (ODA, "arka_sol_renk", -135, 25, RENK_IC, True),
]


def bir_mp(goruntu):
    g, y = goruntu.size
    olcek = (TOPLAM_PIKSEL / (g * y)) ** 0.5
    return goruntu.convert("RGB").resize((round(g * olcek / 16) * 16, round(y * olcek / 16) * 16), Image.LANCZOS)


def uret(boru, gorseller, prompt, boyut, tohum):
    return boru(image=gorseller, prompt=prompt, width=boyut[0], height=boyut[1], num_inference_steps=ADIM,
                guidance_scale=REHBER, generator=torch.Generator("cuda").manual_seed(tohum)).images[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sinir", type=int, help="yalnızca ilk N denemeyi çalıştırır")
    args = ap.parse_args()

    baslangic = time.time()
    boru = Flux2KleinPipeline.from_pretrained(TABAN, torch_dtype=torch.bfloat16)
    boru.load_lora_weights(LORA, weight_name=LORA_DOSYA, adapter_name="sun")
    boru.enable_model_cpu_offload()
    print(f"Model yüklendi: {time.time() - baslangic:.0f} sn", flush=True)

    Path("sonuclar/yerel_4b").mkdir(parents=True, exist_ok=True)
    Path("sonuclar/_ara").mkdir(exist_ok=True)
    kayit = Path("sonuclar/sureler.csv")
    bulut_onbellek = {}

    for gorsel, deneme, gun, yukseklik, ek, bulutlu in DENEMELER[:args.sinir]:
        sahne = bir_mp(Image.open(f"gorseller/{gorsel}.jpg"))
        torch.cuda.reset_peak_memory_stats()
        baslangic = time.time()
        referans = sahne
        if bulutlu:
            if gorsel not in bulut_onbellek:
                boru.disable_lora()
                bulut_onbellek[gorsel] = uret(boru, [sahne], BULUTLU, sahne.size, BULUT_TOHUM)
                bulut_onbellek[gorsel].save(f"sonuclar/_ara/{gorsel}__bulutlu.png")
            referans = bulut_onbellek[gorsel]
        boru.enable_lora()
        top = isik_topu(gun, yukseklik).resize((1024, 1024), Image.LANCZOS)
        sonuc = uret(boru, [referans, top], TETIK + (", " + ek if ek else ""), sahne.size, TOHUM)
        sure = time.time() - baslangic
        cikti = Path("sonuclar/yerel_4b") / f"{gorsel}__{deneme}.png"
        sonuc.save(cikti)
        with open(kayit, "a", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter=";").writerow([datetime.now().isoformat(timespec="seconds"), "yerel_4b",
                                                   gorsel, deneme, round(sure, 1), gun, yukseklik, ek])
        print(f"{cikti}  {sure:.1f} sn, en yüksek VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB", flush=True)


if __name__ == "__main__":
    main()
