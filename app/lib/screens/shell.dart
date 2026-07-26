import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n_helpers.dart';
import '../core/theme.dart';
import '../widgets/query_bar.dart';
import 'concordance_screen.dart';
import 'frequency_screen.dart';
import 'parallel_screen.dart';
import 'semantic_screen.dart';
import 'settings_screen.dart';

/// Navegación adaptativa: barra inferior en móvil, raíl lateral en escritorio.
/// Misma base de código, ergonomía correcta en cada plataforma.
class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key});

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  int _index = 0;

  /// Los rótulos se resuelven en build: cambiar el idioma en Ajustes debe
  /// reflejarse en la navegación sin reiniciar la aplicación.
  List<({IconData icon, IconData selected, String label})> _destinations(
      BuildContext context) {
    final l = context.l10n;
    return [
      (icon: Icons.bar_chart_outlined, selected: Icons.bar_chart, label: l.navFrequency),
      (icon: Icons.format_quote_outlined, selected: Icons.format_quote, label: l.navConcordance),
      (icon: Icons.view_column_outlined, selected: Icons.view_column, label: l.navParallel),
      (icon: Icons.hub_outlined, selected: Icons.hub, label: l.navSemantic),
      (icon: Icons.settings_outlined, selected: Icons.settings, label: l.navSettings),
    ];
  }

  Widget get _body => switch (_index) {
        0 => const FrequencyScreen(),
        1 => const ConcordanceScreen(),
        2 => const ParallelScreen(),
        3 => const SemanticScreen(),
        _ => const SettingsScreen(),
      };

  @override
  Widget build(BuildContext context) {
    final compact = Breakpoints.isCompact(context);
    final destinations = _destinations(context);
    // La barra de consulta es común a las tres primeras pantallas: cambiar de
    // vista no debe obligar a reescribir la búsqueda.
    final showQueryBar = _index < 3;

    final content = Column(
      children: [
        if (showQueryBar) const QueryBar(),
        Expanded(child: _body),
      ],
    );

    if (compact) {
      return Scaffold(
        appBar: AppBar(title: Text(context.l10n.appTitle)),
        body: SafeArea(child: content),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: [
            for (final d in destinations)
              NavigationDestination(
                icon: Icon(d.icon),
                selectedIcon: Icon(d.selected),
                label: d.label,
              ),
          ],
        ),
      );
    }

    return Scaffold(
      body: SafeArea(
        child: Row(
          children: [
            NavigationRail(
              selectedIndex: _index,
              onDestinationSelected: (i) => setState(() => _index = i),
              labelType: NavigationRailLabelType.all,
              leading: const Padding(
                padding: EdgeInsets.symmetric(vertical: 16),
                child: Icon(Icons.menu_book_outlined, size: 28),
              ),
              destinations: [
                for (final d in destinations)
                  NavigationRailDestination(
                    icon: Icon(d.icon),
                    selectedIcon: Icon(d.selected),
                    label: Text(d.label),
                  ),
              ],
            ),
            const VerticalDivider(width: 1),
            Expanded(child: content),
          ],
        ),
      ),
    );
  }
}
