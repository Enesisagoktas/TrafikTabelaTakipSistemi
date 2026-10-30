# Trafik Levhası Sürücü Asistanı

İnternet bağlantısı olmadan telefonda çalışan, trafik levhalarını kameradan algılayıp Türkçe sesli uyarı veren öğrenci projesi (YOLO11n + Flutter).

- Yol haritası, kararlar ve risk listesi: [docs/YOL_HARITASI.md](docs/YOL_HARITASI.md)
- Kurulum kaydı ve günlük komutlar: [docs/KURULUM.md](docs/KURULUM.md)

| Klasör | İçerik |
|---|---|
| `ml/` | Veri seti, model eğitimi (GPU) ve `.tflite` / `.onnx` dışa aktarma |
| `mobile/` | Android uygulaması (Flutter + `ultralytics_yolo`) — ilk ürün |
| `desktop/` | Windows uygulaması (Python + ONNX Runtime + web kamerası) — ilk sürüm hazır |
| `docs/` | Belgeler |

Veri setleri (v8 modeli): [Traffic-Sign-Recognition-V2-Turkiye](https://universe.roboflow.com/hootbu-vhtnl/traffic-sign-recognition-v2-turkiye), Hootbu, CC BY 4.0; [trafik levhaları](https://universe.roboflow.com/trafik-isaretleri-cpsyj/trafik-levhalari-gsqx4), "trafik isaretleri" çalışma alanı, CC BY 4.0; [DFG Traffic Sign Dataset](https://www.vicos.si/resources/dfg/), Tabernik & Skočaj, IEEE T-ITS 2019, CC BY-NC-SA 4.0 (yalnızca "bilinmeyen levha" sınıfı için; sesli sınıflar Türk verisinden). Model DFG ile eğitildiği için yalnızca ticari olmayan kullanım içindir.

> Deneysel bir prototiptir; sürücü güvenlik sistemi değildir.
