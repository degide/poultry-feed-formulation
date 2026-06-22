import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../session.dart';
import '../theme.dart';
import '../widgets/async_builder.dart';
import '../widgets/ui.dart';
import 'flock_detail_screen.dart';

class FlocksScreen extends StatefulWidget {
  const FlocksScreen({super.key});

  @override
  State<FlocksScreen> createState() => _FlocksScreenState();
}

class _FlocksScreenState extends State<FlocksScreen> {
  late Future<List<Flock>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = context.read<Session>().repo.flocks();
  }

  Future<void> _addFlock() async {
    final created = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => const _NewFlockSheet(),
    );
    if (created == true) setState(_reload);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My flocks')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addFlock,
        icon: const Icon(Icons.add),
        label: const Text('New flock'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_reload),
        child: AsyncBuilder<List<Flock>>(
          future: _future,
          onRetry: () => setState(_reload),
          builder: (context, flocks) {
            if (flocks.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 60),
                EmptyState(
                  icon: Icons.pets,
                  title: 'No flocks yet',
                  message: 'Add your first flock to start formulating rations.',
                  action: FilledButton.icon(
                    onPressed: _addFlock,
                    icon: const Icon(Icons.add),
                    label: const Text('Add a flock'),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
              itemCount: flocks.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final f = flocks[i];
                final isLayer = f.type == 'layer';
                return AppCard(
                  padding: const EdgeInsets.all(14),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => FlockDetailScreen(flock: f),
                  )),
                  child: Row(
                    children: [
                      IconBadge(
                        isLayer ? Icons.egg_outlined : Icons.set_meal_outlined,
                        color: isLayer ? AppColors.accent : null,
                        size: 48,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(f.name,
                                style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 6),
                            Row(children: [
                              Pill(isLayer ? 'Layer' : 'Broiler',
                                  color: isLayer ? AppColors.accent : null),
                              const SizedBox(width: 8),
                              Text('${f.ageWeeks} wks · ${f.size} birds',
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurfaceVariant)),
                            ]),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right,
                          color: Theme.of(context).colorScheme.onSurfaceVariant),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _NewFlockSheet extends StatefulWidget {
  const _NewFlockSheet();

  @override
  State<_NewFlockSheet> createState() => _NewFlockSheetState();
}

class _NewFlockSheetState extends State<_NewFlockSheet> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _age = TextEditingController(text: '20');
  final _size = TextEditingController(text: '500');
  String _type = 'layer';
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _age.dispose();
    _size.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _busy = true; _error = null; });
    try {
      await context.read<Session>().repo.createFlock(
            name: _name.text.trim(),
            type: _type,
            ageWeeks: int.parse(_age.text),
            size: int.parse(_size.text),
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
        left: 20, right: 20, top: 16,
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
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text('New flock', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 18),
            TextFormField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                  labelText: 'Name', prefixIcon: Icon(Icons.label_outline)),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _type,
              decoration: const InputDecoration(
                  labelText: 'Type', prefixIcon: Icon(Icons.category_outlined)),
              items: const [
                DropdownMenuItem(value: 'layer', child: Text('Layer')),
                DropdownMenuItem(value: 'broiler', child: Text('Broiler')),
              ],
              onChanged: (v) => setState(() => _type = v ?? 'layer'),
            ),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: TextFormField(
                  controller: _age,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Age (weeks)'),
                  validator: (v) => int.tryParse(v ?? '') == null ? 'Number' : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _size,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Flock size'),
                  validator: (v) =>
                      (int.tryParse(v ?? '') ?? 0) <= 0 ? 'Number' : null,
                ),
              ),
            ]),
            const SizedBox(height: 18),
            if (_error != null) ...[
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              const SizedBox(height: 12),
            ],
            FilledButton(
              onPressed: _busy ? null : _save,
              child: _busy
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Save flock'),
            ),
          ],
        ),
      ),
    );
  }
}
