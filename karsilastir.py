"""Relight sonuçlarını özgün görsellerle karşılaştırır.

Klasör düzeni:
    gorseller/01_dis_cephe_villa.jpg
    sonuclar/<arac>/01_dis_cephe_villa__<deneme>.png

Çalıştırma:
    python karsilastir.py

Çıktılar (sonuclar/_rapor):
    <gorsel>_karsilastirma.jpg   önce, sonra ve fark haritaları
    <gorsel>_bolgeler.jpg        gorseller/bolgeler.json içindeki objelerin kırpıntıları
    bolgeler.csv                 obje başına renk farkı, kayma ve yapı
    metrikler.csv                ölçülen değerler, her çalıştırmada yenilenir
    puan.csv                     elle doldurulur, eski satırlar korunur

Gerekenler: numpy, pillow
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CALISMA_BOYUTU = 1024  # metrikler bu uzun kenarda hesaplanır
NCC_YARICAP = 7  # yerel yapı penceresi: 15x15 piksel
DOKU_ESIGI = 0.02  # bunun altındaki düz alanlar (gökyüzü, boş duvar) sayılmaz
KENAR_TOLERANS = 2  # kenarların eşleşmesi için izin verilen piksel
ORAN_ESIGI = 1.0  # en-boy oranı bu yüzdeden fazla değişirse uyarı verilir
OLCEK_ARALIGI = np.arange(0.80, 1.205, 0.01)  # kadraj değişimi için denenen ölçekler

UZANTILAR = {".png", ".jpg", ".jpeg", ".webp"}
METRIK_ALANLARI = ["arac", "gorsel", "deneme", "yapi", "yapi_hizali", "olcek", "kenar_f1",
                   "isik_degisimi_ev", "pozlama_ev", "kayma_px", "oran_farki_yuzde", "uyari"]
PUAN_ALANLARI = ["arac", "gorsel", "deneme", "sure_sn", "maliyet_usd", "isik_1_5",
                 "geometri_1_5", "malzeme_1_5", "artefakt_1_5", "not"]


def yukle(yol, boyut=None):
    goruntu = Image.open(yol).convert("RGB")
    if boyut is None:
        olcek = CALISMA_BOYUTU / max(goruntu.size)
        boyut = (round(goruntu.width * olcek), round(goruntu.height * olcek))
    return goruntu.resize(boyut, Image.LANCZOS)


def parlaklik(goruntu):
    return np.asarray(goruntu, dtype=np.float64).dot([0.2126, 0.7152, 0.0722]) / 255


def kutu(a, r):
    """Kenarlardan taşırılmış (2r+1)x(2r+1) kutu ortalaması."""
    k = 2 * r + 1
    d = np.pad(a, r + 1, mode="edge").cumsum(0).cumsum(1)
    t = d[k:, k:] - d[:-k, k:] - d[k:, :-k] + d[:-k, :-k]
    return t[:a.shape[0], :a.shape[1]] / (k * k)


def bulanik(a, r):
    for _ in range(3):
        a = kutu(a, r)
    return a


def yerel_ncc(a, b, r=NCC_YARICAP):
    """Yerel korelasyon: pencere içi parlaklık ve kontrast değişiminden etkilenmez."""
    ort_a, ort_b = kutu(a, r), kutu(b, r)
    var_a = np.maximum(kutu(a * a, r) - ort_a ** 2, 0)
    var_b = np.maximum(kutu(b * b, r) - ort_b ** 2, 0)
    kov = kutu(a * b, r) - ort_a * ort_b
    payda = np.sqrt(var_a * var_b)
    ncc = np.divide(kov, payda, out=np.zeros_like(kov), where=payda > 1e-8)
    return np.clip(ncc, -1, 1), np.sqrt(var_a)


def kenarlar(a):
    a = kutu(a, 1)
    gy, gx = np.gradient(a)
    g = np.hypot(gx, gy)
    return g > np.percentile(g, 90)


def kenar_f1(a, b, r=KENAR_TOLERANS):
    ka, kb = kenarlar(a), kenarlar(b)
    yakin_a, yakin_b = kutu(ka.astype(float), r) > 0, kutu(kb.astype(float), r) > 0
    kesinlik = (kb & yakin_a).sum() / max(kb.sum(), 1)
    duyarlilik = (ka & yakin_b).sum() / max(ka.sum(), 1)
    return 2 * kesinlik * duyarlilik / max(kesinlik + duyarlilik, 1e-8)


def oteleme(a, b):
    """Faz korelasyonuyla kenar haritaları arasındaki ötelemeyi bulur."""
    gy_a, gx_a = np.gradient(kutu(a, 1))
    gy_b, gx_b = np.gradient(kutu(b, 1))
    fa = np.fft.rfft2(np.hypot(gx_a, gy_a))
    fb = np.fft.rfft2(np.hypot(gx_b, gy_b))
    kor = fa * np.conj(fb)
    tepe = np.fft.irfft2(kor / np.maximum(np.abs(kor), 1e-8), s=a.shape)
    dy, dx = np.unravel_index(tepe.argmax(), tepe.shape)
    dy = dy - a.shape[0] if dy > a.shape[0] / 2 else dy
    dx = dx - a.shape[1] if dx > a.shape[1] / 2 else dx
    return int(dx), int(dy)


def kayma(a, b):
    return float(np.hypot(*oteleme(a, b)))


def hizali_yapi(once, sonra):
    """Model kadrajı değiştirdiyse en iyi ölçek ve ötelemeyi arar, yapıyı öyle ölçer."""
    a = parlaklik(once)
    g, y = once.size
    _, doku = yerel_ncc(a, a)
    maske = doku > DOKU_ESIGI
    en_iyi, hiza = -1.0, (1.0, 0, 0)
    for olcek in OLCEK_ARALIGI:
        b = parlaklik(hizala(sonra, olcek, 0, 0))
        dx, dy = oteleme(a, b)
        puan = yerel_ncc(a, np.roll(b, (dy, dx), (0, 1)))[0][maske].mean()
        if puan > en_iyi:
            en_iyi, hiza = puan, (float(olcek), dx, dy)
    return float(en_iyi), hiza


def hizala(sonra, olcek, dx, dy):
    g, y = sonra.size
    s = 1 / olcek
    donusum = (s, 0, g / 2 * (1 - s) - s * dx, 0, s, y / 2 * (1 - s) - s * dy)
    return sonra.transform((g, y), Image.AFFINE, donusum, Image.BILINEAR)


def lab_ab(goruntu):
    """CIELAB a ve b kanalları. Parlaklık (L) ışıkla değiştiği için renk farkına katılmaz."""
    rgb = np.asarray(goruntu, dtype=np.float64) / 255
    rgb = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = rgb @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    f = xyz / [0.9505, 1.0, 1.089]
    f = np.where(f > 0.008856, np.cbrt(f), 7.787 * f + 16 / 116)
    return np.stack([500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def bolge_olc(once, hizali, bolgeler):
    """Her bölge için renk farkını (ab) ve genel hizalamadan sonra kalan kaymayı ölçer."""
    g, y = once.size
    ab_a, ab_b = lab_ab(once), lab_ab(hizali)
    a, b = parlaklik(once), parlaklik(hizali)
    sonuc = {}
    for ad, (x0, y0, x1, y1) in bolgeler.items():
        dilim = slice(round(y0 * y), round(y1 * y)), slice(round(x0 * g), round(x1 * g))
        renk = float(np.linalg.norm(ab_a[dilim].mean((0, 1)) - ab_b[dilim].mean((0, 1))))
        ncc, doku = yerel_ncc(a[dilim], b[dilim])
        sonuc[ad] = {"renk_farki": renk, "kayma_px": float(np.hypot(*oteleme(a[dilim], b[dilim]))),
                     "yapi": float(ncc[doku > DOKU_ESIGI].mean())}
    return sonuc


def bolge_tablosu(once, satirlar, bolgeler, yol):
    """Her deneme için bölgelerin önce ve sonra kırpıntılarını yan yana koyar."""
    g, y = once.size
    kare, bosluk, baslik = 150, 6, 22
    genislik = (kare * 2 + bosluk * 2) * len(bolgeler)
    tuval = Image.new("RGB", (genislik, (kare + baslik * 2) * len(satirlar)), "white")
    ciz = ImageDraw.Draw(tuval)
    yt = yazi_tipi(13)
    for i, (ad, hizali, olcum) in enumerate(satirlar):
        ust = i * (kare + baslik * 2)
        ciz.text((3, ust + 3), ad, fill="black", font=yt)
        for j, (bolge, (x0, y0, x1, y1)) in enumerate(bolgeler.items()):
            sol = j * (kare * 2 + bosluk * 2)
            kutu_px = (round(x0 * g), round(y0 * y), round(x1 * g), round(y1 * y))
            ciz.text((sol + 3, ust + baslik + 3),
                     f"{bolge}: renk {olcum[bolge]['renk_farki']:.0f}, kayma {olcum[bolge]['kayma_px']:.0f}",
                     fill="#555555", font=yt)
            for k, kaynak in enumerate((once, hizali)):
                kirpinti = kaynak.crop(kutu_px)
                kirpinti.thumbnail((kare, kare), Image.LANCZOS)
                tuval.paste(kirpinti, (sol + k * kare, ust + baslik * 2))
    tuval.save(yol, quality=90)


def isik_haritasi(a, b):
    """Düşük frekanslı parlaklık farkı (EV). Sonuç, genel pozlama ve yerel değişim olarak ayrılır."""
    r = max(a.shape) // 40
    fark = bulanik(np.log2(b + 0.02), r) - bulanik(np.log2(a + 0.02), r)
    return fark - fark.mean(), float(fark.mean())


def olc(once, sonra, ham_boyut):
    a, b = parlaklik(once), parlaklik(sonra)
    ncc, doku = yerel_ncc(a, b)
    maske = doku > DOKU_ESIGI
    isik, pozlama = isik_haritasi(a, b)
    oran = abs(ham_boyut[0] / ham_boyut[1] / (once.width / once.height) - 1) * 100
    yapi_hizali, hiza = hizali_yapi(once, sonra)
    metrik = {
        "yapi": ncc[maske].mean(),
        "yapi_hizali": yapi_hizali,
        "olcek": hiza[0],
        "kenar_f1": kenar_f1(a, b),
        "isik_degisimi_ev": isik.std(),
        "pozlama_ev": pozlama,
        "kayma_px": kayma(a, b),
        "oran_farki_yuzde": oran,
        "uyari": "en-boy orani degisti" if oran > ORAN_ESIGI else "",
    }
    yapi_farki = bulanik(np.where(maske, 1 - ncc, 0), 2)
    return metrik, yapi_farki, isik, hiza


def yapi_paneli(sonra, fark):
    """Yapının değiştiği yerleri griye çevrilmiş sonucun üstünde kırmızı gösterir."""
    gri = parlaklik(sonra)[..., None].repeat(3, 2) * 0.6 + 0.2
    alfa = np.clip(fark / 0.6, 0, 1)[..., None]
    rgb = gri * (1 - alfa) + np.array([0.9, 0.05, 0.05]) * alfa
    return Image.fromarray((rgb * 255).astype(np.uint8))


def isik_paneli(isik):
    """Kırmızı aydınlanan, mavi kararan bölgeleri gösterir (±2 EV tam doygun)."""
    d = np.clip(isik / 2, -1, 1)[..., None]
    rgb = 1 - np.maximum(d, 0) * [0, 1, 1] - np.maximum(-d, 0) * [1, 1, 0]
    return Image.fromarray((rgb * 255).astype(np.uint8))


def yazi_tipi(boyut):
    for ad in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(ad, boyut)
        except OSError:
            pass
    return ImageFont.load_default()


def tablo(once, satirlar, yol):
    """Her deneme için bir satır: önce, sonra, yapı farkı, ışık farkı."""
    gen = 420
    yuk = round(gen * once.height / once.width)
    bosluk, baslik = 6, 26
    tuval = Image.new("RGB", (gen * 4 + bosluk * 3, (yuk + baslik * 2 + bosluk) * len(satirlar)), "white")
    ciz = ImageDraw.Draw(tuval)
    yt = yazi_tipi(14)
    y = 0
    for ad, metrik, paneller in satirlar:
        ozet = (f"{ad}   yapı {metrik['yapi']:.3f}   hizalı {metrik['yapi_hizali']:.3f}   kenar {metrik['kenar_f1']:.3f}   "
                f"ışık {metrik['isik_degisimi_ev']:.2f} EV   kayma {metrik['kayma_px']:.0f} px")
        if metrik["uyari"]:
            ozet += "   UYARI: " + metrik["uyari"]
        ciz.text((4, y + 5), ozet, fill="black", font=yt)
        y += baslik
        etiketler = ["Önce", "Sonra", "Yapı farkı (kırmızı: değişti)", "Işık farkı (kırmızı: aydınlandı, mavi: karardı)"]
        for i, (panel, etiket) in enumerate(zip([once] + paneller, etiketler)):
            x = i * (gen + bosluk)
            ciz.text((x + 4, y + 5), etiket, fill="#555555", font=yt)
            tuval.paste(panel.resize((gen, yuk), Image.LANCZOS), (x, y + baslik))
        y += baslik + yuk + bosluk
    tuval.save(yol, quality=90)


def deneme_bul(sonuclar):
    """(araç, görsel kökü, deneme, yol) dörtlülerini döndürür."""
    bulunan = []
    for klasor in sorted(p for p in sonuclar.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for yol in sorted(klasor.iterdir()):
            if yol.suffix.lower() not in UZANTILAR:
                continue
            if "__" not in yol.stem:
                print(f"Atlandı, ad '<gorsel>__<deneme>' biçiminde değil: {yol}")
                continue
            gorsel, deneme = yol.stem.split("__", 1)
            bulunan.append((klasor.name, gorsel, deneme, yol))
    return bulunan


def puan_guncelle(yol, satirlar):
    eski = []
    if yol.exists():
        with open(yol, encoding="utf-8-sig", newline="") as f:
            eski = list(csv.DictReader(f, delimiter=";"))
    gorulen = {(s["arac"], s["gorsel"], s["deneme"]) for s in eski}
    yeni = [{"arac": a, "gorsel": g, "deneme": d} for a, g, d in satirlar if (a, g, d) not in gorulen]
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.DictWriter(f, PUAN_ALANLARI, delimiter=";", restval="")
        yazici.writeheader()
        yazici.writerows(eski + yeni)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gorseller", type=Path, default=Path("gorseller"))
    ap.add_argument("--sonuclar", type=Path, default=Path("sonuclar"))
    args = ap.parse_args()

    ozgunler = {p.stem: p for p in args.gorseller.iterdir() if p.suffix.lower() in UZANTILAR}
    denemeler = deneme_bul(args.sonuclar)
    if not denemeler:
        print(f"{args.sonuclar} içinde sonuç bulunamadı.")
        return
    rapor = args.sonuclar / "_rapor"
    rapor.mkdir(exist_ok=True)

    bolge_yolu = args.gorseller / "bolgeler.json"
    tum_bolgeler = json.loads(bolge_yolu.read_text(encoding="utf-8")) if bolge_yolu.exists() else {}

    kayitlar, bolge_kayitlari = [], []
    for kok, ozgun in sorted(ozgunler.items()):
        once = yukle(ozgun)
        satirlar, bolge_satirlari = [], []
        bolgeler = tum_bolgeler.get(kok, {})
        for arac, gorsel, deneme, yol in denemeler:
            if gorsel != kok:
                continue
            ham_boyut = Image.open(yol).size
            sonra = yukle(yol, once.size)
            metrik, yapi_farki, isik, hiza = olc(once, sonra, ham_boyut)
            kayitlar.append({"arac": arac, "gorsel": gorsel, "deneme": deneme, **metrik})
            satirlar.append((f"{arac} / {deneme}", metrik,
                             [sonra, yapi_paneli(sonra, yapi_farki), isik_paneli(isik)]))
            if bolgeler:
                hizali = hizala(sonra, *hiza)
                olcum = bolge_olc(once, hizali, bolgeler)
                bolge_satirlari.append((f"{arac} / {deneme}", hizali, olcum))
                bolge_kayitlari += [{"arac": arac, "gorsel": gorsel, "deneme": deneme, "bolge": ad, **d}
                                    for ad, d in olcum.items()]
        if satirlar:
            tablo(once, satirlar, rapor / f"{kok}_karsilastirma.jpg")
        if bolge_satirlari:
            bolge_tablosu(once, bolge_satirlari, bolgeler, rapor / f"{kok}_bolgeler.jpg")

    eslesmeyen = sorted({g for _, g, _, _ in denemeler} - set(ozgunler))
    if eslesmeyen:
        print("Özgün görseli bulunamadı:", ", ".join(eslesmeyen))

    with open(rapor / "metrikler.csv", "w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.DictWriter(f, METRIK_ALANLARI, delimiter=";")
        yazici.writeheader()
        for k in kayitlar:
            yazici.writerow({a: round(d, 3) if isinstance(d, float) else d for a, d in k.items()})
    if bolge_kayitlari:
        with open(rapor / "bolgeler.csv", "w", encoding="utf-8-sig", newline="") as f:
            alanlar = ["arac", "gorsel", "deneme", "bolge", "renk_farki", "kayma_px", "yapi"]
            yazici = csv.DictWriter(f, alanlar, delimiter=";")
            yazici.writeheader()
            for k in bolge_kayitlari:
                yazici.writerow({a: round(d, 2) if isinstance(d, float) else d for a, d in k.items()})
    puan_guncelle(rapor / "puan.csv", [(k["arac"], k["gorsel"], k["deneme"]) for k in kayitlar])

    print(f"{'gorsel / arac / deneme':<58}{'yapi':>7}{'hizali':>8}{'olcek':>7}{'kenar':>7}{'isik':>7}{'kayma':>7}")
    for k in kayitlar:
        ad = f"{k['gorsel'][:2]} / {k['arac']} / {k['deneme']}"
        print(f"{ad:<58}{k['yapi']:>7.3f}{k['yapi_hizali']:>8.3f}{k['olcek']:>7.2f}{k['kenar_f1']:>7.3f}"
              f"{k['isik_degisimi_ev']:>7.2f}{k['kayma_px']:>7.0f}  {k['uyari']}")
    if bolge_kayitlari:
        print(f"\n{'arac / deneme':<48}{'bolge':<16}{'renk':>6}{'kayma':>7}{'yapi':>7}")
        for k in bolge_kayitlari:
            print(f"{k['arac'] + ' / ' + k['deneme']:<48}{k['bolge']:<16}{k['renk_farki']:>6.1f}"
                  f"{k['kayma_px']:>7.0f}{k['yapi']:>7.2f}")
    print(f"\nÇıktılar: {rapor}")


if __name__ == "__main__":
    main()
