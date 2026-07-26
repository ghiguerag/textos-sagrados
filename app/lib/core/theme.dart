import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Paleta sobria y neutral. La app trata material religioso de cuatro
/// tradiciones: la interfaz no debe evocar la iconografía de ninguna.
abstract final class AppTheme {
  static const _seed = Color(0xFF3D5A80);

  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(seedColor: _seed, brightness: brightness);
    final base = ThemeData(colorScheme: scheme, useMaterial3: true);

    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
        // Los versículos se leen mejor con serifa; es texto largo y denso.
        bodyLarge: GoogleFonts.notoSerif(
          fontSize: 16,
          height: 1.6,
          color: scheme.onSurface,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: const EdgeInsets.symmetric(vertical: 4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surfaceContainerHighest.withValues(alpha: 0.4),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

/// Punto de corte para alternar entre diseño móvil y de escritorio.
abstract final class Breakpoints {
  static const compact = 600.0;
  static const medium = 1000.0;

  static bool isCompact(BuildContext c) =>
      MediaQuery.sizeOf(c).width < compact;
  static bool isExpanded(BuildContext c) =>
      MediaQuery.sizeOf(c).width >= medium;
}
