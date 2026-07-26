# Imagen para desplegar Textos Sagrados como versión web (p. ej. Hugging Face
# Spaces o cualquier servicio que acepte un Dockerfile).
#
# Idea clave: la base de datos (196 MB) NO se sube. El propio contenedor la
# construye al montarse, con los mismos scripts que usas en tu PC, a partir de
# fuentes en dominio público. Así el repositorio se mantiene ligero.
#
# La búsqueda semántica (modelo de ~470 MB) queda desactivada en esta imagen
# para que entre holgada en un plan gratuito. El resto de la aplicación
# —frecuencias, panorama, concordancia, lado a lado, perfil— funciona igual.

FROM python:3.12-slim

# Evita preguntas interactivas y acelera pip.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Dependencias primero, para aprovechar la caché de capas de Docker.
COPY backend/requirements-base.txt ./requirements-base.txt
RUN pip install -r requirements-base.txt

# 2) Código de la aplicación.
COPY backend/ /app/

# 3) Construir el corpus durante el montaje. Sin --all se usa el conjunto por
#    defecto: las cuatro obras canónicas, una por tradición (Biblia, Tanaj,
#    Corán y Bhagavad Gita). El Gita va empaquetado en el repo, así que las
#    cuatro tradiciones quedan garantizadas aunque una fuente web falle.
#    --skip-failed evita que una descarga caída tumbe todo el despliegue.
RUN python scripts/fetch_corpus.py --skip-failed --out data/corpus.db

# 4) La carpeta de datos debe ser escribible: la app guarda ahí la caché de
#    traducciones (Hugging Face ejecuta el contenedor con un usuario sin root).
RUN chmod -R 777 /app/data

# Sin el modelo pesado de embeddings: la versión web es liviana.
ENV TS_ENABLE_EMBEDDINGS=false \
    TS_DB_PATH=/app/data/corpus.db \
    TS_LEXICON_PATH=/app/data/lexicon.json

# El puerto lo fija el servicio de hosting mediante la variable PORT (Render y
# otros). Si no viene, usamos 7860. La forma «shell» permite expandir la
# variable en tiempo de ejecución.
EXPOSE 7860

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
