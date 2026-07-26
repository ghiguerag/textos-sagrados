import 'package:flutter_test/flutter_test.dart';
import 'package:textos_sagrados/models/models.dart';

void main() {
  group('AnalysisQuery', () {
    test('está vacía sin término ni campo semántico', () {
      expect(const AnalysisQuery().isEmpty, isTrue);
      expect(const AnalysisQuery(term: 'mercy').isEmpty, isFalse);
      expect(const AnalysisQuery(semanticField: 'paz').isEmpty, isFalse);
    });

    test('clearField elimina el campo semántico', () {
      const q = AnalysisQuery(semanticField: 'paz');
      expect(q.copyWith(term: 'mercy', clearField: true).semanticField, isNull);
    });

    test('serializa con las claves que espera el backend', () {
      final json = const AnalysisQuery(term: 'mercy', language: 'en').toJson();
      expect(json.keys, containsAll(['term', 'semantic_field', 'language', 'work_ids']));
    });
  });

  group('Tradition', () {
    test('mapea los identificadores del backend', () {
      expect(Tradition.from('islam'), Tradition.islam);
      expect(Tradition.from('JUDAISMO'), Tradition.judaismo);
    });

    test('un valor desconocido no lanza excepción', () {
      expect(Tradition.from('zoroastrismo'), isA<Tradition>());
    });
  });

  group('Deserialización', () {
    test('WorkFrequency admite enteros donde se esperan decimales', () {
      // El backend serializa 0 en vez de 0.0 cuando la tasa es exacta.
      final f = WorkFrequency.fromJson({
        'work_id': 'kjv', 'work_title': 'Biblia (KJV)', 'tradition': 'cristianismo',
        'language': 'en', 'raw_count': 0, 'verse_count': 0, 'total_tokens': 100,
        'per_10k': 0, 'dispersion': 0, 'divisions_present': 0, 'divisions_total': 66,
      });
      expect(f.per10k, 0.0);
      expect(f.traditionEnum, Tradition.cristianismo);
    });

    test('Work tolera campos opcionales ausentes', () {
      final w = Work.fromJson({
        'id': 'gita', 'tradition': 'hinduismo', 'title': 'Bhagavad Gita',
        'edition': 'Arnold', 'language': 'en', 'license': 'public-domain',
      });
      expect(w.year, isNull);
      expect(w.totalTokens, 0);
    });
  });
}
