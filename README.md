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

Veri seti: [Traffic-Sign-Recognition-V2-Turkiye](https://universe.roboflow.com/hootbu-vhtnl/traffic-sign-recognition-v2-turkiye), Hootbu, CC BY 4.0.

> Deneysel bir prototiptir; sürücü güvenlik sistemi değildir.
