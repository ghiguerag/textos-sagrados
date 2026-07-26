# Subir el proyecto a GitHub con GitHub Desktop

Guía para la primera vez. No hace falta escribir ningún comando: todo se hace
con ventanas y botones.

Tiempo estimado: 10–15 minutos.

---

## Antes de empezar

- Necesitas tu cuenta de GitHub (la que ya tienes).
- La base de datos `corpus.db` (196 MB) **no** se sube: ya está excluida en el
  archivo `.gitignore`. GitHub no admite archivos de más de 100 MB, y además no
  hace falta subirla porque se reconstruye con los scripts del proyecto.

---

## Paso 1 · Instalar GitHub Desktop

1. Entra en **https://desktop.github.com** y descarga el programa.
2. Instálalo (doble clic al instalador y siguiente, siguiente).
3. Ábrelo.

## Paso 2 · Iniciar sesión

1. Al abrirlo, elige **"Sign in to GitHub.com"**.
2. Se abrirá el navegador; escribe tu usuario y contraseña de GitHub y autoriza.
3. Vuelve al programa. Te pedirá confirmar tu nombre y correo: usa el mismo de
   tu cuenta (`ghiguerag@gmail.com`).

## Paso 3 · Añadir la carpeta del proyecto

1. En el menú de arriba: **File → Add Local Repository**
   (Archivo → Añadir repositorio local).
2. Pulsa **Choose…** y selecciona esta carpeta:

   `C:\Users\ghigu\OneDrive\Documentos\Claude IA\PROYECTOS\textos-sagrados`

3. Como la carpeta todavía no es un repositorio, GitHub Desktop mostrará un
   aviso con un enlace azul que dice **"create a repository"**. Haz clic en él.
4. En la ventana que aparece:
   - **Name**: `textos-sagrados` (o el nombre que prefieras).
   - **Description**: algo como *"Análisis léxico comparado de textos sagrados"*.
   - Deja lo demás como está.
   - Pulsa **Create Repository**.

## Paso 4 · Hacer la primera "foto" del proyecto (commit)

1. A la izquierda verás la lista de todos los archivos del proyecto marcados.
2. Abajo a la izquierda hay una caja **"Summary"**. Escribe algo como:
   `Primera versión de la aplicación`.
3. Pulsa el botón azul **Commit to main**.

> Un *commit* es una foto del proyecto en este momento. Cada vez que hagas
> cambios importantes, harás un commit nuevo y quedará guardado en el historial.

## Paso 5 · Publicar en GitHub (subir a la nube)

1. Arriba a la derecha aparecerá un botón **"Publish repository"**. Púlsalo.
2. En la ventana:
   - **Keep this code private**: déjalo **marcado** si quieres que solo tú lo
     veas por ahora; **desmárcalo** si quieres que sea público. (Puedes
     cambiarlo después.)
   - Pulsa **Publish Repository**.
3. Espera a que termine de subir. ¡Listo! Ya está en tu cuenta de GitHub.

## Paso 6 · Comprobar

- En GitHub Desktop, menú **Repository → View on GitHub**, o entra a
  `https://github.com/TU-USUARIO/textos-sagrados`.
- Deberías ver todos los archivos: `README.md`, `LICENSE`, las carpetas
  `backend`, `assets`, `docs`, y los instaladores.

---

## De aquí en adelante

Cada vez que cambiemos algo en el proyecto:

1. Abre GitHub Desktop (detecta los cambios solo).
2. Escribe un resumen corto en **Summary**.
3. **Commit to main**.
4. Pulsa **Push origin** (arriba) para subirlo a la nube.

Eso es todo. Público o privado, tu proyecto queda respaldado y con historial.

---

## Dudas frecuentes

**¿Se subió la base de datos por error?**
No debería: está en `.gitignore`. Si en la lista de archivos del Paso 4 ves
`corpus.db`, avísame antes de hacer commit.

**¿Privado o público?**
- *Privado*: solo tú lo ves. Bien mientras desarrollas.
- *Público*: cualquiera puede verlo y es necesario si algún día quieres que
  otras personas colaboren. Con licencia MIT (la que tiene el proyecto) pueden
  usar el código citándote.

**¿Y si me equivoco?**
Nada se rompe. GitHub guarda el historial; casi todo se puede deshacer.
