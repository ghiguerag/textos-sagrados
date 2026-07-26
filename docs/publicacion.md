# Guía de publicación

Notas prácticas para llevar la app a las tiendas. El contenido religioso está
sujeto a revisiones más estrictas de lo habitual: la mayoría de rechazos en esta
categoría son evitables.

## 1. Riesgo principal: contenido religioso

Apple y Google no prohíben el contenido religioso, pero sí el que denigra a un
grupo. Lo que protege a esta app:

- **Posicionamiento descriptivo.** La ficha debe decir «herramienta de análisis
  textual», no «compara religiones». La diferencia importa en la revisión.
- **Sin comparación valorativa.** Nada de rankings, puntuaciones ni conclusiones
  del tipo «el texto X es más violento». La app muestra tasas; el usuario
  interpreta.
- **Advertencias visibles.** Los avisos metodológicos aparecen junto a los
  resultados, no ocultos en un menú.
- **Sin contenido generado libremente.** No hay un LLM redactando comentarios
  sobre religión. El contexto externo procede de una allowlist de fuentes
  académicas y siempre lleva su enlace.

Redacta la descripción de la tienda en ese registro. Un ejemplo:

> Herramienta de análisis léxico para el estudio comparado de textos
> religiosos en dominio público. Calcula frecuencias normalizadas,
> concordancias y distribución de vocabulario mediante métodos estándar de
> lingüística de corpus. No interpreta doctrina.

## 2. Licencias de los textos

Es el segundo motivo de rechazo, y además un riesgo legal real.

- Incluye solo ediciones en dominio público. Verifica año de publicación **y**
  año de muerte del traductor: en la UE la protección se extiende 70 años tras
  la muerte del autor, no tras la publicación.
- La pantalla de Ajustes ya muestra la atribución de cada obra. No la quites:
  es el registro que se enseña si alguien reclama.
- Si algún día añades una traducción con licencia (API.Bible y similares),
  sus términos suelen exigir texto de atribución literal y prohibir el
  almacenamiento en caché. Eso cambia la arquitectura: pasaría a consultarse en
  línea, no a empaquetarse.

## 3. Requisitos por plataforma

### iOS / App Store
- Cuenta de Apple Developer: 99 USD/año.
- Iconos hasta 1024×1024, sin canal alfa.
- Capturas de 6.7" y 5.5", más 12.9" si soportas iPad.
- Política de privacidad obligatoria y accesible por URL pública.
- Ficha de privacidad: si no recoges datos personales, decláralo. Esta app no
  necesita recogerlos, lo cual simplifica mucho la revisión.
- `NSAppTransportSecurity`: el backend debe servirse por HTTPS. En desarrollo,
  añade la excepción solo para localhost.

### Android / Google Play
- Cuenta de desarrollador: 25 USD (pago único).
- Formato AAB: `flutter build appbundle --release`.
- Firma con clave subida a Play App Signing.
- Cuestionario de clasificación de contenido: marca la categoría de
  «referencia / educación», no «estilo de vida».
- Declaración de seguridad de datos, coherente con la política de privacidad.

### Windows / Microsoft Store
- Cuenta de desarrollador: 19 USD (pago único).
- `flutter build windows --release` y empaquetado MSIX
  (paquete `msix` de pub.dev).

### macOS
- Sandbox activado, con `com.apple.security.network.client` para que la app
  pueda hablar con el backend.
- Notarización obligatoria para distribuir fuera de la Mac App Store.

### Linux
- Flatpak o Snap. Sin proceso de revisión editorial.

## 4. Arquitectura de despliegue

Dos caminos, con implicaciones muy distintas:

**A. Backend alojado** (lo que hay ahora)
- Ventajas: corpus actualizable sin republicar, índice semántico completo,
  app ligera.
- Coste: un VPS pequeño basta (2 GB de RAM sin embeddings; 4 GB con ellos).
- Riesgo: si el servidor cae, la app no funciona. Y es un coste recurrente.

**B. Corpus empaquetado**
- El SQLite completo son ~120 MB; comprimido, bastante menos. Cabe en la app.
- Ventajas: funciona sin conexión, sin coste de servidor, sin latencia.
- Limitación: la búsqueda semántica necesita el modelo vectorial (~470 MB), que
  no es razonable empaquetar en móvil. Solución habitual: análisis léxico en
  local y búsqueda semántica en línea como función opcional.

**Recomendación:** híbrido. Empaqueta el corpus para que la app sea útil sin
conexión desde el primer arranque, y deja en línea solo la búsqueda semántica y
el contexto externo. Es lo que mejor resiste que el backend se caiga.

## 5. Checklist previa al envío

- [ ] Política de privacidad publicada y enlazada desde la app
- [ ] Atribución de todas las ediciones visible en Ajustes
- [ ] Descripción de tienda en registro descriptivo, sin lenguaje comparativo
- [ ] Avisos metodológicos visibles junto a los resultados
- [ ] Probado en pantalla pequeña (360 dp) y en escritorio ancho
- [ ] Comportamiento correcto sin conexión: mensaje claro, no pantalla en blanco
- [ ] HTTPS en producción, sin excepciones de transporte
- [ ] Capturas que muestren el análisis, no pantallas vacías
- [ ] Versión y build number coherentes en `pubspec.yaml`
