import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';

/// URL del backend. Configurable para poder apuntar a un servidor local
/// durante el desarrollo y a producción en la app publicada.
final baseUrlProvider = StateNotifierProvider<BaseUrlNotifier, String>(
  (ref) => BaseUrlNotifier(),
);

class BaseUrlNotifier extends StateNotifier<String> {
  BaseUrlNotifier() : super(const String.fromEnvironment(
        'API_URL',
        defaultValue: 'http://localhost:8000',
      )) {
    _restore();
  }

  static const _key = 'api_base_url';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_key);
    if (saved != null && saved.isNotEmpty) state = saved;
  }

  Future<void> set(String url) async {
    state = url.trim().replaceAll(RegExp(r'/+$'), '');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, state);
  }
}

final apiProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(baseUrlProvider));
});

/// Motivo del fallo, en forma de código. El cliente HTTP no conoce el idioma
/// de la interfaz, así que nunca devuelve texto ya traducido.
enum ApiErrorKind { connection, notFound, invalidQuery, semanticUnavailable, unknown }

class ApiException implements Exception {
  ApiException(this.kind, {this.detail, this.statusCode});

  final ApiErrorKind kind;
  final String? detail;
  final int? statusCode;

  @override
  String toString() => detail ?? kind.name;
}

class ApiClient {
  ApiClient(String baseUrl)
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 40),
          headers: {'Accept': 'application/json'},
        ));

  final Dio _dio;

  Never _fail(DioException e) {
    final code = e.response?.statusCode;
    final detail = e.response?.data is Map ? e.response?.data['detail'] : null;
    throw ApiException(
      switch (code) {
        503 => ApiErrorKind.semanticUnavailable,
        404 => ApiErrorKind.notFound,
        400 => ApiErrorKind.invalidQuery,
        _ => e.type == DioExceptionType.connectionError ||
                e.type == DioExceptionType.connectionTimeout
            ? ApiErrorKind.connection
            : ApiErrorKind.unknown,
      },
      detail: detail?.toString(),
      statusCode: code,
    );
  }

  Future<List<Work>> works() async {
    try {
      final r = await _dio.get('/works');
      return (r.data as List).map((e) => Work.fromJson(e)).toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<SemanticField>> semanticFields({String lang = 'en'}) async {
    try {
      final r = await _dio.get('/semantic-fields',
          queryParameters: {'lang': lang});
      return (r.data as List).map((e) => SemanticField.fromJson(e)).toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<FrequencyResult> frequency(AnalysisQuery query) async {
    try {
      final r = await _dio.post('/frequency', data: query.toJson());
      return FrequencyResult.fromJson(r.data);
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<DivisionFrequency>> divisionFrequency(
      String workId, AnalysisQuery query) async {
    try {
      final r = await _dio.post('/frequency/$workId/divisions',
          data: query.toJson());
      return (r.data as List).map((e) => DivisionFrequency.fromJson(e)).toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<ConcordanceResult> concordance(AnalysisQuery query,
      {int limit = 100, int offset = 0}) async {
    try {
      final r = await _dio.post('/concordance',
          data: query.toJson(),
          queryParameters: {'limit': limit, 'offset': offset});
      return ConcordanceResult.fromJson(r.data);
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<ParallelColumn>> parallel(AnalysisQuery query,
      {int limitPerWork = 10}) async {
    try {
      final r = await _dio.post('/parallel', data: {
        ...query.toJson(),
        'limit_per_work': limitPerWork,
      });
      return (r.data['columns'] as List)
          .map((e) => ParallelColumn.fromJson(e))
          .toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<Collocation>> collocations(AnalysisQuery query,
      {int window = 5}) async {
    try {
      final r = await _dio.post('/collocations',
          data: query.toJson(), queryParameters: {'window': window});
      return (r.data['results'] as List)
          .map((e) => Collocation.fromJson(e))
          .toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<SemanticSearchResult> semanticSearch(String q,
      {int topK = 20, List<String>? workIds}) async {
    try {
      final r = await _dio.get('/semantic-search', queryParameters: {
        'q': q,
        'top_k': topK,
        if (workIds != null) 'work_ids': workIds,
      });
      return SemanticSearchResult.fromJson(r.data);
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<Verse>> search(String q, {String? workId, int limit = 50}) async {
    try {
      final r = await _dio.get('/search', queryParameters: {
        'q': q,
        if (workId != null) 'work_id': workId,
        'limit': limit,
      });
      return (r.data as List).map((e) => Verse.fromJson(e)).toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }

  Future<List<ExternalContext>> context({String? ref, String? topic}) async {
    try {
      final r = await _dio.get('/context', queryParameters: {
        if (ref != null) 'ref': ref,
        if (topic != null) 'topic': topic,
      });
      return (r.data['results'] as List)
          .map((e) => ExternalContext.fromJson(e))
          .toList();
    } on DioException catch (e) {
      _fail(e);
    }
  }
}
