import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../widgets/async_builder.dart';
import '../widgets/forecast_chart.dart';
import '../widgets/location_selector.dart';
import '../widgets/ui.dart';

class ForecastsScreen extends StatefulWidget {
  const ForecastsScreen({super.key});

  @override
  State<ForecastsScreen> createState() => _ForecastsScreenState();
}

class _ForecastsScreenState extends State<ForecastsScreen> {
  String _location = 'Rwanda';
  late Future<_ForecastView> _future;
  bool _refreshing = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final repo = context.read<Session>().repo;
    _future = () async {
      final locations = await repo.locations();
      if (!locations.contains(_location)) {
        _location = locations.contains('Rwanda') ? 'Rwanda' : (locations.isNotEmpty ? locations.first : 'Rwanda');
      }
      final forecasts = await repo.forecasts(marketLocation: _location);
      BacktestResult? bt;
      try {
        bt = await repo.backtest(marketLocation: _location);
      } catch (_) {
        bt = null;
      }
      return _ForecastView(forecasts, bt, locations);
    }();
  }

  Future<void> _trainModel() async {
    setState(() => _refreshing = true);
    try {
      final n = await context.read<Session>().repo.refreshForecasts(marketLocation: _location);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Model trained for $_location — $n ingredients forecast')));
        setState(_reload);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Price forecasts'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: TextButton.icon(
              onPressed: _refreshing ? null : _trainModel,
              icon: _refreshing
                  ? const SizedBox(
                      height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.model_training, size: 20),
              label: const Text('Train'),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_reload),
        child: AsyncBuilder<_ForecastView>(
          future: _future,
          onRetry: () => setState(_reload),
          builder: (context, view) {
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeader('Market Sourcing Location', padding: EdgeInsets.only(bottom: 8)),
                      LocationSelector(
                        locations: view.locations,
                        selectedLocation: _location,
                        onChanged: (newLoc) {
                          _location = newLoc;
                          setState(_reload);
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (view.forecasts.isEmpty)
                  EmptyState(
                    icon: Icons.insights,
                    title: 'No forecasts yet',
                    message:
                        'Train the model on this market\'s price history to predict next-period prices.',
                    action: FilledButton.icon(
                      onPressed: _refreshing ? null : _trainModel,
                      icon: const Icon(Icons.model_training),
                      label: const Text('Train the model'),
                    ),
                  )
                else ...[
                  if (view.backtest != null && view.backtest!.methods.isNotEmpty)
                    _BacktestCard(view.backtest!),
                  const SizedBox(height: 6),
                  const SectionHeader('Next-period forecast'),
                  ...view.forecasts.map((f) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _ForecastCard(f),
                      )),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ForecastView {
  _ForecastView(this.forecasts, this.backtest, this.locations);
  final List<IngredientForecast> forecasts;
  final BacktestResult? backtest;
  final List<String> locations;
}

class _ForecastCard extends StatelessWidget {
  const _ForecastCard(this.f);
  final IngredientForecast f;

  @override
  Widget build(BuildContext context) {
    final next = f.forecast.isNotEmpty ? f.forecast.first : null;
    final last = f.history.isNotEmpty ? f.history.last.price : null;
    double? pct;
    if (next != null && last != null && last != 0) {
      pct = 100 * (next.price / last - 1);
    }
    final up = (pct ?? 0) >= 0;
    final scheme = Theme.of(context).colorScheme;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(f.ingredientName,
                    style: Theme.of(context).textTheme.titleMedium),
              ),
              if (next != null)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('${next.price.toStringAsFixed(0)} RWF/kg',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    if (pct != null)
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(up ? Icons.arrow_upward : Icons.arrow_downward,
                            size: 13,
                            color: up ? scheme.error : scheme.primary),
                        Text('${pct.abs().toStringAsFixed(1)}%',
                            style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: up ? scheme.error : scheme.primary)),
                      ]),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 10),
          ForecastChart(forecast: f),
        ],
      ),
    );
  }
}

class _BacktestCard extends StatelessWidget {
  const _BacktestCard(this.bt);
  final BacktestResult bt;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const IconBadge(Icons.verified_outlined, size: 38),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                    'Model accuracy\nWalk-forward, last ${bt.testMonths} months',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Table(
            columnWidths: const {
              0: FlexColumnWidth(2.3),
              1: FlexColumnWidth(1),
              2: FlexColumnWidth(1),
              3: FlexColumnWidth(1),
            },
            children: [
              TableRow(
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                        color: Theme.of(context).colorScheme.outlineVariant),
                  ),
                ),
                children: const [
                  _Cell('method', bold: true),
                  _Cell('MAE', bold: true),
                  _Cell('RMSE', bold: true),
                  _Cell('MAPE', bold: true),
                ],
              ),
              ...bt.methods.map((m) => TableRow(children: [
                    _Cell(_pretty(m.method)),
                    _Cell(m.mae.toStringAsFixed(0)),
                    _Cell(m.rmse.toStringAsFixed(0)),
                    _Cell('${m.mape.toStringAsFixed(1)}%'),
                  ])),
            ],
          ),
        ],
      ),
    );
  }

  static String _pretty(String m) => switch (m) {
        'gradient_boosting' => 'ML (boosting)',
        'naive_random_walk' => 'Random walk',
        'seasonal_naive' => 'Seasonal naive',
        _ => m,
      };
}

class _Cell extends StatelessWidget {
  const _Cell(this.text, {this.bold = false});
  final String text;
  final bool bold;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Text(text,
          style: TextStyle(
              fontSize: 12.5,
              fontWeight: bold ? FontWeight.w700 : FontWeight.w400)),
    );
  }
}
