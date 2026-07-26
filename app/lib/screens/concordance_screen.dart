import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../state/providers.dart';
import '../widgets/common.dart';

/// Todas las apariciones del término, agrupables por tradición.
class ConcordanceScreen extends ConsumerWidget {
  const ConcordanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final async = ref.watch(concordanceProvider);

    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(concordanceProvider),
      ),
      data: (result) {
        if (result == null) {
          return EmptyState(
            icon: Icons.format_quote,
            message: l.concEmptyTitle,
            hint: l.concEmptyHint,
          );
        }
        if (result.items.isEmpty) {
          return EmptyState(
            icon: Icons.search_off,
            message: l.concNoneTitle,
          );
        }

        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Row(
                children: [
                  Text(l.versesCount(result.total),
                      style: theme.textTheme.titleSmall),
                  const Spacer(),
                  if (result.items.length < result.total)
                    Text(l.concShowing(result.items.length),
                        style: theme.textTheme.labelSmall),
                ],
              ),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                itemCount: result.items.length,
                itemBuilder: (context, i) {
                  final item = result.items[i];
                  final previous = i == 0 ? null : result.items[i - 1];
                  final newGroup = previous?.workId != item.workId;

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (newGroup)
                        Padding(
                          padding: EdgeInsets.only(top: i == 0 ? 0 : 16, bottom: 6),
                          child: Row(
                            children: [
                              TraditionDot(tradition: item.traditionEnum, size: 12),
                              const SizedBox(width: 8),
                              Text(item.workTitle,
                                  style: theme.textTheme.titleSmall?.copyWith(
                                      fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      VerseCard(
                        ref_: item.ref,
                        text: item.text,
                        workTitle: item.division,
                        tradition: item.traditionEnum,
                        highlight: item.matchedForms,
                        trailing: item.hits > 1
                            ? Chip(
                                visualDensity: VisualDensity.compact,
                                padding: EdgeInsets.zero,
                                label: Text('×${item.hits}',
                                    style: theme.textTheme.labelSmall),
                              )
                            : null,
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}
