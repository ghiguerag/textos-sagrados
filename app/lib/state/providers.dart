import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/models.dart';
import 'locale_provider.dart';

/// Catálogo de obras. Se carga una vez y se conserva.
final worksProvider = FutureProvider<List<Work>>((ref) async {
  return ref.watch(apiProvider).works();
});

/// Los nombres de los campos semánticos vienen traducidos del backend, así
/// que la petición se rehace al cambiar el idioma de la interfaz.
final semanticFieldsProvider = FutureProvider<List<SemanticField>>((ref) async {
  final locale = ref.watch(localeProvider);
  final lang = locale?.languageCode ??
      PlatformDispatcher.instance.locale.languageCode;
  return ref.watch(apiProvider).semanticFields(lang: lang);
});

/// Consulta activa, compartida por todas las pantallas: el usuario cambia de
/// pestaña y sigue viendo el mismo análisis desde otro ángulo.
final queryProvider = StateProvider<AnalysisQuery>((ref) => const AnalysisQuery());

/// Obras seleccionadas para comparar. Por defecto, todas.
final selectedWorksProvider = StateProvider<Set<String>>((ref) => {});

final frequencyProvider = FutureProvider.autoDispose<FrequencyResult?>((ref) async {
  final query = ref.watch(queryProvider);
  if (query.isEmpty) return null;
  final selected = ref.watch(selectedWorksProvider);
  return ref.watch(apiProvider).frequency(
        query.copyWith(workIds: selected.isEmpty ? null : selected.toList()),
      );
});

final concordanceProvider =
    FutureProvider.autoDispose<ConcordanceResult?>((ref) async {
  final query = ref.watch(queryProvider);
  if (query.isEmpty) return null;
  final selected = ref.watch(selectedWorksProvider);
  return ref.watch(apiProvider).concordance(
        query.copyWith(workIds: selected.isEmpty ? null : selected.toList()),
        limit: 200,
      );
});

final divisionFrequencyProvider = FutureProvider.autoDispose
    .family<List<DivisionFrequency>, String>((ref, workId) async {
  final query = ref.watch(queryProvider);
  if (query.isEmpty) return const [];
  return ref.watch(apiProvider).divisionFrequency(workId, query);
});

final collocationsProvider =
    FutureProvider.autoDispose<List<Collocation>>((ref) async {
  final query = ref.watch(queryProvider);
  if (query.isEmpty) return const [];
  return ref.watch(apiProvider).collocations(query);
});

final parallelProvider =
    FutureProvider.autoDispose<List<ParallelColumn>>((ref) async {
  final query = ref.watch(queryProvider);
  if (query.isEmpty) return const [];
  final selected = ref.watch(selectedWorksProvider);
  final works = await ref.watch(worksProvider.future);
  final ids = selected.isEmpty ? works.map((w) => w.id).toList() : selected.toList();
  return ref
      .watch(apiProvider)
      .parallel(query.copyWith(workIds: ids), limitPerWork: 12);
});

/// Búsqueda semántica: consulta independiente, en lenguaje natural.
final semanticQueryProvider = StateProvider<String>((ref) => '');

final semanticSearchProvider =
    FutureProvider.autoDispose<SemanticSearchResult?>((ref) async {
  final q = ref.watch(semanticQueryProvider);
  if (q.trim().isEmpty) return null;
  return ref.watch(apiProvider).semanticSearch(q, topK: 30);
});
