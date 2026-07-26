/// Modelos del cliente. Reflejan app/schemas.py del backend.
library;

import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

enum Tradition {
  cristianismo(Color(0xFF4A6FA5)),
  judaismo(Color(0xFF5B8C7E)),
  islam(Color(0xFF8C6A4A)),
  hinduismo(Color(0xFF9C5C7A));

  const Tradition(this.color);
  final Color color;

  /// El rótulo se resuelve en tiempo de ejecución: depende del idioma de la
  /// interfaz, que el usuario puede cambiar sin reiniciar.
  String label(L l10n) => switch (this) {
        Tradition.cristianismo => l10n.tradChristianity,
        Tradition.judaismo => l10n.tradJudaism,
        Tradition.islam => l10n.tradIslam,
        Tradition.hinduismo => l10n.tradHinduism,
      };

  static Tradition from(String raw) => values.firstWhere(
        (t) => t.name == raw.toLowerCase(),
        orElse: () => Tradition.cristianismo,
      );
}

class Work {
  const Work({
    required this.id,
    required this.tradition,
    required this.title,
    required this.edition,
    required this.language,
    required this.license,
    required this.totalTokens,
    required this.totalVerses,
    required this.totalDivisions,
    required this.divisionLabel,
    required this.verseLabel,
    this.year,
    this.sourceUrl,
  });

  final String id;
  final String tradition;
  final String title;
  final String edition;
  final String language;
  final String license;
  final int totalTokens;
  final int totalVerses;
  final int totalDivisions;
  final String divisionLabel;
  final String verseLabel;
  final int? year;
  final String? sourceUrl;

  Tradition get traditionEnum => Tradition.from(tradition);
  String get displayName => '$title — $edition';

  factory Work.fromJson(Map<String, dynamic> j) => Work(
        id: j['id'],
        tradition: j['tradition'],
        title: j['title'],
        edition: j['edition'],
        language: j['language'],
        license: j['license'],
        totalTokens: j['total_tokens'] ?? 0,
        totalVerses: j['total_verses'] ?? 0,
        totalDivisions: j['total_divisions'] ?? 0,
        divisionLabel: j['division_label'] ?? 'libro',
        verseLabel: j['verse_label'] ?? 'versículo',
        year: j['year'],
        sourceUrl: j['source_url'],
      );
}

class SemanticField {
  const SemanticField({
    required this.key,
    required this.label,
    required this.description,
    required this.termCount,
  });

  final String key;
  final String label;
  final String description;
  final int termCount;

  factory SemanticField.fromJson(Map<String, dynamic> j) => SemanticField(
        key: j['key'],
        label: j['label'],
        description: j['description'] ?? '',
        termCount: j['term_count'] ?? 0,
      );
}

/// Una consulta puede ser un término suelto o un campo semántico completo.
class AnalysisQuery {
  const AnalysisQuery({
    this.term = '',
    this.semanticField,
    this.extraTerms = const [],
    this.language = 'en',
    this.workIds,
  });

  final String term;
  final String? semanticField;
  final List<String> extraTerms;
  final String language;
  final List<String>? workIds;

  bool get isEmpty => term.trim().isEmpty && semanticField == null;

  String get displayLabel =>
      semanticField != null && term.trim().isEmpty ? semanticField! : term;

  AnalysisQuery copyWith({
    String? term,
    String? semanticField,
    bool clearField = false,
    List<String>? extraTerms,
    String? language,
    List<String>? workIds,
  }) =>
      AnalysisQuery(
        term: term ?? this.term,
        semanticField: clearField ? null : (semanticField ?? this.semanticField),
        extraTerms: extraTerms ?? this.extraTerms,
        language: language ?? this.language,
        workIds: workIds ?? this.workIds,
      );

  Map<String, dynamic> toJson() => {
        'term': term,
        'semantic_field': semanticField,
        'extra_terms': extraTerms,
        'language': language,
        'work_ids': workIds,
      };
}

class WorkFrequency {
  const WorkFrequency({
    required this.workId,
    required this.workTitle,
    required this.tradition,
    required this.rawCount,
    required this.verseCount,
    required this.totalTokens,
    required this.per10k,
    required this.dispersion,
    required this.divisionsPresent,
    required this.divisionsTotal,
  });

  final String workId;
  final String workTitle;
  final String tradition;
  final int rawCount;
  final int verseCount;
  final int totalTokens;
  final double per10k;
  final double dispersion;
  final int divisionsPresent;
  final int divisionsTotal;

  Tradition get traditionEnum => Tradition.from(tradition);

  factory WorkFrequency.fromJson(Map<String, dynamic> j) => WorkFrequency(
        workId: j['work_id'],
        workTitle: j['work_title'],
        tradition: j['tradition'],
        rawCount: j['raw_count'],
        verseCount: j['verse_count'],
        totalTokens: j['total_tokens'],
        per10k: (j['per_10k'] as num).toDouble(),
        dispersion: (j['dispersion'] as num).toDouble(),
        divisionsPresent: j['divisions_present'],
        divisionsTotal: j['divisions_total'],
      );
}

class Keyness {
  const Keyness({
    required this.workId,
    required this.logLikelihood,
    required this.effectSize,
    required this.direction,
    required this.significant,
  });

  final String workId;
  final double logLikelihood;
  final double effectSize;
  final String direction;
  final bool significant;

  factory Keyness.fromJson(Map<String, dynamic> j) => Keyness(
        workId: j['work_id'],
        logLikelihood: (j['log_likelihood'] as num).toDouble(),
        effectSize: (j['effect_size'] as num).toDouble(),
        direction: j['direction'],
        significant: j['significant'] ?? false,
      );
}

class FrequencyResult {
  const FrequencyResult({
    required this.results,
    required this.keyness,
    required this.resolvedStems,
    required this.caveat,
  });

  final List<WorkFrequency> results;
  final List<Keyness> keyness;
  final List<String> resolvedStems;
  final String caveat;

  Keyness? keynessFor(String workId) {
    for (final k in keyness) {
      if (k.workId == workId) return k;
    }
    return null;
  }

  factory FrequencyResult.fromJson(Map<String, dynamic> j) => FrequencyResult(
        results: (j['results'] as List).map((e) => WorkFrequency.fromJson(e)).toList(),
        keyness: (j['keyness'] as List).map((e) => Keyness.fromJson(e)).toList(),
        resolvedStems: (j['resolved_stems'] as List).cast<String>(),
        caveat: j['caveat'] ?? '',
      );
}

class DivisionFrequency {
  const DivisionFrequency({
    required this.divisionId,
    required this.name,
    required this.ordinal,
    required this.rawCount,
    required this.per10k,
    this.section,
  });

  final int divisionId;
  final String name;
  final int ordinal;
  final int rawCount;
  final double per10k;
  final String? section;

  factory DivisionFrequency.fromJson(Map<String, dynamic> j) => DivisionFrequency(
        divisionId: j['division_id'],
        name: j['name'],
        ordinal: j['ordinal'],
        rawCount: j['raw_count'],
        per10k: (j['per_10k'] as num).toDouble(),
        section: j['section'],
      );
}

class ConcordanceItem {
  const ConcordanceItem({
    required this.verseId,
    required this.ref,
    required this.text,
    required this.workId,
    required this.workTitle,
    required this.tradition,
    required this.division,
    required this.matchedForms,
    required this.hits,
  });

  final int verseId;
  final String ref;
  final String text;
  final String workId;
  final String workTitle;
  final String tradition;
  final String division;
  final List<String> matchedForms;
  final int hits;

  Tradition get traditionEnum => Tradition.from(tradition);

  factory ConcordanceItem.fromJson(Map<String, dynamic> j) => ConcordanceItem(
        verseId: j['verse_id'],
        ref: j['ref'],
        text: j['text'],
        workId: j['work_id'],
        workTitle: j['work_title'],
        tradition: j['tradition'],
        division: j['division'] ?? '',
        matchedForms: (j['matched_forms'] as List).cast<String>(),
        hits: j['hits'] ?? 1,
      );
}

class ConcordanceResult {
  const ConcordanceResult({required this.total, required this.items});
  final int total;
  final List<ConcordanceItem> items;

  factory ConcordanceResult.fromJson(Map<String, dynamic> j) => ConcordanceResult(
        total: j['total'] ?? 0,
        items: (j['items'] as List).map((e) => ConcordanceItem.fromJson(e)).toList(),
      );
}

class ParallelColumn {
  const ParallelColumn({
    required this.workId,
    required this.title,
    required this.tradition,
    required this.verses,
  });

  final String workId;
  final String title;
  final String tradition;
  final List<ConcordanceItem> verses;

  Tradition get traditionEnum => Tradition.from(tradition);

  factory ParallelColumn.fromJson(Map<String, dynamic> j) => ParallelColumn(
        workId: j['work_id'],
        title: j['title'],
        tradition: j['tradition'],
        verses: (j['verses'] as List).map((e) => ConcordanceItem.fromJson(e)).toList(),
      );
}

class Collocation {
  const Collocation({
    required this.lemma,
    required this.example,
    required this.jointCount,
    required this.pmi,
  });

  final String lemma;
  final String example;
  final int jointCount;
  final double pmi;

  factory Collocation.fromJson(Map<String, dynamic> j) => Collocation(
        lemma: j['lemma'],
        example: j['example'] ?? j['lemma'],
        jointCount: j['joint_count'],
        pmi: (j['pmi'] as num).toDouble(),
      );
}

class SimilarVerse {
  const SimilarVerse({
    required this.verseId,
    required this.ref,
    required this.text,
    required this.workId,
    required this.tradition,
    required this.similarity,
  });

  final int verseId;
  final String ref;
  final String text;
  final String workId;
  final String tradition;
  final double similarity;

  Tradition get traditionEnum => Tradition.from(tradition);

  factory SimilarVerse.fromJson(Map<String, dynamic> j) => SimilarVerse(
        verseId: j['verse_id'],
        ref: j['ref'],
        text: j['text'],
        workId: j['work_id'],
        tradition: j['tradition'],
        similarity: (j['similarity'] as num).toDouble(),
      );
}

class SemanticSearchResult {
  const SemanticSearchResult({
    required this.query,
    required this.results,
    required this.caveat,
  });

  final String query;
  final List<SimilarVerse> results;
  final String caveat;

  factory SemanticSearchResult.fromJson(Map<String, dynamic> j) =>
      SemanticSearchResult(
        query: j['query'],
        results: (j['results'] as List).map((e) => SimilarVerse.fromJson(e)).toList(),
        caveat: j['caveat'] ?? '',
      );
}

class Verse {
  const Verse({
    required this.id,
    required this.workId,
    required this.ref,
    required this.text,
    this.division,
  });

  final int id;
  final String workId;
  final String ref;
  final String text;
  final String? division;

  factory Verse.fromJson(Map<String, dynamic> j) => Verse(
        id: j['id'],
        workId: j['work_id'],
        ref: j['ref'],
        text: j['text'],
        division: j['division'],
      );
}

class ExternalContext {
  const ExternalContext({
    required this.title,
    required this.url,
    required this.snippet,
    required this.source,
  });

  final String title;
  final String url;
  final String snippet;
  final String source;

  factory ExternalContext.fromJson(Map<String, dynamic> j) => ExternalContext(
        title: j['title'] ?? '',
        url: j['url'] ?? '',
        snippet: j['snippet'] ?? '',
        source: j['source'] ?? '',
      );
}
