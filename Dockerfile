# Imagen para desplegar Textos Sagrados como versión web (Render, un VPS con
# Docker, o cualquier servicio que acepte un Dockerfile).
#
# Idea clave: la base de datos NO se sube. El propio contenedor la construye al
# montarse, con los mismos scripts que usas en tu PC, a partir de fuentes en
# dominio público. Así el repositorio se mantiene ligero.
#
# La búsqueda por significado se activa con el argumento de construcción
# EMB_ENGINE:
#   (vacío)   -> sin búsqueda por significado. Para planes con poca RAM (Render
#                gratuito, 512 MB). Arranque liviano; esa pestaña queda inactiva.
#   ligero    -> model2vec 128M multilingüe. Buena calidad, ~600 MB de RAM.
#                Ideal para un VPS de 4 GB. Rápido de construir (sin PyTorch).
#   minimo    -> el más pequeño (~32 MB), menor calidad. Último recurso.
#   calidad   -> el mejor, pero con PyTorch: pesado y lento en 1 vCPU.
#
#   Render (por defecto):  build normal, sin significado.
#   VPS:  docker build --build-arg EMB_ENGINE=ligero .

FROM python:3.12-slim

# Evita preguntas interactivas y acelera pip. HF_HOME fija dónde se descarga el
# modelo de significado, para que quede dentro de la imagen y no haya que
# volver a bajarlo en cada arranque.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/hf-cache

WORKDIR /app

# 1) Dependencias primero, para aprovechar la caché de capas de Docker.
#    requirements-light = base + model2vec (el motor ligero de significado).
#    model2vec es liviano aunque no se use, así una sola imagen sirve para todo.
COPY backend/requirements-base.txt ./requirements-base.txt
COPY backend/requirements-light.txt ./requirements-light.txt
RUN pip install -r requirements-light.txt

# 2) Código de la aplicación.
COPY backend/ /app/

# 3) Construir el corpus durante el montaje: las cuatro obras canónicas, una por
#    tradición. El Gita va empaquetado en el repo, así que las cuatro quedan
#    garantizadas aunque una fuente web falle. --skip-failed no tumba el build.
RUN python scripts/fetch_corpus.py --skip-failed --out data/corpus.db

# 4) Índice de búsqueda por significado, solo si se pidió un motor. Descarga el
#    modelo (queda en HF_HOME dentro de la imagen) y calcula el vector de cada
#    versículo. Es el paso más lento del montaje.
ARG EMB_ENGINE=
RUN if [ -n "$EMB_ENGINE" ]; then \
        python scripts/build_embeddings.py --engine "$EMB_ENGINE" --db data/corpus.db ; \
    else \
        echo "Sin índice de significado (EMB_ENGINE vacío)." ; \
    fi

# 5) Carpetas escribibles: la app guarda ahí la caché de traducciones y el
#    servicio puede ejecutar el contenedor con un usuario sin privilegios.
RUN chmod -R 777 /app/data /app/hf-cache

ENV TS_DB_PATH=/app/data/corpus.db \
    TS_LEXICON_PATH=/app/data/lexicon.json

# El puerto lo fija el servicio de hosting mediante la variable PORT (Render y
# otros). Si no viene, usamos 7860. La forma «shell» expande la variable.
EXPOSE 7860

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
