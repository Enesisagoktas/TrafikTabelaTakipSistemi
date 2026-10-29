# Telefonda İlk Test (APK)

Kablo gerekmez: APK dosyasını kendine (WhatsApp, Telegram, Drive, e-posta) gönder, telefonda aç.

## 1. Kurulum
1. APK'ya dokun. "Bilinmeyen kaynaklardan yükleme" izni sorulursa o uygulama (ör. Dosyalar ya da WhatsApp) için izin ver.
2. Play Protect uyarı verirse "Yine de yükle" (uygulama imzası geliştirici anahtarı, mağazadan gelmediği için uyarır).
3. Uygulama: **Trafik Asistanı**. İlk açılışta kamera iznini ver; "Deneysel prototip" uyarısına "Anladım" de.

Telefon Android 64 bit ise (Redmi Note 8 ve sonrası hepsi) `app-arm64-v8a-release.apk` dosyasını kur.

## 2. Model testi (1 dakika, araba gerekmez)
Soldaki menüden **Model testi** → **Testi başlat**. Uygulamanın içine gömülü 11 fotoğrafı (10 levha + 1 boş yol) sırayla modele verir.
- Beklenen: **11 / 11 doğru**. Bilgisayarda ve emülatörde 11/11 çıktı.
- Her kartın altında süre (ms) yazar. GPU açık ve kapalı (Ayarlar) iki kez dene, süreleri not et.

## 3. Sürüş ekranı (masada)
Bilgisayarda `ml/data/videolar` içindeki test videolarından birini tam ekran aç (önerilen: `ankara_corum_iskilip.webm`),
telefonu yatay tutup kamerayı ekrana doğrult. Levha göründükçe üstte yazı çıkar ve ses gelir.
- Sol alttaki kutu: FPS, çıkarım süresi (ms), GPU/CPU ve oylama (3/5 ya da 2/3). **5 FPS'in altı** yavaş sayılır, not et.
- Telefon saniyede 8 kareden az işliyorsa oylama ilk 10 saniyeden sonra kendiliğinden 2/3'e geçer (hızlı geçilen levhalar kaçmasın diye).
- Sağ alttaki düğme sesi açar ve kapatır.
- Ekrandan çekim gerçek yoldan daha zordur (yansıma, moiré). Burada amaç uygulamanın çalıştığını görmek, doğruluk ölçmek değil.

## 4. Kayıtlar
**Kayıtlar** sekmesi her olayı saatiyle gösterir:
- UYARI: söylenen uyarı · ONAY: levha oylamayı geçti (5 karenin 3'ü; telefon 8 FPS altındaysa 3 karenin 2'si) · HAM: modelin ham tespiti (eşik altı dahil)
- PERF: son 10 saniyenin hızı · TEST: model testi sonuçları · AYAR: değiştirilen ayarlar ve otomatik oylama geçişi ("Oylama 2/3 (ortalama … FPS)") · HATA: hata

**Paylaş** düğmesi bu oturumun kayıt dosyasını (.txt) gönderir. Testten sonra bu dosyayı bana gönder; FPS, yanlış uyarı ve kaçırılan levhaları ondan çıkarırım.

## 5. Ayarlar (varsayılanlar 10 test videosuna göre seçildi)
- **Güven eşiği 0,70.** Hız levhaları en az 0,65, yaya geçidi bilgi levhası en az 0,70 ister (0,70'te ikisi de etkisiz).
- **Uzak/küçük levhaları yoksay: açık.** Görüntü yüksekliğinin %5'inden küçük kutular sayılmaz.
  10 videoda bu ayar yanlış uyarıyı belirgin şekilde azalttı (bkz. `docs/video_testi.md`).
- **GPU kullan: açık.** Kapatıp FPS farkına bak.
- Ayarlar uygulama kapanınca varsayılana döner.

## Bildirmen gerekenler
- Model testi sonucu (x/11) ve GPU açıkken/kapalıyken süre (ms)
- Sürüş ekranında FPS
- Uygulama çöktü mü, donma oldu mu, ses geldi mi
- Kayıt dosyası (Paylaş)
