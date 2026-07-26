import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../models/models.dart';
import '../state/providers.dart';
import '../widgets/common.dart';
import '../widgets/heatmap.dart';

class FrequencyScreen extends ConsumerWidget {
  const FrequencyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(frequencyProvider);

    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorState(
        error: e,
        onRetry: () => ref.invalidate(frequencyProvider),
      ),
      data: (result) {
        if (result == null) {
          return EmptyState(
            icon: Icons.bar_chart,
            message: context.l10n.freqEmptyTitle,
            hint: context.l10n.freqEmptyHint,
          );
        }
        return _Results(result: result);
      },
    );
  }
}

class _Results extends StatelessWidget {
  const _Results({required this.result});

  final FrequencyResult result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final data = [...result.results]..sort((a, b) => b.per10k.compareTo(a.per10k));
    final hasHits = data.any((d) => d.rawCount > 0);

    if (!hasHits) {
      return EmptyState(
        icon: Icons.search_off,
        message: l.noResultsTitle,
        hint: l.noResultsHint,
      );
    }

    return ListView(
      padding: const EdgeInsets.only(bottom: 32),
      children: [
        CaveatBanner(text: l.caveat(result.caveat)),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Row(
            children: [
              Text(l.freqChartTitle, style: theme.textTheme.titleMedium),
              const Spacer(),
              Tooltip(
                message: result.resolvedStems.join(', '),
                child: Chip(
                  visualDensity: VisualDensity.compact,
                  label: Text(l.rootsCount(result.resolvedStems.length)),
                ),
              ),
            ],
          ),
        ),
        SizedBox(height: 260, child: _BarChart(data: data)),
        const SizedBox(height: 12),
        for (final item in data) _WorkRow(item: item, keyness: result.keynessFor(item.workId)),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(l.distributionTitle, style: theme.textTheme.titleMedium),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 2, 16, 8),
          child: Text(
            l.distributionHint,
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
        for (final item in data.where((d) => d.rawCount > 0))
          DivisionHeatmap(workId: item.workId, title: item.workTitle),
      ],
    );
  }
}

class _BarChart extends StatelessWidget {
  const _BarChart({required this.data});

  final List<WorkFrequency> data;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    final l = l10n;
    final maxY = data.map((d) => d.per10k).fold<double>(0, (a, b) => a > b ? a : b);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: BarChart(
        BarChartData(
          maxY: maxY * 1.2,
          alignment: BarChartAlignment.spaceAround,
          borderData: FlBorderData(show: false),
          gridData: FlGridData(
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(
              color: theme.colorScheme.outlineVariant,
              strokeWidth: 0.5,
            ),
          ),
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipItem: (group, _, rod, __) {
                final item = data[group.x];
                return BarTooltipItem(
                  '${item.workTitle}\n',
                  theme.textTheme.labelMedium!
                      .copyWith(fontWeight: FontWeight.bold),
                  children: [
                    TextSpan(
                      text: '${item.per10k.toStringAsFixed(1)}\n'
                          '${l.occurrences(item.rawCount)}\n'
                          '${l.versesCount(item.verseCount)}',
                      style: theme.textTheme.labelSmall,
                    ),
                  ],
                );
              },
            ),
          ),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(showTitles: true, reservedSize: 38),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 46,
                getTitlesWidget: (value, meta) {
                  final item = data[value.toInt()];
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      item.traditionEnum.label(l10n),
                      style: theme.textTheme.labelSmall,
                      textAlign: TextAlign.center,
                    ),
                  );
                },
              ),
            ),
          ),
          barGroups: [
            for (var i = 0; i < data.length; i++)
              BarChartGroupData(x: i, barRods: [
                BarChartRodData(
                  toY: data[i].per10k,
                  width: 26,
                  color: data[i].traditionEnum.color,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                ),
              ]),
          ],
        ),
      ),
    );
  }
}

class _WorkRow extends StatelessWidget {
  const _WorkRow({required this.item, this.keyness});

  final WorkFrequency item;
  final Keyness? keyness;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final k = keyness;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                TraditionDot(tradition: item.traditionEnum),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(item.workTitle,
                      style: theme.textTheme.titleSmall, overflow: TextOverflow.ellipsis),
                ),
                Text('${item.per10k.toStringAsFixed(1)}',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                Text(' ${l.perTenK}', style: theme.textTheme.labelSmall),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                _Stat(label: l.occurrences(item.rawCount)),
                _Stat(label: l.versesCount(item.verseCount)),
                _Stat(
                  label: l.presentInDivisions(
                      item.divisionsPresent, item.divisionsTotal),
                ),
                if (k != null && k.significant)
                  _Stat(
                    label: '${l.keynessDirection(k.direction)} '
                        '(G²=${k.logLikelihood.toStringAsFixed(0)})',
                    color: k.direction == 'over'
                        ? theme.colorScheme.primaryContainer
                        : theme.colorScheme.errorContainer,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, this.color});

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color ?? theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label, style: theme.textTheme.labelSmall),
    );
  }
}
