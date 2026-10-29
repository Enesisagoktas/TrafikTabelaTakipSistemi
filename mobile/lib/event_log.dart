import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Uygulama içi kayıt: bellekte son [_max] satır + oturum dosyası (Kayıtlar > Paylaş ile telefondan gönderilir).
class EventLog extends ChangeNotifier {
  EventLog._();
  static final instance = EventLog._();
  static const _max = 3000;

  final entries = <LogEntry>[];
  File? _file;
  IOSink? _sink;

  Future<void> init() async {
    final dir = Directory('${(await getApplicationDocumentsDirectory()).path}/kayitlar');
    await dir.create(recursive: true);
    _file = File('${dir.path}/oturum_${_stamp(DateTime.now())}.txt');
    _sink = _file!.openWrite(mode: FileMode.append);
  }

  void add(String type, String message) {
    final e = LogEntry(DateTime.now(), type, message);
    entries.add(e);
    if (entries.length > _max) entries.removeAt(0);
    _sink?.writeln(e.line);
    notifyListeners();
  }

  Future<void> share() async {
    await _sink?.flush();
    final f = _file;
    if (f == null) return;
    await SharePlus.instance.share(
      ShareParams(files: [XFile(f.path, mimeType: 'text/plain')], subject: 'Trafik Asistanı kayıtları'),
    );
  }

  /// Yalnızca ekrandaki listeyi temizler; oturum dosyası korunur.
  void clearView() {
    entries.clear();
    notifyListeners();
  }
}

class LogEntry {
  LogEntry(this.time, this.type, this.message);

  final DateTime time;
  final String type;
  final String message;

  String get line => '${clock(time)}\t$type\t$message';
}

String _two(int v) => v.toString().padLeft(2, '0');
String clock(DateTime t) => '${_two(t.hour)}:${_two(t.minute)}:${_two(t.second)}.${t.millisecond ~/ 100}';
String _stamp(DateTime t) => '${t.year}${_two(t.month)}${_two(t.day)}_${_two(t.hour)}${_two(t.minute)}${_two(t.second)}';

const _typeColors = {
  'UYARI': Colors.red,
  'ONAY': Colors.orange,
  'HAM': Colors.blueGrey,
  'PERF': Colors.blue,
  'MODEL': Colors.green,
  'HATA': Colors.purple,
  'TEST': Colors.teal,
  'AYAR': Colors.brown,
};

class LogsScreen extends StatelessWidget {
  const LogsScreen({super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: EventLog.instance,
        builder: (context, _) {
          final items = EventLog.instance.entries.reversed.toList();
          return Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(children: [
                Text('${items.length} kayıt (en yeni üstte)', style: Theme.of(context).textTheme.titleMedium),
                const Spacer(),
                FilledButton.icon(
                  onPressed: EventLog.instance.share,
                  icon: const Icon(Icons.share),
                  label: const Text('Paylaş'),
                ),
                const SizedBox(width: 8),
                TextButton(onPressed: EventLog.instance.clearView, child: const Text('Ekranı temizle')),
              ]),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Text(
                'UYARI: söylenen uyarı · ONAY: levha oylamayı geçti (5 karenin 3\'ü; 8 FPS altında 3 karenin 2\'si) · HAM: modelin ham tespiti (sınıf başına saniyede en fazla 1) · PERF: 10 sn ortalama hız · AYAR: ayar değişikliği',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ),
            Expanded(
              child: ListView.builder(
                itemCount: items.length,
                itemBuilder: (context, i) {
                  final e = items[i];
                  final color = _typeColors[e.type] ?? Colors.black54;
                  return ListTile(
                    dense: true,
                    visualDensity: VisualDensity.compact,
                    leading: Container(
                      width: 64,
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(6)),
                      child: Text(e.type, textAlign: TextAlign.center, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
                    ),
                    title: Text(e.message),
                    trailing: Text(clock(e.time), style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()])),
                  );
                },
              ),
            ),
          ]);
        },
      );
}
