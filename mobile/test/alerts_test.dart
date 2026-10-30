import 'package:flutter_test/flutter_test.dart';
import 'package:trafik_asistan/alerts.dart';

Det d(String name, [double conf = 0.9, double height = 0.1]) => (name: name, conf: conf, height: height);

final t0 = DateTime(2026);
DateTime at(double s) => t0.add(Duration(milliseconds: (s * 1000).round()));

void main() {
  group('DetectionFilter', () {
    test("5 karenin 3'ünde görülen levha onaylanır", () {
      final f = DetectionFilter();
      expect(f.update([d('stop')]), isEmpty);
      expect(f.update([]), isEmpty);
      expect(f.update([d('stop')]), isEmpty);
      expect(f.update([d('stop')]), {'stop'});
    });

    test("5 karenin 2'sinde görülen levha onaylanmaz", () {
      final f = DetectionFilter();
      for (final frame in [[d('stop')], <Det>[], <Det>[], [d('stop')], <Det>[]]) {
        expect(f.update(frame), isEmpty);
      }
    });

    test('genel ve sınıfa özel güven eşiğinin altı sayılmaz', () {
      final f = DetectionFilter(minConf: 0.5, classMinConf: {'speed70': 0.7});
      for (var i = 0; i < 5; i++) {
        expect(f.update([d('stop', 0.4), d('speed70', 0.6)]), isEmpty);
      }
      expect(f.update([d('speed70', 0.8)]), isEmpty);
    });

    test('çok küçük kutular sayılmaz', () {
      final f = DetectionFilter(minHeight: 0.02);
      for (var i = 0; i < 5; i++) {
        expect(f.update([d('stop', 0.9, 0.01)]), isEmpty);
      }
    });

    test("yavaş telefonda (< 8 FPS) oylama 3 karenin 2'si", () {
      expect(votingFor(5), (window: 3, minHits: 2));
      expect(votingFor(12), (window: 5, minHits: 3));
      final v = votingFor(5);
      final f = DetectionFilter(window: v.window, minHits: v.minHits);
      expect(f.update([d('stop')]), isEmpty);
      expect(f.update([]), isEmpty);
      expect(f.update([d('stop')]), {'stop'});
    });
  });

  group('Cooldown', () {
    test('levha görünür kaldıkça yalnızca bir kez uyarır', () {
      final c = Cooldown();
      expect(c.update({'stop'}, at(0)), ['stop']);
      for (var s = 0.5; s <= 10; s += 0.5) {
        expect(c.update({'stop'}, at(s)), isEmpty);
      }
    });

    test('2 sn kaybolan levha 5 sn dolunca yeniden uyarır', () {
      final c = Cooldown();
      c.update({'stop'}, at(0));
      c.update({'stop'}, at(1));
      c.update({}, at(3.5));
      expect(c.update({'stop'}, at(6)), ['stop']);
    });

    test('yeniden kurulan levha 5 sn dolmadan uyarmaz, dolunca uyarır', () {
      final c = Cooldown();
      c.update({'stop'}, at(0));
      c.update({}, at(2.5));
      expect(c.update({'stop'}, at(3)), isEmpty);
      expect(c.update({'stop'}, at(5)), ['stop']);
    });

    test('farklı levhalar birbirini engellemez', () {
      final c = Cooldown();
      expect(c.update({'stop'}, at(0)), ['stop']);
      expect(c.update({'stop', 'giveway'}, at(1)), ['giveway']);
    });
  });

  group('AlertQueue', () {
    test('yüksek öncelikli uyarı öne geçer', () {
      final q = AlertQueue()
        ..add('nostopping', 3, at(0))
        ..add('stop', 1, at(0));
      expect(q.next(at(0)), 'stop');
      expect(q.next(at(0)), 'nostopping');
      expect(q.next(at(0)), isNull);
    });

    test('en fazla 2 uyarı bekler, en düşük öncelikli atılır', () {
      final q = AlertQueue()
        ..add('speed50', 2, at(0))
        ..add('priorityroad', 3, at(0))
        ..add('noentry', 1, at(0));
      expect(q.next(at(0)), 'noentry');
      expect(q.next(at(0)), 'speed50');
      expect(q.next(at(0)), isNull);
    });

    test("3 sn'den eski uyarı atılır", () {
      final q = AlertQueue()..add('stop', 1, at(0));
      expect(q.next(at(3.5)), isNull);
    });

    test('arkada başka uyarı bekliyorsa isNotEmpty (kısa biçim çalınır)', () {
      final q = AlertQueue()
        ..add('stop', 1, at(0))
        ..add('speed70', 2, at(0));
      expect(q.next(at(0)), 'stop');
      expect(q.isNotEmpty, isTrue);
      expect(q.next(at(0)), 'speed70');
      expect(q.isNotEmpty, isFalse);
    });
  });

  group('label', () {
    test('kısa biçim; diğer levha ve bilinmeyen sınıf', () {
      expect(label('speed70'), 'Yetmiş');
      expect(label(otherSign), 'Bilinmeyen levha');
      expect(label('bilinmeyen'), 'bilinmeyen');
    });
  });

  group('classThresholds', () {
    test('zayıf sınıflar genel eşikten düşük olamaz, genel eşik yüksekse onu alır', () {
      expect(classThresholds(0.5)['speed70'], 0.65);
      expect(classThresholds(0.5)['pedestrian_info'], 0.7);
      expect(classThresholds(0.8)['speed70'], 0.8);
      expect(classThresholds(0.5).containsKey('stop'), isFalse);
    });
  });

  group('RisingEdge', () {
    test('yalnızca yeni giren sınıfları döndürür', () {
      final r = RisingEdge();
      expect(r.update({'stop'}), {'stop'});
      expect(r.update({'stop', 'giveway'}), {'giveway'});
      expect(r.update({'giveway'}), isEmpty);
      expect(r.update({'stop', 'giveway'}), {'stop'});
    });
  });

  group('Throttle', () {
    test('aynı anahtara aralık dolmadan izin vermez, farklı anahtarlar bağımsız', () {
      final t = Throttle(const Duration(seconds: 1));
      expect(t.allow('stop', at(0)), isTrue);
      expect(t.allow('stop', at(0.5)), isFalse);
      expect(t.allow('giveway', at(0.5)), isTrue);
      expect(t.allow('stop', at(1)), isTrue);
    });
  });

  test("katalogda modelin 28 sesli sınıfının hepsi var ve öncelikler 1-3", () {
    const modelNames = [
      'caution', 'crossroads', 'dangerousleft', 'dangerousright', 'donotturnleft', 'donotturnright', 'giveway',
      'keepleft', 'keepright', 'noentry', 'nostopping', 'nouturn', 'pedestrian_info', 'pedestrian_risk',
      'priorityroad', 'schoolpassing', 'speed30', 'speed50', 'speed70', 'stop',
      'kasis', 'durak', 'demiryolu', 'refuj_basi', 'donus_adasi', 'ileri_saga', 'ileri_sola', 'ada_etrafinda', // v7
    ];
    expect(signs.keys.toSet(), modelNames.toSet());
    expect(signs.values.every((s) => s.priority >= 1 && s.priority <= 3), isTrue);
    expect(signs.values.every((s) => s.short.isNotEmpty && s.short.length <= s.text.length), isTrue);
    expect(signs.containsKey(otherSign), isFalse); // diğer levha seslendirilmez
  });
}
