import 'package:flutter/material.dart';

import '../core/l10n_helpers.dart';
import '../models/models.dart';

/// Estado vacío con instrucción concreta, no un icono decorativo.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.message, this.hint});

  final IconData icon;
  final String message;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 44, color: theme.colorScheme.outline),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center, style: theme.textTheme.titleMedium),
            if (hint != null) ...[
              const SizedBox(height: 6),
              Text(
                hint!,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.error, this.onRetry});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off, size: 44, color: theme.colorScheme.error),
            const SizedBox(height: 12),
            Text(context.l10n.apiError(error), textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              FilledButton.tonal(
                onPressed: onRetry,
                child: Text(context.l10n.retry),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Aviso metodológico. Aparece junto a los resultados, no escondido en un
/// menú: quien lee los números debe leer también sus límites.
class CaveatBanner extends StatelessWidget {
  const CaveatBanner({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (text.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(10),
        border: Border(
          left: BorderSide(color: theme.colorScheme.primary, width: 3),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: theme.textTheme.bodySmall?.copyWith(height: 1.45),
            ),
          ),
        ],
      ),
    );
  }
}

class TraditionDot extends StatelessWidget {
  const TraditionDot({super.key, required this.tradition, this.size = 10});

  final Tradition tradition;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: tradition.color, shape: BoxShape.circle),
      );
}

/// Tarjeta de versículo con la palabra buscada resaltada.
class VerseCard extends StatelessWidget {
  const VerseCard({
    super.key,
    required this.ref_,
    required this.text,
    required this.workTitle,
    required this.tradition,
    this.highlight = const [],
    this.trailing,
    this.onTap,
  });

  final String ref_;
  final String text;
  final String workTitle;
  final Tradition tradition;
  final List<String> highlight;
  final Widget? trailing;
  final VoidCallback? onTap;

  /// Resalta las formas encontradas. Se usan los prefijos de las raíces, no
  /// coincidencia exacta, porque el motor busca por lema.
  List<TextSpan> _spans(BuildContext context) {
    final terms = highlight.where((h) => h.trim().length > 2).toList();
    if (terms.isEmpty) return [TextSpan(text: text)];

    final pattern = RegExp(
      r'\b(' + terms.map(RegExp.escape).join('|') + r')\w*',
      caseSensitive: false,
    );

    final spans = <TextSpan>[];
    var last = 0;
    for (final m in pattern.allMatches(text)) {
      if (m.start > last) spans.add(TextSpan(text: text.substring(last, m.start)));
      spans.add(TextSpan(
        text: m.group(0),
        style: TextStyle(
          fontWeight: FontWeight.w700,
          backgroundColor: tradition.color.withValues(alpha: 0.18),
        ),
      ));
      last = m.end;
    }
    if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
    return spans;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  TraditionDot(tradition: tradition),
                  const SizedBox(width: 8),
                  Text(
                    ref_,
                    style: theme.textTheme.labelLarge
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      workTitle,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                    ),
                  ),
                  if (trailing != null) trailing!,
                ],
              ),
              const SizedBox(height: 8),
              SelectableText.rich(
                TextSpan(style: theme.textTheme.bodyLarge, children: _spans(context)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
