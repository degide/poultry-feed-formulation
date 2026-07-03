import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../widgets/async_builder.dart';
import '../widgets/location_selector.dart';
import '../widgets/ui.dart';

class PricesScreen extends StatefulWidget {
  const PricesScreen({super.key});

  @override
  State<PricesScreen> createState() => _PricesScreenState();
}

class _PricesScreenState extends State<PricesScreen> {
  final _locController = TextEditingController(text: 'Rwanda');
  String _location = 'Rwanda';
  late Future<_PriceView> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _locController.dispose();
    super.dispose();
  }

  void _reload() {
    final repo = context.read<Session>().repo;
    _future = () async {
      final locations = await repo.locations();
      if (!locations.contains(_location)) {
        _location = locations.contains('Rwanda') ? 'Rwanda' : (locations.isNotEmpty ? locations.first : 'Rwanda');
      }
      final ingredients = await repo.ingredients();
      final prices = await repo.latestPrices(_location);
      return _PriceView(ingredients, prices, locations);
    }();
  }

  Future<void> _addPrice(List<Ingredient> ingredients) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) =>
          _AddPriceSheet(ingredients: ingredients, location: _location),
    );
    if (ok == true) setState(_reload);
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat('#,##0', 'en');
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Market prices'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_reload),
        child: AsyncBuilder<_PriceView>(
          future: _future,
          onRetry: () => setState(_reload),
          builder: (context, view) {
            final names = {for (final i in view.ingredients) i.id: i.name};
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeader('Sourcing Location', padding: EdgeInsets.only(bottom: 8)),
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
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${view.prices.length} priced at "$_location"',
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(color: scheme.onSurfaceVariant),
                      ),
                    ),
                    SizedBox(
                      height: 36,
                      width: 140,
                      child: FilledButton.tonalIcon(
                        onPressed: () => _addPrice(view.ingredients),
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Add'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (view.prices.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 40),
                    child: EmptyState(
                      icon: Icons.sell_outlined,
                      title: 'No prices here',
                      message: 'No prices recorded at "$_location" yet.',
                    ),
                  )
                else
                  AppCard(
                    padding: EdgeInsets.zero,
                    child: Column(
                      children: [
                        for (var i = 0; i < view.prices.length; i++) ...[
                          if (i > 0)
                            Divider(height: 1, color: scheme.outlineVariant),
                          ListTile(
                            title: Text(names[view.prices[i].ingredientId] ??
                                '#${view.prices[i].ingredientId}'),
                            subtitle: Text(view.prices[i].priceDate,
                                style: Theme.of(context).textTheme.bodySmall),
                            trailing: Text(
                                '${money.format(view.prices[i].pricePerKg)} RWF/kg',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                          ),
                        ],
                      ],
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _PriceView {
  _PriceView(this.ingredients, this.prices, this.locations);
  final List<Ingredient> ingredients;
  final List<MarketPrice> prices;
  final List<String> locations;
}

class _AddPriceSheet extends StatefulWidget {
  const _AddPriceSheet({required this.ingredients, required this.location});
  final List<Ingredient> ingredients;
  final String location;

  @override
  State<_AddPriceSheet> createState() => _AddPriceSheetState();
}

class _AddPriceSheetState extends State<_AddPriceSheet> {
  final _form = GlobalKey<FormState>();
  final _price = TextEditingController();
  int? _ingredientId;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _price.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate() || _ingredientId == null) {
      setState(() => _error = 'Pick an ingredient and a price.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final today = DateTime.now().toIso8601String().substring(0, 10);
      await context.read<Session>().repo.addPrice(
            ingredientId: _ingredientId!,
            price: double.parse(_price.text),
            date: today,
            location: widget.location,
          );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Form(
        key: _form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text('Add price at "${widget.location}"',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 18),
            DropdownButtonFormField<int>(
              value: _ingredientId,
              isExpanded: true,
              decoration: const InputDecoration(
                  labelText: 'Ingredient',
                  prefixIcon: Icon(Icons.grass_outlined)),
              items: widget.ingredients
                  .map(
                      (i) => DropdownMenuItem(value: i.id, child: Text(i.name)))
                  .toList(),
              onChanged: (v) => setState(() => _ingredientId = v),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _price,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                  labelText: 'Price (RWF/kg)',
                  prefixIcon: Icon(Icons.payments_outlined)),
              validator: (v) =>
                  (double.tryParse(v ?? '') ?? 0) <= 0 ? 'Enter a price' : null,
            ),
            const SizedBox(height: 18),
            if (_error != null) ...[
              Text(_error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
              const SizedBox(height: 12),
            ],
            FilledButton(
              onPressed: _busy ? null : _save,
              child: _busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Text('Save price'),
            ),
          ],
        ),
      ),
    );
  }
}
