import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import '../core/l10n_helpers.dart';
import '../state/locale_provider.dart';
import '../state/providers.dart';
import '../widgets/common.dart';

/// Ajustes y, sobre todo, atribución de fuentes.
///
/// La sección de licencias no es opcional: publicar textos exige acreditar
/// cada edición, y las tiendas de aplicaciones lo revisan.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final TextEditingController _controller =
      TextEditingController(text: ref.read(baseUrlProvider));

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = context.l10n;
    final works = ref.watch(worksProvider);
    final locale = ref.watch(localeProvider);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ---------- Idioma ----------
        Text(l.setLanguage, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              RadioListTile<String?>(
                value: null,
                groupValue: locale?.languageCode,
                title: Text(l.setLanguageSystem),
                onChanged: (_) => ref.read(localeProvider.notifier).set(null),
              ),
              for (final loc in LocaleNotifier.supported)
                RadioListTile<String?>(
                  value: loc.languageCode,
                  groupValue: locale?.languageCode,
                  // Cada idioma escrito en sí mismo: es lo que puede reconocer
                  // quien no entiende el idioma activo.
                  title: Text(languageNames[loc.languageCode] ?? loc.languageCode),
                  onChanged: (_) =>
                      ref.read(localeProvider.notifier).set(loc),
                ),
            ],
          ),
        ),

        const SizedBox(height: 28),

        // ---------- Servidor ----------
        Text(l.setServer, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _controller,
          keyboardType: TextInputType.url,
          decoration: InputDecoration(
            hintText: 'http://localhost:8000',
            suffixIcon: IconButton(
              icon: const Icon(Icons.check),
              onPressed: () async {
                await ref.read(baseUrlProvider.notifier).set(_controller.text);
                ref.invalidate(worksProvider);
                ref.invalidate(semanticFieldsProvider);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(l.setServerUpdated)),
                  );
                }
              },
            ),
          ),
        ),

        const SizedBox(height: 28),

        // ---------- Textos y licencias ----------
        Text(l.setTexts, style: theme.textTheme.titleMedium),
        const SizedBox(height: 4),
        Text(
          l.setLicenseNote,
          style: theme.textTheme.bodySmall
              ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
        ),
        const SizedBox(height: 12),
        works.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorState(error: e),
          data: (list) => Column(
            children: [
              for (final w in list)
                Card(
                  child: ListTile(
                    leading: TraditionDot(tradition: w.traditionEnum, size: 14),
                    title: Text(w.displayName),
                    subtitle: Text(
                      '${l.versesCount(w.totalVerses)} · '
                      '${l.setWordsCount(w.totalTokens)} · '
                      '${w.license}${w.year != null ? " · ${w.year}" : ""}',
                    ),
                    trailing: w.sourceUrl == null
                        ? null
                        : IconButton(
                            icon: const Icon(Icons.open_in_new, size: 18),
                            tooltip: w.sourceUrl,
                            onPressed: () => launchUrl(
                              Uri.parse(w.sourceUrl!),
                              mode: LaunchMode.externalApplication,
                            ),
                          ),
                  ),
                ),
            ],
          ),
        ),

        const SizedBox(height: 28),

        // ---------- Método ----------
        Text(l.setMethod, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        _MethodNote(title: l.methodNormTitle, body: l.methodNormBody),
        _MethodNote(title: l.methodSigTitle, body: l.methodSigBody),
        _MethodNote(title: l.methodTransTitle, body: l.methodTransBody),
        _MethodNote(title: l.methodScopeTitle, body: l.methodScopeBody),
      ],
    );
  }
}

class _MethodNote extends StatelessWidget {
  const _MethodNote({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: theme.textTheme.labelLarge
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 2),
          Text(body, style: theme.textTheme.bodySmall?.copyWith(height: 1.5)),
        ],
      ),
    );
  }
}
