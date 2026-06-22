import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../theme.dart';
import '../widgets/ui.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.onNavigate});

  /// Switches the bottom-nav tab (0 Home, 1 Flocks, 2 Prices, 3 Forecasts).
  final void Function(int) onNavigate;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<_Overview> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final repo = context.read<Session>().repo;
    _future = () async {
      List<Flock> flocks = [];
      List<IngredientForecast> forecasts = [];
      try {
        flocks = await repo.flocks();
      } catch (_) {}
      try {
        forecasts = await repo.forecasts();
      } catch (_) {}
      return _Overview(flocks: flocks, forecasts: forecasts);
    }();
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<Session>().user;
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Good morning'
        : hour < 18
            ? 'Good afternoon'
            : 'Good evening';
    final firstName = (user?.name ?? '').split(' ').first;

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async => setState(_reload),
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            GradientHeader(
              title: '$greeting${firstName.isEmpty ? '' : ', $firstName'}',
              subtitle: 'Here is where your feed costs stand today.',
              height: 150,
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: FutureBuilder<_Overview>(
                future: _future,
                builder: (context, snap) {
                  final o = snap.data;
                  final flockCount = o?.flocks.length;
                  final forecastCount = o?.forecasts.length ?? 0;
                  final modelReady = forecastCount > 0;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: StatCard(
                              icon: Icons.pets,
                              value: flockCount?.toString() ?? '—',
                              label: 'Flocks',
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: StatCard(
                              icon: Icons.insights,
                              value: modelReady ? '$forecastCount' : '—',
                              label: 'Forecasted inputs',
                              color: AppColors.accent,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      AppCard(
                        child: Row(
                          children: [
                            IconBadge(
                              modelReady ? Icons.check_circle : Icons.model_training,
                              color: modelReady
                                  ? Theme.of(context).colorScheme.primary
                                  : AppColors.accent,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(modelReady
                                      ? 'Forecast model is ready'
                                      : 'Forecast model not trained yet'),
                                  const SizedBox(height: 2),
                                  Text(
                                    modelReady
                                        ? 'Formulate in forecast mode to use predicted prices.'
                                        : 'Train it from the Forecasts tab to enable dynamic pricing.',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurfaceVariant),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 22),
                      const SectionHeader('Quick actions'),
                      _ActionTile(
                        icon: Icons.add_home_work_outlined,
                        title: 'Manage flocks',
                        subtitle: 'Add a flock or open one to formulate',
                        onTap: () => widget.onNavigate(1),
                      ),
                      const SizedBox(height: 10),
                      _ActionTile(
                        icon: Icons.trending_up,
                        title: 'Price forecasts',
                        subtitle: 'Train the model and view predictions',
                        color: AppColors.accent,
                        onTap: () => widget.onNavigate(3),
                      ),
                      const SizedBox(height: 10),
                      _ActionTile(
                        icon: Icons.sell_outlined,
                        title: 'Market prices',
                        subtitle: 'Review and record ingredient prices',
                        onTap: () => widget.onNavigate(2),
                      ),
                      const SizedBox(height: 22),
                      const SectionHeader('How it works'),
                      AppCard(
                        child: Column(
                          children: const [
                            _Step(
                                n: '1',
                                text: 'Record market prices for your ingredients.'),
                            _Step(
                                n: '2',
                                text:
                                    'The model forecasts where local prices are heading.'),
                            _Step(
                                n: '3',
                                text:
                                    'NSGA-II finds the cheapest ration that still meets nutrition.',
                                last: true),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Overview {
  _Overview({required this.flocks, required this.forecasts});
  final List<Flock> flocks;
  final List<IngredientForecast> forecasts;
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.color,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      onTap: onTap,
      child: Row(
        children: [
          IconBadge(icon, color: color),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                Text(subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant)),
              ],
            ),
          ),
          Icon(Icons.chevron_right,
              color: Theme.of(context).colorScheme.onSurfaceVariant),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.n, required this.text, this.last = false});
  final String n;
  final String text;
  final bool last;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 13,
            backgroundColor: scheme.primaryContainer,
            child: Text(n,
                style: TextStyle(
                    color: scheme.onPrimaryContainer,
                    fontWeight: FontWeight.w700,
                    fontSize: 12)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(text),
            ),
          ),
        ],
      ),
    );
  }
}
