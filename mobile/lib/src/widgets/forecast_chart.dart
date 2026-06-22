import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme.dart';

class ForecastChart extends StatelessWidget {
  const ForecastChart({super.key, required this.forecast});
  final IngredientForecast forecast;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AspectRatio(
      aspectRatio: 2.0,
      child: CustomPaint(
        painter: _LinePainter(
          history: forecast.history,
          forecast: forecast.forecast,
          line: scheme.primary,
          forecastLine: AppColors.accent,
          axis: scheme.outlineVariant,
          label: scheme.onSurfaceVariant,
        ),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _LinePainter extends CustomPainter {
  _LinePainter({
    required this.history,
    required this.forecast,
    required this.line,
    required this.forecastLine,
    required this.axis,
    required this.label,
  });

  final List<ForecastPoint> history;
  final List<ForecastPoint> forecast;
  final Color line, forecastLine, axis, label;

  @override
  void paint(Canvas canvas, Size size) {
    const padL = 46.0, padB = 18.0, padT = 12.0, padR = 10.0;
    final plot = Rect.fromLTRB(padL, padT, size.width - padR, size.height - padB);

    final pts = [...history, ...forecast];
    if (pts.length < 2) return;
    final n = pts.length;

    double minY = pts.map((p) => p.lower).reduce(math.min);
    double maxY = pts.map((p) => p.upper).reduce(math.max);
    if (maxY == minY) maxY = minY + 1;
    final pad = (maxY - minY) * 0.12;
    minY -= pad; maxY += pad;

    Offset px(int i, double v) => Offset(
          plot.left + plot.width * i / (n - 1),
          plot.bottom - (v - minY) / (maxY - minY) * plot.height,
        );

    // gridlines + y labels
    for (var i = 0; i <= 3; i++) {
      final fy = minY + (maxY - minY) * i / 3;
      final y = plot.bottom - plot.height * i / 3;
      canvas.drawLine(Offset(plot.left, y), Offset(plot.right, y),
          Paint()..color = axis.withValues(alpha: 0.5)..strokeWidth = 1);
      _text(canvas, fy.toStringAsFixed(0), Offset(2, y - 6), 9);
    }

    final hLen = history.length;

    // divider where forecast begins
    if (forecast.isNotEmpty && hLen > 0) {
      final x = px(hLen - 1, history.last.price).dx;
      final dashPaint = Paint()
        ..color = axis
        ..strokeWidth = 1;
      var y = plot.top;
      while (y < plot.bottom) {
        canvas.drawLine(Offset(x, y), Offset(x, math.min(y + 4, plot.bottom)), dashPaint);
        y += 7;
      }
    }

    // forecast uncertainty band
    if (forecast.isNotEmpty && hLen > 0) {
      final bandPath = Path();
      final start = hLen - 1;
      final s = px(start, history.last.price);
      bandPath.moveTo(s.dx, s.dy);
      for (var i = 0; i < forecast.length; i++) {
        final o = px(hLen + i, forecast[i].upper);
        bandPath.lineTo(o.dx, o.dy);
      }
      for (var i = forecast.length - 1; i >= 0; i--) {
        final o = px(hLen + i, forecast[i].lower);
        bandPath.lineTo(o.dx, o.dy);
      }
      bandPath.close();
      canvas.drawPath(bandPath, Paint()..color = forecastLine.withValues(alpha: 0.14));
    }

    // gradient fill under history
    final fill = Path()..moveTo(px(0, history.first.price).dx, plot.bottom);
    for (var i = 0; i < history.length; i++) {
      final o = px(i, history[i].price);
      fill.lineTo(o.dx, o.dy);
    }
    fill.lineTo(px(history.length - 1, history.last.price).dx, plot.bottom);
    fill.close();
    canvas.drawPath(
      fill,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [line.withValues(alpha: 0.28), line.withValues(alpha: 0.0)],
        ).createShader(plot),
    );

    // history line
    final hpath = Path();
    for (var i = 0; i < history.length; i++) {
      final o = px(i, history[i].price);
      i == 0 ? hpath.moveTo(o.dx, o.dy) : hpath.lineTo(o.dx, o.dy);
    }
    canvas.drawPath(
      hpath,
      Paint()..color = line..strokeWidth = 2.4..style = PaintingStyle.stroke,
    );

    // forecast dashed line + markers
    if (forecast.isNotEmpty && hLen > 0) {
      final fp = Paint()
        ..color = forecastLine
        ..strokeWidth = 2.4
        ..style = PaintingStyle.stroke;
      var prev = px(hLen - 1, history.last.price);
      for (var i = 0; i < forecast.length; i++) {
        final o = px(hLen + i, forecast[i].price);
        _dashed(canvas, prev, o, fp);
        canvas.drawCircle(o, 3.5, Paint()..color = forecastLine);
        canvas.drawCircle(o, 3.5,
            Paint()..color = Colors.white..style = PaintingStyle.stroke..strokeWidth = 1.4);
        prev = o;
      }
    }
  }

  void _dashed(Canvas c, Offset a, Offset b, Paint p) {
    const dash = 5.0, gap = 3.0;
    final total = (b - a).distance;
    if (total == 0) return;
    final dir = (b - a) / total;
    var d = 0.0;
    while (d < total) {
      final s = a + dir * d;
      final e = a + dir * math.min(d + dash, total);
      c.drawLine(s, e, p);
      d += dash + gap;
    }
  }

  void _text(Canvas c, String s, Offset o, double size) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: label, fontSize: size)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(c, o);
  }

  @override
  bool shouldRepaint(covariant _LinePainter old) =>
      old.history != history || old.forecast != forecast;
}
