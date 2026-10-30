/// Uyarı mantığı (cihazsız test edilir): filtre -> tekrar önleme -> ses sırası.
/// Kurallar: docs/YOL_HARITASI.md bölüm 1 ve risk 36, 39–45.
library;

/// Eklentiden gelen tek tespit; [height] kutunun normalize yüksekliği (0–1).
typedef Det = ({String name, double conf, double height});

/// Model sınıfı -> Türkçe cümle, kısa biçim ve öncelik (1 kritik, 2 uyarı/yasak, 3 bilgi).
/// Kısa biçim ekran şeridinde ve arkada başka bir uyarı beklerken seste kullanılır (uzun cümleler
/// art arda gelen levhalarda ikinci uyarıyı 1–2 sn geciktiriyordu; 29 Ekim canlı demo).
/// Ses dosyaları: `assets/sounds/<sınıf>.wav` (cümle) ve `assets/sounds/<sınıf>_kisa.wav` (kısa biçim).
/// `crossroads` aslında "ana yol – tali yol kavşağı" üçgeni (veri setinde "+" kavşak levhası yok).
const signs = <String, ({String text, String short, int priority})>{
  'stop': (text: 'Dur', short: 'Dur', priority: 1),
  'noentry': (text: 'Girilmez', short: 'Girilmez', priority: 1),
  'giveway': (text: 'Yol ver', short: 'Yol ver', priority: 1),
  'schoolpassing': (text: 'Dikkat, okul geçidi', short: 'Okul geçidi', priority: 1),
  'pedestrian_risk': (text: 'Dikkat, yaya geçidi', short: 'Yaya geçidi', priority: 1),
  'dangerousleft': (text: 'Sola tehlikeli viraj', short: 'Sola viraj', priority: 2),
  'dangerousright': (text: 'Sağa tehlikeli viraj', short: 'Sağa viraj', priority: 2),
  'crossroads': (text: 'Kavşak yaklaşıyor', short: 'Kavşak', priority: 2),
  'caution': (text: 'Dikkat', short: 'Dikkat', priority: 2),
  'donotturnleft': (text: 'Sola dönülmez', short: 'Sola dönülmez', priority: 2),
  'donotturnright': (text: 'Sağa dönülmez', short: 'Sağa dönülmez', priority: 2),
  'nouturn': (text: 'U dönüşü yasak', short: 'U dönüşü yasak', priority: 2),
  'keepleft': (text: 'Soldan gidiniz', short: 'Soldan', priority: 2),
  'keepright': (text: 'Sağdan gidiniz', short: 'Sağdan', priority: 2),
  'speed30': (text: 'Hız sınırı otuz', short: 'Otuz', priority: 2),
  'speed50': (text: 'Hız sınırı elli', short: 'Elli', priority: 2),
  'speed70': (text: 'Hız sınırı yetmiş', short: 'Yetmiş', priority: 2),
  'nostopping': (text: 'Duraklamak ve park etmek yasak', short: 'Park yasak', priority: 3),
  'priorityroad': (text: 'Ana yol', short: 'Ana yol', priority: 3),
  'pedestrian_info': (text: 'Yaya geçidi', short: 'Yaya geçidi', priority: 3),
  // v7 (29 Ekim gecesi): "trafik levhaları" setinden gelen, yeterli örneği olan 8 Türk levhası daha; hepsi sesli.
  'kasis': (text: 'Kasis', short: 'Kasis', priority: 2),
  'durak': (text: 'Durak', short: 'Durak', priority: 3),
  'demiryolu': (text: 'Demiryolu geçidi', short: 'Demiryolu', priority: 1),
  'refuj_basi': (text: 'Refüj başı', short: 'Refüj', priority: 3),
  'donus_adasi': (text: 'Dönüş adası', short: 'Dönüş adası', priority: 3),
  'ileri_saga': (text: 'İleri ve sağa mecburi', short: 'İleri sağa', priority: 2),
  'ileri_sola': (text: 'İleri ve sola mecburi', short: 'İleri sola', priority: 2),
  'ada_etrafinda': (text: 'Ada etrafında dönünüz', short: 'Ada', priority: 2),
};

/// Modelin tanıdığı ama uyarısı olmayan levha (v6'daki 21. sınıf: 20 sınıfın dışındaki her trafik levhası).
/// Ekranda gösterilir, Kayıtlar'a ONAY olarak düşer, seslendirilmez. Model yabancı levhayı bildiği bir
/// sınıfa zorlamasın diye eklendi (taş düşebilir → kavşak gibi yanlış uyarılar, 29 Ekim).
const otherSign = 'diger_levha';

/// Ekran şeridindeki ad: kataloğun kısa biçimi, diğer levha için "Bilinmeyen levha".
String label(String name) => name == otherSign ? 'Bilinmeyen levha' : (signs[name]?.short ?? name);

/// Zayıf sınıfların taban eşikleri (Hafta 2 hata analizi: hız levhaları birbirine,
/// pedestrian_info başka mavi levhalara karışıyor).
const _weakFloor = {'speed30': 0.65, 'speed50': 0.65, 'speed70': 0.65, 'pedestrian_info': 0.7};

/// Sınıfa özel eşikler: taban eşik ile genel eşikten büyük olanı.
Map<String, double> classThresholds(double minConf) =>
    {for (final e in _weakFloor.entries) e.key: e.value > minConf ? e.value : minConf};

/// Bir önceki çağrıya göre kümeye yeni giren sınıflar (kayıtta "ONAY" satırı için).
class RisingEdge {
  Set<String> _prev = {};

  Set<String> update(Set<String> current) {
    final out = current.difference(_prev);
    _prev = {...current};
    return out;
  }
}

/// Anahtar başına en fazla [interval]'de bir izin verir (kayıt seli olmasın).
class Throttle {
  Throttle(this.interval);

  final Duration interval;
  final _last = <String, DateTime>{};

  bool allow(String key, DateTime now) {
    final last = _last[key];
    if (last != null && now.difference(last) < interval) return false;
    _last[key] = now;
    return true;
  }
}

/// Oylama FPS'e göre: yavaş telefonda (ortalama < 8 FPS) 3 karenin 2'si, değilse 5 karenin 3'ü. Yavaşta 5 kare
/// 0,6–1 sn sürer, levha o kadar uzun büyük görünmez. 10 test videosunda (v5b, güven 0,7) ~5 FPS'te yakalanan levha
/// 16 → 24, yanlış uyarı 3 → 5; 10 FPS'te ise 5'te 3 daha az yanlış uyarı veriyor (29 Ekim, docs/video_testi.md).
({int window, int minHits}) votingFor(double fps) => fps < 8 ? (window: 3, minHits: 2) : (window: 5, minHits: 3);

/// Güven eşiği + en küçük kutu + "son [window] karenin en az [minHits]'inde görüldü" oylaması.
class DetectionFilter {
  DetectionFilter({
    this.window = 5,
    this.minHits = 3,
    this.minConf = 0.5,
    this.minHeight = 0,
    this.classMinConf = const {},
  });

  final int window, minHits;
  final double minConf, minHeight;
  final Map<String, double> classMinConf;
  final _frames = <Set<String>>[];

  /// Bir karenin tespitlerini ekler, oylamayı geçen sınıfları döndürür.
  Set<String> update(Iterable<Det> dets) {
    _frames.add({
      for (final d in dets)
        if (d.conf >= (classMinConf[d.name] ?? minConf) && d.height >= minHeight) d.name,
    });
    if (_frames.length > window) _frames.removeAt(0);
    final hits = <String, int>{};
    for (final f in _frames) {
      for (final n in f) {
        hits[n] = (hits[n] ?? 0) + 1;
      }
    }
    return {for (final e in hits.entries) if (e.value >= minHits) e.key};
  }
}

/// Aynı levha için tekrar uyarıyı engeller: en az [minGap] sessizlik ve levha [rearmAfter]
/// boyunca görünmeyip yeniden kurulmalı. Kimlik takibi yok (risk 40–41).
class Cooldown {
  Cooldown({this.minGap = const Duration(seconds: 5), this.rearmAfter = const Duration(seconds: 2)});

  final Duration minGap, rearmAfter;
  final _lastAlert = <String, DateTime>{};
  final _lastSeen = <String, DateTime>{};
  final _disarmed = <String>{};

  /// Onaylanmış sınıfları alır, şimdi uyarılması gerekenleri döndürür.
  List<String> update(Set<String> seen, DateTime now) {
    _disarmed.removeWhere((n) => !seen.contains(n) && now.difference(_lastSeen[n]!) >= rearmAfter);
    final out = <String>[];
    for (final n in seen) {
      _lastSeen[n] = now;
      final last = _lastAlert[n];
      if (_disarmed.contains(n) || (last != null && now.difference(last) < minGap)) continue;
      _lastAlert[n] = now;
      _disarmed.add(n);
      out.add(n);
    }
    return out;
  }
}

/// Öncelik sıralı, kısa ve bayatlayan ses kuyruğu (risk 43–45).
class AlertQueue {
  AlertQueue({this.maxLen = 2, this.maxAge = const Duration(seconds: 3)});

  final int maxLen;
  final Duration maxAge;
  final _items = <({String name, int priority, DateTime at})>[];

  void add(String name, int priority, DateTime now) {
    _items
      ..add((name: name, priority: priority, at: now))
      ..sort((a, b) => a.priority != b.priority ? a.priority.compareTo(b.priority) : a.at.compareTo(b.at));
    if (_items.length > maxLen) _items.removeLast();
  }

  String? next(DateTime now) {
    _items.removeWhere((i) => now.difference(i.at) > maxAge);
    return _items.isEmpty ? null : _items.removeAt(0).name;
  }

  /// [next]'ten hemen sonra: arkada başka uyarı bekliyor mu (bekliyorsa kısa biçim çalınır).
  bool get isNotEmpty => _items.isNotEmpty;
}
