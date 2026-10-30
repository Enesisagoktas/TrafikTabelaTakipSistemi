import 'package:audio_session/audio_session.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import 'package:flutter/foundation.dart' show setEquals;

import 'alerts.dart';
import 'event_log.dart';
import 'model_test.dart';

const kModelPath = 'assets/models/levha.tflite';
const kModelName = 'v6 · YOLO11n · 640 px · 21 sınıf';

/// Uzak levha sınırı: görüntü yüksekliğinin %5'inden kısa kutular sayılmaz. 10 test videosunda (ml/scripts/esik_tarama.py)
/// v2 ile güven 0,5 → 0,6 ve bu sınır %2,5 → %5 olunca yanlış uyarı 58 → 20, yakalanan levha 25 → 30 oldu (29 Ekim).
const kMinHeight = 0.05;

/// Ayarlar (bellekte tutulur; uygulama yeniden açılınca varsayılana döner).
class Settings extends ChangeNotifier {
  double minConf = 0.7; // 10 test videosunda 0,6'ya göre daha az yanlış uyarı, aynı ya da daha çok yakalama (v5b)
  bool ignoreSmall = true; // uzak (küçük) kutular yanlış alarmın ana kaynağı; bkz. kMinHeight
  bool sound = true;
  bool useGpu = true;

  /// [log] null değilse değişiklik kayda yazılır (kaydırıcı sürüklenirken yazılmasın diye).
  void set(String? log, VoidCallback change) {
    change();
    if (log != null) EventLog.instance.add('AYAR', log);
    notifyListeners();
  }
}

final settings = Settings();

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
  await WakelockPlus.enable();
  // Uyarı çalarken çalan müziği geçici olarak kıs (risk 46).
  await (await AudioSession.instance).configure(const AudioSessionConfiguration(
    androidAudioAttributes: AndroidAudioAttributes(
      contentType: AndroidAudioContentType.speech,
      usage: AndroidAudioUsage.assistanceNavigationGuidance,
    ),
    androidAudioFocusGainType: AndroidAudioFocusGainType.gainTransientMayDuck,
  ));
  await EventLog.instance.init();
  EventLog.instance.add('MODEL', 'Uygulama açıldı · $kModelName');
  runApp(MaterialApp(
    title: 'Trafik Asistanı',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(colorSchemeSeed: Colors.red, useMaterial3: true),
    home: const HomeScreen(),
  ));
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _showDisclaimer());
  }

  Future<void> _showDisclaimer() => showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Deneysel prototip'),
          content: const Text(
            'Bu uygulama sürücüye yardımcı olmak için geliştirilmiş bir öğrenci projesidir; güvenlik sistemi değildir. '
            'Trafik levhalarına ve kurallara her zaman kendiniz dikkat edin. Sürüş sırasında telefona dokunmayın.\n\n'
            'Veri setleri: Hootbu, "Traffic-Sign-Recognition-V2-Turkiye", Roboflow Universe, CC BY 4.0; '
            '"trafik levhaları", trafik isaretleri çalışma alanı, Roboflow Universe, CC BY 4.0.',
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Anladım'))],
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Row(children: [
            NavigationRail(
              selectedIndex: _tab,
              onDestinationSelected: (i) => setState(() => _tab = i),
              labelType: NavigationRailLabelType.all,
              destinations: const [
                NavigationRailDestination(icon: Icon(Icons.directions_car), label: Text('Sürüş')),
                NavigationRailDestination(icon: Icon(Icons.list_alt), label: Text('Kayıtlar')),
                NavigationRailDestination(icon: Icon(Icons.fact_check), label: Text('Model testi')),
                NavigationRailDestination(icon: Icon(Icons.tune), label: Text('Ayarlar')),
              ],
            ),
            const VerticalDivider(width: 1),
            // Sekme değişince kamera kapanır (Sürüş dışında boşuna çalışmasın).
            Expanded(
              child: switch (_tab) {
                0 => const DriveScreen(),
                1 => const LogsScreen(),
                2 => ModelTestScreen(modelPath: kModelPath, useGpu: settings.useGpu),
                _ => const SettingsScreen(),
              },
            ),
          ]),
        ),
      );
}

class DriveScreen extends StatefulWidget {
  const DriveScreen({super.key});

  @override
  State<DriveScreen> createState() => _DriveScreenState();
}

class _DriveScreenState extends State<DriveScreen> {
  DetectionFilter? _filter;
  String _filterKey = '';
  final _cooldown = Cooldown();
  final _queue = AlertQueue();
  final _player = AudioPlayer();
  final _confirmed = RisingEdge();
  final _rawLog = Throttle(const Duration(seconds: 1));
  bool _speaking = false;
  String _banner = '';
  Set<String> _seen = const {}; // oylamayı geçen levhalar (diğer levha dâhil): ekran şeridi
  String _perf = 'Model yükleniyor…';
  int _frames = 0;
  double _msSum = 0;
  DateTime _perfSince = DateTime.now(); // her 10 sn'lik pencere o pencerenin ilk karesinde başlar

  var _voting = votingFor(30); // ilk 10 sn'lik FPS ortalamasına kadar 5 karenin 3'ü

  DetectionFilter get _activeFilter {
    final key = '${settings.minConf}/${settings.ignoreSmall}/$_voting';
    if (key != _filterKey) {
      _filterKey = key;
      _filter = DetectionFilter(
        window: _voting.window,
        minHits: _voting.minHits,
        minConf: settings.minConf,
        minHeight: settings.ignoreSmall ? kMinHeight : 0,
        classMinConf: classThresholds(settings.minConf),
      );
    }
    return _filter!;
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  void _onResult(List<YOLOResult> results) {
    final now = DateTime.now();
    final dets = [for (final r in results) (name: r.className, conf: r.confidence, height: r.normalizedBox.height)];
    for (final d in dets) {
      if (d.conf >= 0.3 && _rawLog.allow(d.name, now)) {
        EventLog.instance.add('HAM', '${d.name} ${d.conf.toStringAsFixed(2)} · yükseklik %${(d.height * 100).toStringAsFixed(1)}');
      }
    }
    final seen = _activeFilter.update(dets);
    for (final n in _confirmed.update(seen)) {
      EventLog.instance.add('ONAY', '$n (${label(n)})');
    }
    // Yalnızca katalogdaki sınıflar uyarı olur; diğer levha (ve bilinmeyen sınıf) ekranda kalır, seslendirilmez.
    for (final n in _cooldown.update(seen.where(signs.containsKey).toSet(), now)) {
      _queue.add(n, signs[n]!.priority, now);
    }
    if (mounted && !setEquals(seen, _seen)) setState(() => _seen = seen);
    _speak();
  }

  void _onPerf(YOLOPerformanceMetrics m) {
    final now = DateTime.now();
    if (_frames == 0) _perfSince = now; // model yükleme ve kamera açılışı pencereye girmesin
    _frames++;
    _msSum += m.processingTimeMs;
    final ms = now.difference(_perfSince).inMilliseconds;
    if (ms >= 10000) {
      // Eklenti her işlenen karede bu çağrıyı yapıyor; hız gerçek kare sayısından. m.fps 0'dan başlayan bir
      // ortalama olduğu için ilk saniyelerde gerçek hızdan sapıyor.
      final fps = (_frames - 1) * 1000 / ms;
      EventLog.instance.add('PERF',
          '${fps.toStringAsFixed(1)} FPS · ${(_msSum / _frames).toStringAsFixed(0)} ms · ${settings.useGpu ? 'GPU istendi' : 'CPU'}');
      if (votingFor(fps) != _voting) {
        _voting = votingFor(fps);
        EventLog.instance.add('AYAR', 'Oylama ${_voting.minHits}/${_voting.window} (ortalama ${fps.toStringAsFixed(1)} FPS)');
      }
      _frames = 0;
      _msSum = 0;
    }
    if (mounted) setState(() => _perf = '${m.fps.toStringAsFixed(1)} FPS · ${m.processingTimeMs.toStringAsFixed(0)} ms');
  }

  /// Sıradaki uyarıları tek tek çalar; aynı anda yalnızca bir ses (risk 43).
  Future<void> _speak() async {
    if (_speaking) return;
    _speaking = true;
    try {
      for (var n = _queue.next(DateTime.now()); n != null; n = _queue.next(DateTime.now())) {
        final brief = _queue.isNotEmpty; // arkada başka uyarı bekliyor: kısa biçim, ikinci levha gecikmesin
        final text = brief ? signs[n]!.short : signs[n]!.text;
        EventLog.instance.add('UYARI', '$text ($n${brief ? ', kısa' : ''})');
        if (mounted) setState(() => _banner = text);
        if (!settings.sound) continue;
        await _player.setAsset('assets/sounds/$n${brief ? '_kisa' : ''}.wav');
        await _player.play(); // çalma bitince döner
      }
    } catch (e) {
      EventLog.instance.add('HATA', 'Ses: $e');
    } finally {
      _speaking = false;
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: settings,
        builder: (context, _) => Stack(children: [
          YOLOView(
            key: ValueKey(settings.useGpu), // useGpu yalnızca açılışta okunur; değişince görünüm yeniden kurulur
            modelPath: kModelPath,
            task: YOLOTask.detect,
            confidenceThreshold: 0.25, // asıl eşik Dart filtresinde (Ayarlar); HAM kayıtları eşik altını da görsün
            useGpu: settings.useGpu,
            onResult: _onResult,
            onPerformanceMetrics: _onPerf,
            onModelLoad: (_, _) => EventLog.instance.add('MODEL', 'Kamera modeli yüklendi · GPU istendi: ${settings.useGpu}'),
            onModelError: (e, _, _) {
              EventLog.instance.add('HATA', 'Model: $e');
              if (mounted) setState(() => _perf = 'Model hatası: $e');
            },
          ),
          if (_banner.isNotEmpty)
            Align(
              alignment: Alignment.topCenter,
              child: Container(
                margin: const EdgeInsets.only(top: 12),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(12)),
                child: Text(_banner, style: const TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.bold)),
              ),
            ),
          // Şu an görülen (oylamayı geçen) bütün levhalar; uyarı sırası beklemeden hepsi aynı anda görünür.
          if (_seen.isNotEmpty)
            Positioned(
              left: 8,
              bottom: 52,
              child: Wrap(spacing: 6, runSpacing: 4, children: [
                for (final n in _seen.toList()..sort())
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: n == otherSign ? Colors.blueGrey.shade700 : Colors.orange.shade800,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(label(n), style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
                  ),
              ]),
            ),
          Positioned(
            left: 8,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(8)),
              child: Text('$_perf · ${settings.useGpu ? 'GPU' : 'CPU'} · oylama ${_voting.minHits}/${_voting.window}',
                  style: const TextStyle(color: Colors.white)),
            ),
          ),
          Positioned(
            right: 8,
            bottom: 8,
            child: IconButton.filledTonal(
              iconSize: 32,
              icon: Icon(settings.sound ? Icons.volume_up : Icons.volume_off),
              onPressed: () => settings.set('ses ${settings.sound ? 'kapalı' : 'açık'}', () => settings.sound = !settings.sound),
            ),
          ),
        ]),
      );
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: settings,
        builder: (context, _) => ListView(padding: const EdgeInsets.all(16), children: [
          Text('Güven eşiği: ${settings.minConf.toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleMedium),
          const Text(
            'Model bu orandan emin değilse levha sayılmaz. Yükseltmek yanlış alarmı azaltır ama levhaları daha geç algılatır. '
            'Hız levhaları en az 0,65, yaya geçidi bilgi levhası en az 0,70 ister.',
          ),
          Slider(
            value: settings.minConf,
            min: 0.3,
            max: 0.8,
            divisions: 10,
            label: settings.minConf.toStringAsFixed(2),
            onChanged: (v) => settings.set(null, () => settings.minConf = v),
            onChangeEnd: (v) => settings.set('güven eşiği ${v.toStringAsFixed(2)}', () {}),
          ),
          SwitchListTile(
            title: const Text('Uzak/küçük levhaları yoksay'),
            subtitle: const Text('Görüntü yüksekliğinin %5\'inden küçük kutular sayılmaz (yanlış alarmın ana kaynağı). Levha yaklaşınca yine algılanır.'),
            value: settings.ignoreSmall,
            onChanged: (v) => settings.set('küçük levhaları yoksay: ${v ? 'açık' : 'kapalı'}', () => settings.ignoreSmall = v),
          ),
          SwitchListTile(
            title: const Text('Sesli uyarı'),
            value: settings.sound,
            onChanged: (v) => settings.set('ses ${v ? 'açık' : 'kapalı'}', () => settings.sound = v),
          ),
          SwitchListTile(
            title: const Text('GPU kullan'),
            subtitle: const Text('Kapalıysa model işlemcide çalışır. Hız karşılaştırması için.'),
            value: settings.useGpu,
            onChanged: (v) => settings.set('GPU ${v ? 'açık' : 'kapalı'}', () => settings.useGpu = v),
          ),
          const Divider(),
          const ListTile(title: Text('Model'), subtitle: Text(kModelName)),
          const ListTile(
            title: Text('Veri setleri'),
            subtitle: Text('Hootbu, "Traffic-Sign-Recognition-V2-Turkiye", Roboflow Universe, CC BY 4.0\n'
                '"trafik levhaları", trafik isaretleri çalışma alanı, Roboflow Universe, CC BY 4.0'),
          ),
          const ListTile(
            title: Text('Not'),
            subtitle: Text('Deneysel öğrenci projesidir; güvenlik sistemi değildir. Ayarlar uygulama kapanınca varsayılana döner.'),
          ),
        ]),
      );
}
