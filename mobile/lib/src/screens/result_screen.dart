import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../theme.dart';
import '../widgets/pareto_chart.dart';
import '../widgets/ui.dart';
import 'formulation_detail_screen.dart';

class ResultScreen extends StatefulWidget {
  const ResultScreen({super.key, required this.jobId, required this.flock});
  final String jobId;
  final Flock flock;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  Timer? _timer;
  JobResult? _job;
  String? _error;
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(milliseconds: 1500), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final job = await context.read<Session>().repo.job(widget.jobId);
      if (!mounted) return;
      setState(() => _job = job);
      if (job.isDone) _timer?.cancel();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
      _timer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = _job;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(_changed),
        ),
        title: const Text('Optimisation result'),
      ),
      body: _error != null
          ? _centered(Icons.error_outline, _error!)
          : job == null || !job.isDone
              ? _running(job)
              : job.state == 'failed'
                  ? _centered(Icons.warning_amber, job.error ?? 'Optimisation failed')
                  : _done(job),
    );
  }

  Widget _running(JobResult? job) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
                height: 46, width: 46, child: CircularProgressIndicator(strokeWidth: 3)),
            const SizedBox(height: 20),
            Text(job?.state == 'running' ? 'Running NSGA-II…' : 'Queued…',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Searching for least-cost rations',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ],
        ),
      );

  Widget _centered(IconData icon, String msg) => EmptyState(
        icon: icon,
        title: 'Something went wrong',
        message: msg,
      );

  Widget _done(JobResult job) {
    final front = [...job.nsga2Front]..sort((a, b) => a.cost.compareTo(b.cost));
    final lp = job.lpSolution;
    final scheme = Theme.of(context).colorScheme;
    final cheapest = front.isNotEmpty
        ? front.first
        : lp; // for the headline number

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      children: [
        if (cheapest != null)
          AppCard(
            child: Row(
              children: [
                const IconBadge(Icons.savings_outlined, size: 48),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Lowest cost found',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: scheme.onSurfaceVariant)),
                      Text('${cheapest.cost.toStringAsFixed(1)} RWF/kg',
                          style: Theme.of(context).textTheme.headlineSmall),
                    ],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 14),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Pareto front', style: Theme.of(context).textTheme.titleMedium),
              Text('${front.length} NSGA-II solutions · cost vs ration change',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant)),
              const SizedBox(height: 10),
              ParetoChart(front: front, lp: lp),
              const SizedBox(height: 10),
              Wrap(spacing: 18, runSpacing: 6, children: [
                _legend(scheme.primary, 'NSGA-II solution'),
                if (lp != null) _legend(AppColors.accent, 'LP benchmark'),
              ]),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const SectionHeader('Solutions (cheapest first)'),
        if (lp != null) _solutionTile(lp, isLp: true),
        ...front.map((p) => _solutionTile(p)),
      ],
    );
  }

  Widget _legend(Color c, String label) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 12, height: 12, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ],
      );

  Widget _solutionTile(ParetoPoint p, {bool isLp = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: AppCard(
        padding: const EdgeInsets.all(14),
        onTap: () async {
          final result = await Navigator.of(context).push<bool>(MaterialPageRoute(
            builder: (_) => FormulationDetailScreen(formulationId: p.formulationId),
          ));
          if (result == true) _changed = true;
        },
        child: Row(
          children: [
            IconBadge(
              isLp ? Icons.straighten : Icons.scatter_plot_outlined,
              color: isLp ? AppColors.accent : null,
              size: 44,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${p.cost.toStringAsFixed(1)} RWF/kg',
                      style: Theme.of(context).textTheme.titleMedium),
                  Text('${p.generatedBy} · DTSI ${p.dtsi.toStringAsFixed(2)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            Icon(Icons.chevron_right,
                color: Theme.of(context).colorScheme.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}
