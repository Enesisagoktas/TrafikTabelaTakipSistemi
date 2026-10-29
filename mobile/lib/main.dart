import 'package:audio_session/audio_session.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import 'alerts.dart';
import 'event_log.dart';
import 'model_test.dart';

const kModelPath = 'assets/models/levha.tflite';
const kModelName = 'v2 · YOLO11n · 640 px';

/// Uzak levha sınırı: görüntü yüksekliğinin %5'inden kısa kutular sayılmaz. 10 test videosunda (ml/scripts/esik_tarama.py)
/// v2 ile güven 0,5 → 0,6 ve bu sınır %2,5 → %5 olunca yanlış uyarı 58 → 20, yakalanan levha 25 → 30 oldu (29 Ekim).
const kMinHeight = 0.05;

/// Ayarlar (bellekte tutulur; uygulama yeniden açılınca varsayılana döner).
class Settings extends ChangeNotifier {
  double minConf = 0.6;
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
            'Veri seti: Hootbu, "Traffic-Sign-Recognition-V2-Turkiye", Roboflow Universe, CC BY 4.0.',
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
  String _perf = 'Model yükleniyor…';
  int _frames = 0;
  double _fpsSum = 0, _msSum = 0;
  DateTime _perfSince = DateTime.now();

  DetectionFilter get _activeFilter {
    final key = '${settings.minConf}/${settings.ignoreSmall}';
    if (key != _filterKey) {
      _filterKey = key;
      _filter = DetectionFilter(
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
      EventLog.instance.add('ONAY', '$n (${signs[n]?.text ?? n})');
    }
    for (final n in _cooldown.update(seen, now)) {
      _queue.add(n, signs[n]?.priority ?? 3, now);
    }
    _speak();
  }

  void _onPerf(YOLOPerformanceMetrics m) {
    _frames++;
    _fpsSum += m.fps;
    _msSum += m.processingTimeMs;
    final now = DateTime.now();
    if (now.difference(_perfSince) >= const Duration(seconds: 10)) {
      EventLog.instance.add('PERF',
          '${(_fpsSum / _frames).toStringAsFixed(1)} FPS · ${(_msSum / _frames).toStringAsFixed(0)} ms · ${settings.useGpu ? 'GPU istendi' : 'CPU'}');
      _frames = 0;
      _fpsSum = _msSum = 0;
      _perfSince = now;
    }
    if (mounted) setState(() => _perf = '${m.fps.toStringAsFixed(1)} FPS · ${m.processingTimeMs.toStringAsFixed(0)} ms');
  }

  /// Sıradaki uyarıları tek tek çalar; aynı anda yalnızca bir ses (risk 43).
  Future<void> _speak() async {
    if (_speaking) return;
    _speaking = true;
    try {
      for (var n = _queue.next(DateTime.now()); n != null; n = _queue.next(DateTime.now())) {
        final text = signs[n]?.text ?? n;
        EventLog.instance.add('UYARI', '$text ($n)');
        if (mounted) setState(() => _banner = text);
        if (!settings.sound) continue;
        await _player.setAsset('assets/sounds/$n.wav');
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
          Positioned(
            left: 8,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(8)),
              child: Text('$_perf · ${settings.useGpu ? 'GPU' : 'CPU'}', style: const TextStyle(color: Colors.white)),
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
            title: Text('Veri seti'),
            subtitle: Text('Hootbu, "Traffic-Sign-Recognition-V2-Turkiye", Roboflow Universe, CC BY 4.0'),
          ),
          const ListTile(
            title: Text('Not'),
            subtitle: Text('Deneysel öğrenci projesidir; güvenlik sistemi değildir. Ayarlar uygulama kapanınca varsayılana döner.'),
          ),
        ]),
      );
}
