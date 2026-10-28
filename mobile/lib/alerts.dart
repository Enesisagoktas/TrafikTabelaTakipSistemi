/// Uyarı mantığı (cihazsız test edilir): filtre -> tekrar önleme -> ses sırası.
/// Kurallar: docs/YOL_HARITASI.md bölüm 1 ve risk 36, 39–45.
library;

/// Eklentiden gelen tek tespit; [height] kutunun normalize yüksekliği (0–1).
typedef Det = ({String name, double conf, double height});

/// Model sınıfı -> Türkçe cümle ve öncelik (1 kritik, 2 uyarı/yasak, 3 bilgi).
/// Ses dosyası: `assets/sounds/<sınıf>.wav`
const signs = <String, ({String text, int priority})>{
  'stop': (text: 'Dur', priority: 1),
  'noentry': (text: 'Girilmez', priority: 1),
  'giveway': (text: 'Yol ver', priority: 1),
  'schoolpassing': (text: 'Dikkat, okul geçidi', priority: 1),
  'pedestrian_risk': (text: 'Dikkat, yaya geçidi', priority: 1),
  'dangerousleft': (text: 'Sola tehlikeli viraj', priority: 2),
  'dangerousright': (text: 'Sağa tehlikeli viraj', priority: 2),
  'crossroads': (text: 'Kavşak yaklaşıyor', priority: 2),
  'caution': (text: 'Dikkat', priority: 2),
  'donotturnleft': (text: 'Sola dönülmez', priority: 2),
  'donotturnright': (text: 'Sağa dönülmez', priority: 2),
  'nouturn': (text: 'U dönüşü yasak', priority: 2),
  'keepleft': (text: 'Soldan gidiniz', priority: 2),
  'keepright': (text: 'Sağdan gidiniz', priority: 2),
  'speed30': (text: 'Hız sınırı otuz', priority: 2),
  'speed50': (text: 'Hız sınırı elli', priority: 2),
  'speed70': (text: 'Hız sınırı yetmiş', priority: 2),
  'nostopping': (text: 'Duraklamak ve park etmek yasak', priority: 3),
  'priorityroad': (text: 'Ana yol', priority: 3),
  'pedestrian_info': (text: 'Yaya geçidi', priority: 3),
};

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
}
