# Hız Ölçümleri

Hafta 1'in kapısı: telefonda imgsz 640 ya da 480'de **≥ 5 FPS** (hedef ≥ 8).
Telefonda ölçüm her zaman `flutter run --release` ile yapılır. Uygulamanın sağ alt köşesinde FPS, çıkarım süresi (ms) ve GPU/CPU düğmesi var. Her satır için en az 30 saniye bekleyip ortalama değeri yaz.

| Tarih | Cihaz | Model | imgsz | Hızlandırıcı | Çıkarım (ms) | FPS | Not |
|---|---|---|---|---|---|---|---|
| 29.10.2026 | Windows, i7-12700H | `desktop/levha.onnx` (v2) | 640 | CPU (ONNX Runtime) | ~22 | ~33 | 60 test görseli, uçtan uca |
| | Redmi Note 8 sınıfı | `levha.tflite` (v2 FP16) | 640 | GPU | | | |
| | Redmi Note 8 sınıfı | `levha.tflite` (v2 FP16) | 640 | CPU | | | |
| | Redmi Note 8 sınıfı | 480 ile dışa aktarılmış | 480 | GPU / CPU | | | yalnızca 640 yetmezse |

Telefonda ayrıca kontrol edilecekler:
- [ ] Model yükleniyor, ekranda "Model hatası" yok.
- [ ] Kutular levhaların üstüne doğru çiziliyor (girdi NHWC, koordinatlar normalize; risk 54 ve 64).
- [ ] Kameranın önünde el sallanınca belirgin bir gecikme yok (risk 30).
- [ ] Uçak modunda uygulama aynen çalışıyor (risk 47).
- [ ] Aynı fotoğraf bilgisayarda ve telefonda aynı levhayı veriyor (risk 24).
