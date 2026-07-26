import 'package:flutter/widgets.dart';

import '../l10n/app_localizations.dart';
import 'api_client.dart';

/// Traduce los identificadores que devuelve el backend.
///
/// La API no envía texto para el usuario, solo claves. Toda la correspondencia
/// clave → texto vive aquí, en un único sitio.
extension L10nMapping on L {
  /// Avisos metodológicos (`caveat` en las respuestas de la API).
  String caveat(String key) => switch (key) {
        'frequency_normalization' => caveatFrequencyNormalization,
        'semantic_similarity' => caveatSemanticSimilarity,
        _ => '',
      };

  /// Dirección del contraste estadístico (`direction` en keyness).
  String keynessDirection(String key) => switch (key) {
        'over' => distinctivelyFrequent,
        'under' => distinctivelyRare,
        _ => '',
      };

  /// Mensaje de error a partir del tipo de fallo del cliente HTTP.
  String apiError(Object error) {
    if (error is! ApiException) return errGeneric;
    return switch (error.kind) {
      ApiErrorKind.connection => errConnection,
      ApiErrorKind.notFound => errNotFound,
      ApiErrorKind.invalidQuery => error.detail ?? errInvalidQuery,
      ApiErrorKind.semanticUnavailable => errSemanticUnavailable,
      ApiErrorKind.unknown => error.detail ?? errGeneric,
    };
  }
}

/// Atajo para no repetir `L.of(context)` en cada widget.
extension L10nContext on BuildContext {
  L get l10n => L.of(this);
}
