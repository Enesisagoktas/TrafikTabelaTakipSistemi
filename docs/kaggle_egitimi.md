# Kaggle'da v14 Eğitimi (7 Kasım 2026)

Amaç: daha çok Türk verisi ve daha çok ayrılan levha. v14, v13'ün 38 sınıfına 8 yeni sınıf ekler (46 sınıf) ve daha önce
kullanılmamış doğrulanmış Türk setlerini katar. Eğitim Kaggle GPU'sunda; video kapısı, dışa aktarma ve uygulama yine bilgisayarda.

## Yeni sınıflar ve yerel verideki örnek sayısı

Eski "diğer levha" kutularının bir kısmı artık kendi sınıfında. DFG kodları örnek kırpıntılarına bakılarak, Erzurum setindekiler
KGM adlarından eşlendi; böylece eski veriyle yeni sınıflar çelişmiyor.

| Sınıf | Levha | Yerel kutu (DFG + Erzurum + TTSD) |
|---|---|---|
| `speed20` | Azami hız 20 | 9 (asıl kaynak Kaggle'daki Robotaksi seti) |
| `park_yasak` | Park etmek yasaktır (tek çizgi) | 54 |
| `park_yeri` | Park yeri (P) | 243 |
| `ileri_mecburi` | İleri mecburi yön | 70 |
| `saga_mecburi` | Sağa mecburi yön | 115 |
| `sola_mecburi` | Sola mecburi yön | 38 |
| `ileri_saga` | İleri veya sağa mecburi yön | 154 |
| `ileri_sola` | İleri veya sola mecburi yön | 603 |

`ileri_saga` ve `ileri_sola` uygulamanın kataloğunda zaten sesli; öteki 6 sınıf için `alerts.dart`'a ses eklenecek.
Ana yol–tali yol kavşağı, v9'daki Erzurum eşlemesiyle tutarlı olsun diye `crossroads` sayıldı.

## Veri

- **Yerelde hazırlanan (pakette):** train_v14 18.421 görsel = v13 verisi (DFG ve Erzurum seti v14 sınıflarıyla yeniden
  etiketli) + **TTSD** 1.617 görsel. TTSD'de "Yaya Gecidi" hem mavi kareyi hem üçgeni kapsıyordu: kutuda kırmızı kenar varsa
  `pedestrian_risk`, yoksa `pedestrian_info` (`ek_veri.py` `YAYA_RENK`; 525 kutunun pafta denetiminde 1 hata). Val (494) ve temiz
  test (308) değişmedi, yalnız DFG kutuları yeni sınıflarla.
- **Kaggle'da eklenen:** [Traffic Signs in Türkiye](https://www.kaggle.com/datasets/nezahatkk/traffic-signs-in-turkiye)
  (Kaggle'ın en çok indirilen Türk tespit seti, Apache 2.0, ~16 bin görsel, 24 sınıf, Robotaksi tipi). İsteğe bağlı, kullanıcının
  Roboflow anahtarıyla: Hootbu 17 sınıf (7.479), Hootbu "Traffic Sign Recognition 2" (1.563), ETÜ (1.211). Hepsi CC BY 4.0.
- **Eşleme:** Kaggle'daki setlerin sınıf adları önceden bilinmediği için kural tabanlı (`scripts/oto_esleme.py`; Erzurum ve TTSD'nin
  elle eşlemesini birebir veriyor). Tanınmayan sınıfı içeren görsel alınmaz; trafik ışığı, duba gibi levha olmayan kutular atılır.
  `ek_veri.py` bizim valid/test'e benzeyen görselleri (phash <= 12) atar; defter yeni setlerin bizim train'in ve birbirinin
  kopyası olan görsellerini (phash <= 4) de atar.

## Kaggle adımları

1. `ml/data/kaggle_yukle/trafik_levha_v14_kaggle.zip` dosyasını Kaggle → Datasets → New Dataset ile yükle, Private bırak.
2. File → Import Notebook → `ml/kaggle/egitim.ipynb`.
3. Input → Add Input: kendi veri setin ve `nezahatkk/traffic-signs-in-turkiye`.
4. Settings: Accelerator GPU P100 (ya da T4), Internet açık. Kaggle bunun için telefon doğrulaması ister.
5. İsteğe bağlı: Add-ons → Secrets → `ROBOFLOW_API_KEY`. Anahtar yalnız Kaggle'da kalır, defter yazdırmaz.
6. Save Version → Save & Run All. En çok 12 saat; 10,5 saatte eğitim kendiliğinden bitirilir. Sonuç: Output → `cikti.zip`
   (v14.pt, val/test mAP ve sınıf AP'leri, sınıf sayımı, eşleme raporu, her yeni set için sınıf paftası).

Eğitim tarifi v9 ile aynı: v13 ağırlığından, AdamW lr0 0,0003, 60 epoch, imgsz 640, fliplr 0. Batch 32 (P100 16 GB).

## Sonra (bilgisayarda)

1. `cikti.zip` içindeki paftalara bak: Kaggle setlerinin eşlemesi doğru mu.
2. `v14.pt` → `ml/runs/detect/v14/weights/`; 10 video kapısı (`analiz.py kurallar`), temiz test, `export_tflite.py`.
3. Uygulama: 46 sınıf; 6 yeni sesli levha (`alerts.dart`, `tool/sesleri_uret.ps1`), testlerdeki sınıf sayısı.

## Çekinceler

- Robotaksi tipi set yarışma pistinde çekilmiş olabilir; yol görüntüsünden farklı. Paftalar ve val sonucu gösterir.
- Sözde etiketli eski karelerdeki (Amasra, Pexels, yeni videolar) "diğer" kutuları yeni sınıflardan levhalar içerebilir.
- TTSD'nin lisansı yazılı değil: yalnız akademik kullanım, makaleye atıf (aşağıda). Model zaten DFG yüzünden ticari değil.

## Atıf

- TTSD / NAVIGATR: E. Tuna, K. Özacar, "Detecting and Recognizing Turkish Traffic Signs Using a New Dataset Based on Deep
  Learning", Current Trends in Computing 1(1):44–53, 2024; veri: https://github.com/erdituna/TurkeyTrafficSignDataSet (test bölümü;
  train görselleri depoda yok).
- Traffic Signs in Türkiye, nezahatkk, Kaggle, Apache 2.0.
- Roboflow Universe: Hootbu "Traffic Signs Recognition" ve "Traffic Sign Recognition 2"; ETU Veri Kumesi "ETÜ Trafik Levhaları
  Veri Kümesi"; CC BY 4.0.
