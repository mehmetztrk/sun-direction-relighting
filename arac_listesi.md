# Relight araçları: doğrulanmış liste (6 Kasım 2026)

Space durumları Hugging Face API'sinden, fiyatlar resmî sayfalardan alındı.
Space'lerde "çalışıyor" yalnızca sunucu durumunu gösterir, görsel yükleyip denenmedi.

## Denenecekler

| Sıra | Araç | Işık kontrolü | Space | Lisans | Not |
|---|---|---|---|---|---|
| 1 | Sun-Direction LoRA (FLUX.2 Klein) | Işık topu + bulutlu ara görsel | [linoyts](https://huggingface.co/spaces/linoyts/sun-direction-flux2-klein): çalışıyor | LoRA Apache-2.0; 9B taban model ticari değil, 4B Apache-2.0 | Güneş için özel eğitilmiş. Yazarı iç mekân için garanti vermiyor. |
| 2 | Qwen-Edit + çok açılı ışık | Yön metni + parlaklık haritası | [3D Lighting Control](https://huggingface.co/spaces/prithivMLmods/Qwen-Image-Edit-3D-Lighting-Control): çalışıyor | Apache-2.0 | İç mekânda da denenebilir. Yazarı bazı açıların kontrolsüz olduğunu söylüyor. |
| 3 | FLUX.1 Kontext [dev] | Yalnızca metin | [BFL](https://huggingface.co/spaces/black-forest-labs/FLUX.1-Kontext-Dev): çalışıyor | Ticari değil. Pro API kullanılabilir. | Genel düzenleme modeli, karşılaştırma için temel çizgi. |

## Yedekler ve diğerleri

| Araç | Durum | Tek satır |
|---|---|---|
| [IC-Light](https://huggingface.co/spaces/lllyasviel/IC-Light) | Space çalışıyor | Eski (SD1.5) relight modeli. Lisans bilgisi çelişkili: GitHub Apache-2.0, HF OpenRAIL. "Başarısızlık" örneği olabilir. |
| [Qwen Light Migration](https://huggingface.co/spaces/multimodalart/Qwen-Image-Light-Migration) | Space çalışıyor | Referans görselin ışığını aktarır. Apache-2.0. Örneğin bir gün batımı fotoğrafı referans verilir. |
| [Qwen Relight LoRA](https://huggingface.co/dx8152/Qwen-Image-Edit-2509-Relight) | Özel Space'leri kapalı veya hatalı | Metinle ışık tarifi. [LoRAs-Fast Space](https://huggingface.co/spaces/prithivMLmods/Qwen-Image-Edit-2509-LoRAs-Fast) çalışıyor, ama bu LoRA'yı içerip içermediğini görmedim. |
| [LTX-2.3 Relight](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Relight) | Space çalışıyor | Dış mekân videosu için, güneş yönü ve sertliği seçilebiliyor. Topluluk lisansını okumadım. |
| Nano Banana ailesi (Gemini) | API ücretli | Prompt ile düzenleme. Ücretsiz API kotası görünmüyor. |
| fal relighting | $0.04/görsel | Hangi modeli kullandığı doğrulanmadı. |
| Magnific, Krea, Clipdrop | Abonelik | Fiyatlar yalnızca üçüncü taraf sitelerden geldi ve çelişiyor. Mimari kullanım kanıtı bulunamadı. |

## Elenenler

- **LBM Relighting:** Ön plandaki nesneyi arka plana uydurur, tüm sahneyi yeniden aydınlatmaz. Lisansı CC BY-NC.
- **UniRelight (NVIDIA):** Yalnızca video, ticari olmayan lisans, Space yok.
- **HELIOS, OutCast ve benzeri makaleler:** Güneş açısı için ilginç, ama hazır model ağırlığı doğrulanmadı. Raporda "takip edilecek" diye geçebilir.

## Fiyatlar

| Yol | Fiyat | Kaynak |
|---|---|---|
| Nano Banana 2.1 | $0.0336 (1K), $0.0504 (2K), $0.113 (4K) | Google* |
| Nano Banana Pro | $0.134 (1K/2K), $0.24 (4K) | Google* |
| FLUX Kontext Pro | $0.04/görsel | fal |
| Qwen Edit 2511 | $0.03/MP (1536×1024 için yaklaşık $0.047) | fal |
| Qwen Edit 2511 | $0.02/istek | RunPod |
| FLUX Kontext dev | $0.025/istek | RunPod |
| RTX 4090 kiralama | $0.34/s (community), $0.89/s (secure), $1.34/s (serverless) | RunPod, 4 Kasım |
| L40S kiralama | $0.79–1.09/s, serverless $1.75/s | RunPod |

\* Google sayfası kısmen özet olarak okundu. Rapora yazmadan önce sayfadan kontrol et.
Bulunamadı: BFL doğrudan fiyatları (sayfa boş geldi), OpenAI fiyatları (erişim reddedildi).

## Ücretsiz deneme sınırı

- ZeroGPU günlük kota: girişsiz 2 dakika, ücretsiz hesapla 5 dakika.
- Kota, ilk kullanımdan tam 24 saat sonra yenilenir.
- Google, fal ve Replicate sayfalarında görsel düzenleme için ücretsiz kredi görünmüyor.
- Görev için 3 görsel × 3 araç = en az 9 deneme, tekrarlar hariç. Bu yüzden denemeleri günlere yay.

## Şirket bağlamı (myarchitectai.com)

- Ana vaat: "keeping the geometry and materials unchanged".
- "Lighting control tools" özelliği "coming soon" listesinde. Bu görev büyük olasılıkla o özelliğin ön çalışması (bu benim çıkarımım).
- Kendi API'leri: düzenleme $0.03/çağrı, ortalama 13.4 sn, 4K indirme. Bunlar şirketin kendi verdiği rakamlar.
- Hangi modeli kullandıklarını yazmıyorlar.
- Üretim önerini bu çıtayla karşılaştır: görsel başına $0.03 civarı, yaklaşık 15 sn, 4K çıktı.

## Kaba üretim hesabı

Süreler varsayım, kendi ölçümlerinle değiştir.

- 7/24 açık RTX 4090: $0.89 × 730 saat ≈ $650/ay.
- $0.02'lik hazır uç noktayla başa baş: ayda yaklaşık 32.500 görsel.
- $0.04'lük API ile başa baş: ayda yaklaşık 16.000 görsel.
- Serverless RTX 4090: görsel 20 sn sürerse yaklaşık $0.0074 (soğuk başlatma hariç).

## Kaynaklar

- https://huggingface.co/eric-venti-seeds/Sun-Direction-Lora-Flux2Klein9B
- https://huggingface.co/dx8152/Qwen-Edit-2509-Multi-Angle-Lighting
- https://huggingface.co/dx8152/Qwen-Edit-2509-Light-Migration
- https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
- https://huggingface.co/jasperai/LBM_relighting
- https://huggingface.co/nvidia/UniRelight
- https://github.com/lllyasviel/IC-Light
- https://github.com/houyuanchen111/Awesome-Relight
- https://docs.ltx.io/open-source-model/feature-guides/editing-effects/relight
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://aistudio.google.com/docs/pricing
- https://fal.ai/pricing
- https://fal.ai/models/fal-ai/flux-pro/kontext
- https://fal.ai/models/fal-ai/qwen-image-edit-2511
- https://fal.ai/models/fal-ai/image-apps-v2/relighting
- https://replicate.com/pricing
- https://www.runpod.io/gpu-cloud/pricing
- https://www.myarchitectai.com/
- https://www.myarchitectai.com/blog/nano-banana-api-pricing
