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
python scripts\kucult.py   # bir kez: data\levha -> data\levha640 (640 px kopya, ~20 s)
yolo train model=models/yolo11n.pt data=data/levha640/data_temiz.yaml imgsz=640 epochs=150 time=1.6 patience=30 fliplr=0.0 batch=16 workers=3 name=v1
```
- `levha640`: Görüntüler bir kez 640 px'e küçültülüyor; Ultralytics da eğitimde aynı küçültmeyi yapıyor, yani sonuç aynı. Neden gerekli: darboğaz 1080p JPEG'lerin her epoch'ta yeniden açılması. `cache=ram` bunu çözüyor ama **Windows'ta önbellek her işçi sürece ayrı ayrı kopyalanıyor** (3,2 GB × işçi sayısı), bu yüzden 16 GB RAM'e sığmıyor. Küçük JPEG'ler önbelleksiz de hızlı okunuyor.
- `data_temiz.yaml`: erken durdurma ve en iyi modelin seçimi sızıntısız valid ile yapılır (bkz. `docs/veri_denetimi.md`).
- `workers=3`: Windows'ta her işçi ayrı bir Python süreci ve süreç başına ~0,6 GB RAM tutuyor. Doğrulama aşaması işçi sayısını ikiye katlıyor. Ölçüm (29 Ekim): `workers=6` → 18 süreç, 11,7 GB, boş RAM 0,7 GB'a düştü. `workers=3` → 11 süreç, ~6,6 GB.
- `time=1.6`: eğitimi 1,6 saatle sınırlar; Ultralytics epoch sayısını ve öğrenme hızı planını bu süreye göre ayarlar.
- `batch=16`: 4 GB VRAM'e rahat sığıyor (batch 11'de 1,6 GB kullanılmıştı).
- Çıktılar `ml\runs\detect\<name>\` altına yazılır. `project=` parametresi **verilmemeli**, yoksa klasörler iç içe geçer.
- Eğitim sırasında laptop prizde ve Armoury Crate'te Turbo/Performans modunda olmalı.

**Yarıda kalan eğitime devam** (her epoch sonunda `last.pt` kaydedilir; bilgisayar kapatılınca en fazla yarım epoch kaybolur):
```powershell
yolo train resume model=runs/detect/v1/weights/last.pt
```
Ayarlar (`workers`, `batch` vb.) kayıttan otomatik alınır.

⚠️ **Devam ederken `time=` kullanma.** Ultralytics `time` modunda toplam epoch sayısını "süre ÷ devamdan beri ölçülen ortalama epoch süresi" diye hesaplıyor ve daha önce bitmiş epoch'ları saymıyor. 28 Ekim'de 47. epoch'tan `time=1.1` ile devam edilince ilk epoch (açılış dahil 102 s) yüzünden hedef 39 çıktı ve eğitim hemen durdu; öğrenme hızının düşürüldüğü son aşama hiç çalışmadı. Kısa ve öngörülebilir bir bitiş için sabit `epochs` ile ince ayar eğitimi yapılır:
```powershell
yolo train model=runs/detect/v1/weights/best.pt data=data/levha640/data_temiz.yaml imgsz=640 epochs=20 optimizer=AdamW lr0=0.0004 warmup_epochs=1 close_mosaic=10 fliplr=0.0 batch=16 workers=3 name=v2
```

**Test sonuçları (eğitimden sonra, iki test setinde):**
```powershell
yolo val model=runs/detect/v1/weights/best.pt data=data/levha640/data.yaml split=test        # orijinal test (Roboflow ile kıyas)
yolo val model=runs/detect/v1/weights/best.pt data=data/levha640/data_temiz.yaml split=test  # temiz test (gerçek başarı)
```

**Telefon için `.tflite` dışa aktarma:**
```powershell
python scripts\export_tflite.py runs/detect/v2/weights/best.pt
# -> runs/detect/v2/weights/best_tflite/best_float32.tflite ve best_float16.tflite
```
⚠️ `yolo export ... format=saved_model` ile çıkan `.tflite` dosyalarını **kullanma**. Ultralytics 8.4.191'de bu yol kutu koordinatlarını piksel (0–640) olarak veriyor, ama `.tflite` okuyucuları (Ultralytics ve Flutter eklentisi) 0–1 arası normalize koordinat bekliyor. Sonuç mAP 0 olur (28 Ekim'de yaşandı). Betik ONNX çıkışına "xywh ÷ 640" ekleyip yeniden çeviriyor ve sınıf isimlerini (`metadata.json`) dosyaya gömüyor. INT8 varyantı betikte henüz yok; gerekirse (Hafta 1 hız ölçümüne göre) eklenecek.

**`.tflite` modelini Windows'ta doğrulama** (`.pt` ile aynı puanı almalı):
```powershell
yolo val model=runs/detect/v2/weights/best_tflite/best_float16.tflite data=data/levha640/data_temiz.yaml split=test
```

**Windows betiklerinde** (`.py`) ana kod `if __name__ == "__main__":` içinde olmalı. Aksi hâlde DataLoader işçileri betiği baştan çalıştırır ve süreç kilitlenir (28 Ekim'de yaşandı).

**Windows uygulaması için ONNX dışa aktarma (Hafta 6):**
```powershell
yolo export model=runs/detect/v2/weights/best.pt format=onnx imgsz=640
```
(ONNX çıkışı piksel koordinatlıdır; Windows uygulamasında Ultralytics'in son işlemesi bu şekilde bekler.)

**Mobil uygulama (`mobile\` klasöründe):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\mobile
# yeni model eğitildiyse:
Copy-Item ..\ml\runs\detect\v2\weights\best_tflite\best_float16.tflite assets\models\levha.tflite
.\tool\sesleri_uret.ps1           # 20 uyarı sesini Türkçe "Tolga" sesiyle üretir (cümleler lib\alerts.dart'tan)
flutter test                      # uyarı mantığı testleri
flutter build apk --release       # build\app\outputs\flutter-apk\app-release.apk
```

**Telefonda çalıştırma:**
```powershell
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
