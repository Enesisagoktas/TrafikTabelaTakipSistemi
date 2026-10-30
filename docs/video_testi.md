# Video Testi: Gerçek Sürüş Videolarında Uçtan Uca Deneme (29 Ekim 2026)

## Neden
Test setindeki puan (mAP) tek tek fotoğraflarda ölçülür. Uygulama ise videoda kare kare çalışır:
kare oylaması, aynı levha için bekleme süresi ve tek seferde tek ses kuralı da işin içindedir.
Gerçek hayattaki asıl sorun da test setinde pek görünmüyor: **levha olmayan şeye uyarı vermek** (halüsinasyon).

## Nasıl ölçüldü
1. **Videolar:** 10 açık lisanslı araç içi video, toplam yaklaşık 9 dakika (`docs/test_videolari.md`).
2. **Gerçek durum:** her saniyeden 1 kare çıkarıldı (530 kare, `ml/scripts/kare_cikar.py`). İki bağımsız inceleyici
   (yapay zekâ alt ajanları) her karedeki levhaları ayrı ayrı yazdı. Bir levha, **ikisi de "net" dediyse** sayıldı
   (`ml/degerlendirme/video_gercek_durum.json`). Aynı levhanın art arda (arada en fazla 1 sn boşluk olan)
   saniyeleri tek "olay" sayıldı: toplam **42 olay**.
3. **Uygulama:** telefondaki kurallar bilgisayarda aynen çalıştırıldı (`desktop/app.py video --sessiz`). Model aynı;
   eşik 0,25 ve sınıftan bağımsız NMS telefondaki eklentiyle aynı. Her kare, kutusu ve yüksekliğiyle birlikte loglandı.
   Bütün modeller aynı videoların 1280 px kopyalarında çalıştırıldı (`ml/scripts/video_kucult.py`).
4. **Puanlama** (`ml/scripts/video_degerlendir.py`):
   - **Yakalandı:** levha görünürken (1 sn önce ile 2 sn sonra arası) aynı sınıf için uyarı geldi.
   - **Zamanında:** uyarı, levhanın net göründüğü son saniyeden en geç 0,5 sn sonra geldi (kareler saniyede bir
     alındığı için yarım saniye pay).
   - **Yanlış uyarı:** hiçbir gerçek levhaya denk gelmeyen uyarı.
5. **Kural taraması** (`ml/scripts/esik_tarama.py <model> <kare_adımı>`): model yeniden çalıştırılmadan, loglar farklı
   kural ayarlarıyla yeniden oynatıldı (güven eşiği, en küçük kutu yüksekliği, oylama 5'te 3 / 5'te 4 / 7'de 5 / 3'te 2).
   Telefon videodan yavaş çalışacağı için her şey **her karede** ("30 FPS") ve **her 3. karede** ("~10 FPS") ayrı ayrı
   ölçüldü; oylama için her 4., 5. ve 6. karede de (~7,5, ~6, ~5 FPS). Videoların 7'si 30 FPS, 2'si 60, 1'i 25 FPS.
   Kare adımı sabit olduğu için o üç videoda FPS etiketi 2 kat ya da 0,83 kat (42 olayın 3'ü bu videolarda). Adım her
   videonun kendi FPS'ine göre seçilince sayılar en çok 2 değişiyor, sonuçlar aynı kalıyor.
   Tablolardaki bütün sayılar bu yeniden oynatmadan. Uygulamanın kendi çalıştırması, log saatleri 0,01 sn'ye
   yuvarlandığı için ±2 uyarı farklı çıkabiliyor (ör. v4, güven 0,6: oynatmada 27, uygulamada 25 yanlış uyarı).

Düzeltme: bizim `crossroads` sınıfı bütün "ana yol - tali yol kavşağı" üçgenlerini kapsıyor (T, kademeli, Y birleşme).
Bu, eğitim etiketlerine bakılarak doğrulandı. İnceleyicilere yalnızca "+" şekli anlatılmıştı, bu yüzden notlarında
"kavşak" geçen üçgenler crossroads sayıldı.

## Sonuçlar (42 gerçek levha olayı)
Kurallar: güven eşiği / en küçük kutu (görüntü yüksekliğine oranla). Oylama hepsinde 5 karenin 3'ü.
"0,5 / %2,5" gece çalışmasından önceki uygulamanın ayarı.

| Model | Kurallar | 30 FPS: yakalanan (zamanında) / yanlış uyarı | ~10 FPS: yakalanan (zamanında) / yanlış uyarı |
|---|---|---|---|
| v2 | 0,5 / %2,5 (eski) | 25 (16) / 59 | 20 (18) / 38 |
| v2 | 0,6 / %5 | 30 (20) / 28 | 21 (18) / 13 |
| v2 | 0,7 / %5 | 27 (20) / 26 | 20 (18) / 8 |
| v4 | 0,5 / %2,5 | 26 (20) / 63 | 27 (20) / 42 |
| v4 | 0,6 / %5 | 28 (22) / 27 | 26 (22) / 17 |
| v4 | 0,7 / %5 | 29 (23) / 19 | 26 (22) / 12 |
| v5b | 0,5 / %2,5 | 27 (19) / 58 | 31 (23) / 35 |
| v5b | 0,6 / %5 | 30 (23) / 23 | 27 (23) / 10 |
| **v5b** | **0,7 / %5 (şimdiki)** | **32 (26) / 18** | **27 (23) / 6** |

1. **En büyük kazanç kuraldan geldi.** Uzak (görüntü yüksekliğinin %5'inden küçük) kutuları saymamak, aynı güven
   eşiğinde (0,5) üç modelde de yanlış uyarıyı yaklaşık yarıya indirdi (%47–69 azalma). 30 FPS'te yakalanan levha
   arttı: yanlış uyarılar ses sırasını işgal etmeyince doğru uyarılar zamanında çalabiliyor. ~10 FPS'te v5b'de
   yakalanan 31'den 27'ye düştü, zamanında gelenler aynı kaldı (23).
2. **Güven 0,6 → 0,7** üç modelde ve iki FPS'te yanlış uyarıyı azalttı. Yakalanan levha yalnızca v2'de azaldı
   (30 FPS'te 30 → 27, ~10 FPS'te 21 → 20); v4 ve v5b'de aynı kaldı ya da arttı.
3. **Model: v5b.** Aynı kurallarla en çok levhayı yakalayan ve en az yanlış uyarı veren model. v2'ye göre farkın asıl
   kısmı yakalamada: 0,7 ile 30 FPS'te zamanında uyarı 20 → 26, ~10 FPS'te yakalanan 20 → 27. Bu yakalama kazancının
   çoğu v4'te de var (~10 FPS'te 26; uzun eğitim). DFG verisinin katkısı (v4 → v5b): ~10 FPS'te yanlış uyarı yarıya
   indi (12 → 6), 30 FPS'te zamanında uyarı 23 → 26 oldu; 30 FPS'te yanlış uyarı neredeyse aynı kaldı (19 → 18).
4. **Gürültü büyük.** Aynı v2 modeli, aynı kurallarla (0,6 / %5) orijinal videolarda 30 FPS'te 20, 1280 px
   kopyalarda 28 yanlış uyarı verdi (~10 FPS'te 11 ve 13). Yani 30 FPS'te birkaç uyarılık fark anlamlı değil.
   v5b'nin yanlış uyarıdaki üstünlüğü bu yüzden temkinli okunmalı. Yakalamadaki fark (~10 FPS'te 27'ye 20) daha sağlam.

Gece çalışmasının net etkisi (eski uygulama v2 + 0,5 / %2,5 → yeni uygulama v5b + 0,7 / %5):
30 FPS'te **25 (16) / 59 → 32 (26) / 18**, ~10 FPS'te **20 (18) / 38 → 27 (23) / 6**.

## Yavaş telefon: oylama FPS'e göre
"5 karenin 3'ü" yavaş telefonda uzun sürer: 5 FPS'te 5 kare 1 saniye demek. Levha o kadar uzun büyük görünmediği için
kaçırılıyor. v5b, güven 0,7, en küçük kutu %5:

| Telefon hızı | 5 karenin 3'ü | 3 karenin 2'si |
|---|---|---|
| ~10 FPS | **27 (23) / 6** | 30 (24) / 13 |
| ~7,5 FPS | 24 (20) / 3 | **28 (25) / 6** |
| ~6 FPS | 18 (16) / 4 | **25 (22) / 8** |
| ~5 FPS | 16 (15) / 3 | **24 (21) / 5** |

v2 ve v4'te de aynı tablo çıktı (ör. ~5 FPS'te v4: 16 (15) / 6 → 24 (20) / 12).
**Karar:** telefon son 10 saniyede saniyede 8 kareden az işlediyse oylama kendiliğinden "3 karenin 2'si" oluyor
(`mobile/lib/alerts.dart` `votingFor`; hız, işlenen kare sayısından ölçülüyor). Kayıtlar'a "AYAR · Oylama 2/3 (ortalama … FPS)" satırı düşüyor, Sürüş
ekranının altında da "oylama 2/3" yazıyor. Emülatörde (~2,5 FPS) bu geçiş görüldü. Bilgisayar uygulaması en az ~21 FPS
(GPU'da ~63) çalıştığı için hep 5 karenin 3'ünü kullanıyor.

## v6 (29 Ekim gecesi): 21. sınıf "diğer levha", yalnız Türk verisi

Aynı 10 video, aynı kurallar (güven 0,7, boy ≥ %5, 5 karenin 3'ü), aynı 1280 px kopyalar:

| Model | 30 FPS: yakalanan (zamanında) / yanlış uyarı | ~10 FPS |
|---|---|---|
| v5b (DFG'li) | 32 (26) / 18 | 27 (23) / 6 |
| v6 (DFG yok, + trafik levhaları seti, 21 sınıf) | 32 (26) / **14** | 28 (23) / **9** |
| v7 (v6 + 8 yeni sesli sınıf: kasis, durak, demiryolu…; 29 sınıf, 112 epoch) | 29 (23) / 20 | 25 (19) / 10 |
| **v8** (v6 + DFG'nin öteki levhaları "bilinmeyen levha" olarak; 21 sınıf, 31 epoch) | 32 (**28**) / **14** | 27 (23) / 10 |

v7 (30 Ekim gecesi) daha kötü: yakalama düştü, yanlış uyarı arttı; 8 yeni sınıfın hiçbiri 10 videoda 0,5 güvenle tek
tespit vermedi (tek kaynak: Erzurum seti). Uygulamada v6 kaldı.

**v8 (30 Ekim öğle, uygulamada):** DFG'nin 20 sınıfımıza eşlenmeyen 174 sınıfı (13.572 kutu) `diger_levha` olarak geri
alındı; sesli 20 sınıf yine Türk verisinden. Uyarı sayıları v6 ile aynı (30 FPS'te 2 uyarı daha zamanında; ~10 FPS'te
1 yakalama eksik, 1 yanlış fazla — tek olay, gürültü sınırında). Asıl kazanç "bilinmeyen levha": v6'da 10 videoda
toplam 15 tespit verirken v8'de 9 videoda 1.122 kare. İnceleyicilerin "sınıf dışı levha" yazdığı 356 saniyenin
222'sinde (%62) bilinmeyen tespiti var; bilinmeyen tespiti olan 133 saniyenin 129'u (%97) böyle bir nota denk geliyor.
Yani ekranda "Bilinmeyen levha" şeridi artık gerçekten çalışıyor. Temiz test .pt 0,887 / 0,716, FP16 tflite 0,888 / 0,721
(v6 ile aynı).
DFG CC BY-NC-SA olduğu için ticari olmayan kullanım notu README'ye ve uygulamaya geri geldi.

**Sarı zemin kuralı (30 Ekim sabahı, v6):** tespit kutusundaki sarı piksel oranı loga eklendi (`sari` sütunu) ve
"oran ≥ eşik ise yok say" kuralı tarandı. 30 FPS'te yanlış uyarı 14 → 13 (eşik 0,3/0,4), 0,2'de yakalama 32 → 30.
İşe yaramadı: yol çalışması bölgesinde gerçek geçici hız levhaları da sarı zeminli (Ankara 140–290 sn; doğru hız 50
uyarılarının sarı oranı 0,3–0,5). Kural kapalı, ölçüm sütunu duruyor.

Yakalama aynı; 30 FPS'te yanlış uyarı azaldı, ~10 FPS'te arttı. "Diğer levha" sınıfı yalnızca Bilecik (14) ve Ankara (1)
videolarında tespit verdi; öteki 8 videoda ve bizim eğitim görsellerinde hiç. Ayrıntı ve karar: `docs/YOL_HARITASI.md`
(v6 bölümü). Komutlar: `docs/KURULUM.md`.

## Tek kare test seti (temiz test, 308 fotoğraf, 435 levha)
| Model | mAP50 | mAP50-95 | Güven 0,7 ile: kesinlik | Yakalama (kutu ≥ %5, 285 levha) | 100 fotoğrafta yanlış alarm |
|---|---|---|---|---|---|
| v2 | 0,896 | 0,726 | 0,948 | 0,891 | 4,5 |
| v4 | 0,895 | 0,728 | 0,930 | 0,888 | 6,2 |
| v5b | 0,894 | 0,725 | 0,927 | 0,884 | 6,5 |
| v5b, telefondaki FP16 `.tflite` | 0,892 | 0,727 | | | |

Validasyon mAP50-95: v2 0,732, v4 0,743, v5b 0,744. Üç model test setinde aynı seviyede. Tek kare yanlış alarmda
v2 biraz önde (308 fotoğrafta 14'e 20); farkın yarısı (6'nın 3'ü) v5b'nin yaya geçidi bilgi levhası hataları (8'e 5),
kalanı çoğunlukla hız 30 (3'e 1) ve girilmez (2'ye 0).
Seçim videoya göre yapıldı, çünkü uygulama videoda çalışıyor ve oylama tek karelik hataların çoğunu eliyor.
`.tflite` (FP16) `.pt` ile aynı puanı alıyor; uygulamaya gömülü 11 test fotoğrafında bilgisayarda ve emülatörde 11/11.

## Kalan hatalar (v5b, güven 0,7, en küçük kutu %5)
**30 FPS'te 18 yanlış uyarı.** 2'si büyük ihtimalle gerçek uzak levha (inceleyicilerden biri görmüş). Kalan 16'nın
kaynakları:
- Uzaktaki sarı zeminli yol çalışması levhaları: 4.
- Başka uyarı üçgenleri (çift viraj, kasis, düşen kaya, okunamayan uzak üçgen): 4.
- Kırmızı-beyaz ikaz direkleri ve viraj okları: 2.
- Reklam panosu ve dükkân tabelası: 2.
- Uzak, tanınamayan küçük levhalar: 2.
- Şerit gösteren mavi levha: 1.
- 4.80 m yükseklik sınırı: 1.

Sınıf olarak en çok **hız 30** (5 uyarı) yanlış çıkıyor.

**~10 FPS'te 6 yanlış uyarı.** 2'si büyük ihtimalle gerçek. Kalan 4'ü: çift viraj üçgeni, uzak küçük levha, mavi
şerit levhası ve uzak sarı levha.

**Kaçırmalar** (30 FPS'te 10, ~10 FPS'te 15): en büyük grup Ankara videosundaki **hız 50** levhaları (30 FPS'te 4,
~10 FPS'te 8). Bunlar yol kenarında bir saniyeden kısa net görünüyor. Ankara'da yan yoldaki **dur** levhası da kaçtı
(209. sn; ~10 FPS'te 194. sn'deki de); kaçırılan tek öncelik-1 levha türü bu. Diğerleri (iki FPS'te de aynı 5 levha):
dikey çekilmiş Bilecik videosundaki küçük yaya geçidi levhası, Fethiye'de bir hız 50 ile bir kavşak, İstanbul'da bir
hız 30 ve tünel içindeki "soldan gidiniz".

DFG verisinin etkisi (v4 → v5b, ikisi de 0,7 / %5): 30 FPS'te yanlış uyarı neredeyse aynı kaldı (19 → 18), zamanında
uyarı arttı (23 → 26); ~10 FPS'te yanlış uyarı yarıya indi (12 → 6), yakalanan neredeyse aynı (26 → 27). Kalanlar
için en etkili adım, kendi telefon videolarımızdan bu tür levhaları "levha değil" diye eklemek (Hafta 4).

## Sınırlar
- Kurallar (en küçük kutu %5, güven 0,7, FPS'e göre oylama) aynı 10 videoda seçildi, bu yüzden sonuçlar iyimser.
  Kaba adımlar seçildi ve her biri üç modelde, birden fazla FPS'te aynı yönde sonuç verdi. Asıl karar gerçek yol
  testinde verilecek (`docs/saha_testi.md`).
- 42 olay az; sınıf bazında sonuç çıkarmak için yetmez. Videonun ölçeği bile 30 FPS'te yanlış uyarı sayısını 8
  değiştirebiliyor (yukarıda madde 4).
- Telefonun görüş açısı araç kameralarından dardır. Aynı levha telefonda daha büyük görünür, yani %5 sınırına
  daha uzaktan ulaşılır.
- Telefonun gerçek FPS'i henüz ölçülmedi. ~5 FPS'te en iyi ayarla bile 42 levhanın 24'ü yakalanıyor.
