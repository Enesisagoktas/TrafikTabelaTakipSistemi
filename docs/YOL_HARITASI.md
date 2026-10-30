# Trafik Levhası Sürücü Asistanı — Yol Haritası

> Hazırlanma: 28 Ekim 2026 · Teslim hedefi: ~6 hafta (en geç 9 Aralık 2026)
> Öncelik: Önce **Android uygulaması** yapılır ve ilk sürüm telefonda test edilir. **Windows uygulaması** en son yapılır (Hafta 6).
> Geliştirme, eğitim, dışa aktarma ve testlerin tamamı bu **Windows 11** bilgisayarda yapılır; Linux kullanılmaz.

---

## 0. Verilen kararlar

| Konu | Karar | Neden |
|---|---|---|
| İlk platform | Android (Flutter); en son Windows uygulaması | Test telefonu Android; Windows'tan iOS derlenemez. |
| Model | **YOLO11n** (yedek plan: YOLO26n) | YOLOv8/YOLO11 için topluluk örneği çok fazla; ikisi de aynı çıktı biçimini kullanır (`[1, 4+sınıf, 8400]`). |
| Mobil çıkarım | Resmi **`ultralytics_yolo`** Flutter eklentisi | Kamera, YUV→RGB, LiteRT, GPU→CPU geçişi ve NMS'i yerel (Kotlin) kodda hazır yapar. Bizim yazacağımız kısım: filtreleme, cooldown, ses kuyruğu ve arayüz. |
| Hedef cihaz | Redmi Note 8 seviyesi (Snapdragon 665, Adreno 610, 4 GB RAM) | Alt-orta segment: "bunda çalışıyorsa her yerde çalışır." |
| Veri seti | [Hootbu — Traffic-Sign-Recognition-V2-Turkiye](https://universe.roboflow.com/hootbu-vhtnl/traffic-sign-recognition-v2-turkiye) | 5.527 görsel, 20 sınıf, **CC BY 4.0** (atıf zorunlu). Roboflow'un kendi modeli bu veride mAP50 %85,1 alıyor; bu bizim kıyas çizgimiz. Ancak test setindeki sızıntı nedeniyle bu değer büyük ihtimalle şişkin (bkz. `docs/veri_denetimi.md`). |
| Eğitim | Bu bilgisayar (Windows 11, RTX 3050 Laptop 4 GB) | Yerel GPU, çevrimdışı eğitim. |
| TFLite dışa aktarma | Windows'ta, eğitimle aynı `ml/.venv` içinde: `format=saved_model` (ONNX → onnx2tf → `.tflite`) | Ultralytics'in yeni `litert` formatı Windows'u desteklemiyor. Eski ve yaygın onnx2tf yolu ise Windows'ta çalışıyor ve sınıf isimlerini dosyaya gömüyor (28 Ekim'de doğrulandı). |
| Sesler | Önceden kaydedilmiş Türkçe `.wav` dosyaları + `just_audio` | TTS gecikmesi yok, tamamen çevrimdışı. |

**Proje önerisinden sapmalar (raporda gerekçesiyle yazılmalı):**
- Öneride `camera` + `tflite_flutter` + Isolate yazıyor. Bunların yerine resmi eklenti kullanılıyor. Eklenti çıkarımı yerel bir arka plan thread'inde yapıyor ve Dart tarafına yalnızca küçük bir sonuç listesi geliyor. Önerideki "arayüz donmasın" hedefi bu yolla karşılanıyor.
- Öneride eğitim ortamı olarak Linux Mint yazıyor. Eğitim, dışa aktarma ve testler dahil her şey Windows 11'de yapılıyor.

---

## 1. Mimari (mobil)

```
 [Arka kamera 720p]
        │
        ▼
 ┌──────────────── ultralytics_yolo eklentisi (yerel Kotlin, arka plan thread) ────────────────┐
 │ CameraX (yalnızca en son kare) → YUV→RGB + letterbox → LiteRT (GPU, olmazsa CPU) → NMS      │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
        │  onResult(List<YOLOResult>)   ← Dart'a yalnızca kutu + sınıf + güven gelir (görüntü gelmez)
        ▼
 DetectionFilter    güven eşiği + en küçük kutu boyutu + "son 5 karenin en az 3'ünde görüldü" oylaması
                    (telefon saniyede 8 kareden az işliyorsa "son 3 karenin en az 2'sinde"; alerts.dart votingFor)
        ▼
 CooldownManager    sınıf bazlı: en az 5 sn sessizlik VE levha ≥2 sn görünmez olduktan sonra yeniden kurulur
        ▼
 AlertQueue         3 öncelik seviyesi, en fazla 2 bekleyen, 3 sn'den eski uyarılar atılır, tek oynatıcı
        ▼
 just_audio + audio_session (müziği geçici kısar)  ←  assets/sounds/*.wav   +   ekranda büyük uyarı şeridi
```

Dart tarafındaki iş her karede en fazla birkaç kutuluk bir liste olduğu için hafif. Bu yüzden ayrıca bir Isolate gerekmiyor. Ağır iş zaten eklentinin yerel thread'inde yapılıyor.

**Kod düzeni (`mobile/lib/`):**
- `alerts.dart`: `signs` kataloğu (20 sınıfın Türkçe cümlesi ve önceliği; tek kaynak), `DetectionFilter`, `Cooldown`, `AlertQueue`. Saf Dart, cihazsız testleri `test/alerts_test.dart`'ta.
- `main.dart`: yatay mod, ekran açık, ses oturumu (müziği kısma), açılış uyarısı, YOLOView, ses oynatma ve uyarı şeridi.
- `assets/models/levha.tflite` (v5b FP16 modeli), `assets/sounds/<sınıf>.wav` (`tool/sesleri_uret.ps1` ile Windows'un Türkçe "Tolga" sesinden üretildi; kendi kaydınla aynı adla değiştirilebilir).

---

## 2. Geliştirme ortamı

| Araç | Ne için |
|---|---|
| Python 3.12 + `ml/.venv` | Eğitim (PyTorch CUDA 12.6, Ultralytics, albumentations, imagehash); dışa aktarma ve doğrulama (ONNX, TensorFlow + onnx2tf, ai-edge-litert) |
| Flutter (stable) + Android SDK (API 36) | Mobil uygulama |
| JDK 21 (Temurin) | Gradle / Android derlemesi |
| VS Code + Flutter/Python eklentileri | Editör |

Hepsi Windows 11 üzerinde çalışıyor.

Kurulu sürümlerin tamamı `docs/KURULUM.md` dosyasında.

---

## 3. Haftalık plan

Her haftanın sonunda bir **kapı** var. Kapıyı geçemezsek yazılı B planına geçeriz, beklemeyiz.

### Hafta 0 — 28 Ekim: Kurulum ✔
Ortam kuruldu ve araçlar doğrulandı (bkz. `docs/KURULUM.md`):
- GPU ile 1 epoch'luk deneme eğitimi çalıştı (RTX 3050, CUDA).
- Ham `yolo11n.pt` Windows'ta `.tflite`'a çevrildi: FP32 (10,2 MB) ve FP16 (5,1 MB); çıkış `1×84×8400`; sınıf isimleri dosyaya gömülü. Aynı fotoğrafta `.pt` ile aynı 5 nesneyi buldu → **Hafta 1'in 1. adımı tamamlandı.**
- Eklentiyle birlikte boş Flutter uygulamasının APK'sı derlendi.
- Veri seti indirilip `ml/data/levha` altına yerleştirildi ve denetlendi (Hafta 1'in 5. adımı, bkz. `docs/veri_denetimi.md`).

### Hafta 1 — 29 Ekim–4 Kasım: Dönüşüm risk testi + veri denetimi
1. Ham (eğitilmemiş) `yolo11n.pt` modelini `.tflite`'a dönüştür: 640 için yapıldı ✔. Aynı komutla 480 ve 320 için de dönüştür (`yolo export model=models/yolo11n.pt format=saved_model imgsz=480`).
2. Boş Flutter uygulamasına eklentiyi ve bu modeli koy. Telefonda COCO nesnelerini (insan, şişe, araba) algıladığını gör.
3. Telefonda ölç: FPS ve çıkarım süresi (ms), `useGpu: true/false`, her imgsz için. Sonuçları `docs/olcumler.md` dosyasına yaz.
4. Aynı fotoğrafı PC'de (`.pt`) ve telefonda çalıştır; kutuların ve sınıfların aynı çıktığını doğrula.
5. Veri seti denetimi ✔ (`ml/scripts/veri_denetimi.py` → `docs/veri_denetimi.md`):
   - Sınıflar dengeli: train'de her sınıftan 298–330 kutu var.
   - Levhalar küçük: imgsz=640'ta kısa kenarın medyanı 21 px. imgsz=320'de levhaların %69'u 16 px'in altına iniyor → **320 kullanılamaz**, en fazla 480'e inilebilir.
   - **Veri sızıntısı:** valid/test görsellerinin ~%45'i train'deki bir görselin neredeyse aynısı (aynı sahnenin peş peşe kareleri). Bunlar çıkarılarak `data/levha/data_temiz.yaml` oluşturuldu (temiz valid/test listeleri).
   - Görsellerin önemli bir kısmı Google Street View ekran görüntüsü; kenarlarında tarayıcı ve görev çubuğu görünüyor (bkz. risk 63).

**Kapı:** YOLO11 `.tflite` eklentide çalışıyor **ve** imgsz 640 ya da 480'de ≥ 5 FPS (hedef ≥ 8).
**B planı:** Model eklentide çalışmazsa eklentinin resmi desteklediği YOLO26n'e geçilir. FPS düşükse sırayla şunlar denenir: GPU → INT8 → imgsz 480 → YOLO26n.

### Hafta 2 — 5–11 Kasım: Eğitim + dışa aktarma
1. Eğitim 1: `yolo11n.pt`, `data=data/levha640/data_temiz.yaml` (640 px kopya; erken durdurma sızıntısız valid ile yapılsın), `imgsz=640`, `time=1.6` (saat), `patience=30`, **`fliplr=0.0`**, `batch=16`, `workers=3`. Komut ve gerekçeler `docs/KURULUM.md`'de.
2. Değerlendirme: sınıf bazlı mAP ve karışıklık matrisi. Sonuç **iki test setinde** raporlanır: orijinal test (Roboflow'un %85,1'iyle kıyas için) ve temiz test (gerçek başarı).
3. Dışa aktarma (Windows): `format=saved_model` FP32 ve FP16 üretir; `quantize=8 data=data/levha/data.yaml` eklenince INT8 varyantları da çıkar. Doğruluk Windows'ta `yolo val` ile ölçülür (`.tflite` doğrudan çalıştırılabiliyor); hız telefonda ölçülür. En iyi varyant seçilir.
4. Sürümler sabit tutulur (`ml/requirements.txt` ✔, `mobile/pubspec.lock`); çalışan bir şey olduğunda paket güncellenmez.

**Kapı:** Orijinal test setinde mAP50 ≥ 0,80 **ve** telefonda ≥ 5 FPS. Temiz test sonucu ayrıca raporlanır (sızıntı olmadığı için daha düşük çıkması beklenir).
**B planı:** mAP düşükse veri denetimindeki sorunlu sınıflara bak; daha uzun eğitim veya imgsz artışı denenir. Hız düşükse INT8 veya daha küçük imgsz.

**Durum: eğitim 28 Ekim'de erken tamamlandı ✔** (telefondaki hız kapısı Hafta 1'deki ölçümü bekliyor)
- **v1:** yolo11n.pt'den 47 epoch. Bilgisayar kapatılacağı için bir kez durdurulup devam ettirildi. İkinci devamda `time=1.1` verilince erken bitti (bkz. risk 65); en iyisi 42. epoch.
- **v2:** v1'in en iyisinden 20 epoch'luk bitirme eğitimi (`AdamW lr0=0.0004`, son 10 epoch mozaik kapalı). Telefona gidecek model bu: `ml/runs/detect/v2/weights/best.pt`.
- `.tflite`: `scripts/export_tflite.py` → `best_tflite/best_float16.tflite` (5,1 MB).

| Model | Test seti | mAP50 | mAP50-95 |
|---|---|---|---|
| v1 best.pt | orijinal / temiz | 0,876 / 0,883 | 0,699 / 0,706 |
| **v2 best.pt** | **orijinal / temiz** | **0,900 / 0,896** | **0,730 / 0,726** |
| v2 FP16 `.tflite` | temiz | 0,897 | 0,725 |

- Orijinal test setinde **0,900 ≥ 0,80** (kapı ✔; Roboflow'un aynı setteki modeli 0,851). Temiz testte sonuç neredeyse aynı, yani sızıntı bu modelin skorunu şişirmemiş.
- `.tflite` dönüşüm kaybı 0,1 puanın altında (başarı ölçütü 1: ≤ 2 puan ✔).
- Ezberleme yok: doğrulama kaybı sona kadar düştü.
- **Zayıf sınıflar** (temiz test AP50): pedestrian_info 0,55 (precision 0,53, başka mavi levhaları bu sınıf sanıyor), speed70 0,70 (recall 0,53, 50 ya da 30 sanıyor), speed30 0,79, giveway 0,83. Sık karışmalar: 70→50, okul geçidi ↔ yaya levhaları, girilmez→dur, sağa dönülmez→sola dönülmez (2 kez).
- Sonraki adımlar: uygulamada hız levhaları ve pedestrian_info için daha yüksek güven eşiği (Hafta 3); bu sınıflardan kendi fotoğraflarımızı ekleyip yeniden eğitmek (Hafta 4).

**Hata analizi (29 Ekim, v2, orijinal test, güven ≥ 0,4)**: `ml/scripts/hata_analizi.py`, kırpılmış kaçırmalar `docs/img/kacirilanlar_v2.jpg`

| Sınıf | Doğru | Kaçırılan / karışan | Kaçırılanın kısa kenarı | Doğrunun kısa kenarı | Yanlış pozitif |
|---|---|---|---|---|---|
| speed70 | 34 | 17 (13 hiç, 4 → speed50) | **9 px** | 16 px | 6 |
| speed30 | 34 | 5 (hepsi hiç) | **8 px** | 25 px | 8 |
| giveway | 33 | 10 (hepsi hiç) | **8 px** | 18 px | 2 |
| pedestrian_info | 26 | 7 (5 hiç) | 25 px | 16 px | **10** (9'u arka plan) |

- Hız ve yol ver levhalarındaki kaçırmaların çoğu **çok uzaktaki (8–9 px) levhalar**, yani sorun çözünürlük. Sürüşte levha yaklaştıkça büyüdüğü için pratik etkisi daha küçük; asıl ölçülmesi gereken "uyarı levhadan önce geldi mi" (saha testi).
- Gerçek hatalar: net bir 70'in 50 sanılması (4 kez) ve pedestrian_info'nun boş yerde görülmesi (9 kez).
- Veri çeşitliliği eksiği: **sarı zeminli ve geçici levhalar** (okul bölgesi "30", yol çalışması panosunda "yol ver", mavi bilgi panosuna basılmış "70") az temsil ediliyor. Hafta 4'te bunlardan kendi fotoğraflarımız eklenmeli.
- Veri setinde **etiket hatası** şüphesi: bir pedestrian_info etiketinin kırpıntısında levha yok.
- Seçenek (telefon hızı yeterse): daha büyük girişle eğitim (imgsz 800) uzaktaki küçük levhaları iyileştirir, ama çıkarımı ~1,6 kat yavaşlatır. Karar Hafta 1'deki telefon ölçümünden sonra.

**v3 deneyi (29 Ekim): zayıf sınıfları çoğaltma.** `ml/scripts/agirlikli_liste.py`, zayıf 4 sınıfın geçtiği 1.012 eğitim görselini listeye ikinci kez ekledi. v2'den 15 epoch eğitildi (`AdamW lr0=0.0002`, son 5 epoch mozaik kapalı).

| Model | Orijinal test mAP50 / 50-95 | Temiz test mAP50 / 50-95 | Temiz valid mAP50-95 |
|---|---|---|---|
| v2 | 0,900 / 0,730 | 0,896 / 0,726 | **0,732** |
| v3 | 0,905 / 0,736 | 0,901 / 0,733 | 0,722 |

Hata analizinde (`docs/img/kacirilanlar_v3.jpg`) pedestrian_info (yanlış alarm 10 → 6) ve speed70 (doğru 34 → 37) iyileşti, ama **speed30 yanlış alarmları 8 → 14'e çıktı**. Fark ölçüm gürültüsü içinde ve validasyonda v2 önde. **Karar: uygulamalarda v2 kalıyor.** v3 aday olarak saklanıyor; araç içi video testinde ikisi aynı videoda karşılaştırılacak. Ders: çoğaltma, sorunun asıl kaynağı olan uzak/küçük levhaları çözmüyor.

**Uçtan uca demo testi (Windows uygulaması, v2):** test setinden 6 levhanın görüntüsü sündürülmeden 3'er saniyelik bir videoya kondu. Uyarılar **6/6 doğru sırada** geldi (dur, hız 70, yol ver, hız 30, yaya geçidi, girilmez), her biri levha göründükten 0,13 s sonra, yanlış alarm yok.

**Gece çalışması (29 Ekim): gerçek sürüş videoları, yeni kurallar, DFG verisi.** Ayrıntılar `docs/video_testi.md`'de.
- **10 açık lisanslı araç içi videoda** (42 gerçek levha olayı) v2, eski kurallarla 25 levha yakaladı ama **58 yanlış uyarı** verdi. Halüsinasyonun kaynağı test setinde olmayan şeyler: şerit levhaları, başka uyarı üçgenleri, 4.80 m yükseklik sınırı, mavi yön tabelaları.
- **Kural düzeltmesi:** güven 0,5 → 0,6 ve en küçük kutu %2,5 → %5 olunca v2'de yanlış uyarı 58 → 20, yakalanan 25 → 30 oldu (orijinal videolar, 30 FPS). Telefon ve masaüstü uygulamasında varsayılan yapıldı.
- **v4:** aynı veriyle COCO'dan 200 epoch'luk temiz eğitim (160'ta erken durdu). Temiz testte 0,895 / 0,728, yani v2 ile aynı. Videoda da v2'den belirgin iyi değil. Ders: aynı veriyle daha uzun eğitim halüsinasyonu çözmüyor.
- **DFG verisi** (Slovenya, Tabernik & Skočaj 2019, **CC BY-NC-SA 4.0**: ticari olmayan kullanım, atıf zorunlu): 6.957 gerçek araç kamerası görüntüsü, 200 sınıfın hepsi etiketli. Sınıf eşlemesi kırpıntılarla gözle doğrulandı (`ml/scripts/esleme_dfg.json`): bizim 20 sınıfımızdan 19'una giren 3.411 levha (U dönüşü yasak levhası eşlemede yok) etiket olarak, geri kalan her levha "uyarı verme" örneği (arka plan) olarak kullanıldı. Hız 40/60 levhaları, hız sonu levhaları, yükseklik ve ağırlık sınırı da bu sayede arka plan. "CONA 30" bölge levhalı görüntüler alınmadı. Betikler: `ml/scripts/dfg_hazirla.py` + `ek_veri.py --arka-plan`.
- **v5:** v4'ten başlayıp bizim veri + 415 arka plan kırpıntısı + 6.733 DFG görüntüsüyle (toplam 11.570) eğitildi. İlk deneme bellek yetmediği için 3 epoch'tan sonra (4. epoch'ta) çöktü (risk 66). Kaldığı yerden **v5b** olarak devam etti.
- **v5b sonucu:** temiz testte v2 ile aynı (0,894 / 0,725; validasyon mAP50-95 0,744). Videoda, aynı 1280 px kopyalarda ve aynı kurallarla (0,6 / %5) en iyi model: 30 FPS'te 30 yakalanan (23 zamanında) / 23 yanlış uyarı, ~10 FPS'te 27 (23) / 10. v2: 30 (20) / 28 ve 21 (18) / 13.
- **Güven 0,6 → 0,7:** üç modelde de yanlış uyarıyı azalttı. v5b + 0,7: 30 FPS'te **32 (26) / 18**, ~10 FPS'te **27 (23) / 6**. Gecenin başındaki uygulamaya göre (v2 + 0,5 / %2,5; aynı kopyalarda 25 (16) / 59 ve 20 (18) / 38) yanlış uyarı üçte birin altına indi, yakalanan levha 7 arttı.
- **Yavaş telefon:** ~5 FPS'te "5 karenin 3'ü" oylaması levhaların çoğunu kaçırıyor (42 levhadan 16'sı yakalanıyor). Telefon 10 sn'lik ortalamada 8 FPS'in altındaysa oylama kendiliğinden "3 karenin 2'si"ne geçiyor: ~5 FPS'te 24 (21) / 5 (`alerts.dart` `votingFor`, risk 68).
- **Karar: uygulamalarda v5b, güven 0,7.** FP16 `.tflite` temiz testte 0,892 / 0,727; 11 test fotoğrafında bilgisayarda ve emülatörde 11/11. `desktop/levha.onnx` ve `desktop/levha.pt` de v5b. Ölçüm gürültüsü büyük: aynı v2 orijinal videolarda 20, küçültülmüş kopyalarda 28 yanlış uyarı verdi. Sonuç gerçek yol testinde doğrulanacak.
- Ders: DFG arka planının etkisi (v4 → v5b) FPS'e göre değişiyor: 30 FPS'te yanlış uyarı neredeyse aynı (19 → 18), zamanında uyarı 23 → 26; ~10 FPS'te yanlış uyarı yarıya indi (12 → 6). v2'ye göre yakalama kazancının çoğu v4'te de var (uzun eğitim). Kalan yanlış uyarıların çoğu uzaktaki sarı yol çalışması levhaları, başka uyarı üçgenleri ve ikaz direkleri; en çok "hız 30" olarak çıkıyor.

**Canlı demo (29 Ekim öğleden sonra).** Ankara videosu masaüstü uygulamasında GPU'da, gerçek hızında ve sesli izlendi. Fark edilenler: taş düşebilir levhasına "kavşak", olmayan sağ viraja "sağa tehlikeli viraj", hız 70'e geç uyarı.
- v5b logunun tekrarında Ankara'daki 13 yanlış uyarının 12'si 20 sınıfın dışındaki levhalardan geliyor (biri belirsiz): S-viraj, taş düşebilir ve iki yönlü trafik → kavşak; viraj okları → dikkat / tehlikeli viraj; sarı yol çalışması ve kasis üçgeni → hız 30. Eğitimde hata yok; modelin "bu bizim levhamız değil" diyebileceği bir sınıf yok.
- Gecikme boy sınırından gelmiyor. Uzaktaki levhada güven düşük: hız 70, %2,6 boyda 0,31; 0,7'yi ancak %5,5'te geçti. Aynı anda gelen levhaların sesleri de sırayla çalınıyor: hız 70, "Sağdan gidiniz" bitene kadar 1 sn bekledi. Boy sınırını %3'e indirmek yanlış uyarıyı 30 FPS'te 18 → 36, ~10 FPS'te 6 → 21 yapıyor.
- **Sonraki adım:** 21. sınıf `diger_levha` (tespit edilir, seslendirilmez). Yeni veri Türk levhalarından olacak. Uygulamada: tanınan bütün levhalar ekranda aynı anda gösterilecek, birden çok levha gelince uyarılar kısalacak.

**v6 (29 Ekim gecesi, bu bilgisayarda): 21. sınıf "diğer levha", yalnız Türk verisi.** Karar: yabancı veri (DFG) çıkarıldı; "çok denenmiş" Türk tespit seti arandı. Tek büyük aday TTVS (İTÜ, 33.764 görüntü, 108 sınıf) erişim için 500 görüntü etiketleme istiyor; kullanılabilen tek set Roboflow "trafik levhaları" (trafik isaretleri çalışma alanı, 2.940 araç kamerası karesi, 42 KGM kodlu sınıf, CC BY 4.0, Erzurum, sisli/kışlık). 20 sınıfı bizimkilere eşlendi (`ml/scripts/esleme_trafik_levhalari.json`), kalan 18 sınıf (kasis, viraj okları, onarım, dönüş adası, demiryolu, hız 20, mecburi yön…) `diger_levha` oldu: 2.933 görsel, 5.995 kutu (2.396'sı diğer levha), test setimizle çakışan 7 kare ayıklandı. Eğitim: v5b'den, 7.770 görsel, 60 epoch (31'den sonra 4 veri işçisiyle sürdürüldü: epoch 1,7 → 1,3 dk, GPU %30–100 → %90+; bellek sınırda, sayfa dosyası 37 GB'a büyüdü). Validasyon mAP50-95 0,737 (v5b 0,744).
- **Temiz test (20 sınıf):** .pt 0,890 / 0,721, FP16 .tflite 0,889 / 0,718 (v5b 0,894 / 0,725): aynı seviye.
- **10 video, aynı kurallar (0,7 / %5):** 30 FPS'te 32 (26) / **14** yanlış uyarı (v5b 18); ~10 FPS'te 28 (23) / **9** (v5b 6). Yakalama aynı; yanlış uyarı 30 FPS'te azaldı, ~10 FPS'te arttı (gürültü payı ±2–8). DFG'nin ~10 FPS kazancı gitti.
- **Bulgu: "diğer levha" genelleşmedi.** v6 bu sınıfı yalnızca Erzurum setine benzeyen karelerde söylüyor: Bilecik videosunda 14, Ankara'da 1 tespit, öteki 8 videoda 0; bizim 4.837 eğitim görselinde 0,3 güvenle bile 0. Nedeni: sınıfın tek kaynağı dar bir alan (tek şehir, sis), üstelik bizim Hootbu görsellerindeki etiketsiz öteki levhalar modele hâlâ "arka plan" diye gösteriliyor (çelişki). Sözde etiket turu (`ml/scripts/sozde_etiket.py`) bu yüzden 0 kutu buldu, v6b eğitilmedi. Ankara'daki yanlış uyarılar aynı levhalardan: S-viraj → kavşak, sarı yol çalışması → hız 30, sollama yasağı → hız 30.
- **v7 denemesi (30 Ekim gecesi, otomatik zincir):** "her levha sesli" isteği için trafik levhaları setinden yeterli örneği olan 8 levha kendi sınıfı yapıldı (kasis 499, dönüş adası 535, ileri ve sola mecburi 492, refüj başı 214, demiryolu 139, ileri ve sağa mecburi 132, durak 127, ada etrafında dönünüz 90 kutu); kalan levhalar "Bilinmeyen levha" (ekranda, sessiz). 29 sınıf, v6'dan 150 epoch'a kadar (erken durdurma 40; 112. epoch'ta durdu, en iyi 72.), kosinüs öğrenme hızı. Validasyon 0,735; temiz test .pt 0,884 / 0,716, .tflite 0,894 / 0,725 (v6 ile aynı). **Videoda daha kötü:** 30 FPS'te 29 (23) / 20, ~10 FPS'te 25 (19) / 10 (v6: 32 (26) / 14 ve 28 (23) / 9). 8 yeni sınıfın hiçbiri 10 videoda 0,5 güvenle tespit vermedi: tek şehirlik, sisli kaynaktan öğrenilen sınıflar başka yollara taşınmıyor; "diğer levha"daki ders tekrarlandı. Ağırlıklar `ml/runs/detect/v7`.
- **Karar:** uygulamada v6 (Türk verisi şartı, 21 sınıf); v5b dosyaları `ml/runs/detect/v5b` altında duruyor. Katalog 28 sesli sınıfı ve 16 yeni sesi taşıyor; v6 bunları hiç üretmediği için zararsız, ileride çeşitli kaynaklı bir Türk seti gelince kullanılacak. Yeni levhaları gerçekten öğretmek için tek yol **farklı şehir ve havadan** örnekler: ya TTVS'ye katkı verip 33 bin görüntülük seti almak ya da kendi telefon kayıtlarımızı etiketlemek. Sonraki adım, "diğer levha" için ikinci bir Türk kaynağı: Hootbu TSR2 (1.563 araç kamerası karesi, 42 sınıf: çift viraj, kasis, buz/kar, 4,80 m, iki yönlü) ve/veya ETÜ seti; ya da DFG'nin öteki levhalarını diğer levha olarak geri almak (10 FPS yanlış uyarısı için en güçlü kanıt onda).

### Hafta 3 — 12–18 Kasım: Mobil uygulama (ilk çalışan sürüm)
1. YOLOView + eğitilmiş model (`assets/models/`) + DetectionFilter + CooldownManager + AlertQueue + ses dosyaları.
2. Yatay mod kilidi, ekran hep açık (`wakelock_plus`), sade ayar ekranı (güven eşiği, zoom).
3. Açılışta "Deneysel prototip — güvenlik sistemi değildir" uyarısı. Açılışta ve Ayarlar'da veri seti atıfları (Hootbu CC BY 4.0, DFG CC BY-NC-SA 4.0).
4. Cooldown, filtre ve kuyruk için birim testleri (`flutter test`).
5. **Uçak modunda** release APK ile tam çalışma testi.

**Kapı:** Masada, ekrandaki veya basılı levha fotoğraflarıyla "gör → konuş" uçtan uca çalışıyor; uçak modunda da çalışıyor.

**Durum (29 Ekim): kod hazır, telefonda henüz denenmedi.**
- Uyarı mantığı (filtre, tekrar önleme, ses sırası) test öncelikli yazıldı; 12 birim testi geçiyor ✔.
- Ekran, model, sesler ve açılış uyarısı bağlandı. `flutter analyze` temiz. Release APK derlendi (82,9 MB, model ve 20 ses içinde) ✔.
- Hız levhaları için 0,65, pedestrian_info için 0,70 güven eşiği (Hafta 2'de zayıf çıkan sınıflar).
- Release APK'da **INTERNET izni yok** (aapt2 ile doğrulandı) ✔.
- Eksik: telefonda deneme (Hafta 1'in kalanıyla birlikte), ayar ekranı (eşik/zoom), sesleri önyükleme. Bunlar telefonda ölçüm yapıldıktan sonra eklenecek.

**Durum (29 Ekim sabah): test arayüzü hazır, emülatörde çalıştı ✔**
- Dört sekme: **Sürüş** (kamera, uyarı yazısı, FPS), **Kayıtlar** (her olay saatiyle; Paylaş düğmesi oturum dosyasını gönderir), **Model testi** (gömülü 11 fotoğraf; telefonda modelin doğru çalıştığını tek dokunuşla gösterir), **Ayarlar** (güven eşiği, uzak levhaları yoksay, ses, GPU).
- **Önemli hata bulundu ve düzeltildi:** ilk release APK açılışta çöküyordu. R8 küçültmesi WorkManager'ın veritabanı sınıfını bozuyordu (risk 67). Küçültme kapatıldı. Android 14 emülatöründe uygulama açıldı ve model testi **11/11 doğru** verdi (güvenler bilgisayardakiyle aynı).
- Telefonda deneme adımları: `docs/telefon_testi.md`.

**Durum (29 Ekim öğlen): v5b'li APK hazır, emülatörde çalıştı ✔**
- Model v5b (FP16 `.tflite`, 5,1 MB). Güven eşiği varsayılanı 0,7.
- FPS'e göre oylama: telefon 8 FPS'in altındaysa 3 karenin 2'si. Geçiş Kayıtlar'a "AYAR" satırı olarak yazılıyor ve Sürüş ekranının altında görünüyor. Emülatör ~2,5 FPS'te çalıştı ve 2/3'e geçti.
- 16 birim testi geçiyor, `flutter analyze` temiz. Telefon için `app-arm64-v8a-release.apk` (42,8 MB).
- Android 14 emülatöründe model testi 11/11; güvenler bilgisayardaki `.tflite` ile aynı.

### Hafta 4 — 19–25 Kasım: Saha testi 1 + iyileştirme
1. **Güvenlik kuralı:** Sürücü telefona hiç dokunmaz. Telefonu yolcu ayarlar; telefon vantuzlu tutucuda durur.
2. Önce yol videosu çek, modeli PC'de bu videolar üzerinde değerlendir. Ardından canlı test.
3. Ölçüm formu (`docs/saha_testi.md`): levha, hız, hava ve ışık, algılandı mı, uyarı levha geçilmeden önce mi geldi, yanlış uyarı oldu mu.
4. 30 dakikalık sürekli kullanımda ısınma ve pil testi; FPS düşüşünü kaydet.
5. Ayar: güven eşiği, oylama penceresi, cooldown süreleri, zoom (1.0x ve 1.5x).
6. Kendi çektiğin telefon görüntülerinden zor örnekleri etiketleyip eğitime ekle ve yeniden eğit. Veri setinin büyük kısmı Street View ekran görüntüsü olduğu için bu adım önemli (risk 63).

### Hafta 5 — 26 Kasım–2 Aralık: Saha testi 2 + rapor
Farklı koşullarda (gündüz/akşam, mümkünse yağmur) testler ve sonuç tablosu. Rapor bölümleri: mimari, ölçümler, sınırlar, demo videosu.

### Hafta 6 — 3–9 Aralık: Windows uygulaması + tampon
Bu bilgisayar için Windows uygulaması: web kamerası + `best.onnx` + ONNX Runtime + OpenCV. Kamera okuma Ultralytics'in akış iş parçacığında, ses `winsound` ile eşzamansız çalınır. Filtre, cooldown ve ses kuyruğu kuralları mobil sürümle aynıdır. Ön işleme ve son işlemede Ultralytics'in kendi kodu birebir kullanılır. Canlı test bu bilgisayarda web kamerasıyla yapılır. Kalan süre, önceki haftalardan kalan işler için tampondur.

**Durum (29 Ekim): ilk sürüm erken hazırlandı** (`desktop/app.py`; model: ekran kartı varsa `desktop/levha.pt`, yoksa `desktop/levha.onnx`)
- Levha kataloğu `mobile/lib/alerts.dart`'tan okunuyor (tek kaynak); sesler mobil uygulamanınkiyle aynı WAV dosyaları.
- Kural öz-testi geçiyor (`app.py --test`).
- 29 Ekim öğlen: model v5b, güven 0,7. Düzeltme: sınıf tabanları (hız levhaları 0,65) artık genel eşiğin altına inmiyor; telefondaki `classThresholds` ile aynı.
- Demo videosunda "Dur → Hız sınırı otuz → Yol ver" uyarıları sırayla çalındı. İkinci levha aslında hız 50'ydi: demo videosu görüntüyü sündürdüğü için yanlış okundu. Bozulmamış görüntüde `.pt` ve `.onnx` speed50 0,94 veriyor.
- 29 Ekim öğleden sonra, pencereyle ölçüm (1280 px video): CPU/ONNX ~21–30 FPS. Pencere arkadayken Windows 11 işlemi kısıyordu (~3 FPS); `high_qos()` ile düzeldi. Varsayılan artık GPU: `levha.pt` PyTorch'la CUDA'da ~63 FPS (`onnxruntime-gpu` CUDA 13 istediği için ONNX GPU'da çalışmıyor). Video kendi hızında oynuyor.
- Eksik: web kamerasıyla canlı deneme (senin yapman gerekiyor), ayar/eşik arayüzü.

---

## 4. Sorun listesi → çözüm eşlemesi

**Durum işaretleri:**
- 🟢 **Eklenti çözüyor** (Hafta 1'de doğrulanacak)
- 🔧 **Bizim önlemimiz**
- 📏 **Ölçülüp ayarlanacak**
- ⚠️ **Kabul edilen sınır** (raporda açıkça yazılacak)

### Kamera ve görüntü kalitesi
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 1 | Hareket bulanıklığı | 🔧📏 | `albumentations` kurulu, bu sayede Ultralytics eğitimde bulanıklaştırma artırımını otomatik uygular. Sağlam tutucu kullanılır; 3/5 oylama tek bulanık kareyi tolere eder. | H2, H4 |
| 2 | Odak arama (autofocus hunting) | ⚠️📏 | Eklenti CameraX'in sürekli odak modunu kullanıyor; ayrı bir odak kontrolü sunup sunmadığı H1'de incelenir. Sahada sorun çıkarsa B planı: eklentiyi çatallayıp (fork) odağı kilitlemek. | H1, H4 |
| 3 | Sonsuza odak desteği | ⚠️ | Elle odak kilidi kullanmıyoruz (her telefonda desteklenmiyor). Araçta levhalar hep birkaç metreden uzakta olduğu için sürekli odak yeterli olmalı; sahada doğrulanır. | H4 |
| 4 | Otomatik pozlama ve beyaz dengesi | 🔧 | Eğitimde HSV (parlaklık/doygunluk) artırımı uygulanır; oylama ani ışık sıçramalarını tolere eder. | H2 |
| 5 | Titreşim | 🔧 | Vantuzlu tutucu + oylama + bulanıklık artırımı. | H4 |
| 6 | YUV420 → RGB dönüşümü | 🟢 | Dönüşüm eklentinin yerel kodunda yapılıyor; görüntü Dart'a hiç taşınmıyor. | H1 |
| 7 | Uzak levhanın az piksel kaplaması | 📏🔧 | Ölçüldü ✔: imgsz=640'ta kısa kenarın medyanı 21 px, levhaların %35'i 16 px'in altında. Bu yüzden model girişi 640 (zorunlu kalırsa 480); 320 kullanılmaz. Kamera 720p; gerekirse 1.5x zoom kullanılır. | H1, H4 |
| 8 | ROI kırpma kaynaklı kayıp | 🔧 | Kırpma **yok**, tam kare kullanılıyor. Zoom kenarları keser; 1.0x ve 1.5x sahada kıyaslanır. | H4 |
| 9 | Gece / tünel | ⚠️ | Birincil hedef gündüz koşulları. Gece performansı ölçülüp raporlanır; veri setindeki gece örneği oranı denetlenir. | H1, H5 |
| 10 | Parlama / ters ışık | ⚠️🔧 | HSV artırımı ve oylama; kalan etki sınır olarak raporlanır. | H2, H5 |
| 11 | Yağmur, sis, kirli lens | ⚠️ | Lens temizliği test öncesi kontrol listesinde. Kötü hava sınır olarak raporlanır. | H4 |
| 12 | Kısmen kapanmış levha | 🔧⚠️ | Mosaic artırımı eğitimde kısmi görünen levhaları zaten üretir; ağır kapanma sınır olarak kalır. | H2 |
| 13 | Kamera donanım farkları | ⚠️ | Tek hedef cihaz sınıfı seçildi; ikinci bir telefon bulunursa karşılaştırılır. | H5 |

### Veri seti ve model eğitimi
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 14 | Yetersiz çeşitlilik | 🔧📏 | Denetlendi ✔: veri seti Street View ekran görüntüleri ile araç içinden çekilmiş fotoğrafların karışımı; bazı görseller 90° yan dönmüş (etiketleri piksellerle uyumlu). H4'te kendi telefon görüntülerimiz eklenecek (risk 63). | H1, H4 |
| 15 | Sınıf dengesizliği, hatalı etiket | 🔧 | Denetlendi ✔: sınıflar dengeli (train'de sınıf başına 298–330 kutu). 100 rastgele etiket çizildi (`ml/runs/denetim/etiketler/`); örneklerde kutular levhaların üstünde. Sınıf bazlı mAP eğitimde takip edilir. | H1, H2 |
| 16 | Veri sızıntısı | 🔧 | Bulundu ve ayıklandı ✔: valid/test'in ~%45'i train'deki görsellerin neredeyse aynısı (algısal hash ≤ 12, gözle doğrulandı). `data_temiz.yaml` → temiz valid 296, temiz test 308 görsel. Bu setlerde sınıf başına 7–37 kutu kaldığı için sınıf bazlı skorlar gürültülü olabilir. | H1 |
| 17 | Yetersiz doğrulama | 🔧 | Ayrı ve hiç dokunulmamış test seti; ayrıca kendi yol videolarımızla gerçek dünya testi. | H2, H4 |
| 18 | Erken durdurma / aşırı öğrenme | 🔧 | `patience=30`, `epochs=150`; loss eğrileri izlenir; `best.pt` val mAP'e göre seçilir. | H2 |
| 19 | Eğitim donanımı yetersizliği | 🔧 | Ölçüldü ✔: `batch=-1` 4 GB VRAM için batch 11 seçiyor. Darboğaz GPU değil, 1080p JPEG'lerin her epoch'ta yeniden açılması. `cache=ram` bunu ~5 kat hızlandırıyor, ama Windows'ta önbellek her işçi sürece kopyalandığı için RAM'e sığmıyor. Çözüm: veri seti bir kez 640 px'e küçültülüyor (`scripts/kucult.py`) ve önbelleksiz okunuyor. İşçi süreçleri de RAM yiyor (süreç başına ~0,6 GB; 6 işçide boş RAM 0,7 GB'a düştü), bu yüzden `workers=3`. Laptop prize takılı ve Armoury Crate'te Turbo modda olmalı. | H2 |
| 20 | Eğitim ile gerçek kamera arasındaki fark | 🔧📏 | Eğitimdeki imgsz ile çıkarımdaki imgsz aynı tutulur; kendi videolarımızla doğrulanır. Somut kanıt bulundu: risk 63. | H2, H4 |

### Dışa aktarma ve mobil entegrasyon
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 21 | ONNX / TFLite dönüşüm hataları | 🔧 | Önce ham modelle dönüşüm denendi (fail-fast): Windows'ta onnx2tf yoluyla başarılı ✔. `.tflite` doğruluğu `yolo val` ile `.pt`'ye kıyaslanır (fark ≤ 2 puan mAP olmalı). | H1, H2 |
| 22 | NMS operatörü uyumsuzluğu | 🟢 | `nms=None` ile dışa aktarılır, yani modelin içinde NMS yok; NMS'i eklenti Kotlin'de yapıyor. | H1 |
| 23 | Yazılımsal NMS performansı | 🟢 | NMS Dart'ta değil, yerel kodda çalışıyor. | H1 |
| 24 | Ön işleme uyumsuzluğu | 🟢 | Eklenti imgsz ve stride değerlerini modelin metadata'sından okuyor. Aynı fotoğraf PC'de ve telefonda çalıştırılıp kıyaslanır. | H1 |
| 25 | Çıktı tensörünün yanlış çözülmesi | 🟢 | Çözümlemeyi eklenti yapıyor; sınıf adları modelin metadata'sından geliyor, elle yazılmış etiket listesi olmadığı için kayma hatası olamaz. | H1 |
| 26 | INT8 / FP16 seçimi | 📏 | FP32, FP16 ve INT8 varyantlarının doğruluğu Windows'ta, hızı telefonda ölçülür; seçim tabloyla yapılır. | H2 |
| 27 | Donanım hızlandırıcı uyumsuzluğu | 🟢📏 | Eklentinin GPU → CPU otomatik geçiş zinciri var. Adreno 610'da hangi yolun kullanıldığı logcat'ten doğrulanır. | H1 |
| 28 | Kamera yönü / koordinatlar | 🟢🔧 | Sensör dönüşünü eklenti hallediyor; uygulama yatay moda kilitlenir. | H3 |

### Gerçek zamanlı performans ve bellek
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 29 | Kare kaybı | 🟢📏 | Kare atlanması bilinçli bir tercih: her zaman **en son** kare işlenir. Hesap: 90 km/s = 25 m/s. 8 FPS'te kareler arası ~3 m. ~50 m'den görülen bir levha ~2 sn, yani ~16 kare boyunca görünür. | H1 |
| 30 | Kuyruk birikmesi | 🟢 | CameraX'in varsayılan "yalnızca en son kare" stratejisi kullanılıyor. Kameranın önünde el sallama testiyle gecikme gözle doğrulanır. | H1 |
| 31 | Isolate ve bellek yükü | 🟢 | `includeOriginalImage: false` ayarıyla görüntüler Dart'a gelmez; Dart'a yalnızca kutu listesi gelir. | H3 |
| 32 | Düşük FPS | 📏🔧 | H1'de ölçülür. Sırayla denenecekler: GPU → INT8 → imgsz 480 → YOLO26n. imgsz 320 kullanılmaz (risk 7). | H1, H2 |
| 33 | Isınma ve pil | 📏🔧 | `YOLOStreamingConfig` ile kare hızı üst sınırı (ör. 10 FPS) konur; 30 dakikalık test; araç şarjı kullanılır. | H4 |
| 34 | Yüksek çözünürlükte bellek | 🟢🔧 | Kamera 720p (4K değil) ve görüntü kopyası Dart'a aktarılmıyor. | H3 |
| 35 | Platformlar arası performans farkı | ⚠️📏 | Her platformun ölçümü ayrı raporlanır. | H5, H6 |

### Tespit, takip ve sesli uyarı
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 36 | Yanlış pozitif | 🔧 | Güven eşiği (başlangıç 0,5), en küçük kutu boyutu ve 5 karenin en az 3'ünde görülme şartı. | H3, H4 |
| 37 | Yanlış negatif | 📏⚠️ | Recall ölçülür. Oylama penceresi kısa tutulur (yanlış pozitifle denge). | H4 |
| 38 | Geç algılama | 📏🔧 | Ölçüm formunda "uyarı levha geçilmeden önce mi geldi?" alanı var. 3/5 oylama 8 FPS'te yalnızca ~0,4 sn gecikme ekler. | H4 |
| 39 | Cooldown'un yanlış davranması | 🔧 | İki koşullu kural: aynı sınıf için **en az 5 sn sessizlik** ve levha **≥2 sn görünmez olduktan sonra** yeniden kurulma. Böylece tekrar önlenir, kısa süre sonra gelen yeni aynı levha da kaçmaz. Birim testiyle doğrulanır. | H3 |
| 40 | IoU takip hataları | 🔧 | Kimlik takibi **kullanmıyoruz**; sınıf ve zaman bazlı kural (39) kimlik kaybı sorununu ortadan kaldırır. | H3 |
| 41 | Takip ve cooldown entegrasyonu | 🔧 | 40 ile aynı. | H3 |
| 42 | Sesli uyarı gecikmesi | 🔧📏 | Cümleler kısa (≤1,5 sn), sesler uygulamanın içinde yerel WAV olarak duruyor. Şu an her uyarıda yerelden yükleniyor. "Levha göründü → ses başladı" gecikmesi telefonda ölçülecek; gerekirse sesler önyüklenecek. | H3, H4 |
| 43 | Seslerin çakışması | 🔧 | Tek oynatıcı ve kuyruk; aynı anda yalnızca bir ses çalar. | H3 |
| 44 | Önceliklendirme hataları | 🔧 | 3 seviye (bkz. Bölüm 6). Yüksek öncelikli uyarı kuyrukta öne geçer. | H3 |
| 45 | Ses kuyruğunun uzaması | 🔧 | Kuyrukta en fazla 2 uyarı bekler; 3 sn'den eski uyarılar atılır. | H3 |
| 46 | Ortam gürültüsü / ses seviyesi | 🔧 | `audio_session` ile çalan müzik geçici olarak kısılır. Ekranda büyük uyarı şeridi gösterilir, ses duyulmasa da uyarı görülür. | H3 |

### Çevrimdışı çalışma, kapsam ve test
| # | Sorun | Durum | Ne yapıyoruz | Ne zaman |
|---|---|---|---|---|
| 47 | Çevrimdışı dosya bağımlılıkları | 🔧 | Model ve sesler `assets/` içinde; eklentinin "model ID ile indirme" özelliği kullanılmıyor. Release APK'da INTERNET izni yok ✔: uygulama işletim sistemi düzeyinde internete çıkamaz. Uçak modunda da test edilecek. | H3 |
| 48 | Yol bağlamının anlaşılamaması | ⚠️ | Kapsam dışı: sistem gördüğü levhayı söyler, levhanın hangi şeride ait olduğunu yorumlamaz. Raporda yazılır. | H5 |
| 49 | ONNX ile TFLite'ın farklı sonuç vermesi | 📏 | Aynı 50 test görüntüsünde `.pt`, `.tflite` ve `.onnx` sonuçları kıyaslanır. | H2, H6 |
| 50 | Yetersiz saha testi | 🔧 | Yapılandırılmış ölçüm formu ve video kaydı. Güvenlik kuralı: sürücü telefona dokunmaz. | H4, H5 |
| 51 | Erken güvenlik iddiası | 🔧 | Uygulamada ve raporda "deneysel prototip, güvenlik sistemi değildir" ifadesi yer alır; metrikler dürüstçe raporlanır. | H3, H5 |

### ChatGPT listesinde olmayan, araştırmada bulunan riskler
| # | Sorun | Durum | Ne yapıyoruz |
|---|---|---|---|
| 52 | ‼️ **Yatay çevirme artırımı sol/sağ levhaları bozar.** Ultralytics varsayılan olarak görüntülerin %50'sini aynalar. Bu durumda `keepleft` ↔ `keepright`, `dangerousleft` ↔ `dangerousright`, `donotturnleft` ↔ `donotturnright` görüntüleri yanlış etiketle öğrenilir. | 🔧 | Eğitimde **`fliplr=0.0`**. |
| 53 | Veri setinde yalnızca 20 sınıf var; hız levhalarından sadece 30, 50 ve 70 mevcut. Model 80, 90 veya 120 levhasını bunlardan biri sanabilir. | ⚠️🔧 | Kapsam raporda net yazılır. Hız sınıfları için daha yüksek güven eşiği kullanılır; sahada görülen kapsam dışı levhalar ayrıca kaydedilir. |
| 54 | Ultralytics'in yeni `litert` dışa aktarması Windows'ta desteklenmiyor. | 🔧 | `format=saved_model` (onnx2tf) yolu Windows'ta `.tflite` üretiyor ✔. Bu yolda modelin girişi NHWC biçiminde (yeni `litert` formatında NCHW). Eklentinin bunu doğru okuduğu H1'de telefonda doğrulanacak. |
| 55 | Xiaomi/MIUI: USB'den uygulama yüklemek için ek ayar gerekiyor, MIUI pil tasarrufu uygulamayı kapatabiliyor. | 🔧 | Geliştirici seçeneklerinde "USB hata ayıklama" ve "USB üzerinden yükle" açılır (Mi hesabı/SIM isteyebilir). Uygulama hep ön planda ve ekran açık çalışır. |
| 56 | Sürüm kayması: Ultralytics ve eklenti çok sık güncelleniyor (ör. 8.4.83 sürümünde `tflite` formatı kaldırıldı). | 🔧 | H1 başarılı olunca sürümler sabitlenir. |
| 57 | Lisanslar | 🔧 | Veri seti CC BY 4.0: raporda ve uygulamada atıf zorunlu. DFG (v5b'nin ek verisi) CC BY-NC-SA 4.0: atıf zorunlu, ticari kullanım yok; model paylaşılırsa aynı lisansla paylaşmak en güvenlisi. Öğrenci projesi için uygun. Ultralytics ve eklenti AGPL-3.0: uygulama dağıtılırsa kaynak kodu açık olmalı (GitHub'da public repo yeterli). |
| 58 | Disk alanı (C: sürücüsünde ~60 GB boş) | 🔧 | Telefon yokken deneme için Android 14 emülatörü kuruldu (AVD `levha_test`, x86_64; çalışırken ~3 GB bellek). FPS ölçümü gerçek telefonda yapılacak. `ml/runs/` klasörü düzenli temizlenir. |
| 59 | GPU sürücüsü CUDA 12.7'yi destekliyor | 🔧 | PyTorch, sürücüyle uyumlu olan CUDA 12.6 derlemesiyle kuruldu ✔. |
| 60 | *(Kurulumda yaşandı)* Yeni Android cmdline-tools (23.0) paket adlarında `ndk/28.2…` yazımını bekliyor, Flutter 3.47 ise `ndk;28.2…` gönderiyor. Bu yüzden NDK otomatik kurulamadı ve derleme durdu. | 🔧 | NDK elle `ndk/28.2.13676358` yazımıyla kuruldu ✔. İleride Flutter yeni bir NDK sürümü isterse aynı yöntemle kurulur (bkz. `docs/KURULUM.md`). |
| 61 | Dışa aktarma paketleri (TensorFlow, onnx2tf) eğitimle aynı ortamda. TensorFlow kurulumu `protobuf` ve `onnx` sürümlerini düşürdü. Ayrıca Ultralytics eksik paketi dışa aktarma *sırasında* kurmaya kalkarsa süreç çökebilir. | 🔧 | Paketler önceden ve sabit sürümle kuruldu (`ml/requirements.txt`) ✔. torch ve GPU eğitimi etkilenmedi ✔. Paketler `pip install -U` ile güncellenmeyecek. |
| 62 | Ultralytics varsayılan olarak anonim kullanım verisi gönderiyor (`sync=True`); bu, "tam çevrimdışı" iddiasıyla çelişir. | 🔧 | `yolo settings sync=False` yapıldı ✔. |
| 63 | **Veri setinin büyük kısmı Google Street View ekran görüntüsü** (kenarlarda tarayıcı, görev çubuğu ve mini harita var). Bu görüntüler net ve bulanıklıksız; telefon kamerasının ön camdan çektiği görüntüye benzemiyor. Model tarayıcı arayüzü gibi alakasız ipuçlarını da öğrenebilir. | 🔧📏 | Eğitimde bulanıklık, renk ve parlaklık artırımları kullanılır. H4'te kendi telefon görüntülerimizden zor örnekler etiketlenip eğitime eklenir. Temiz testin yanında kendi videolarımızla ayrıca ölçüm yapılır. |
| 64 | *(Yaşandı)* `format=saved_model` ile çıkan `.tflite`, kutu koordinatlarını piksel olarak veriyor; okuyucular ise normalize koordinat bekliyor. Sonuç: mAP 0. | 🔧 | `scripts/export_tflite.py` ONNX çıkışına "xywh ÷ 640" ekleyip yeniden çeviriyor ✔. Temiz testte `.tflite` 0,897, `.pt` 0,896. Eklentinin normalize koordinatla doğru çizdiği Hafta 1'de telefonda doğrulanacak. |
| 65 | *(Yaşandı)* `resume` ile `time=` birlikte kullanılınca Ultralytics bitmiş epoch'ları saymıyor ve eğitimi hemen bitiriyor; öğrenme hızını düşürme aşaması atlanıyor. | 🔧 | Devam ederken `time` verilmiyor. Bitirme aşaması sabit epoch'lu ince ayar eğitimiyle (v2) yapıldı ✔: mAP50-95 0,716 → 0,732. |
| 66 | *(Yaşandı)* Windows'ta asıl sınır RAM değil **sanal bellek (commit)**: RAM + otomatik disk belleği dosyası, 24–40 GB arasında oynuyor. Eğitim (3 + 6 veri yükleyici işçisi) tek başına ~18–20 GB kullanıyor. Yanına torch/TensorFlow açan bir iş (TFLite dışa aktarma) başlatılınca v5 çöktü. | 🔧 | Eğitim sürerken başka ağır Python işi çalıştırılmıyor. `workers=2` ile ~3 GB tasarruf. Flutter derlemesinden kalan Gradle süreci (~3 GB) derlemeden sonra kapatılıyor. Disk belleği ayarına (sistem ayarı) dokunulmadı. |
| 67 | *(Yaşandı)* Release APK açılışta çöküyordu: R8 küçültmesi WorkManager'ın Room veritabanı sınıfını bozuyor ("Failed to create an instance of class androidx.work.impl.WorkDatabase"). | 🔧 | `mobile/android/app/build.gradle.kts`: `isMinifyEnabled = false`, `isShrinkResources = false`. Android 14 emülatöründe açıldı, model testi 11/11 ✔. APK biraz büyüdü; mağazaya çıkılırsa R8 için koruma kuralı yazılabilir. |
| 68 | Telefon yavaş çalışırsa (~5–6 FPS) "5 karenin 3'ü" oylaması 1 saniyeye yayılıyor; yol kenarındaki levha o kadar uzun büyük görünmediği için kaçırılıyor (10 videoda 42 levhadan 16'sı yakalandı). | 🔧📏 | 8 FPS altında oylama kendiliğinden "3 karenin 2'si" (`alerts.dart` `votingFor`): ~5 FPS'te 24 yakalanan / 5 yanlış uyarı. Telefonun gerçek FPS'i Hafta 1'de ölçülecek. |

---

## 5. Senin yapman gerekenler (bende yetki yok)

1. **Telefonu hazırla:** Ayarlar → Telefon hakkında → "MIUI sürümü"ne 7 kez dokun. Ardından Ek ayarlar → Geliştirici seçenekleri → **USB hata ayıklama** ve **USB üzerinden yükle** seçeneklerini aç. Telefonu USB ile bağla ve çıkan "Bu bilgisayara izin ver" sorusunu onayla.
2. **Veri setini indir:** Roboflow'da ücretsiz hesap aç. [Veri seti sayfasında](https://universe.roboflow.com/hootbu-vhtnl/traffic-sign-recognition-v2-turkiye) bir sürüm seç (sürüm sayfasında "Augmentations: none" olanı tercih et) → Download → **YOLOv11** formatı → zip. Zip'i `ml/data/raw/` içine koy; gerisini ben düzenlerim.
3. **Telefon tutucu** (vantuzlu, ön cama) temin et.
4. **Sesleri kaydet:** Bölüm 6'daki 20 cümleyi telefonla, sessiz bir odada kaydet; ya da sesleri TTS ile bir kere üretmeyi tercih edersen söyle.

---

## 6. Sınıflar, Türkçe uyarılar ve öncelikler

Öncelik: **1** = kritik, **2** = uyarı/yasak, **3** = bilgi

| Sınıf | Uyarı cümlesi | Öncelik |
|---|---|---|
| stop | "Dur" | 1 |
| noentry | "Girilmez" | 1 |
| giveway | "Yol ver" | 1 |
| schoolpassing | "Dikkat, okul geçidi" | 1 |
| pedestrian_risk | "Dikkat, yaya geçidi" | 1 |
| dangerousleft | "Sola tehlikeli viraj" | 2 |
| dangerousright | "Sağa tehlikeli viraj" | 2 |
| crossroads | "Kavşak yaklaşıyor" | 2 |
| caution | "Dikkat" | 2 |
| donotturnleft | "Sola dönülmez" | 2 |
| donotturnright | "Sağa dönülmez" | 2 |
| nouturn | "U dönüşü yasak" | 2 |
| keepleft | "Soldan gidiniz" | 2 |
| keepright | "Sağdan gidiniz" | 2 |
| speed30 | "Hız sınırı otuz" | 2 |
| speed50 | "Hız sınırı elli" | 2 |
| speed70 | "Hız sınırı yetmiş" | 2 |
| nostopping | "Duraklamak ve park etmek yasak" | 3 |
| priorityroad | "Ana yol" | 3 |
| pedestrian_info | "Yaya geçidi" | 3 |

---

## 7. Başarı ölçütleri (öneri §7'nin ölçülebilir hâli)

| Öneri maddesi | Ölçüt |
|---|---|
| 1. Kayıpsız dönüşüm | `.tflite` ile `.pt` arasındaki mAP50 farkı ≤ 2 puan; telefonda "desteklenmeyen operatör" hatası yok |
| 2. Gerçek zamanlı | Hedef cihazda ≥ 8 FPS (en az 5) |
| 3. Levhadan önce uyarı | Saha testinde algılanan levhaların ≥ %80'inde uyarı levha geçilmeden önce tamamlanıyor |
| 4. Tam çevrimdışı | Release APK uçak modunda bütün özellikleriyle çalışıyor |
