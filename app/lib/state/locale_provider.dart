import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Idioma de la interfaz.
///
/// `null` significa "el del sistema operativo", que es el comportamiento por
/// defecto y el que esperan las tiendas de aplicaciones. El usuario puede
/// forzar otro desde Ajustes, y la elección persiste entre sesiones.
final localeProvider =
    StateNotifierProvider<LocaleNotifier, Locale?>((ref) => LocaleNotifier());

class LocaleNotifier extends StateNotifier<Locale?> {
  LocaleNotifier() : super(null) {
    _restore();
  }

  static const _key = 'ui_locale';

  /// Español primero por ser el idioma de partida del proyecto; el resto
  /// cubre los mercados y las tradiciones representadas en el corpus.
  static const supported = [
    Locale('es'),
    Locale('en'),
    Locale('pt'),
    Locale('fr'),
    Locale('ar'),
    Locale('hi'),
  ];

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_key);
    if (code != null && code.isNotEmpty) state = Locale(code);
  }

  Future<void> set(Locale? locale) async {
    state = locale;
    final prefs = await SharedPreferences.getInstance();
    if (locale == null) {
      await prefs.remove(_key);
    } else {
      await prefs.setString(_key, locale.languageCode);
    }
  }
}

/// Nombre de cada idioma escrito en ese mismo idioma: es lo que espera ver
/// alguien que no entiende el idioma actual de la aplicación.
const languageNames = {
  'es': 'Español',
  'en': 'English',
  'pt': 'Português',
  'fr': 'Français',
  'ar': 'العربية',
  'hi': 'हिन्दी',
};
