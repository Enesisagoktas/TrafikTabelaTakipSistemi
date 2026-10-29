import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:ultralytics_yolo/ultralytics_yolo.dart';

import 'alerts.dart';
import 'event_log.dart';

/// Uygulamaya gömülü, cevabı bilinen test fotoğrafları (`assets/test_images/<sınıf>.jpg`; "bos" = levha yok).
/// PC'de v5b modeli (.pt ve telefondaki FP16 .tflite) hepsini doğru buluyor; telefonda fark çıkarsa sorun model değil entegrasyondur.
const _cases = [
  'stop', 'noentry', 'giveway', 'speed30', 'speed50', 'speed70',
  'pedestrian_info', 'keepright', 'priorityroad', 'schoolpassing', 'bos',
];

class _Result {
  _Result(this.bytes, this.boxes, this.width, this.height, this.ok, this.ms);

  final Uint8List bytes;
  final List<Map> boxes;
  final double width, height;
  final bool ok;
  final int ms;
}

class ModelTestScreen extends StatefulWidget {
  const ModelTestScreen({super.key, required this.modelPath, required this.useGpu});

  final String modelPath;
  final bool useGpu;

  @override
  State<ModelTestScreen> createState() => _ModelTestScreenState();
}

class _ModelTestScreenState extends State<ModelTestScreen> {
  final _results = <String, _Result>{};
  bool _running = false;

  Future<void> _run() async {
    setState(() {
      _running = true;
      _results.clear();
    });
    final log = EventLog.instance;
    final yolo = YOLO(modelPath: widget.modelPath, task: YOLOTask.detect, useGpu: widget.useGpu);
    try {
      await yolo.loadModel();
      log.add('TEST', 'Model yüklendi (GPU istendi: ${widget.useGpu})');
      for (final c in _cases) {
        final bytes = (await rootBundle.load('assets/test_images/$c.jpg')).buffer.asUint8List();
        final sw = Stopwatch()..start();
        final r = await yolo.predict(bytes, confidenceThreshold: 0.25);
        final ms = sw.elapsedMilliseconds;
        final boxes = (r['boxes'] as List? ?? const []).cast<Map>().toList()
          ..sort((a, b) => (b['confidence'] as num).compareTo(a['confidence'] as num));
        final size = (r['imageSize'] as Map?) ?? const {'width': 1, 'height': 1};
        final top = boxes.isEmpty ? null : boxes.first;
        final got = top?['className']?.toString();
        final ok = c == 'bos' ? boxes.isEmpty : got == c;
        _results[c] = _Result(bytes, boxes, (size['width'] as num).toDouble(), (size['height'] as num).toDouble(), ok, ms);
        final conf = top == null ? '' : ' ${(top['confidence'] as num).toStringAsFixed(2)}';
        log.add('TEST', '$c -> ${got ?? 'yok'}$conf ${ok ? 'DOĞRU' : 'YANLIŞ'} ($ms ms, ${boxes.length} kutu)');
        if (mounted) setState(() {});
      }
      log.add('TEST', 'Sonuç: ${_results.values.where((r) => r.ok).length}/${_cases.length} doğru');
    } catch (e) {
      log.add('HATA', 'Model testi: $e');
    } finally {
      await yolo.dispose();
      if (mounted) setState(() => _running = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final okCount = _results.values.where((r) => r.ok).length;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
        child: Row(children: [
          FilledButton.icon(
            onPressed: _running ? null : _run,
            icon: _running
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.play_arrow),
            label: Text(_running ? 'Test ediliyor…' : 'Testi başlat'),
          ),
          const SizedBox(width: 16),
          if (_results.isNotEmpty)
            Text('$okCount / ${_results.length} doğru',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: okCount == _results.length ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
          const Spacer(),
          Flexible(
            child: Text('Gömülü ${_cases.length} fotoğraf: 10 levha + 1 levhasız. Hepsi doğruysa model telefonda doğru çalışıyor.',
                style: const TextStyle(fontSize: 12, color: Colors.black54)),
          ),
        ]),
      ),
      Expanded(
        child: GridView.extent(
          maxCrossAxisExtent: 260,
          padding: const EdgeInsets.all(8),
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 1.1,
          children: [for (final c in _cases) _card(c, _results[c])],
        ),
      ),
    ]);
  }

  Widget _card(String c, _Result? r) {
    final expected = c == 'bos' ? 'levha yok' : (signs[c]?.text ?? c);
    final top = (r == null || r.boxes.isEmpty) ? null : r.boxes.first;
    final found = top == null ? 'yok' : '${signs[top['className']]?.text ?? top['className']} ${(top['confidence'] as num).toStringAsFixed(2)}';
    return Card(
      clipBehavior: Clip.antiAlias,
      color: r == null ? null : (r.ok ? Colors.green.shade50 : Colors.red.shade50),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Expanded(
          child: r == null
              ? Image.asset('assets/test_images/$c.jpg', fit: BoxFit.contain)
              : Center(
                  child: AspectRatio(
                    aspectRatio: r.width / r.height,
                    child: Stack(fit: StackFit.expand, children: [
                      Image.memory(r.bytes, fit: BoxFit.fill),
                      CustomPaint(painter: _BoxPainter(r.boxes)),
                    ]),
                  ),
                ),
        ),
        Padding(
          padding: const EdgeInsets.all(6),
          child: Text(
            r == null ? 'Beklenen: $expected' : '${r.ok ? '✓' : '✗'} Beklenen: $expected\nBulunan: $found · ${r.ms} ms',
            style: const TextStyle(fontSize: 12),
          ),
        ),
      ]),
    );
  }
}

class _BoxPainter extends CustomPainter {
  _BoxPainter(this.boxes);

  final List<Map> boxes;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = Colors.yellowAccent;
    for (final b in boxes) {
      double v(String k) => (b[k] as num).toDouble();
      canvas.drawRect(
        Rect.fromLTRB(v('x1_norm') * size.width, v('y1_norm') * size.height, v('x2_norm') * size.width, v('y2_norm') * size.height),
        p,
      );
    }
  }

  @override
  bool shouldRepaint(_BoxPainter old) => old.boxes != boxes;
}
