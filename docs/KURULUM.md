# Kurulum Kaydı ve Günlük Komutlar

> Kurulum tarihi: 28 Ekim 2026 · Bilgisayar: ASUS TUF F15 (i7-12700H, 16 GB RAM, RTX 3050 Laptop 4 GB), Windows 11

## Neler kurulu?

| Araç | Sürüm | Konum | Not |
|---|---|---|---|
| NVIDIA sürücüsü | 566.07 (CUDA ≤ 12.7) | — | Önceden vardı |
| Python | 3.12.10 | `%LOCALAPPDATA%\Programs\Python\Python312` | Yeni. Eski Python 3.14'e dokunulmadı (onun torch'u CPU sürümü, GPU kullanamıyor). |
| Eğitim ortamı | torch 2.14.1+cu126, ultralytics 8.4.191, albumentations 2.0.8, onnxruntime-gpu 1.31.1 | `ml\.venv` | Liste: `ml/requirements.txt` |
| WSL2 Ubuntu | 24.04 (Python 3.12.3) | `wsl -d Ubuntu-24.04` | Yalnızca `.tflite` dışa aktarma için |
| Dışa aktarma ortamı | torch 2.14.1, ultralytics 8.4.191, litert-torch 0.10.0 | WSL: `/root/venvs/export` | torch'u **güncelleme**: litert-torch `torch<2.15` istiyor |
| Flutter / Dart | 3.47.8 / 3.13.7 | `C:\src\flutter` | Önceden vardı, güncellendi |
| ultralytics_yolo (Flutter eklentisi) | 0.7.1 | `mobile/pubspec.yaml` | |
| Android SDK | cmdline-tools 23.0, platform-tools 37.0.1, platform 36, build-tools 36.1.0, NDK 28.2.13676358, CMake 3.22.1 | `%LOCALAPPDATA%\Android\Sdk` | `ANDROID_HOME` ve `platform-tools` PATH'e eklendi |
| JDK | Temurin 21.0.11 | `C:\Program Files\Eclipse Adoptium` | Önceden vardı |
| Git | 2.54 | — | Önceden vardı |
| VS Code eklentileri | Flutter/Dart, Python | — | Yeni |

Ultralytics ayarları (iki ortamda da): `sync=False` (anonim veri gönderimi kapalı). Windows'ta ayrıca `datasets_dir=ml\data`, `runs_dir=ml\runs`, `weights_dir=ml\models`.

## Günlük komutlar

**Eğitim (Windows, `ml\` klasöründe):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\ml
.\.venv\Scripts\activate
yolo train model=models/yolo11n.pt data=data/levha/data.yaml imgsz=640 epochs=150 patience=30 fliplr=0.0 batch=-1 workers=4 name=v1
```
Çıktılar `ml\runs\detect\<name>\` altına yazılır. `project=` parametresi **verilmemeli**, yoksa klasörler iç içe geçer.

**`.tflite` dışa aktarma (Windows'tan çalıştırılır, iş WSL'de yapılır):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\ml
.\scripts\export_tflite.ps1 -Model runs\detect\v1\weights\best.pt -ImgSz 640
.\scripts\export_tflite.ps1 -Model runs\detect\v1\weights\best.pt -Quantize w8a32
```

**Telefonda çalıştırma (`mobile\` klasöründe):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\mobile
adb devices          # telefon "device" olarak görünmeli
flutter run          # geliştirme
flutter run --release  # FPS ölçümü her zaman release modda yapılır
```

## Kurulumda yaşanan sorunlar ve çözümleri

1. **NDK kurulamadı (`Package ndk not found`).** Yeni Android cmdline-tools paket adlarını `ndk/<sürüm>` biçiminde bekliyor, Flutter ise `ndk;<sürüm>` gönderiyor. Çözüm: NDK elle kuruldu. Flutter ileride başka bir NDK sürümü isterse:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin\sdkmanager.bat" --install "ndk/<istenen-sürüm>"
   ```
2. **İlk `.tflite` dışa aktarmasında `duplicate registrations` hatası.** Ultralytics eksik `litert-torch` paketini çalışma sırasında kurarken torch'u da değiştirdi ve süreç çöktü. Komut ikinci kez çalıştırılınca sorun çıkmadı. Bu hatayı yeniden görürsen komutu bir kez daha çalıştır.
3. **PowerShell'in `Invoke-WebRequest` komutu büyük indirmelerde çok yavaş.** Bunun yerine `curl.exe` kullan.
4. `flutter doctor` çıktısındaki **Visual Studio uyarısı önemsiz**: o araç yalnızca Windows masaüstü uygulaması derlemek için gerekiyor.
