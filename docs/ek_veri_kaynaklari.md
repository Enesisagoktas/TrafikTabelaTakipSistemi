# Ek Veri Kaynakları ve Atıf (v12–v13, 31 Ekim – 1 Kasım 2026)

v12 eğitimine giren yeni verinin kaynağı, lisansı ve nasıl ayıklandığı. Kural: giriş gerektirmeyen, açık lisanslı, Türk
levhası; YouTube yok; tanınmayan küçük yüklemeler yok. Dosyalar `ml/data/dis/` altında, git'e girmez. Wikimedia API'si
tanıtıcı User-Agent (proje adresi) ve ~5 sn aralık ister; 429'da `Retry-After` beklendi, tarayıcı taklidi yapılmadı.

## 1. Sürüş videoları (`ml/data/dis/yeni_videolar/`, atıf: `atif.csv`)

| Ad | Kaynak | Lisans | Kare (2/sn) | Durum |
|---|---|---|---|---|
| `e80_pegasus` | WiFi & Cell Phone Radiation, "Pegasus uçak kazası E80 den canlı görüntüleri (yeni).webm", [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Pegasus_u%C3%A7ak_kazas%C4%B1_E80_den_canl%C4%B1_g%C3%B6r%C3%BCnt%C3%BCleri_(yeni).webm) | CC BY 3.0 | 69 | eğitimde |
| `ist_otoyol` | [Pexels video 31660095](https://www.pexels.com/video/31660095/) | Pexels Lisansı | 41 | eğitimde |
| `ist_bogaz_koprusu` | [Pexels video 38740040](https://www.pexels.com/video/38740040/) | Pexels Lisansı | 15 | eğitimde |
| `bayrak_otoyol` | [Pexels video 39278559](https://www.pexels.com/video/39278559/) | Pexels Lisansı | 33 | eğitimde |
| `ist_buyukdere` | [Pexels video 11914938](https://www.pexels.com/video/11914938/) | Pexels Lisansı | 24 | **hariç:** test videosu `pexels_istanbul` ile aynı çekim (24 karenin 7'si 16×16 imza MSE < 0,15) |
| Çorum şehir merkezi | Emine Yabacıoğlu, Commons | CC BY 3.0 | – | inmedi (1,3 GB; `upload.wikimedia.org` ~30 MB'da kesiyor) |
| Çanakkale 1915 Bridge | Commons | CC BY 3.0 | – | inmedi (159 MB; aynı neden) |

158 kareden v9 (eşik 0,3) 47'sinde levha buldu; ajan paneli denetiminden 39 kare / 40 kutu kaldı. Ayıklama: `scripts/test_benzerlik.py`
(10 test videosuyla çakışma), `scripts/yeni_kare_denetim.py` + `scripts/ajan/pafta_denetim.js` (her pafta iki bağımsız ajan).

## 2. Levha fotoğrafları (`ml/data/dis/commons_levha/`, atıf: `atif.csv`)

Wikimedia Commons "Category:Road signs in Turkey" ağacı (SVG, çizim, sokak tabelası, tarihî kategoriler hariç; `scripts/commons_tara.py`,
`scripts/commons_indir.py`); yalnız CC0 / CC BY / CC BY-SA / kamu malı dosyalar. 112 fotoğraf indi (Wikimedia hız kısıtı yüzünden
çok yavaş); atıf satırı yazılmış 95'i tarandı, v9 9'unda levha buldu, denetimden 2 fotoğraf / 4 kutu eğitime girdi:

- Safa.daneshvar, "050413-VanLake-Turkey-IMG_2742-2.jpg", CC0 — https://commons.wikimedia.org/wiki/File:050413-VanLake-Turkey-IMG_2742-2.jpg
- MERMERCİ ÖZGÜR1, "11230 Deresakarı-Bilecik Merkez-Bilecik, Turkey - panoramio.jpg", CC BY 3.0 — https://commons.wikimedia.org/wiki/File:11230_Deresakar%C4%B1-Bilecik_Merkez-Bilecik,_Turkey_-_panoramio.jpg

Geri kalan fotoğraflar (çoğu yön/şehir tabelası ya da model küçük levhaya alışık olduğundan bulamadığı yakın planlar) v13 için
duruyor; tam liste `atif.csv`.

## 3. Resmî levha çizimleri → sentetik görseller (`ml/data/dis/commons_svg/`, liste: `liste.csv`)

Commons "Diagrams of warning / prohibitory / mandatory / priority / information / temporary road signs of Turkey" kategorileri
(`scripts/commons_svg_indir.py`, 256 px PNG): 293 çizim. İki bağımsız ajan her çizimi 38 sınıftan birine eşledi, yalnız anlaşılanlar
alındı (`scripts/ajan/svg_esleme.js`, sonuç `scripts/esleme_svg_v12.json`); 1952 serisi ve "(old)" tasarımlar dışarıda, T-22a–e yan yol
kavşak varyantları "kavşak"a sayılmadı. Kullanılan 136 çizim: CC BY-SA 4.0 125, CC0 9, kamu malı 2; yazarlar Gigillo83 (104),
มองโกเลีย๔๔ (18), Jelican9 (10), Kingwarnen (2), Kurmanbek (2). 40 ve 60 hız sınırı çizimi Commons'ta yok: 30/40/50/60/70 diskleri
PIL ile çizildi (`uretilen_hiz_*.png`, bizim).

Sentetik görseller (`scripts/sentetik.py`, `ml/data/levha640/ek/sentetik/`, v12 1.397 + v13 945 = 2.342 görsel; v13'te "diğer" çizimleri 10 kat ağır ve %15'i sarı zeminli) bizim eğitim karelerine ve levhasız yeni
karelere yapıştırmayla üretildi; CC BY-SA 4.0 çizimlerden türetildikleri için **dağıtılmıyor** (git dışı). Model ağırlıkları için
atıf: yukarıdaki yazarlar, Wikimedia Commons, CC BY-SA 4.0.

## Alınan dersler
- Wikimedia: User-Agent'ta iletişim adresi olmadan ve eş zamanlı isteklerle 429 yağıyor; tek sıra + 5 sn + Retry-After ile düzeldi, ama
  `upload.wikimedia.org` bu akşam büyük dosyalarda ~30 MB'da bağlantıyı kesti ve fotoğraflarda okuma zaman aşımı verdi.
- Pexels sayfaları bot korumalı (403); indirme adresi tanıtıcı User-Agent ile çalışıyor. Lisans atıf istemiyor, yine de kimlik/URL yazıldı.
- cv2 Windows'ta Türkçe karakterli yolu okumuyor (`ek_veri.py` çöktü): dosya adları ASCII'ye çevrildi (`ad_eslemesi.json`).
