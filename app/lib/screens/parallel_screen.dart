import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../core/theme.dart';
import '../models/models.dart';
import '../state/providers.dart';
import '../widgets/common.dart';

/// Lectura en paralelo: una columna por tradición, sincronizadas por concepto.
/// En escritorio se ven todas a la vez; en móvil se navegan con pestañas.
class ParallelScreen extends ConsumerWidget {
  const ParallelScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(parallelProvider);

    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(parallelProvider),
      ),
      data: (columns) {
        final withContent = columns.where((c) => c.verses.isNotEmpty).toList();
        if (withContent.isEmpty) {
          return EmptyState(
            icon: Icons.view_column,
            message: context.l10n.parEmptyTitle,
            hint: context.l10n.parEmptyHint,
          );
        }

        if (Breakpoints.isCompact(context)) {
          return DefaultTabController(
            length: withContent.length,
            child: Column(
              children: [
                TabBar(
                  isScrollable: true,
                  tabs: [
                    for (final c in withContent)
                      Tab(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TraditionDot(tradition: c.traditionEnum, size: 8),
                            const SizedBox(width: 6),
                            Text(c.traditionEnum.label(context.l10n)),
                          ],
                        ),
                      ),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: [for (final c in withContent) _Column(column: c)],
                  ),
                ),
              ],
            ),
          );
        }

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          // stretch, no start: las columnas necesitan altura acotada porque
          // cada una contiene un ListView expandido.
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final c in withContent)
                SizedBox(width: 380, child: _Column(column: c, showHeader: true)),
            ],
          ),
        );
      },
    );
  }
}

class _Column extends StatelessWidget {
  const _Column({required this.column, this.showHeader = false});

  final ParallelColumn column;
  final bool showHeader;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showHeader)
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 12, 8, 6),
            child: Row(
              children: [
                TraditionDot(tradition: column.traditionEnum, size: 12),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(column.title,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 24),
            itemCount: column.verses.length,
            itemBuilder: (context, i) {
              final v = column.verses[i];
              return VerseCard(
                ref_: v.ref,
                text: v.text,
                workTitle: v.division,
                tradition: v.traditionEnum,
                highlight: v.matchedForms,
              );
            },
          ),
        ),
      ],
    );
  }
}
