import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../models/models.dart';
import '../state/providers.dart';

/// Entrada de consulta: palabra suelta o campo semántico, más el filtro de
/// obras. Es el control central de la aplicación.
class QueryBar extends ConsumerStatefulWidget {
  const QueryBar({super.key});

  @override
  ConsumerState<QueryBar> createState() => _QueryBarState();
}

class _QueryBarState extends ConsumerState<QueryBar> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit(String value) {
    final query = ref.read(queryProvider);
    ref.read(queryProvider.notifier).state =
        query.copyWith(term: value.trim(), clearField: value.trim().isNotEmpty);
  }

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final query = ref.watch(queryProvider);
    final fields = ref.watch(semanticFieldsProvider);
    final works = ref.watch(worksProvider);
    final selected = ref.watch(selectedWorksProvider);

    return Material(
      color: Theme.of(context).colorScheme.surface,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    textInputAction: TextInputAction.search,
                    onSubmitted: _submit,
                    // Sin esto el icono de limpiar no aparece hasta que el
                    // widget se reconstruye por otro motivo.
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      hintText: l.searchHint,
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _controller.text.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _controller.clear();
                                _submit('');
                              },
                            ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                // Idioma del CORPUS, no de la interfaz. Son ejes distintos:
                // se puede usar la app en árabe y analizar textos en inglés.
                Tooltip(
                  message: '${l.corpusLanguage}\n${l.corpusLanguageHint}',
                  child: Semantics(
                    label: l.corpusLanguage,
                    child: SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(value: 'en', label: Text('EN')),
                        ButtonSegment(value: 'es', label: Text('ES')),
                      ],
                      selected: {query.language},
                      onSelectionChanged: (s) =>
                          ref.read(queryProvider.notifier).state =
                              query.copyWith(language: s.first),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 40,
              child: fields.when(
                loading: () => const Center(
                  child: SizedBox(
                    height: 2,
                    child: LinearProgressIndicator(),
                  ),
                ),
                error: (e, _) => Text(
                  l.apiError(e),
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
                data: (list) => ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: list.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 6),
                  itemBuilder: (context, i) {
                    final field = list[i];
                    final isSelected = query.semanticField == field.key;
                    return Tooltip(
                      message: field.description.isEmpty
                          ? field.label
                          : field.description,
                      child: FilterChip(
                        label: Text(field.label),
                        selected: isSelected,
                        onSelected: (on) {
                          _controller.clear();
                          ref.read(queryProvider.notifier).state = query.copyWith(
                            term: '',
                            semanticField: on ? field.key : null,
                            clearField: !on,
                          );
                        },
                      ),
                    );
                  },
                ),
              ),
            ),
            works.maybeWhen(
              data: (list) => Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Wrap(
                  spacing: 6,
                  children: [
                    for (final w in list)
                      FilterChip(
                        label: Text(w.edition, style: const TextStyle(fontSize: 11)),
                        visualDensity: VisualDensity.compact,
                        selected: selected.isEmpty || selected.contains(w.id),
                        avatar: CircleAvatar(
                          radius: 5,
                          backgroundColor: w.traditionEnum.color,
                        ),
                        onSelected: (on) {
                          final current = {...selected};
                          if (current.isEmpty) current.addAll(list.map((e) => e.id));
                          if (on) {
                            current.add(w.id);
                          } else {
                            current.remove(w.id);
                          }
                          ref.read(selectedWorksProvider.notifier).state =
                              current.length == list.length ? {} : current;
                        },
                      ),
                  ],
                ),
              ),
              orElse: () => const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}
