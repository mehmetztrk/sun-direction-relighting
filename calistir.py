"""Bir görseli ücretsiz Hugging Face Space'lerinden biriyle yeniden aydınlatır.

Örnek:
    python calistir.py sun_direction gorseller/03_dis_cephe_beton_bina.jpg sol --gun 90 --yukseklik 30
    python calistir.py qwen_3d gorseller/01_dis_cephe_villa.jpg sol --gun 270 --yukseklik 30
    python calistir.py kontext gorseller/02_ic_mekan_oturma_odasi.jpg gunbatimi --prompt "..."

--gun: güneşin kameraya göre yönü. sun_direction için -180..180 (0 kameranın arkası,
90 sağ, -90 sol). qwen_3d için 0..315 (0 ön, 90 sağ, 270 sol, 45 derecelik adımlar).

Çıktı sonuclar/<arac>/<gorsel>__<deneme>.png olarak kaydedilir, süre sonuclar/sureler.csv
dosyasına eklenir. "hf auth login" ile giriş yapıldıysa ücretsiz hesabın kotası kullanılır.

Gerekenler: gradio_client, huggingface_hub, numpy, pillow
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

SPACE = {
    "sun_direction": "linoyts/sun-direction-flux2-klein",
    "qwen_3d": "prithivMLmods/Qwen-Image-Edit-3D-Lighting-Control",
    "kontext": "black-forest-labs/FLUX.1-Kontext-Dev",
}


def isik_topu(rotation, elevation, intensity=1.5, boyut=512):
    """Space'teki Three.js sahnesinin eşdeğeri: gri zemin üstünde yönlü ışıkla aydınlatılmış küre."""
    gri = (0x8a / 255) ** 2.2  # doğrusal uzayda sahne rengi
    kamera = np.array([0.0, 6.0, 8.0])
    ileri = np.array([0.0, -0.5, 0.0]) - kamera
    ileri /= np.linalg.norm(ileri)
    sag = np.cross(ileri, [0.0, 1.0, 0.0])
    sag /= np.linalg.norm(sag)
    yukari = np.cross(sag, ileri)
    t = np.tan(np.radians(35 / 2))
    v, u = np.mgrid[0:boyut, 0:boyut]
    px, py = (2 * (u + 0.5) / boyut - 1) * t, (1 - 2 * (v + 0.5) / boyut) * t
    yon = ileri + px[..., None] * sag + py[..., None] * yukari
    yon /= np.linalg.norm(yon, axis=-1, keepdims=True)

    a, e = np.radians(rotation), np.radians(elevation)
    gunes = np.array([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)])

    def kure_kesisimi(baslangic, yonler):
        b = (baslangic * yonler).sum(-1)
        d = b ** 2 - ((baslangic ** 2).sum(-1) - 1)
        return np.where(d > 0, -b - np.sqrt(np.maximum(d, 0)), np.inf)

    tk = kure_kesisimi(kamera, yon)
    tz = np.where(yon[..., 1] < 0, (-1 - kamera[1]) / yon[..., 1], np.inf)
    kure = tk < tz
    tm = np.where(kure, tk, tz)
    nokta = kamera + yon * np.where(np.isinf(tm), 0, tm)[..., None]
    normal = np.where(kure[..., None], nokta, [0.0, 1.0, 0.0])
    albedo = np.where(kure, (0xcc / 255) ** 2.2, gri)
    lambert = np.maximum((normal * gunes).sum(-1), 0)
    golge = (kure_kesisimi(nokta + normal * 1e-3, gunes[None, None]) < np.inf) & ~kure
    renk = albedo * (0.2 + intensity * lambert * ~golge)
    renk = np.where(np.isinf(tm), gri, renk)
    return Image.fromarray((np.clip(renk, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).convert("RGB")


def top_durumu(rotation, elevation, intensity=1.5):
    tampon = io.BytesIO()
    isik_topu(rotation, elevation, intensity).save(tampon, "PNG")
    png = "data:image/png;base64," + base64.b64encode(tampon.getvalue()).decode()
    return json.dumps({"rotation": rotation, "elevation": elevation, "intensity": intensity, "png": png})


def calistir(arac, gorsel, args):
    client = Client(SPACE[arac], token=get_token(), verbose=False)
    if arac == "sun_direction":
        sonuc = client.predict(handle_file(str(gorsel)), top_durumu(args.gun, args.yukseklik),
                               args.prompt, True, args.seed, False, api_name="/relight")
        return sonuc[0][1]
    if arac == "qwen_3d":
        g, y = client.predict(handle_file(str(gorsel)), api_name="/update_dimensions_on_upload")
        sonuc = client.predict(handle_file(str(gorsel)), args.gun, args.yukseklik, args.seed, False,
                               1.0, 4, y, g, api_name="/infer_lighting_edit")
        return sonuc[0]
    sonuc = client.predict(handle_file(str(gorsel)), args.prompt, args.seed, False, 2.5, 28, api_name="/infer")
    return sonuc[0]["path"] if isinstance(sonuc[0], dict) else sonuc[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arac", choices=SPACE)
    ap.add_argument("gorsel", type=Path)
    ap.add_argument("deneme", help="dosya adına eklenecek kısa ad, örneğin sol")
    ap.add_argument("--gun", type=float, default=90)
    ap.add_argument("--yukseklik", type=float, default=30)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    baslangic = time.time()
    gecici = calistir(args.arac, args.gorsel, args)
    sure = time.time() - baslangic

    hedef = Path("sonuclar") / args.arac
    hedef.mkdir(parents=True, exist_ok=True)
    cikti = hedef / f"{args.gorsel.stem}__{args.deneme}.png"
    Image.open(gecici).convert("RGB").save(cikti)
    shutil.rmtree(Path(gecici).parent, ignore_errors=True)

    kayit = Path("sonuclar/sureler.csv")
    yeni = not kayit.exists()
    with open(kayit, "a", encoding="utf-8-sig" if yeni else "utf-8", newline="") as f:
        yazici = csv.writer(f, delimiter=";")
        if yeni:
            yazici.writerow(["zaman", "arac", "gorsel", "deneme", "toplam_sn", "gun", "yukseklik", "prompt"])
        yazici.writerow([datetime.now().isoformat(timespec="seconds"), args.arac, args.gorsel.stem,
                         args.deneme, round(sure, 1), args.gun, args.yukseklik, args.prompt])
    print(f"{cikti}  ({sure:.1f} sn, kuyruk dahil)")


if __name__ == "__main__":
    main()
