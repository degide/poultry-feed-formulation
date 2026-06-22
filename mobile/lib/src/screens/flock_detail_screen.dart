import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../theme.dart';
import '../widgets/async_builder.dart';
import '../widgets/ui.dart';
import 'formulate_screen.dart';
import 'formulation_detail_screen.dart';

class FlockDetailScreen extends StatefulWidget {
  const FlockDetailScreen({super.key, required this.flock});
  final Flock flock;

  @override
  State<FlockDetailScreen> createState() => _FlockDetailScreenState();
}

class _FlockDetailScreenState extends State<FlockDetailScreen> {
  late Future<List<FormulationSummary>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = context.read<Session>().repo.history(widget.flock.id);
  }

  Future<void> _formulate() async {
    await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => FormulateScreen(flock: widget.flock)),
    );
    if (mounted) setState(_reload);
  }

  @override
  Widget build(BuildContext context) {
    final f = widget.flock;
    final isLayer = f.type == 'layer';
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: Text(f.name)),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _formulate,
        icon: const Icon(Icons.science_outlined),
        label: const Text('New formulation'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_reload),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            AppCard(
              child: Row(
                children: [
                  IconBadge(
                    isLayer ? Icons.egg_outlined : Icons.set_meal_outlined,
                    color: isLayer ? AppColors.accent : null,
                    size: 52,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${isLayer ? 'Layer' : 'Broiler'} flock',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 4),
                        Text('${f.ageWeeks} weeks old · ${f.size} birds',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: scheme.onSurfaceVariant)),
                        if (f.previousFormulationId != null) ...[
                          const SizedBox(height: 8),
                          Pill('Baseline ration #${f.previousFormulationId}',
                              icon: Icons.flag_outlined),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            const SectionHeader('Past formulations'),
            AsyncBuilder<List<FormulationSummary>>(
              future: _future,
              onRetry: () => setState(_reload),
              builder: (context, items) {
                if (items.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 30),
                    child: EmptyState(
                      icon: Icons.science_outlined,
                      title: 'No formulations yet',
                      message: 'Tap "New formulation" to generate a ration.',
                    ),
                  );
                }
                return Column(
                  children: items.map((s) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: AppCard(
                        padding: const EdgeInsets.all(14),
                        onTap: () async {
                          await Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) =>
                                FormulationDetailScreen(formulationId: s.id),
                          ));
                          if (mounted) setState(_reload);
                        },
                        child: Row(
                          children: [
                            IconBadge(
                              s.isSelected
                                  ? Icons.check_circle
                                  : Icons.receipt_long_outlined,
                              size: 44,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(children: [
                                    Text('${s.cost.toStringAsFixed(1)} RWF/kg',
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleMedium),
                                    const SizedBox(width: 8),
                                    if (s.isSelected)
                                      const Pill('Active', icon: Icons.check),
                                  ]),
                                  const SizedBox(height: 2),
                                  Text(
                                      '${s.generatedBy} · DTSI ${s.dtsi.toStringAsFixed(1)} · ${s.createdAt.substring(0, 10)}',
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodySmall
                                          ?.copyWith(
                                              color: scheme.onSurfaceVariant)),
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_right,
                                color: scheme.onSurfaceVariant),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
