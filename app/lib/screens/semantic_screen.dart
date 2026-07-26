import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../state/providers.dart';
import '../widgets/common.dart';

/// Búsqueda por significado, no por palabra.
///
/// Permite escribir una idea en lenguaje natural y encontrar pasajes que la
/// expresan aunque no compartan vocabulario. Es la función que ninguna
/// concordancia clásica puede ofrecer.
class SemanticScreen extends ConsumerStatefulWidget {
  const SemanticScreen({super.key});

  @override
  ConsumerState<SemanticScreen> createState() => _SemanticScreenState();
}

class _SemanticScreenState extends ConsumerState<SemanticScreen> {
  final _controller = TextEditingController();

  /// Los ejemplos se traducen: son sugerencias de consulta, y una sugerencia
  /// en un idioma que el usuario no lee no sugiere nada.
  List<String> _examples(BuildContext context) {
    final l = context.l10n;
    return [
      l.semExample1,
      l.semExample2,
      l.semExample3,
      l.semExample4,
      l.semExample5,
    ];
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _run(String value) {
    _controller.text = value;
    ref.read(semanticQueryProvider.notifier).state = value;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final async = ref.watch(semanticSearchProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _controller,
            textInputAction: TextInputAction.search,
            onSubmitted: _run,
            decoration: InputDecoration(
              hintText: l.semHint,
              prefixIcon: const Icon(Icons.hub_outlined),
            ),
          ),
        ),
        Expanded(
          child: async.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => ErrorState(
              error: e,
              onRetry: () => ref.invalidate(semanticSearchProvider),
            ),
            data: (result) {
              if (result == null) {
                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text(l.semTryTitle, style: theme.textTheme.titleSmall),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final e in _examples(context))
                          ActionChip(label: Text(e), onPressed: () => _run(e)),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Text(l.semExplanation, style: theme.textTheme.bodyMedium),
                  ],
                );
              }
              if (result.results.isEmpty) {
                return EmptyState(
                  icon: Icons.search_off,
                  message: l.semNoneTitle,
                  hint: l.semNoneHint,
                );
              }

              return ListView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                children: [
                  CaveatBanner(text: l.caveat(result.caveat)),
                  for (final v in result.results)
                    VerseCard(
                      ref_: v.ref,
                      text: v.text,
                      workTitle: v.traditionEnum.label(l),
                      tradition: v.traditionEnum,
                      trailing: _SimilarityBadge(value: v.similarity),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _SimilarityBadge extends StatelessWidget {
  const _SimilarityBadge({required this.value});

  final double value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '${(value * 100).toStringAsFixed(0)}%',
        style: theme.textTheme.labelSmall?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }
}
