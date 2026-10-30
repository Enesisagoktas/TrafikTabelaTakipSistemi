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
| Android emülatörü | emulator 37.2.12, sistem görüntüsü `system-images;android-34;google_apis;x86_64`, AVD `levha_test` (Android 14) | `%LOCALAPPDATA%\Android\Sdk\emulator`, `%USERPROFILE%\.android\avd` | Yeni (29 Ekim). Telefon yokken APK denemesi için; çalışırken ~3 GB bellek, eğitim sürerken açma |
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

**Ek veri (29 Ekim): arka plan kırpıntıları ve DFG.** Amaç yanlış uyarıyı azaltmak: modele "bu levha değil" örnekleri göstermek.
```powershell
python scripts\negatif.py          # bizim train görsellerinin levhasız kenarlarından 422 kırpıntı (415'i elle kontrol sonrası kaldı)
# DFG (Slovenya, CC BY-NC-SA 4.0, https://www.vicos.si/resources/dfg/). dfg_hazirla.py şu düzeni bekler (ml\ altında):
#   data\dis\dfg\annot\    <- açılmış JSON'lar: train-difficult.json ve test.json (sitedeki annotation zip'lerinden)
#   data\dis\dfg\parcalar\ <- JPEGImages.tar.bz2'nin baştan 64 MiB'lık parçaları: p000, p001, ... (yalnızca baştan
#                             kesintisiz, tam boyutlu parçalar okunur; indirme yarım kalsa da inen kısım kullanılır)
python scripts\dfg_hazirla.py      # gerçek 6.957 görüntü -> data\dis\dfg\stage (YOLO düzeni, 200 sınıf)
python scripts\ek_veri.py data\dis\dfg\stage dfg scripts\esleme_dfg.json --atla "III-29-30,III-29-40,III-30-30" --arka-plan
# -> data\levha640\ek\dfg ve data_v5.yaml (bizim train + ek\*; val/test bizim temiz setler)
yolo train model=runs/detect/v4/weights/best.pt data=data/levha640/data_v5.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 epochs=100 time=2.5 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v5
# v5, 3 epoch bittikten sonra bellek yetmediği için çöktü (yanında TFLite dışa aktarma çalışıyordu). v5b, v5'in last.pt'sinden
# yeni bir eğitim olarak başlatıldı (resume değil; workers 3 -> 2, süre 2,5 -> 2,2 saat):
yolo train model=runs/detect/v5/weights/last.pt data=data/levha640/data_v5.yaml imgsz=640 batch=16 workers=2 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 epochs=100 time=2.2 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v5b

# v6 (29 Ekim gecesi): 21. sınıf diger_levha, yalnız Türk verisi. DFG eğitimden çıkarıldı (ek\dfg -> data\dis\dfg\ek_dfg_v5),
# Roboflow "trafik levhaları" (trafik-isaretleri-cpsyj/trafik-levhalari-gsqx4, v2, YOLOv11 zip) data\dis\trafik_levhalari altına açıldı:
python scripts\ek_veri.py data\dis\trafik_levhalari trafik_levhalari scripts\esleme_trafik_levhalari.json --diger   # -> data_v6.yaml (21 sınıf)
yolo train model=runs/detect/v5b/weights/best.pt data=data/levha640/data_v6.yaml imgsz=640 batch=16 workers=2 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 epochs=60 patience=20 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v6
# 31. epoch'ta durdurulup 4 işçiyle sürdürüldü (epoch 1,7 -> 1,3 dk; RAM sınırda, sayfa dosyası büyüdü):
yolo train model=runs/detect/v6/weights/last.pt data=data/levha640/data_v6.yaml imgsz=640 batch=16 workers=4 optimizer=AdamW lr0=0.0002 warmup_epochs=0 warmup_bias_lr=0 epochs=29 patience=15 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v6_devam
# Temiz test (test etiketleri 20 sınıflı; diger_levha satırı boş): yolo val model=runs/detect/v6_devam/weights/best.pt data=data/levha640/data_v6.yaml split=test
# Sözde etiket (bizim görsellerde modelin bulduğu diger_levha kutuları): python scripts\sozde_etiket.py runs/detect/v6_devam/weights/best.pt 0.5

# v7 (30 Ekim gecesi, uygulamaya alınmadı): 8 yeni sesli sınıf; eşleme esleme_trafik_levhalari_v7.json, data_v7.yaml (29 sınıf)
python scripts\ek_veri.py data\dis\trafik_levhalari trafik_levhalari scripts\esleme_trafik_levhalari_v7.json --ek-siniflar kasis,durak,demiryolu,refuj_basi,donus_adasi,ileri_saga,ileri_sola,ada_etrafinda --diger
yolo train model=runs/detect/v6_devam/weights/best.pt data=data/levha640/data_v7.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 epochs=150 patience=40 cos_lr=True close_mosaic=15 fliplr=0 mixup=0 cache=False name=v7
# Not: ek\trafik_levhalari v8 için yeniden v6 eşlemesiyle üretildi (21 sınıf).

# v8 (30 Ekim öğle, uygulamada): DFG'nin eşlenmeyen 174 sınıfı diger_levha olarak geri alındı (yalnız "bilinmeyen levha" için;
# sesli 20 sınıf Türk verisinden). train_birlesik.txt 14.503 görsel (Hootbu 4.422 + negatif 415 + trafik_levhalari 2.933 + dfg 6.733).
python scripts\ek_veri.py data\dis\trafik_levhalari trafik_levhalari scripts\esleme_trafik_levhalari.json --diger
python scripts\ek_veri.py data\dis\dfg\stage dfg scripts\esleme_dfg.json --atla "III-29-30,III-29-40,III-30-30" --diger   # -> ek\dfg: 6.733 görsel, 13.572 diger_levha kutusu
yolo train model=runs/detect/v6_devam/weights/best.pt data=data/levha640/data_v6.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0003 warmup_epochs=1 warmup_bias_lr=0 epochs=40 patience=15 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v8
# 31 epoch (erken durdu; epoch ~2,5 dk), en iyi 16. epoch val 0,886/0,725; temiz test .pt 0,887/0,716; 10 video: 30 FPS 32 (28) / 14, ~10 FPS 27 (23) / 10.
# Zincir betiği dersi: PowerShell 5.1 BOM'suz .ps1'i ANSI okur -> betikteki 'ş' regex'i eşleşmedi; betiklerde ASCII kullan.

# v9 (30 Ekim öğleden sonra): 17 yeni sesli sınıf (20 temel + 17 + diger_levha = 38). Yeni sınıflar Türkiye'de aynı tasarımı
# olan levhalar; örnekler DFG (çok yol/hava) + Erzurum seti. Eşlemeler: esleme_dfg_v9.json, esleme_trafik_levhalari_v9.json.
# DFG kodları paftalardan gözle + Slovenya yönetmeliğinden doğrulandı (I-11 kaygan yol, I-19 yolda çalışma; ilk eşlemede karışmıştı).
# Erzurum'a özgü refüj başı / dönüş adası / ileri-sağa / ileri-sola yine diger_levha (tek kaynak, v7'de genellemedi).
set EK=kasis,durak,demiryolu,ada_etrafinda,isikli_isaret,keskin_viraj,devamli_viraj,sollama_yasak,dusen_kaya,hayvan,daralan_yol,dik_egim,speed40,speed60,hiz_sonu,yol_calismasi,kaygan_yol
python scripts\ek_veri.py data\dis\trafik_levhalari trafik_levhalari scripts\esleme_trafik_levhalari_v9.json --diger --ek-siniflar %EK% --yaml data_v9.yaml
python scripts\ek_veri.py data\dis\dfg\stage dfg scripts\esleme_dfg_v9.json --atla "III-29-30,III-29-40,III-30-30" --diger --ek-siniflar %EK% --yaml data_v9.yaml
python scripts\sozde_etiket.py runs/detect/v8/weights/best.pt 0.5 data_v9.yaml   # Hootbu + negatif görsellerde v8'in bulduğu bilinmeyen levhalar (33 görsel, 43 kutu)
yolo train model=runs/detect/v8/weights/best.pt data=data/levha640/data_v9.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 epochs=60 patience=20 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v9
# Video değerlendirmesinde yeni sınıf uyarıları, ±3 sn içindeki inceleyici notu tutuyorsa "yeni sınıf doğru" sayılır (video_degerlendir.py NEW_NOTE).
# Sesler: mobile\tool\sesleri_uret.ps1 (82 wav). Katalog 41 sesli sınıf; refüj/dönüş adası/ileri-sağa/sola sesleri modelde yok, zararsız.
# Sonuç: 47 epoch (erken durdu), en iyi 27. epoch val 0,889/0,728; temiz test .pt 0,884/0,719; 10 video: 30 FPS 31 (27) / 19 (+4 yeni sınıf doğru), ~10 FPS 26 (23) / 10.
# Kapı (>= 31 yakalama, <= 14 yanlış uyarı) tutmadı -> uygulama v8'de kaldı. Ayrıntı docs/video_testi.md.

# v10 hazırlığı (30 Ekim akşam): Türk yol karelerinden sözde etiket + gözle denetim (yeni_kare_denetim.py başlığındaki 3 adım).
# Kareler: data\dis\amasra_sinop\kareler (Wikimedia Commons "Amasra Sinop arası", fatih kaplan, 2019, CC BY 3.0; motosiklet kamerası, 1 kare/sn)
#          ve data\dis\pexels_ek\kareler (Pexels 34626400 / 34625837, Pexels lisansı, 2 kare/sn). Sonuç: 112 + 4 görsel, 144 + 5 kutu -> ek\amasra, ek\pexels_ek.
python scripts\yeni_kare_denetim.py tara runs/detect/v9/weights/best.pt data\dis\amasra_sinop\kareler amasra 0.35
python scripts\yeni_kare_denetim.py tara runs/detect/v9/weights/best.pt data\dis\pexels_ek\kareler pexels_ek 0.35
# pafta_<sinif>_<n>.jpg'lere bak, ret.txt yaz (sinif:no | sinif:* | sinif:no=yeni_sinif), sonra:
python scripts\yeni_kare_denetim.py uygula amasra
python scripts\yeni_kare_denetim.py uygula pexels_ek
python scripts\ek_veri.py data\dis\amasra_sozde amasra scripts\esleme_kimlik_v10.json --diger --ek-siniflar %EK% --yaml data_v10.yaml
python scripts\ek_veri.py data\dis\pexels_ek_sozde pexels_ek scripts\esleme_kimlik_v10.json --diger --ek-siniflar %EK% --yaml data_v10.yaml
yolo train model=runs/detect/v9/weights/best.pt data=data/levha640/data_v10.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0003 warmup_epochs=1 warmup_bias_lr=0 epochs=35 patience=12 close_mosaic=8 fliplr=0 mixup=0 cache=False name=v10
# Sonuç: 15 epoch (erken durdu, en iyi 3.), val 0,887/0,722; temiz test .pt 0,878/0,708; 10 video: 30 FPS 31 (25) / 21 (+8 yeni sınıf doğru), ~10 FPS 27 (24) / 10.
# Kapı tutmadı -> uygulama v8'de kaldı. Ayrıntı docs/video_testi.md.
```
- `--atla` virgüllü listesi PowerShell'de tırnak içinde yazılır, yoksa PowerShell listeyi böler.
- ⚠️ Eğitim sürerken **başka ağır Python işi** (dışa aktarma, ikinci bir eğitim) çalıştırma: Windows'un sanal bellek sınırı (RAM + disk belleği dosyası) aşılıyor ve eğitim `ArrayMemoryError` ile çöküyor (29 Ekim'de v5'te yaşandı). APK derlemesinden sonra kalan Gradle sürecini de kapat (`mobile\android\gradlew --stop`).

**Video testi ve kural taraması** (araç içi videolar `data\videolar\`, gerçek durum `degerlendirme\video_gercek_durum.json`):
```powershell
python scripts\video_kucult.py                     # bir kez: 1280 px MJPG kopyalar -> data\videolar\kucuk\*.avi
# <model_adı> = .onnx dosyasının uzantısız adı; log dosyasının adına girer. yolo export hep best.onnx üretir, önce adlandır:
Copy-Item runs\detect\v5b\weights\best.onnx runs\detect\v5b\weights\v5b.onnx
# her video için (proje kökünde); log videonun yanına (kucuk\) yazılır, betikler data\videolar\ altında arar:
#   ml\.venv\Scripts\python desktop\app.py ml\data\videolar\kucuk\<video>.avi ml\runs\detect\v5b\weights\v5b.onnx --sessiz
#   Move-Item ml\data\videolar\kucuk\*.v5b.log.csv ml\data\videolar\ -Force
python scripts\video_degerlendir.py <model_adı>    # yakalanan / zamanında / kaçan / yanlış uyarı, tek tek
python scripts\esik_tarama.py <model_adı> 3        # kural ayarlarını ~10 FPS'te tarar (3 = her 3. kare; 4-6 = ~7,5-5 FPS)
```

**Test sonuçları (eğitimden sonra, iki test setinde):**
```powershell
yolo val model=runs/detect/v1/weights/best.pt data=data/levha640/data.yaml split=test        # orijinal test (Roboflow ile kıyas)
yolo val model=runs/detect/v1/weights/best.pt data=data/levha640/data_temiz.yaml split=test  # temiz test (gerçek başarı)
```

**Telefon için `.tflite` dışa aktarma:**
```powershell
python scripts\export_tflite.py runs/detect/v5b/weights/best.pt      # uygulamadaki model: v5b (29 Ekim)
# -> runs/detect/v5b/weights/best_tflite/best_float32.tflite ve best_float16.tflite
```
⚠️ `yolo export ... format=saved_model` ile çıkan `.tflite` dosyalarını **kullanma**. Ultralytics 8.4.191'de bu yol kutu koordinatlarını piksel (0–640) olarak veriyor, ama `.tflite` okuyucuları (Ultralytics ve Flutter eklentisi) 0–1 arası normalize koordinat bekliyor. Sonuç mAP 0 olur (28 Ekim'de yaşandı). Betik ONNX çıkışına "xywh ÷ 640" ekleyip yeniden çeviriyor ve sınıf isimlerini (`metadata.json`) dosyaya gömüyor. INT8 varyantı betikte henüz yok; gerekirse (Hafta 1 hız ölçümüne göre) eklenecek.

**`.tflite` modelini Windows'ta doğrulama** (`.pt` ile aynı puanı almalı):
```powershell
yolo val model=runs/detect/v5b/weights/best_tflite/best_float16.tflite data=data/levha640/data_temiz.yaml split=test
# v5b: .pt 0,894 / 0,725, FP16 .tflite 0,892 / 0,727 (mAP50 / mAP50-95)
```

**Windows betiklerinde** (`.py`) ana kod `if __name__ == "__main__":` içinde olmalı. Aksi hâlde DataLoader işçileri betiği baştan çalıştırır ve süreç kilitlenir (28 Ekim'de yaşandı).

**Windows uygulaması için model dosyaları (Hafta 6):**
```powershell
yolo export model=runs/detect/v5b/weights/best.pt format=onnx imgsz=640
Copy-Item runs\detect\v5b\weights\best.onnx ..\desktop\levha.onnx
Copy-Item runs\detect\v5b\weights\best.pt ..\desktop\levha.pt     # ekran kartı varsa bu kullanılır
```
(ONNX çıkışı piksel koordinatlıdır; Windows uygulamasında Ultralytics'in son işlemesi bu şekilde bekler.)

**Windows uygulaması (proje kökünde):**
```powershell
ml\.venv\Scripts\python desktop\app.py            # web kamerası; çıkış: q
ml\.venv\Scripts\python desktop\app.py yol.mp4    # video dosyası, kendi hızında oynar -> yol.levha.log.csv (zaman_sn;olay;sinif;guven;yukseklik)
ml\.venv\Scripts\python desktop\app.py yol.mp4 ml\runs\detect\v3\weights\best.onnx   # başka modelle -> yol.best.log.csv
ml\.venv\Scripts\python desktop\app.py --test     # kural öz-testi
```
Video dosyasında saat videonun kendi zamanıdır; kurallar (oylama, tekrar önleme) gerçek sürüşteki gibi işler. Araç içi videolar `ml\data\videolar\` klasörüne konur (git'e girmez).
Ekran kartı varsa `desktop\levha.pt` PyTorch'la GPU'da çalışır (RTX 3050'de pencereyle ~63 FPS); yoksa `desktop\levha.onnx` CPU'da (~21–30 FPS). GPU'da ONNX değil PyTorch kullanılıyor: `onnxruntime-gpu` 1.31 CUDA 13 istiyor, sürücü 566 en fazla 12.7 destekliyor. Windows 11 arkadaki ya da küçültülmüş pencerenin işlemini kısıyordu (CPU'da ~3 FPS); uygulama açılışta kendi kısılmasını kapatıyor (`high_qos()`, sistem ayarı değişmez).

**Mobil uygulama (`mobile\` klasöründe):**
```powershell
cd C:\Projeler\TrafikTabelaTakipSistemi\mobile
# yeni model eğitildiyse:
Copy-Item ..\ml\runs\detect\v5b\weights\best_tflite\best_float16.tflite assets\models\levha.tflite
.\tool\sesleri_uret.ps1           # 20 uyarı sesini Türkçe "Tolga" sesiyle üretir (cümleler lib\alerts.dart'tan)
flutter test                      # uyarı mantığı testleri
flutter build apk --release --split-per-abi   # build\app\outputs\flutter-apk\app-arm64-v8a-release.apk (telefon)
android\gradlew --stop            # derlemeden sonra Gradle sürecini kapat (~3 GB bellek tutuyor)
```
R8 küçültmesi kapalı (`android\app\build.gradle.kts`): açıkken uygulama açılışta çöküyordu (WorkManager veritabanı sınıfı bozuluyordu).

**Emülatörde deneme** (telefon yokken; `levha_test` = Android 14 x86_64):
```powershell
$sdk = "$env:LOCALAPPDATA\Android\Sdk"
& "$sdk\emulator\emulator.exe" -avd levha_test -no-window -no-audio -no-snapshot -memory 1536 -gpu swiftshader_indirect
& "$sdk\platform-tools\adb.exe" install -r build\app\outputs\flutter-apk\app-x86_64-release.apk
& "$sdk\platform-tools\adb.exe" shell am start -n com.trafikasistan.trafik_asistan/.MainActivity
& "$sdk\platform-tools\adb.exe" emu kill
```
Emülatör ~3 GB bellek kullanır; eğitim sürerken açma.

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
