# Publicar la versión web de prueba en Hugging Face Spaces

Objetivo: poner la aplicación en internet, gratis, para que unos probadores la
usen desde un enlace y te den sugerencias. No necesitan instalar nada.

Cómo funciona: subimos el código a un «Space» de Hugging Face con el
`Dockerfile` de la raíz. El contenedor construye la base de datos él mismo al
desplegar, así que no hay que subir el archivo de 196 MB. La búsqueda semántica
va desactivada en esta versión para que entre en el plan gratuito; el resto
funciona igual.

## Lo que hará el desarrollador (tú) y lo que hago yo

- **Tú**: crear una cuenta gratuita en Hugging Face y un «token» de acceso
  (una contraseña temporal para subir el código). No compartas ese token en el
  chat; lo pegas solo cuando Git te lo pida.
- **Yo**: te guío por cada pantalla, dejo listos los archivos y preparo el
  envío del código.

## Pasos

### 1. Crear la cuenta

1. Entra en https://huggingface.co/join
2. Regístrate con tu correo (`ghiguerag@gmail.com`) y confirma desde el email.

### 2. Crear el Space

1. Entra en https://huggingface.co/new-space
2. **Owner**: tu usuario. **Space name**: `textos-sagrados`.
3. **License**: MIT.
4. **Select the SDK**: elige **Docker** → **Blank**.
5. **Visibility**: Public (para que los probadores entren sin cuenta).
6. Pulsa **Create Space**.

### 3. Crear un token de acceso

1. Entra en https://huggingface.co/settings/tokens
2. **New token** → tipo **Write** → nómbralo `deploy` → **Generate**.
3. Cópialo y guárdalo un momento. Lo usarás como contraseña al subir el código.

### 4. Subir el código

Se sube con Git a la dirección del Space. Como el `README.md` del Space necesita
una cabecera especial (la que está en `deploy/hf-space-README.md`), usamos esa
versión al publicar. Te acompaño en este paso por Git Bash; en resumen:

```bash
# dentro de la carpeta del proyecto
git remote add space https://huggingface.co/spaces/TU_USUARIO/textos-sagrados
git subtree ...      # (te doy el comando exacto según tu caso)
```

No te preocupes por esta parte técnica: la hacemos juntos y te digo qué escribir.

### 5. Esperar el despliegue

Hugging Face construye la imagen (instala dependencias y arma el corpus). Tarda
unos minutos. Cuando el Space muestre «Running», tu app estará en:

`https://TU_USUARIO-textos-sagrados.hf.space`

Ese es el enlace que compartes con tus probadores.

## Notas

- Si una fuente de textos estuviera caída durante el despliegue, esa obra podría
  faltar; se soluciona volviendo a desplegar (botón «Restart» / «Factory
  rebuild» del Space).
- Para recibir sugerencias ordenadas, puedes pedir a los probadores que usen el
  botón de contacto que ya tiene la app en «Acerca de».
