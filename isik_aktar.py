"""Model sonucundan yalnızca ışığı alıp özgün fotoğrafa uygular.

Özgün piksellerin rengi ve detayı korunur. Modelden sadece yumuşatılmış parlaklık
oranı alınır, bu yüzden model bir objeyi yeniden çizdiyse o değişiklik taşınmaz.

Çalıştırma:
    python isik_aktar.py

sonuclar/<arac>/ içindeki her sonuç için sonuclar/aktarim_<arac>/ altına aynı adla
yeni bir dosya yazar. Özgün denemelere dokunmaz.

Gerekenler: numpy, pillow
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import karsilastir as k

YARICAP = 12  # kılavuzlu filtre yarıçapı (1024 px'te)
EPSILON = 0.002  # büyüdükçe özgün kenarlara daha az yapışır
SINIR_EV = 2.0  # uygulanacak en büyük ışık değişimi


def kilavuzlu_filtre(kilavuz, p, r, eps):
    """Oranı özgün görselin kenarlarını izleyerek yumuşatır."""
    ort_i, ort_p = k.kutu(kilavuz, r), k.kutu(p, r)
    var_i = k.kutu(kilavuz * kilavuz, r) - ort_i ** 2
    kov = k.kutu(kilavuz * p, r) - ort_i * ort_p
    a = kov / (var_i + eps)
    b = ort_p - a * ort_i
    return k.kutu(a, r) * kilavuz + k.kutu(b, r)


def isik_orani(once, sonra, yaricap=YARICAP, epsilon=EPSILON):
    """Hizalanmış sonuçla özgün görsel arasındaki yumuşak log2 parlaklık oranı."""
    _, hiza = k.hizali_yapi(once, sonra)
    hizali = k.hizala(sonra, *hiza)
    bos = Image.new("L", sonra.size, 255)
    gecerli = np.asarray(k.hizala(bos.convert("RGB"), *hiza), dtype=np.float64)[..., 0] / 255

    log_a = np.log2(k.parlaklik(once) + 0.02)
    log_b = np.log2(k.parlaklik(hizali) + 0.02)
    oran = (log_b - log_a) * (gecerli > 0.99)
    oran = kilavuzlu_filtre(log_a / 6, oran, yaricap, epsilon)
    return np.clip(oran * k.bulanik(gecerli, 8), -SINIR_EV, SINIR_EV)


def uygula(ozgun_yol, oran):
    """Oranı özgün çözünürlüğe büyütüp doğrusal ışık uzayında uygular."""
    tam = Image.open(ozgun_yol).convert("RGB")
    buyuk = Image.fromarray(oran.astype(np.float32), "F").resize(tam.size, Image.BICUBIC)
    rgb = (np.asarray(tam, dtype=np.float64) / 255) ** 2.2
    cikti = rgb * (2.0 ** np.asarray(buyuk, dtype=np.float64))[..., None]
    return Image.fromarray((np.clip(cikti, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gorseller", type=Path, default=Path("gorseller"))
    ap.add_argument("--sonuclar", type=Path, default=Path("sonuclar"))
    ap.add_argument("--arac", help="yalnızca bu aracın sonuçlarını işler")
    ap.add_argument("--yaricap", type=int, default=YARICAP)
    ap.add_argument("--epsilon", type=float, default=EPSILON)
    ap.add_argument("--etiket", default="aktarim", help="çıktı klasörünün öneki")
    args = ap.parse_args()

    ozgunler = {p.stem: p for p in args.gorseller.iterdir() if p.suffix.lower() in k.UZANTILAR}
    for arac, gorsel, deneme, yol in k.deneme_bul(args.sonuclar):
        if arac.startswith("aktarim") or gorsel not in ozgunler or args.arac not in (None, arac):
            continue
        once = k.yukle(ozgunler[gorsel])
        oran = isik_orani(once, k.yukle(yol, once.size), args.yaricap, args.epsilon)
        hedef = args.sonuclar / f"{args.etiket}_{arac}"
        hedef.mkdir(exist_ok=True)
        uygula(ozgunler[gorsel], oran).save(hedef / yol.name)
        print(f"{hedef / yol.name}  en büyük ışık değişimi {np.abs(oran).max():.2f} EV")


if __name__ == "__main__":
    main()
