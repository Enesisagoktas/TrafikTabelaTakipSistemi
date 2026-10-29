# Hız Ölçümleri

Hafta 1'in kapısı: telefonda imgsz 640 ya da 480'de **≥ 5 FPS** (hedef ≥ 8).
Telefonda ölçüm release APK ile yapılır (`flutter run --release` ya da kablo yoksa APK'yı kendine gönderip kur). Sürüş ekranının sol alt köşesinde FPS, çıkarım süresi (ms), GPU/CPU ve oylama yazar; sağ alttaki düğme sesi açıp kapatır. GPU açma/kapama Ayarlar sekmesinde ("GPU kullan"). Kayıtlar sekmesindeki PERF satırları son 10 saniyenin hızıdır. Her satır için en az 30 saniye bekleyip ortalama değeri yaz.

| Tarih | Cihaz | Model | imgsz | Hızlandırıcı | Çıkarım (ms) | FPS | Not |
|---|---|---|---|---|---|---|---|
| 29.10.2026 | Windows, i7-12700H | `desktop/levha.onnx` (v2) | 640 | CPU (ONNX Runtime) | ~22 | ~33 | 60 test görseli, uçtan uca |
| 29.10.2026 | Windows, i7-12700H | `desktop/levha.onnx` (v5b) | 640 | CPU (ONNX Runtime) | ~23–27 | ~21–30 | 1280 px video, pencereyle. Pencere arkadayken Windows kısıyordu (~3 FPS); `high_qos()` ile düzeldi |
| 29.10.2026 | Windows, RTX 3050 Laptop | `desktop/levha.pt` (v5b) | 640 | GPU (PyTorch, CUDA 12.6) | ~8–9 | ~63 | 1280 px video, pencereyle; kare başına ~16 ms |
| | Redmi Note 8 sınıfı | `levha.tflite` (v5b FP16) | 640 | GPU | | | |
| | Redmi Note 8 sınıfı | `levha.tflite` (v5b FP16) | 640 | CPU | | | |
| | Redmi Note 8 sınıfı | 480 ile dışa aktarılmış | 480 | GPU / CPU | | | yalnızca 640 yetmezse |

Telefonda ayrıca kontrol edilecekler:
- [ ] Model yükleniyor, ekranda "Model hatası" yok.
- [ ] Kutular levhaların üstüne doğru çiziliyor (girdi NHWC, koordinatlar normalize; risk 54 ve 64).
- [ ] Kameranın önünde el sallanınca belirgin bir gecikme yok (risk 30).
- [ ] Uçak modunda uygulama aynen çalışıyor (risk 47).
- [ ] Aynı fotoğraf bilgisayarda ve telefonda aynı levhayı veriyor (risk 24).
