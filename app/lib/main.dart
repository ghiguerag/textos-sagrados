import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'l10n/app_localizations.dart';
import 'screens/shell.dart';
import 'state/locale_provider.dart';

void main() {
  runApp(const ProviderScope(child: TextosSagradosApp()));
}

class TextosSagradosApp extends ConsumerWidget {
  const TextosSagradosApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(localeProvider);

    return MaterialApp(
      onGenerateTitle: (context) => L.of(context).appTitle,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,

      // null = seguir al sistema. Flutter aplica la dirección derecha-izquierda
      // automáticamente en árabe, así que no hace falta tocar los layouts.
      locale: locale,
      supportedLocales: LocaleNotifier.supported,
      localizationsDelegates: const [
        L.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],

      home: const AppShell(),
    );
  }
}
