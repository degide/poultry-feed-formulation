import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../widgets/async_builder.dart';
import '../widgets/ui.dart';

class FormulationDetailScreen extends StatefulWidget {
  const FormulationDetailScreen({super.key, required this.formulationId});
  final int formulationId;

  @override
  State<FormulationDetailScreen> createState() => _FormulationDetailScreenState();
}

class _FormulationDetailScreenState extends State<FormulationDetailScreen> {
  late Future<FormulationDetail> _future;
  bool _changed = false;
  bool _selecting = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = context.read<Session>().repo.formulation(widget.formulationId);
  }

  Future<void> _select() async {
    setState(() => _selecting = true);
    try {
      await context.read<Session>().repo.select(widget.formulationId);
      _changed = true;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Set as the active ration for this flock')));
        setState(_reload);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _selecting = false);
    }
  }

  void _copyCsv(FormulationDetail d) {
    final b = StringBuffer('ingredient,proportion_percent\n');
    for (final ing in d.ingredients) {
      b.writeln('${ing.name},${ing.percent.toStringAsFixed(2)}');
    }
    b.writeln('total_cost_per_kg_rwf,${d.cost.toStringAsFixed(2)}');
    b.writeln('dtsi_score,${d.dtsi.toStringAsFixed(2)}');
    Clipboard.setData(ClipboardData(text: b.toString()));
    ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ration copied as CSV')));
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvoked: (didPop) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).pop(_changed),
          ),
          title: const Text('Ration detail'),
        ),
        body: AsyncBuilder<FormulationDetail>(
          future: _future,
          onRetry: () => setState(_reload),
          builder: (context, d) {
            final sorted = [...d.ingredients]
              ..sort((a, b) => b.percent.compareTo(a.percent));
            final scheme = Theme.of(context).colorScheme;
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Pill(d.generatedBy, icon: Icons.memory),
                          const Spacer(),
                          if (d.isSelected)
                            Pill('Active', icon: Icons.check_circle),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: _Metric(
                              label: 'Cost',
                              value: '${d.cost.toStringAsFixed(1)}',
                              unit: 'RWF/kg',
                              icon: Icons.payments_outlined,
                            ),
                          ),
                          Container(
                              width: 1, height: 44, color: scheme.outlineVariant),
                          Expanded(
                            child: _Metric(
                              label: 'Transition (DTSI)',
                              value: d.dtsi.toStringAsFixed(2),
                              icon: Icons.swap_horiz,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                const SectionHeader('Composition'),
                AppCard(
                  child: Column(
                    children: [
                      for (final ing in sorted)
                        _IngredientBar(name: ing.name, percent: ing.percent),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _copyCsv(d),
                        icon: const Icon(Icons.copy_all),
                        label: const Text('Copy CSV'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: (d.isSelected || _selecting) ? null : _select,
                        icon: _selecting
                            ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.check_circle_outline),
                        label: Text(d.isSelected ? 'Active' : 'Set active'),
                      ),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, required this.icon, this.unit});
  final String label;
  final String value;
  final String? unit;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(icon, size: 16, color: scheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Expanded(
            child: Text(label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.onSurfaceVariant)),
          ),
        ]),
        const SizedBox(height: 6),
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(value, style: Theme.of(context).textTheme.titleLarge),
            if (unit != null) ...[
              const SizedBox(width: 4),
              Text(unit!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant)),
            ],
          ],
        ),
      ],
    );
  }
}

class _IngredientBar extends StatelessWidget {
  const _IngredientBar({required this.name, required this.percent});
  final String name;
  final double percent;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(name)),
              Text('${percent.toStringAsFixed(1)}%',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: (percent / 100).clamp(0.0, 1.0),
              minHeight: 8,
            ),
          ),
        ],
      ),
    );
  }
}
