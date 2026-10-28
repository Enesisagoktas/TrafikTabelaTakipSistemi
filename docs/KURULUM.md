# Kurulum Kaydı ve Günlük Komutlar

> Kurulum tarihi: 28 Ekim 2026 · Bilgisayar: ASUS TUF F15 (i7-12700H, 16 GB RAM, RTX 3050 Laptop 4 GB), Windows 11
> Her şey bu Windows bilgisayarda çalışır; Linux/WSL kullanılmaz.

## Neler kurulu?

| Araç | Sürüm | Konum | Not |
|---|---|---|---|
| NVIDIA sürücüsü | 566.07 (CUDA ≤ 12.7) | — | Önceden vardı |
| Python | 3.12.10 | `%LOCALAPPDATA%\Programs\Python\Python312` | Yeni. Eski Python 3.14'e dokunulmadı (onun torch'u CPU sürümü, GPU kullanamıyor). |
| Eğitim + dışa aktarma ortamı | torch 2.14.1+cu126, ultralytics 8.4.191, tensorflow 2.19.0, onnx2tf 1.28.8, ai-edge-litert 2.3.0 | `ml\.venv` | Tam liste: `ml/requirements.txt` |
| Flutter / Dart | 3.47.8 / 3.13.7 | `C:\src\flutter` | Önceden vardı, güncellendi |
| ultralytics_yolo (Flutter eklentisi) | 0.7.1 | `mobile/pubspec.yaml` | |
| Android SDK | cmdline-tools 23.0, platform-tools 37.0.1, platform 36, build-tools 36.1.0, NDK 28.2.13676358, CMake 3.22.1 | `%LOCALAPPDATA%\Android\Sdk` | `ANDROID_HOME` ve `platform-tools` PATH'e eklendi |
| JDK | Temurin 21.0.11 | `C:\Program Files\Eclipse Adoptium` | Önceden vardı |
| Git | 2.54 | — | Önceden vardı |
| VS Code eklentileri | Flutter/Dart, Python | — | Yeni |

Ultralytics ayarları: `sync=False` (anonim veri gönderimi kapalı), `datasets_dir=ml\data`, `runs_dir=ml\runs`, `weights_dir=ml\models`.

Veri seti: `ml\data\levha` (Roboflow sürüm 17, augmentasyonsuz, 4.422 / 553 / 552). Orijinal zip `ml\data\raw\` altında duruyor.

## Günlük komutlar

Bütün ML komutları `ml\` klasöründe, ortam etkinken çalıştırılır:
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\ml
.\.venv\Scripts\activate
```

**Veri denetimi:**
```powershell
python scripts\veri_denetimi.py      # rapor: docs\veri_denetimi.md
```

**Eğitim:**
```powershell
yolo train model=models/yolo11n.pt data=data/levha/data.yaml imgsz=640 epochs=150 patience=30 fliplr=0.0 batch=-1 workers=4 name=v1
```
Çıktılar `ml\runs\detect\<name>\` altına yazılır. `project=` parametresi **verilmemeli**, yoksa klasörler iç içe geçer.

**Telefon için `.tflite` dışa aktarma:**
```powershell
yolo export model=runs/detect/v1/weights/best.pt format=saved_model imgsz=640
# -> runs/detect/v1/weights/best_saved_model/best_float32.tflite ve best_float16.tflite
yolo export model=runs/detect/v1/weights/best.pt format=saved_model imgsz=640 quantize=8 data=data/levha/data.yaml
# -> ek olarak INT8 varyantları (kalibrasyon için veri setini kullanır)
```
Sınıf isimleri `.tflite` dosyasının içine gömülür (`metadata.json`), yani eklenti isimleri dosyadan okur.

**`.tflite` modelini Windows'ta doğrulama:**
```powershell
yolo val model=runs/detect/v1/weights/best_saved_model/best_float32.tflite data=data/levha/data.yaml split=test
```

**Windows uygulaması için ONNX dışa aktarma (Hafta 6):**
```powershell
yolo export model=runs/detect/v1/weights/best.pt format=onnx imgsz=640
```

**Telefonda çalıştırma (`mobile\` klasöründe):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\mobile
adb devices            # telefon "device" olarak görünmeli
flutter run            # geliştirme
flutter run --release  # FPS ölçümü her zaman release modda yapılır
```

## Kurulumda yaşanan sorunlar ve çözümleri

1. **NDK kurulamadı (`Package ndk not found`).** Yeni Android cmdline-tools paket adlarını `ndk/<sürüm>` biçiminde bekliyor, Flutter ise `ndk;<sürüm>` gönderiyor. Çözüm: NDK elle kuruldu. Flutter ileride başka bir NDK sürümü isterse:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin\sdkmanager.bat" --install "ndk/<istenen-sürüm>"
   ```
2. **Ultralytics'in yeni `litert` formatı Windows'ta çalışmıyor.** Bunun yerine `format=saved_model` kullanılıyor: ONNX → onnx2tf → `.tflite`. TensorFlow ve onnx2tf önceden ve sabit sürümle kuruldu. Ultralytics eksik bir paketi dışa aktarma *sırasında* kurmaya kalkarsa süreç çökebilir; böyle olursa komutu bir kez daha çalıştır.
3. **TensorFlow'un bilgi mesajları** (`oneDNN custom operations`, `NativeCommandError`) hata değil. Gizlemek için: `$env:TF_CPP_MIN_LOG_LEVEL = "3"`.
4. **PowerShell'in `Invoke-WebRequest` komutu büyük indirmelerde çok yavaş.** Bunun yerine `curl.exe` kullan.
5. **PowerShell'den `python -c "..."` ile çalıştırılan kodda tırnaklar kayboluyor.** Kodu bir `.py` dosyasına yazıp öyle çalıştır.
6. `flutter doctor` çıktısındaki **Visual Studio uyarısı önemsiz**: o araç yalnızca Flutter ile Windows masaüstü uygulaması derlemek için gerekiyor. Windows uygulamamız Python ile yazılacak.
