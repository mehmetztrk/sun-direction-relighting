# Sun direction relighting test

Task for MyArchitectAI: change the sun direction in an architectural image without changing its geometry, materials or layout.

The report is in [MyArchitectAI_sun_direction_report.pdf](MyArchitectAI_sun_direction_report.pdf). The longer version is in [RAPOR.md](RAPOR.md).

## Result

No tested tool moved the sun cleanly and kept the scene intact. The closest was the Sun-Direction LoRA on exteriors. All attempts, including failures, are kept in `sonuclar/`.

## Files

| File | Purpose |
|---|---|
| `calistir.py` | Runs an image through a free Hugging Face Space |
| `yerel_sun.py` | Runs the Sun-Direction 4B LoRA on a local GPU |
| `isik_aktar.py` | Applies only a result's light to the original photo |
| `karsilastir.py` | Measures results and builds comparison images |
| `pdf_olustur.py` | Builds the report PDF |
| `arac_listesi.md` | Tool, license and price notes, in Turkish |
| `gorseller/` | Test photos, sources and object regions |
| `sonuclar/` | All results and reports |

## Setup

```bash
pip install -r requirements.txt
hf auth login
```

`yerel_sun.py` also needs PyTorch with CUDA and about 16 GB for the model. It peaked at 10.4 GB of GPU memory on an RTX 4070.

## Run

```bash
python calistir.py sun_direction gorseller/03_dis_cephe_beton_bina.jpg sag --gun 90 --yukseklik 30
python yerel_sun.py
python isik_aktar.py
python karsilastir.py
python pdf_olustur.py
```

Photos are from Unsplash. Credits and links are in `gorseller/KAYNAKLAR.md`.
