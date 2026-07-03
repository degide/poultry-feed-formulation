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
  const ResultScreen({super.key, required this.jobId, required this.flock, required this.selectedLocation});
  final String jobId;
  final Flock flock;
  final String selectedLocation;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  Timer? _timer;
  JobResult? _job;
  String? _error;
  bool _changed = false;
  List<MarketPrice> _latestPrices = [];
  List<Ingredient> _ingredients = [];
  bool _loadingPrices = true;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(milliseconds: 1500), (_) => _poll());
    _loadPricesAndIngredients();
  }

  Future<void> _loadPricesAndIngredients() async {
    final repo = context.read<Session>().repo;
    try {
      final prices = await repo.latestPrices(widget.selectedLocation);
      final ings = await repo.ingredients();
      if (mounted) {
        setState(() {
          _latestPrices = prices;
          _ingredients = ings;
          _loadingPrices = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadingPrices = false;
        });
      }
    }
  }

  double _costUnderLatest(ParetoPoint p, Map<int, String> names) {
    if (_latestPrices.isEmpty) return 0.0;
    double sum = 0.0;
    p.proportions.forEach((name, prop) {
      final lpPrice = _latestPrices.firstWhere(
        (lp) => names[lp.ingredientId] == name,
        orElse: () => MarketPrice(priceId: 0, ingredientId: 0, pricePerKg: 0, priceDate: '', marketLocation: ''),
      );
      if (lpPrice.pricePerKg > 0) {
        sum += (prop / 100.0) * lpPrice.pricePerKg;
      }
    });
    return sum;
  }

  Widget _buildComparisonCard(ParetoPoint lp, ParetoPoint cheapestNsga, Map<int, String> names) {
    final lpLatest = _costUnderLatest(lp, names);
    final nsgaLatest = _costUnderLatest(cheapestNsga, names);
    final scheme = Theme.of(context).colorScheme;
    final allIngs = <String>{...lp.proportions.keys, ...cheapestNsga.proportions.keys}.toList()..sort();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const IconBadge(Icons.compare_arrows, size: 36),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('LP vs. NSGA-II Comparison', style: Theme.of(context).textTheme.titleMedium),
                    Text('Out-of-sample cost & recipe shifts', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text('Price Comparison (RWF/kg)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
          const SizedBox(height: 6),
          Table(
            columnWidths: const {
              0: FlexColumnWidth(1.8),
              1: FlexColumnWidth(1.1),
              2: FlexColumnWidth(1.1),
              3: FlexColumnWidth(1.1),
            },
            children: [
              TableRow(
                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: scheme.outlineVariant))),
                children: const [
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('Metric', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('LP', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('NSGA-II', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('Diff', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                ],
              ),
              TableRow(
                children: [
                  const Padding(padding: EdgeInsets.symmetric(vertical: 6), child: Text('Forecast Cost', style: TextStyle(fontSize: 11.5))),
                  Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Text(lp.cost.toStringAsFixed(1), style: const TextStyle(fontSize: 11.5))),
                  Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Text(cheapestNsga.cost.toStringAsFixed(1), style: const TextStyle(fontSize: 11.5))),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Text(
                      '+${(cheapestNsga.cost - lp.cost).toStringAsFixed(1)}',
                      style: TextStyle(fontSize: 11.5, color: scheme.error, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              if (lpLatest > 0 && nsgaLatest > 0)
                TableRow(
                  children: [
                    const Padding(padding: EdgeInsets.symmetric(vertical: 6), child: Text('Recent Price Cost', style: TextStyle(fontSize: 11.5))),
                    Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Text(lpLatest.toStringAsFixed(1), style: const TextStyle(fontSize: 11.5))),
                    Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Text(nsgaLatest.toStringAsFixed(1), style: const TextStyle(fontSize: 11.5))),
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Text(
                        '+${(nsgaLatest - lpLatest).toStringAsFixed(1)}',
                        style: TextStyle(fontSize: 11.5, color: scheme.error, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 16),
          const Text('Ingredient Composition (%)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
          const SizedBox(height: 6),
          Table(
            columnWidths: const {
              0: FlexColumnWidth(2.0),
              1: FlexColumnWidth(0.9),
              2: FlexColumnWidth(0.9),
              3: FlexColumnWidth(0.9),
            },
            children: [
              TableRow(
                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: scheme.outlineVariant))),
                children: const [
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('Ingredient', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('LP', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('NSGA-II', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                  Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('Shift', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5))),
                ],
              ),
              for (final ingName in allIngs) ...[
                if ((lp.proportions[ingName] ?? 0.0) > 0.1 || (cheapestNsga.proportions[ingName] ?? 0.0) > 0.1)
                  TableRow(
                    children: [
                      Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Text(ingName, style: const TextStyle(fontSize: 11))),
                      Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Text('${(lp.proportions[ingName] ?? 0.0).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 11))),
                      Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Text('${(cheapestNsga.proportions[ingName] ?? 0.0).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 11))),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 5),
                        child: () {
                          final diff = (cheapestNsga.proportions[ingName] ?? 0.0) - (lp.proportions[ingName] ?? 0.0);
                          final color = diff.abs() < 0.1 ? scheme.onSurfaceVariant : (diff > 0 ? scheme.primary : scheme.error);
                          final prefix = diff > 0 ? '+' : '';
                          return Text(
                            '$prefix${diff.toStringAsFixed(1)}%',
                            style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold),
                          );
                        }(),
                      ),
                    ],
                  ),
              ],
            ],
          ),
        ],
      ),
    );
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
    final names = {for (final i in _ingredients) i.id: i.name};
    final cheapestNsga = front.isNotEmpty ? front.first : null;
    final cheapest = cheapestNsga ?? lp;

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
        if (lp != null && cheapestNsga != null) ...[
          const SizedBox(height: 14),
          if (_loadingPrices)
            const Center(child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator()))
          else
            _buildComparisonCard(lp, cheapestNsga, names),
        ],
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
