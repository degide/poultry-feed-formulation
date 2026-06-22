import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme.dart';

/// Scatter plot of the Pareto front: x = DTSI (ration change), y = cost.
/// NSGA-II solutions are joined by a faint frontier line; the LP benchmark is a
/// star. A selected/highlighted point gets an accent ring.

class ParetoChart extends StatelessWidget {
  const ParetoChart({super.key, required this.front, this.lp, this.selectedId});

  final List<ParetoPoint> front;
  final ParetoPoint? lp;
  final int? selectedId;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AspectRatio(
      aspectRatio: 1.5,
      child: CustomPaint(
        painter: _ParetoPainter(
          front: front,
          lp: lp,
          selectedId: selectedId,
          point: scheme.primary,
          accent: AppColors.accent,
          axis: scheme.outlineVariant,
          label: scheme.onSurfaceVariant,
        ),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _ParetoPainter extends CustomPainter {
  _ParetoPainter({
    required this.front,
    required this.lp,
    required this.selectedId,
    required this.point,
    required this.accent,
    required this.axis,
    required this.label,
  });

  final List<ParetoPoint> front;
  final ParetoPoint? lp;
  final int? selectedId;
  final Color point, accent, axis, label;

  @override
  void paint(Canvas canvas, Size size) {
    const padL = 50.0, padB = 30.0, padT = 14.0, padR = 14.0;
    final plot = Rect.fromLTRB(padL, padT, size.width - padR, size.height - padB);

    final all = [...front, if (lp != null) lp!];
    if (all.isEmpty) return;

    double minX = all.map((p) => p.dtsi).reduce(math.min);
    double maxX = all.map((p) => p.dtsi).reduce(math.max);
    double minY = all.map((p) => p.cost).reduce(math.min);
    double maxY = all.map((p) => p.cost).reduce(math.max);
    if (maxX == minX) maxX = minX + 1;
    if (maxY == minY) maxY = minY + 1;
    final pX = (maxX - minX) * 0.1, pY = (maxY - minY) * 0.12;
    minX -= pX; maxX += pX; minY -= pY; maxY += pY;

    Offset toPx(double x, double y) => Offset(
          plot.left + (x - minX) / (maxX - minX) * plot.width,
          plot.bottom - (y - minY) / (maxY - minY) * plot.height,
        );

    // gridlines + tick labels
    final grid = Paint()
      ..color = axis.withValues(alpha: 0.5)
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final fy = minY + (maxY - minY) * i / 3;
      final y = plot.bottom - plot.height * i / 3;
      canvas.drawLine(Offset(plot.left, y), Offset(plot.right, y), grid);
      _text(canvas, fy.toStringAsFixed(0), Offset(4, y - 6), label, 10);
    }
    for (var i = 0; i <= 3; i++) {
      final fx = minX + (maxX - minX) * i / 3;
      final x = plot.left + plot.width * i / 3;
      _text(canvas, fx.toStringAsFixed(2), Offset(x - 12, plot.bottom + 8), label, 10);
    }

    // axes
    final axisPaint = Paint()..color = axis..strokeWidth = 1.4;
    canvas.drawLine(plot.bottomLeft, plot.bottomRight, axisPaint);
    canvas.drawLine(plot.topLeft, plot.bottomLeft, axisPaint);
    _text(canvas, 'cost (RWF/kg)', const Offset(4, padT - 4), label, 10);
    _text(canvas, 'ration change (DTSI) ->',
        Offset(plot.right - 140, plot.bottom + 16), label, 10);

    // frontier line through sorted NSGA-II points
    if (front.length > 1) {
      final sorted = [...front]..sort((a, b) => a.dtsi.compareTo(b.dtsi));
      final path = Path();
      for (var i = 0; i < sorted.length; i++) {
        final o = toPx(sorted[i].dtsi, sorted[i].cost);
        i == 0 ? path.moveTo(o.dx, o.dy) : path.lineTo(o.dx, o.dy);
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = point.withValues(alpha: 0.35)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }

    // NSGA-II points
    for (final p in front) {
      final isSel = selectedId != null && p.formulationId == selectedId;
      final o = toPx(p.dtsi, p.cost);
      if (isSel) {
        canvas.drawCircle(o, 11, Paint()..color = accent.withValues(alpha: 0.20));
        canvas.drawCircle(o, 6, Paint()..color = accent);
        canvas.drawCircle(
            o, 6, Paint()..color = Colors.white..style = PaintingStyle.stroke..strokeWidth = 2);
      } else {
        canvas.drawCircle(o, 6, Paint()..color = point.withValues(alpha: 0.18));
        canvas.drawCircle(o, 3.6, Paint()..color = point);
      }
    }

    // LP star
    if (lp != null) {
      _star(canvas, toPx(lp!.dtsi, lp!.cost), 7.5, Paint()..color = accent);
    }
  }

  void _star(Canvas c, Offset center, double r, Paint paint) {
    final path = Path();
    for (var i = 0; i < 10; i++) {
      final rad = (i.isEven ? r : r * 0.45);
      final a = -math.pi / 2 + i * math.pi / 5;
      final p = center + Offset(math.cos(a) * rad, math.sin(a) * rad);
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    path.close();
    c.drawPath(path, paint);
  }

  void _text(Canvas c, String s, Offset o, Color color, double size) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: color, fontSize: size)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(c, o);
  }

  @override
  bool shouldRepaint(covariant _ParetoPainter old) =>
      old.front != front || old.lp != lp || old.selectedId != selectedId;
}
