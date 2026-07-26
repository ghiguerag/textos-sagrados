# Textos Sagrados

Análisis léxico comparado de textos sagrados de cuatro tradiciones, para móvil
y escritorio. Responde con datos a preguntas como *¿qué peso tiene la
misericordia en cada corpus?* o *¿dónde se concentra el vocabulario de la
guerra?*

**Enfoque: descriptivo y neutral.** La aplicación mide patrones léxicos. No
interpreta doctrina, no compara tradiciones en términos de valor y no emite
juicios. Esa decisión también es lo que hace viable publicarla en las tiendas.

---

## Qué hace

| Función | Descripción |
|---|---|
| **Frecuencias normalizadas** | Tasas por 10.000 palabras, nunca conteos brutos |
| **Campos semánticos** | 20 conceptos con ~485 términos: busca *misericordia* y encuentra también *compasión*, *clemencia*, *piedad* |
| **Keyness estadístico** | Log-likelihood (Dunning 1993) para distinguir diferencias reales del ruido |
| **Mapa de calor** | Distribución del término por libro / sura / capítulo |
| **Concordancia** | Cada aparición con su referencia canónica y la forma exacta hallada |
| **Colocaciones** | Qué palabras acompañan al término (PMI): revela el marco conceptual |
| **Contadores desplegables** | Cada cifra abre su detalle: qué formas de la palabra la componen, en qué libros aparece y en qué versículos |
| **Lectura en paralelo** | Cuatro columnas sincronizadas por concepto |
| **Búsqueda semántica** | Encuentra pasajes afines aunque no compartan vocabulario |
| **Contexto en línea** | Comentario externo de Sefaria, Quran.com y Wikipedia, siempre con enlace a la fuente |

## Corpus

Solo ediciones en **dominio público**:

| Tradición | Edición | Año |
|---|---|---|
| Cristianismo | Biblia King James | 1611 |
| Cristianismo | Reina-Valera | 1909 |
| Judaísmo | Tanaj, JPS | 1917 |
| Islam | Corán, trad. E. H. Palmer | 1880 |
| Islam | Corán, trad. M. Pickthall | 1930 |
| Hinduismo | Bhagavad Gita, trad. Edwin Arnold | 1885 |
| Hinduismo | Bhagavad Gita, trad. Swami Sivananda | — |

> Las traducciones modernas (Reina-Valera 1960/1995, NVI, NIV, Corán de Cortés,
> Sahih International) **están protegidas por copyright**. No las añadas al
> corpus sin licencia expresa: es el riesgo legal más serio del proyecto.

**Verificación automática de licencias.** El adaptador de Sefaria comprueba la
licencia declarada de cada libro que descarga y aborta si no es de dominio
público. No es paranoia: la API de Sefaria devuelve por defecto la edición JPS
de 2023, que es CC-BY-NC, y basta con no pedir explícitamente la de 1917 para
acabar distribuyendo material con copyright sin darse cuenta.

---

## Puesta en marcha

### La forma fácil

**Windows:** doble clic en `INSTALAR-Windows.bat`

**macOS y Linux:** abre una terminal en esta carpeta y ejecuta
`bash instalar-mac-linux.sh`

El instalador comprueba que tengas Python, prepara todo, descarga los textos y
arranca el servidor. Si algo falta te dice exactamente qué hacer. Puedes
ejecutarlo las veces que quieras: no repite lo que ya descargó.

Después, para usar la aplicación basta con `INICIAR-Windows.bat` o
`bash iniciar-mac-linux.sh`.

**Búsqueda por significado (opcional).** Hay dos versiones:

- `INSTALAR-BUSQUEDA-LIGERA-Windows.bat` — unos 130 MB, sin PyTorch. **Es la
  que se empaquetaría en la app publicada.**
- `INSTALAR-BUSQUEDA-Windows.bat` — unos 3 GB, calidad máxima. Útil como
  referencia para medir cuánto se pierde con la ligera.

Ambas pueden convivir y compararse con `scripts/comparar_motores.py`. Ver
[`docs/busqueda-por-significado.md`](docs/busqueda-por-significado.md).

> **Si el antivirus avisa de una amenaza durante la instalación**, mira la ruta
> del archivo antes de hacer nada. Si contiene `Temp` y `pip-install`, es un
> falso positivo conocido y está explicado en
> [`docs/problemas-frecuentes.md`](docs/problemas-frecuentes.md). Si está en
> otro sitio, no lo restaures.

Cuando arranque, se abre solo el navegador en **http://localhost:8000** con la
interfaz web: buscador, gráficos de barras, mapas de calor, concordancia y
lectura en paralelo. No requiere instalar nada más y funciona sin conexión.

### La forma manual

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-base.txt

# 1. Comprueba que los endpoints públicos siguen vivos
python scripts/fetch_corpus.py --check

# 2. Descarga y construye el corpus (varios minutos)
python scripts/fetch_corpus.py --out data/corpus.db --skip-failed

# 3. Índice semántico (opcional, ~2-3 GB de descarga)
pip install --only-binary=:all: -r requirements-semantic.txt
python scripts/build_embeddings.py --db data/corpus.db

# 4. Arranca
uvicorn app.main:app --reload
```

Documentación interactiva en <http://localhost:8000/docs>.

Para desarrollar sin red hay un corpus de muestra:

```bash
python scripts/build_sample.py --out data/sample.db
TS_DB_PATH=data/sample.db uvicorn app.main:app --reload
```

### Aplicación

```bash
cd app
flutter pub get
flutter run -d macos     # o windows, linux, chrome, ios, android
```

Apuntando a otro servidor:

```bash
flutter run --dart-define=API_URL=https://api.tudominio.com
```

### Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q   # 71 tests
cd app && flutter test
cd app && python3 tool/verificar_traducciones.py                 # coherencia de los 6 idiomas

# Interfaz web: ejecuta las funciones de pintado con datos reales
cd backend && python tests/ui/generar_payload.py && node tests/ui/test_paneles.js
```

---

## Idiomas

La interfaz está en **español, inglés, portugués, francés, árabe e hindi**. El
árabe activa la disposición de derecha a izquierda automáticamente.

Por defecto la app sigue el idioma del sistema; el usuario puede forzar otro
desde Ajustes.

**Dos ejes distintos que conviene no confundir:** el idioma de la *interfaz* y
el idioma del *corpus* que se analiza. Se puede usar la app en árabe para
analizar textos en inglés. El selector EN/ES de la barra de búsqueda se refiere
al corpus, no a la interfaz.

Para añadir un idioma:

1. Copia `app/lib/l10n/app_es.arb` a `app_<código>.arb` y traduce los valores
2. Añade el `Locale` en `LocaleNotifier.supported`
3. Añade el rótulo de cada campo semántico en `backend/data/lexicon.json`
4. Añade `android/app/src/main/res/values-<código>/strings.xml` y
   `ios/Runner/<código>.lproj/InfoPlist.strings`
5. Ejecuta `python3 tool/verificar_traducciones.py`

> Las traducciones al árabe y al hindi son mías y no han sido revisadas por
> hablantes nativos. Antes de publicar conviene que alguien las repase: un
> error de registro en un texto sobre religión se nota mucho más que en
> cualquier otra app.

---

## Arquitectura

```
backend/
  app/core/
    tokenizer.py    Normalización multilingüe y stemming (sin dependencias)
    schema.sql      Esquema unificado obra → división → versículo
    ingest.py       Adaptadores de formato; añadir un texto = añadir un adaptador
    analysis.py     Frecuencias, keyness, concordancia, colocaciones
    lexicon.py      Campos semánticos (editables en data/lexicon.json)
    embeddings.py   Similitud vectorial multilingüe
    websearch.py    Contexto externo, restringido por allowlist
  app/main.py       API REST
  scripts/          Ingesta, muestra, embeddings

app/lib/
  l10n/             Traducciones (6 ficheros ARB)
  core/             Cliente HTTP, tema y correspondencia clave → texto
  models/           Espejo de los contratos del backend
  state/            Providers de Riverpod
  screens/          Frecuencias · Concordancia · Paralelo · Semántica · Ajustes
  widgets/          Barra de consulta, mapa de calor, tarjeta de versículo
app/tool/           Verificador de traducciones
docs/fichas-tienda/ Textos de App Store y Google Play en los 6 idiomas
```

**La API no devuelve texto para el usuario, solo identificadores.** Los avisos
metodológicos y las direcciones estadísticas viajan como claves
(`frequency_normalization`, `over`, `under`) y la app las traduce. Así el
servidor no necesita saber nada del idioma del usuario, y añadir un idioma no
obliga a tocar el backend.

**Por qué SQLite y no un motor de búsqueda.** El corpus completo son unos 40 MB
de texto. SQLite con FTS5 y un índice de lemas propio resuelve cada consulta en
milisegundos, cabe en un móvil y permite un futuro modo totalmente offline.
Elasticsearch sería infraestructura sin contrapartida.

---

## Documentación

- [`docs/guia-interpretacion.md`](docs/guia-interpretacion.md) — **qué significa
  cada cifra y qué conclusiones no se pueden sacar.** Empieza por aquí.
- [`docs/busqueda-por-significado.md`](docs/busqueda-por-significado.md) — qué
  motor de embeddings empaquetar y por qué
- [`docs/publicacion.md`](docs/publicacion.md) — requisitos de App Store y
  Google Play
- [`docs/problemas-frecuentes.md`](docs/problemas-frecuentes.md) — errores
  habituales y su solución
- [`docs/fichas-tienda/`](docs/fichas-tienda/) — textos de tienda en 6 idiomas

## Decisiones metodológicas

Estas cuatro decisiones son las que separan una herramienta creíble de un
generador de cifras llamativas:

1. **Nada de conteos brutos.** La Biblia KJV tiene ~790.000 palabras; el
   Bhagavad Gita, ~20.000. «La Biblia menciona *amor* 300 veces y el Gita 40»
   no significa nada. Todo se normaliza por 10.000 palabras.

2. **Significación explícita.** Una diferencia de tasas puede ser azar. Se
   contrasta con log-likelihood y solo se marca como distintivo lo que supera
   p < 0,0001.

3. **Dispersión junto a la frecuencia.** Un término que aparece 50 veces en un
   único capítulo no caracteriza la obra igual que uno repartido por todo el
   texto.

4. **Un solo idioma por comparación.** El conjunto por defecto son cuatro
   textos en inglés. La interfaz detecta qué idiomas tienes instalados y avisa
   si eliges uno sin textos, en vez de devolver cero resultados sin explicar
   por qué.

5. **Se compara la traducción, no el original.** El vocabulario del traductor
   condiciona el resultado. Por eso el conjunto por defecto usa cuatro textos
   en inglés: comparar frecuencias entre idiomas distintos no es lingüísticamente
   válido. La app lo advierte en cada pantalla de resultados.

---

## Estado y siguientes pasos

Funciona hoy: motor, API, corpus, las cinco pantallas, 70 tests en verde.

Pendiente antes de publicar:

- [ ] Ejecutar el instalador y ajustar los adaptadores cuyas URLs hayan cambiado
- [ ] Revisión nativa de las traducciones al árabe y al hindi
- [ ] Modo offline: empaquetar el SQLite en la app y prescindir del backend
- [ ] Iconos y capturas de pantalla (fichas de tienda ya redactadas en
      `docs/fichas-tienda/`)
- [ ] Corpus en español (Reina-Valera 1909) como conjunto paralelo separado

## Licencia

Código bajo MIT. Los textos son de dominio público y cada obra declara su
edición y procedencia en la pantalla de Ajustes.
