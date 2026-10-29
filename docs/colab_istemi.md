# Colab istemi: v6 eğitimi (21. sınıf diger_levha, Türk verisi)

Colab'daki Claude'a olduğu gibi yapıştırılır (29 Ekim 2026). Önce: Drive'da `levha_colab/` klasörüne `ml/data/colab_yukle/` içindeki üç zip yüklenir; Colab Secrets'a `GH_TOKEN` (depoya erişen GitHub anahtarı) ve `ROBOFLOW_API_KEY` girilir; çalışma zamanı GPU seçilir.

---

Merhaba Claude. Google Colab'da öğrenci projemin trafik levhası modelini yeniden eğiteceğiz. Benimle Türkçe, kısa ve samimi konuş; her adımdan sonra ne yaptığını ve sonucu söyle. Geri dönüşü zor ya da benim kararım olan şeylerde önce bana sor: veri setinin şartlarını kabul etmek, büyük indirme, Drive'da silme, GitHub'a push. Çıktı uydurma; beklenmedik bir şey çıkarsa göster.

## Proje
- Telefonda (Android, Flutter + resmi `ultralytics_yolo` eklentisi) çevrimdışı Türk trafik levhası tespiti ve Türkçe sesli uyarı. Hedef telefon Redmi Note 8 sınıfı; model YOLO11n (nano), imgsz 640 kalacak.
- Kod özel GitHub deposunda: `Enesisagoktas/TrafikTabelaTakipSistemi` (dal `main`). Bu istem `docs/colab_istemi.md`'de de var. Yöntem ve sonuçlar: `docs/YOL_HARITASI.md` ("Canlı demo" bölümü) ve `docs/video_testi.md`; eski eğitim komutları: `docs/KURULUM.md`.
- Şu anki model v5b, 20 sınıf, bu sırayla (indeksler korunacak): caution, crossroads, dangerousleft, dangerousright, donotturnleft, donotturnright, giveway, keepleft, keepright, noentry, nostopping, nouturn, pedestrian_info, pedestrian_risk, priorityroad, schoolpassing, speed30, speed50, speed70, stop. Ağırlıkları depoda: `desktop/levha.pt`.

## Sorun (29 Ekim, gerçek sürüş videosunda canlı demo)
1. Yanlış uyarı: Ankara videosundaki 13 yanlış uyarının 12'si 20 sınıfın dışındaki levhalardan geliyor. S-viraj, taş düşebilir ve iki yönlü trafik → "kavşak"; kırmızı-beyaz viraj okları → "dikkat" ya da "tehlikeli viraj"; sarı zeminli yol çalışması ve kasis üçgenleri → "hız 30". Model bilmediği levhayı en çok benzeyen bildiği sınıfa zorluyor.
2. Gecikme: uzaktaki levhada güven düşük. Hız 70 levhası %2,6 boydayken güven 0,31; 0,7'yi ancak %5,5 boyda geçti. Boy sınırını düşürmek çözüm değil: yanlış uyarı 18 → 36.
3. Aynı anda birkaç levha gelince seslerin sıraya girmesi uygulamanın işi; ona dokunma.

## Hedef: v6
- 21. sınıf `diger_levha` (indeks 20): 20 sınıfımızın dışındaki her trafik levhası (uyarı üçgenleri, yasak ve bilgi levhaları, viraj ve şerit okları, sarı yol çalışması levhaları, kasis vb.). Uygulama bu sınıfı tespit eder ama seslendirmez; `desktop/app.py` onu zaten yok sayıyor. Reklam ve dükkân tabelaları ile şehir isimli büyük yön tabelaları etiketsiz (arka plan) kalsın.
- Türk levhası şart (proje şartı). Yabancı veri (DFG vb.) kullanmadan önce bana sor.

## 1. Kurulum
1. Çalışma zamanı GPU olsun (`!nvidia-smi`).
2. Drive'ı bağla. `Drive'ım/levha_colab/` klasörüne şunları yükledim:
   - `levha640.zip` (1,2 GB): 640 px eğitim seti.
     - `levha640/train`: bizim Türk verimiz (Roboflow Universe "Hootbu" Traffic-Sign-Recognition-V2-Turkiye, CC BY 4.0). Yalnız 20 sınıf etiketli.
     - `ek/negatif`: 415 arka plan kırpıntısı.
     - `ek/dfg`: 6.733 Slovenya DFG görüntüsü (CC BY-NC-SA 4.0). 19 sınıf eşli, öteki levhalar etiketsiz.
     - `val_temiz.txt` / `test_temiz.txt`: temiz doğrulama ve test (296 / 308 görsel).
     - Ayrıca `data_temiz.yaml`, `data_v5.yaml`, `train_birlesik.txt`.
   - `videolar.zip` (1,3 GB): 10 açık lisanslı sürüş videosunun 1280 px kopyaları.
   - `dfg_etiketler.zip` (1 MB): DFG'nin 200 sınıflı bütün etiketleri. `dis/dfg/stage/labels/<ad>.txt` dosyası `ek/dfg/images/dfg_<ad>.jpg` görseline karşılık gelir; koordinatlar aynı (normalize).
3. Depoyu klonla. GitHub anahtarım Colab Secrets'ta `GH_TOKEN` adıyla; anahtarı asla yazdırma:
   ```python
   from google.colab import userdata
   import subprocess
   url = f"https://x-access-token:{userdata.get('GH_TOKEN')}@github.com/Enesisagoktas/TrafikTabelaTakipSistemi.git"
   subprocess.run(["git", "clone", "-q", url, "/content/proje"], check=True)
   subprocess.run(["git", "-C", "/content/proje", "remote", "set-url", "origin", "https://github.com/Enesisagoktas/TrafikTabelaTakipSistemi.git"], check=True)
   ```
4. Zip'leri Drive'dan okuma, yerel diske aç: üçünü de `/content/proje/ml/data/` içine çıkar (`levha640/`, `videolar/kucuk/` ve `dis/dfg/stage/` oluşur). Sonra `yolo settings datasets_dir=/content/proje/ml/data` çalıştır; yaml'lardaki `path: levha640` buna göre çözülür.
5. `pip install ultralytics==8.4.191 imagehash==4.3.2` (bizdeki sürüm). TFLite dışa aktarma paketlerinin sürümleri `ml/requirements.txt`'te.

## 2. Veri
1. Yeni Türk veri setleri bul. Roboflow Universe ve Kaggle'da Türk trafik levhası TESPİT setleri ara: tam sahne + kutu olsun, sınıflandırma kırpıntısı olmasın.
   - En değerlileri, 20 sınıfımızın dışındaki levhaları da etiketleyenler: taş düşebilir, S-viraj, iki yönlü trafik, kaygan yol, yol çalışması, kasis, hız 40/60/80/90, sollama yasağı, park, şerit okları… Gerçek araç kamerası görüntüleri de değerli.
   - Her aday için ad, bağlantı, lisans, görsel sayısı ve sınıf listesini bir tabloda göster; indirmeden önce onayımı al.
   - İnternette arayamıyorsan söyle, bağlantıları ben veririm.
   - Roboflow API anahtarım Secrets'ta `ROBOFLOW_API_KEY` adıyla. `roboflow` paketiyle YOLO biçiminde indir; anahtarı yazdırma.
2. Eşleme: yeni setlerin sınıflarını 20 sınıfımıza eşle.
   - Ada değil görsele bak: her sınıftan birkaç kırpıntı göster ve kontrol et.
   - Geri kalan trafik levhası sınıfları → `diger_levha`. Levha olmayan sınıfları (trafik ışığı, araç, yaya) at.
   - `ml/scripts/ek_veri.py` eşleme, 640 px küçültme ve test sızıntısı denetimini (phash) yapıyor, ama şu an eşlenmeyen kutuyu atıyor. Ona "geri kalan levhalar diger_levha" seçeneği ekle ya da eşleme json'unda bunu açıkça yaz. Eşleme json'larını `ml/scripts/` altına kaydet.
3. Çelişkiye dikkat: aynı tür levha bir yerde `diger_levha`, başka yerde arka plan olarak görünürse model bozulur.
   - `ek/dfg` şu hâliyle diğer levhaları etiketsiz tutuyor. DFG'yi kullanacaksak (önce bana sor) etiketlerini `dfg_etiketler.zip`'ten yeniden üret:
     - `ml/scripts/esleme_dfg.json`'daki 23 sınıf → bizim sınıflar;
     - geri kalan sınıflar → `diger_levha`.
     - `III-29-30`, `III-29-40` ve `III-30-30` içeren görseller zaten çıkarılmıştı.
   - DFG'yi kullanmayacaksak eğitim listesinden çıkar.
   - Bizim train görsellerinde ve `ek/negatif` kırpıntılarında etiketsiz başka levhalar olabilir. İlk v6'dan sonra v6'yı train görsellerinde çalıştır ve güveni ≥ 0,5 olan `diger_levha` tespitlerinden örnekler göster. Mantıklıysa bunları sözde etiket olarak ekleyip bir tur daha eğit. Negatif kırpıntılardan levha içerenlere de `diger_levha` etiketi ver.
4. Test temiz kalmalı: `val_temiz.txt`, `test_temiz.txt` ve 10 test videosu eğitime asla girmez. 21 sınıflı yeni bir data yaml yaz: ilk 20 isim aynı sırayla, sonra `diger_levha`.

## 3. Eğitim
- `desktop/levha.pt`'den (v5b) başla. 21 sınıflı yaml verilince Ultralytics baş katmanını yeniden kurar, gövdeyi aktarır.
- v5b'nin ayarları: `imgsz=640 optimizer=AdamW lr0=0.0004 warmup_epochs=1 warmup_bias_lr=0 close_mosaic=10 fliplr=0 mixup=0`.
  - **fliplr=0 şart:** yatay aynalama "sağdan gidiniz"i "soldan gidiniz"e, sağa virajı sola viraja çevirir.
  - Yeni sınıf ve veri olduğu için ~100 epoch ve `patience=30` kullan; batch'i GPU'ya göre seç.
- Çıktıları Drive'a yaz (`project=/content/drive/MyDrive/levha_colab/runs name=v6`). Oturum düşerse `resume` ile devam et; `resume` ile `time=` verme.
- Eğitim bitince temiz testte 20 sınıfın mAP50 / mAP50-95 değerlerini v5b ile karşılaştır (v5b test: 0,894 / 0,725). `diger_levha` test setimizde etiketli değil; onun puanına bakma.

## 4. Asıl ölçü: gerçek sürüş videoları
- Gerçek durum depoda: `ml/degerlendirme/video_gercek_durum.json`. Log adı model dosyasının adından gelir. `desktop/levha.pt`'yi `v5b.pt`, yeni modeli `v6.pt` diye kopyala; sonra iki model için de şunu çalıştır:
  ```bash
  cd /content/proje
  for v in ml/data/videolar/kucuk/*.avi; do python desktop/app.py "$v" v6.pt --sessiz; done
  mv ml/data/videolar/kucuk/*.v6.log.csv ml/data/videolar/
  cd ml && python scripts/video_degerlendir.py v6 && python scripts/analiz.py kurallar --etiket v6
  ```
- `video_degerlendir.py`: 42 gerçek levha olayında yakalanan (zamanında) / yanlış uyarı sayısı.
- `analiz.py kurallar`: ilk satır şimdiki kural (30 FPS ve ~10 FPS). Ayrıntı için: `python scripts/analiz.py uyarilar ankara_corum_iskilip --etiket v6 --yanlis`.
- v5b: 30 FPS'te 32 (26) / 18; ~10 FPS'te 27 (23) / 6. Hedef: daha az yanlış uyarı, en az aynı yakalama. Kurallar bu 10 videoda seçildi ve gürültü büyük (aynı model, videonun farklı ölçekteki kopyasında 8 farklı yanlış uyarı verdi); küçük farkları abartma.

## 5. Dışa aktarma ve teslim
- Telefon: `cd ml && python scripts/export_tflite.py <v6 best.pt yolu>` çalıştır; çıktı `best_tflite/best_float16.tflite`.
  - Düz `yolo export format=tflite` KULLANMA: eklenti 0..1 aralığında normalize kutu bekliyor ve betik bu adımı ekliyor. O adım olmazsa mAP 0 çıkar.
  - Eksik paket kurulurken süreç çökerse komutu bir kez daha çalıştır.
  - `.tflite`'ı temiz testte doğrula; sonuç .pt'ye yakın olmalı (v5b: .pt 0,894 / 0,725, FP16 0,892 / 0,727).
- Masaüstü: `best.pt`, ayrıca `yolo export format=onnx imgsz=640` ile `best.onnx`.
- Drive'da `levha_colab/v6_teslim/` klasörüne şunları koy:
  - `best.pt`, `best.onnx`, `best_float16.tflite`, `results.csv`
  - karışıklık matrisi ve video sonuçları
  - kısa bir Türkçe rapor: ne değişti, sayılar, v5b ile karşılaştırma, kullanılan veri setleri (ad, sahibi, lisans, bağlantı) ve sınırlar.
- Kod değişikliklerini (betikler, eşleme json'ları) commit'le; veri ve ağırlık dosyalarını commit'leme. Push'tan önce bana sor; gerekirse aynı `GH_TOKEN` ile, anahtarı yazdırmadan push et.
- Telefon uygulamasındaki değişiklikleri sonra bilgisayarda yapacağız (`diger_levha`'yı seslendirmemek, `alerts.dart`, APK); onlara dokunma.
