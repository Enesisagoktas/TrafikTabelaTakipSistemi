import 'package:audio_session/audio_session.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import 'alerts.dart';

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
  runApp(const MaterialApp(title: 'Trafik Asistanı', debugShowCheckedModeBanner: false, home: DetectorScreen()));
}

class DetectorScreen extends StatefulWidget {
  const DetectorScreen({super.key});

  @override
  State<DetectorScreen> createState() => _DetectorScreenState();
}

class _DetectorScreenState extends State<DetectorScreen> {
  // Hız levhaları birbirine, pedestrian_info başka mavi levhalara karışıyor (YOL_HARITASI, Hafta 2 sonuçları).
  final _filter = DetectionFilter(classMinConf: {'speed30': 0.65, 'speed50': 0.65, 'speed70': 0.65, 'pedestrian_info': 0.7});
  final _cooldown = Cooldown();
  final _queue = AlertQueue();
  final _player = AudioPlayer();
  bool _speaking = false;
  String _banner = '';
  // Hafta 1 ölçümü: FPS / çıkarım süresi ve GPU-CPU karşılaştırması.
  bool _gpu = true;
  String _perf = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _showDisclaimer());
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  void _onResult(List<YOLOResult> results) {
    final now = DateTime.now();
    final seen = _filter.update(results.map((r) => (name: r.className, conf: r.confidence, height: r.normalizedBox.height)));
    for (final n in _cooldown.update(seen, now)) {
      _queue.add(n, signs[n]?.priority ?? 3, now);
    }
    _speak();
  }

  /// Sıradaki uyarıları tek tek çalar; aynı anda yalnızca bir ses (risk 43).
  Future<void> _speak() async {
    if (_speaking) return;
    _speaking = true;
    try {
      for (var n = _queue.next(DateTime.now()); n != null; n = _queue.next(DateTime.now())) {
        if (mounted) setState(() => _banner = signs[n]?.text ?? n!);
        await _player.setAsset('assets/sounds/$n.wav');
        await _player.play(); // çalma bitince döner
      }
    } finally {
      _speaking = false;
    }
  }

  Future<void> _showDisclaimer() => showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Deneysel prototip'),
          content: const Text(
            'Bu uygulama sürücüye yardımcı olmak için geliştirilmiş bir öğrenci projesidir; güvenlik sistemi değildir. '
            'Trafik levhalarına ve kurallara her zaman kendiniz dikkat edin.\n\n'
            'Veri seti: Hootbu, "Traffic-Sign-Recognition-V2-Turkiye", Roboflow Universe, CC BY 4.0.',
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Anladım'))],
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.black,
        body: Stack(children: [
          YOLOView(
            key: ValueKey(_gpu), // useGpu yalnızca açılışta okunur; değişince görünüm yeniden kurulur
            modelPath: 'assets/models/levha.tflite',
            task: YOLOTask.detect,
            confidenceThreshold: 0.4,
            useGpu: _gpu,
            onResult: _onResult,
            onPerformanceMetrics: (m) => setState(
              () => _perf = '${m.fps.toStringAsFixed(1)} FPS · ${m.processingTimeMs.toStringAsFixed(0)} ms',
            ),
            onModelError: (e, _, _) => setState(() => _perf = 'Model hatası: $e'),
          ),
          Align(
            alignment: Alignment.bottomRight,
            child: Container(
              margin: const EdgeInsets.all(12),
              padding: const EdgeInsets.only(left: 12),
              color: Colors.black54,
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(_perf, style: const TextStyle(color: Colors.white)),
                TextButton(
                  onPressed: () => setState(() {
                    _gpu = !_gpu;
                    _perf = '';
                  }),
                  child: Text(_gpu ? 'GPU' : 'CPU'),
                ),
              ]),
            ),
          ),
          if (_banner.isNotEmpty)
            Align(
              alignment: Alignment.topCenter,
              child: Container(
                margin: const EdgeInsets.only(top: 16),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(12)),
                child: Text(_banner, style: const TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.bold)),
              ),
            ),
        ]),
      );
}
