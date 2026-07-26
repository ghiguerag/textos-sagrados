# Publicar la versión web de prueba (gratis) en Render

Objetivo: poner la aplicación en internet, gratis, para que unos probadores la
usen desde un enlace, sin instalar nada, y te den sugerencias.

Por qué Render: en 2026, Hugging Face pasó a cobrar por los Spaces con Docker,
y Fly.io y Koyeb cerraron sus planes gratuitos. Render mantiene un plan gratuito
y, lo mejor, despliega directamente desde tu repositorio de GitHub: no hay que
subir archivos ni manejar tokens.

Cómo funciona: Render lee el `Dockerfile` de tu repositorio, construye la imagen
(instala dependencias y arma el corpus él mismo) y publica la app. No se sube la
base de datos de 196 MB. La búsqueda semántica va desactivada en esta versión
para que quepa en el plan gratuito; el resto funciona igual.

Ten en cuenta del plan gratuito: la app «se duerme» tras un rato sin uso, así
que la primera visita después de un descanso tarda ~30-60 segundos en despertar.
Para probadores es perfectamente aceptable.

## Requisito previo

El `Dockerfile` y el `.dockerignore` deben estar subidos a GitHub (ya los
subimos). Render los toma de ahí.

## Pasos

### 1. Crear la cuenta en Render

1. Entra en https://render.com y pulsa **Get Started** / **Sign up**.
2. Regístrate **con GitHub** (botón «GitHub»): así Render queda conectado a tus
   repositorios sin pasos extra. Autoriza el acceso cuando lo pida.

### 2. Crear el servicio web

1. En el panel, pulsa **New +** → **Web Service**.
2. Elige **Build and deploy from a Git repository** → **Next**.
3. Busca y selecciona tu repositorio **textos-sagrados**. Si no aparece, pulsa
   «Configure account» y concédele acceso a ese repositorio.
4. Render detectará el `Dockerfile` automáticamente (Runtime: Docker).
5. Rellena:
   - **Name**: `textos-sagrados` (formará parte del enlace).
   - **Region**: la más cercana (por ejemplo, Ohio/Oregon).
   - **Instance Type**: **Free**.
6. Pulsa **Create Web Service**.

### 3. Esperar el primer despliegue

Render construye la imagen: instala dependencias y arma el corpus desde las
fuentes en dominio público. Tarda unos minutos; puedes seguirlo en los «Logs».
Cuando aparezca **Live**, tu app estará disponible en un enlace tipo:

`https://textos-sagrados.onrender.com`

Ese es el enlace que compartes con tus probadores.

## Notas

- Si una fuente de textos estuviera caída durante el despliegue, esa obra podría
  faltar; se soluciona pulsando **Manual Deploy → Deploy latest commit**.
- Cada vez que subamos cambios a GitHub, Render vuelve a desplegar solo.
- Para recibir sugerencias, pide a los probadores que usen el botón de contacto
  que la app ya tiene en «Acerca de».
