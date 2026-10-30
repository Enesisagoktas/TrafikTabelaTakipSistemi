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
| v9 (v8 + 17 yeni sesli sınıf DFG + Erzurum'dan; 38 sınıf, 47 epoch) | 31 (27) / 19 (+4 yeni sınıf doğru) | 26 (23) / 10 |
| v10 (v9 + 116 gözle denetlenmiş Türk karesi; 38 sınıf, 15 epoch) | 31 (25) / 21 (+8 yeni sınıf doğru) | 27 (24) / 10 |
| v11 (v9'dan sınıf ağırlıklı devam, cls_pw 0,5, yeni sınıflı val; 38 sınıf, 30 epoch) | 31 (27) / 18 (+3 yeni sınıf doğru) | 27 (23) / 9 |
| **v9 + 5 sınıfta 0,8 güven tabanı (uygulamada, 30 Ekim gece)** | 32 (27) / **11** (+4 yeni sınıf doğru) | 26 (23) / **7** |
| v8 + aynı taban (karşılaştırma) | 32 (28) / 11 | 27 (23) / 10 |

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

**v9 (30 Ekim akşam, uygulamaya alınmadı):** v8 + 17 yeni sesli sınıf (kasis, durak, demiryolu, ada etrafında, ışıklı
işaret, keskin viraj, devamlı viraj, sollama yasak, düşen kaya, hayvan, daralan yol, eğim, hız 40/60, hız sonu, yol
çalışması, kaygan yol); örnekler DFG (çok yol/hava) + Erzurum seti; 38 sınıf, 14.503 görsel. v8'den 60 epoch planlandı,
47'de erken durdu (en iyi 27.), val 0,889 / 0,728; temiz test .pt 0,884 / 0,719 (v8 ile aynı). Videoda 30 FPS'te
31 (27) / 19, ~10 FPS'te 26 (23) / 10. Yeni sınıflardan 4 doğru uyarı çıktı (hepsi keskin viraj: İstanbul 1, sürücü
koltuğu 3; inceleyici notlarıyla eşleşti), ~10 FPS'te 0. Ama 20 temel sınıfta yanlış uyarı 14 → 19: 3 yeni speed30
(Ankara 208, 276, 282 sn: uzak üçgen, sarı yol çalışması karesi, küçük sarı yuvarlak), düşen kaya üçgenine "sağa
tehlikeli viraj" (Zonguldak 1,6 sn), 4,80 m yükseklik levhasına "yaya geçidi" (minibüs 9,8 sn), iki yönlü trafik
üçgenine "daralan yol" (Ankara 273 sn). Yani yeni sınıflar o levhaları devralmadı: model düşen kaya / yol çalışması /
S-viraj için hâlâ temel sınıfları seçiyor (DFG'de bu sınıfların örneği az: yol çalışması 40, düşen kaya 119 kutu; Türk
örneği hiç yok). Kapı (≥ 31 yakalama, ≤ 14 yanlış uyarı) tutmadı; uygulama v8'de. Ağırlıklar `ml/runs/detect/v9`.
Sonraki adım aynı 38 sınıfla Türk yol karelerinden (Amasra–Sinop, Pexels) sözde etiket + gözle denetim → v10.

**v10 (30 Ekim gece, uygulamaya alınmadı):** v9'un üstüne Amasra–Sinop motosiklet videosu (Wikimedia Commons, fatih
kaplan, CC BY 3.0) ve 2 Pexels klibinden `yeni_kare_denetim.py` ile sözde etiketlenip paftadan gözle ayıklanan 116 görsel
(149 kutu: 16 şevron, 3 sollama yasak, 3 kaygan yol, 2 düşen kaya, 2 devamlı viraj, 88 ikaz direği/tabela "bilinmeyen").
v9'dan ince ayar (lr 0,0003), 15 epoch'ta erken durdu, en iyi 3. epoch (val 0,887 / 0,722); temiz test 0,878 / 0,708.
Videoda 30 FPS'te 31 (25) / 21, yeni sınıf doğru 8 (hepsi keskin viraj); ~10 FPS'te 27 (24) / 10 (v8 ile aynı).
30 FPS'teki yanlış uyarılar yine aynı nesneler: uzak/okunmaz levhalar, sarı yol çalışması levhaları, şevron/ikaz
direkleri ve sınıf dışı levhalar (kasis üçgeni → speed30, 4,80 m → yaya, S-viraj → kavşak). Kapı tutmadı; uygulama v8'de.
Ağırlıklar `ml/runs/detect/v10`.

**v11 (30 Ekim gece, uygulamaya alınmadı):** ajan analizinin eğitim önerileri: v9 best.pt'den sınıf ağırlıklı devam
(`cls_pw` 0,5 = ters sıklığın karekökü), yeni sınıf içeren 198 DFG görseli val'e (`liste_v11.py`; val 494), sabır 30 =
epoch (mozaiksiz son 10 epoch atlanmadı), lr0 0,0002. Val mAP50 30 epoch boyunca 0,839–0,850 arasında düz kaldı (en iyi
1. epoch, 0,850 / 0,733); temiz test .pt 0,879 / 0,710. Yeni sınıflı val ilk kez hangi yeni sınıfların zayıf olduğunu
gösterdi: keskin viraj 0,71, hayvan 0,62, yol çalışması 0,63 (duyarlılık 0,19), speed60 0,72 (az ve yalnız DFG örnekli);
düşen kaya, demiryolu, sollama yasak, eğim ≥ 0,97. Videoda 30 FPS'te 31 (27) / 18, yeni sınıf doğru 3; 5 sınıf 0,8
tabanıyla 31 (27) / 15; ~10 FPS'te 27 (23) / 9. Sınıf ağırlığı yanlış okumaları azaltmadı (düşen kayaya "dikkat", yol
çalışmasına "kavşak" eklendi). Kapı tutmadı. Ağırlıklar `ml/runs/detect/v11`.

**Sarı zemin kuralı (30 Ekim sabahı, v6):** tespit kutusundaki sarı piksel oranı loga eklendi (`sari` sütunu) ve
"oran ≥ eşik ise yok say" kuralı tarandı. 30 FPS'te yanlış uyarı 14 → 13 (eşik 0,3/0,4), 0,2'de yakalama 32 → 30.
İşe yaramadı: yol çalışması bölgesinde gerçek geçici hız levhaları da sarı zeminli (Ankara 140–290 sn; doğru hız 50
uyarılarının sarı oranı 0,3–0,5). Kural kapalı, ölçüm sütunu duruyor.

**Ajan analizi (30 Ekim gece, v8/v9/v10 logları; 3 analiz + 5 bağımsız doğrulama ajanı):**
- *Yanlış uyarıların nedeni:* v9'un 19 ve v10'un 21 yanlış uyarısından 13 / 12'si v8'in de uyardığı yerler. Fazlası
  yeni nesne değil, 5–8 % boydaki **gerçek Türk levhalarının kendinden emin yanlış okunması**: 50 → 30 (v9 ×3, v10 ×4;
  v8 ×1), 70 → U dönüşü yasak (v10), kavşak üçgeni → yaya (v9, v10) ve yeni sınıf nesnelerinin (S-viraj 7, düşen kaya 5,
  sollama yasak 3, sarı zeminli yol çalışması 5, hayvan 3 uyarı) temel sınıf olarak ses vermesi. Şevron/ikaz direği hiç
  uyarı üretmemiş: inceleyici notlarındaki "chevron" suçlamalarının hepsinde asıl kutu yanındaki üçgen/daire levha.
  Temiz testte speed30 mAP50 0,764 → 0,725 → 0,705: v9 yalnızca DFG'den speed40/60 ve hız sonu ekledi, Türk hız örneği
  aynı kaldı. Ankara 133 sn ve sürücü koltuğu 12 sn "yanlış" uyarıları aslında gerçek levha (sahne kesmesi; 1 kare/sn
  gerçek durum kaçırmış).
- *Eğitim:* val_temiz / test_temiz yalnızca 20 temel sınıfı içeriyor → v9/v10'da best.pt seçimi ve erken durma 17 yeni
  sınıfı **hiç ölçmedi**. Eğitim kutularının %42'si diger_levha (12.489), 20 temel sınıf %45, 17 yeni sınıf %12 ve
  12'si ≥ %94 DFG. Ultralytics 8.4'ün `cls_pw` sınıf ağırlığı hiç kullanılmamıştı. v10, v9'un bitirdiği lr'nin 3 katıyla
  ve ısınma/mozaikle yeniden başlayıp 1. epoch'tan itibaren v9'un altında kaldı. Sıfırdan eğitim için kanıt yok (v1 bile
  ~0,885 tavanına veriyle takılmış).
- *Kural taraması (258 satır):* yanlış uyarı üreten sınıflara **0,8 güven tabanı** (speed30, crossroads, dangerousright,
  pedestrian_risk, schoolpassing; caution/dangerousleft/pedestrian_info tabanı hiçbir yanlış uyarıyı silmediği için
  dışarıda) 30 FPS'te v8 32 (28) / **11**, v9 32 (27) / **11** (+4 yeni sınıf doğru), v10 32 (25) / 19; ~10 FPS'te
  v8 27 (23) / 10, v9 26 (23) / **7**, v10 26 (23) / 10. Hiçbir yakalama kaybolmuyor (bu videolardaki tabanlı sınıf
  olaylarının hepsinde en yüksek güven ≥ 0,886). Doğrulayıcıların çekinceleri: kural aynı 10 videoda ayarlandı; v8'e de
  aynı ölçüde yarıyor (yani v9 kapıyı **model üstünlüğüyle değil kural değişikliğiyle** geçiyor); 31 → 32 yakalama
  Ankara 291 sn'de yanlış okul uyarısının ses kuyruğunu boşaltmasından; 0,7–0,8 arası gerçek levhaların kaybı bu videolarla
  ölçülemiyor. Güven 0,85 tabanı ~10 FPS'te 2 gerçek sağa viraj levhasını kaybettiği, 4'te 4 oylama bütün modellerde
  ~10 FPS yakalamayı 26 → 21'e düşürdüğü, genel eşik 0,75 yeni sınıf doğru sayısını 4 → 1'e indirdiği için elendi.
  *Tabanın tek kare maliyeti (temiz test, 5 sınıfın 91 kutusu, güven 0,7 → 0,8):* v8'de 6, v9'da 4 kutu daha kaçıyor
  (yaya tehlikesi ve okul geçidi 2'şer, kavşak 1, speed30 1–2; kesinlik yaya tehlikesinde 0,94 → 1,00). Videoda hiç olay
  kaybolmadı çünkü bir levha onlarca kare verir ve 5'te 3'ünün 0,8'i geçmesi yeter; yine de uzak/soluk levhalarda uyarı
  biraz geç gelebilir.
- *Veri önerileri:* Türk S-viraj, sollama yasak, düşen kaya, sarı zeminli yol çalışması, hayvan ve iki yönlü trafik
  örnekleri; küçük (< 60 px) Türk 30/50/70 kırpıntıları; EDS kamerası / KGM amblemi / mavi yer adı tabelası gibi
  levha olmayan karıştırıcılar diger_levha olarak.

**Sevk kararı (30 Ekim gece): v9 + 5 sınıfta 0,8 güven tabanı uygulamada.** Üç eğitim (v9, v10, v11) kapıyı kendi
başına geçemedi; 17 yeni sesli sınıf ancak kural taramasındaki tabanla alınabiliyor. Uygulanan kural: speed30, crossroads,
dangerousright, pedestrian_risk, schoolpassing için güven ≥ 0,8, ötekiler 0,7 (`desktop/app.py` CLASS_MIN_CONF,
`mobile/lib/alerts.dart` _weakFloor; taban = max(taban, genel eşik)). Aynı kuralla 30 FPS'te v8 32 (28) / 11, v9 32 (27)
/ 11 + 4 yeni sınıf doğru; ~10 FPS'te v8 27 (23) / 10, v9 26 (23) / 7 (yeni kuralla `analiz.py kurallar` "şimdiki"
satırı; tablodaki v8–v11 satırları eski kuralla). Temel 20 sınıfta v9, v8'e denk (30 FPS'te 1 uyarı geç, ~10 FPS'te 1
eksik yakalama, 3 az yanlış uyarı) ve üstüne yeni sınıflar seslendiriliyor. Yukarıdaki çekinceler geçerli: kural aynı 10
videoda ayarlandı ve v8'e de aynı ölçüde yarıyor; 0,7–0,8 arası gerçek levhalar tek karede daha çok kaçıyor (v9'da
91'de 4). Temiz test .pt 0,884 / 0,719, FP16 tflite 0,889 / 0,715. Yeni sınıflardan keskin viraj dışındakiler
videolarda hiç denenmedi; telefonda gerçek yol testi şart.

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
