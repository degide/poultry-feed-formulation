import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../widgets/ui.dart';
import 'result_screen.dart';

class FormulateScreen extends StatefulWidget {
  const FormulateScreen({super.key, required this.flock});
  final Flock flock;

  @override
  State<FormulateScreen> createState() => _FormulateScreenState();
}

class _FormulateScreenState extends State<FormulateScreen> {
  final _location = TextEditingController(text: 'Rwanda');
  String _method = 'both';
  String _priceMode = 'forecast';
  int _horizon = 1;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _location.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    setState(() { _busy = true; _error = null; });
    final repo = context.read<Session>().repo;
    try {
      final jobId = await repo.generate(
        flockId: widget.flock.id,
        location: _location.text.trim().isEmpty ? 'Rwanda' : _location.text.trim(),
        method: _method,
        priceMode: _priceMode,
        horizon: _horizon,
        population: 80,
        generations: 120,
      );
      if (!mounted) return;
      final changed = await Navigator.of(context).push<bool>(MaterialPageRoute(
        builder: (_) => ResultScreen(jobId: jobId, flock: widget.flock),
      ));
      if (mounted) Navigator.of(context).pop(changed == true);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text('Formulate · ${widget.flock.name}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeader('Market', padding: EdgeInsets.only(bottom: 8)),
                TextField(
                  controller: _location,
                  decoration: const InputDecoration(
                    labelText: 'Market location',
                    prefixIcon: Icon(Icons.place_outlined),
                    helperText: 'Where to source ingredient prices from',
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
                const SectionHeader('Pricing', padding: EdgeInsets.only(bottom: 8)),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'latest', label: Text('Latest'), icon: Icon(Icons.history)),
                    ButtonSegment(value: 'forecast', label: Text('Forecast'), icon: Icon(Icons.trending_up)),
                  ],
                  selected: {_priceMode},
                  onSelectionChanged: (s) => setState(() => _priceMode = s.first),
                ),
                const SizedBox(height: 8),
                Text(
                  _priceMode == 'forecast'
                      ? 'Optimise against ML-predicted next-period prices (dynamic).'
                      : 'Optimise against the most recent observed prices.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant),
                ),
                if (_priceMode == 'forecast') ...[
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(Icons.schedule, size: 18, color: scheme.onSurfaceVariant),
                      const SizedBox(width: 8),
                      const Expanded(child: Text('Horizon (months ahead)')),
                      DropdownButton<int>(
                        value: _horizon,
                        underline: const SizedBox.shrink(),
                        items: [1, 2, 3]
                            .map((m) => DropdownMenuItem(value: m, child: Text('$m')))
                            .toList(),
                        onChanged: (v) => setState(() => _horizon = v ?? 1),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeader('Engine', padding: EdgeInsets.only(bottom: 8)),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'both', label: Text('Both')),
                    ButtonSegment(value: 'nsga2', label: Text('NSGA-II')),
                    ButtonSegment(value: 'lp', label: Text('LP')),
                  ],
                  selected: {_method},
                  onSelectionChanged: (s) => setState(() => _method = s.first),
                ),
                const SizedBox(height: 8),
                Text(
                  'NSGA-II explores a trade-off front; LP is a single least-cost benchmark.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          if (_error != null) ...[
            Text(_error!, style: TextStyle(color: scheme.error)),
            const SizedBox(height: 12),
          ],
          FilledButton.icon(
            onPressed: _busy ? null : _run,
            icon: _busy
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.play_arrow),
            label: Text(_busy ? 'Starting…' : 'Run optimisation'),
          ),
        ],
      ),
    );
  }
}
