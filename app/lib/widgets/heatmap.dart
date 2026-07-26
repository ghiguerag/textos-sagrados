import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../state/providers.dart';

/// Mapa de calor de la distribución interna de un término.
///
/// Cada celda es un libro / sura / capítulo. La intensidad usa la tasa
/// normalizada, no el conteo bruto: si no, los libros largos siempre se verían
/// más oscuros por el mero hecho de ser largos.
class DivisionHeatmap extends ConsumerWidget {
  const DivisionHeatmap({super.key, required this.workId, required this.title});

  final String workId;
  final String title;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final async = ref.watch(divisionFrequencyProvider(workId));

    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LinearProgressIndicator(),
      ),
      error: (e, _) => const SizedBox.shrink(),
      data: (divisions) {
        if (divisions.isEmpty) return const SizedBox.shrink();
        final maxRate =
            divisions.map((d) => d.per10k).fold<double>(0, (a, b) => a > b ? a : b);
        if (maxRate == 0) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: theme.textTheme.labelLarge),
              const SizedBox(height: 8),
              Wrap(
                spacing: 3,
                runSpacing: 3,
                children: [
                  for (final d in divisions)
                    Tooltip(
                      message: '${d.name}\n'
                          '${l.occurrences(d.rawCount)}\n'
                          '${d.per10k.toStringAsFixed(1)} ${l.perTenK}',
                      child: Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary
                              .withValues(alpha: 0.08 + 0.85 * (d.per10k / maxRate)),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                l.heatmapLegend,
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        );
      },
    );
  }
}
