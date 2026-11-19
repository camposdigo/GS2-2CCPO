import 'dart:math' as math;
import 'package:flutter/material.dart';

Map<String, dynamic> asMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};
String readable(dynamic value) => value is Map
    ? (value['label'] ??
              value['level'] ??
              value['description'] ??
              value['value'] ??
              value)
          .toString()
    : value?.toString() ?? 'Não informado';

class InfoCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  const InfoCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Icon(icon, size: 30, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.labelLarge),
                const SizedBox(height: 6),
                Text(value, style: Theme.of(context).textTheme.headlineSmall),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class Notice extends StatelessWidget {
  final String text;
  final IconData icon;
  const Notice(this.text, {super.key, this.icon = Icons.info_outline});
  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.secondaryContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon),
          const SizedBox(width: 12),
          Expanded(child: Text(text)),
        ],
      ),
    ),
  );
}

class WaterChart extends StatelessWidget {
  final List<dynamic> series;
  const WaterChart({super.key, required this.series});
  @override
  Widget build(BuildContext context) {
    final rows = series
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
    final observed = rows.where((row) => row['observed'] is num).toList();
    if (rows.isEmpty) return const Notice('Série hídrica indisponível.');
    final summary = observed.isEmpty
        ? 'Gráfico sem observações disponíveis.'
        : 'Volume observado: ${observed.first['observed']} a ${observed.last['observed']} por cento, de ${observed.first['date']} a ${observed.last['date']}.';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Histórico e previsão',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Volume útil (%) · verde: observado · laranja: previsão',
            ),
            const SizedBox(height: 16),
            Semantics(
              label: summary,
              image: true,
              child: SizedBox(
                height: 180,
                width: double.infinity,
                child: CustomPaint(painter: _SeriesPainter(rows)),
              ),
            ),
            const SizedBox(height: 8),
            Text('${rows.first['date']} — ${rows.last['date']}'),
            Text(summary),
          ],
        ),
      ),
    );
  }
}

class _SeriesPainter extends CustomPainter {
  final List<Map<String, dynamic>> rows;
  _SeriesPainter(this.rows);
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = const Color(0xffdeded5)
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    for (final entry in {
      'observed': const Color(0xff175847),
      'forecast': const Color(0xffb15b12),
    }.entries) {
      final line = Path();
      bool started = false;
      for (var i = 0; i < rows.length; i++) {
        final value = rows[i][entry.key];
        if (value is! num || !value.isFinite) {
          started = false;
          continue;
        }
        final x = size.width * i / math.max(1, rows.length - 1);
        final y = size.height * (1 - value.clamp(0, 100) / 100);
        if (!started) {
          line.moveTo(x, y);
          started = true;
        } else {
          line.lineTo(x, y);
        }
        canvas.drawCircle(
          Offset(x, y),
          entry.key == 'forecast' ? 3 : 1.2,
          Paint()..color = entry.value,
        );
      }
      canvas.drawPath(
        line,
        Paint()
          ..color = entry.value
          ..strokeWidth = 2.5
          ..style = PaintingStyle.stroke,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _SeriesPainter oldDelegate) =>
      oldDelegate.rows != rows;
}
