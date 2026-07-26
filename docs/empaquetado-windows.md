# Empaquetar y publicar en la Microsoft Store

Guía paso a paso para convertir Textos Sagrados en un programa de Windows con
icono propio y llevarlo a la tienda. El camino más barato: 19 USD una sola vez,
sin necesidad de un Mac.

Estado: el icono y el empaquetado ya están preparados. Lo que sigue lo ejecutas
tú en tu ordenador, porque construir el `.exe` y firmarlo requiere Windows.

---

## Paso 1 · Construir el programa

Doble clic en `CONSTRUIR-APP-Windows.bat`.

Instala las herramientas, construye el ejecutable y copia los textos a su lado.
Construye en una carpeta local (no en OneDrive, para que no bloquee los
archivos) y te deja un **acceso directo «Textos Sagrados» en el Escritorio**.

El programa queda en:

```
%LOCALAPPDATA%\TextosSagrados\dist\Textos Sagrados\Textos Sagrados.exe
```

Doble clic en el acceso directo del Escritorio para probarlo. Se abre en una
ventana limpia (Edge en «modo app», sin barras ni pestañas), con el icono del
libro y sin ventana negra.

> Si te sobra una carpeta `backend\dist` de un intento anterior dentro del
> proyecto, puedes borrarla: ocupa espacio y ya no se usa (la construcción va
> ahora a la carpeta local de arriba).

**Si la construcción falla**, casi siempre es un «hidden import» que PyInstaller
no detectó. El error dice cuál. Se añade una línea al archivo
`backend\TextosSagrados.spec` en la lista `hiddenimports` y se vuelve a
construir. Pásame el error y te digo la línea exacta.

> La versión de escritorio incluye todo el análisis léxico —frecuencias,
> panorama, concordancia, lado a lado, perfiles— pero **no** la búsqueda por
> significado, cuyos modelos pesan cientos de MB. La app lo gestiona sola: esa
> pestaña avisa de que no está disponible. Si más adelante quieres incluirla,
> se puede, a cambio de un ejecutable mucho más grande.

---

## Paso 2 · Los iconos y mosaicos (ya generados)

En la carpeta `assets\` tienes todo lo que pide la tienda:

| Archivo | Para qué |
|---|---|
| `icono.ico` | El ejecutable y la barra de tareas |
| `Square44x44Logo.png` | Icono en la lista de apps |
| `Square150x150Logo.png` | Mosaico mediano |
| `Square310x310Logo.png` | Mosaico grande |
| `Wide310x150Logo.png` | Mosaico ancho |
| `StoreLogo.png` | Logo en la ficha de la tienda |
| `icono-512.png`, `icono-1024.png` | Ficha e ilustración |

No hay que crear nada más de gráficos base. Faltan solo las **capturas de
pantalla** de la app funcionando, que se hacen cuando el programa esté
construido.

---

## Paso 3 · Cuenta de desarrollador

1. Entra en <https://partner.microsoft.com/dashboard>
2. Regístrate como desarrollador individual (19 USD, pago único)
3. Reserva el nombre de la app: «Textos Sagrados» (o el que elijas si está
   tomado). Reservar el nombre es gratis y se hace antes de enviar nada.

---

## Paso 4 · Empaquetar en MSIX

La Store acepta programas en formato MSIX. Dos maneras:

**La fácil — MSIX Packaging Tool** (recomendada para empezar):
1. Instala «MSIX Packaging Tool» desde la propia Microsoft Store (gratis).
2. Elige «Application package» → «Create package on this computer».
3. Cuando pida el instalador, apúntale al `.exe` que construiste.
4. Rellena los datos: nombre, editor (el que te dé tu cuenta), versión,
   y los logos de la carpeta `assets\`.
5. Genera el `.msix`.

**La de línea de comandos** (más control, para cuando ya domines lo anterior):
se escribe un `AppxManifest.xml` y se usa `makeappx.exe` del SDK de Windows.
Cuando llegues aquí, te preparo el manifiesto a medida.

---

## Paso 5 · Firma y envío

- La Store **firma tu paquete por ti** al enviarlo, así que para publicar ahí no
  necesitas comprar un certificado. (Solo harían falta certificados de pago si
  quisieras distribuir el `.exe` por tu cuenta fuera de la tienda.)
- En el panel de desarrollador: «Create new submission», sube el `.msix`,
  añade las fichas de tienda (ya escritas en `docs\fichas-tienda\`, en seis
  idiomas), las capturas, la clasificación de contenido y la política de
  privacidad.
- Para la privacidad puedes enlazar una página sencilla o reutilizar el texto
  de la pestaña «Acerca de»: la app no recopila datos.

La revisión de Microsoft suele tardar de unas horas a un par de días.

---

## Checklist antes de enviar

- [ ] El `.exe` abre y funciona en un Windows onde NO esté instalado Python
- [ ] Icono correcto en la ventana y la barra de tareas
- [ ] Capturas de pantalla hechas (frecuencias, panorama, lado a lado)
- [ ] Ficha de tienda elegida (`docs\fichas-tienda\`)
- [ ] Categoría: «Libros y referencia», no «Estilo de vida»
- [ ] Clasificación: apta para todos; sin datos personales; sin compras
- [ ] Política de privacidad enlazada
- [ ] Nombre reservado en el panel

---

## Nota honesta

No puedo construir ni probar el `.exe` desde donde trabajo —hace falta Windows—,
así que el primer intento puede pedir uno o dos ajustes de «hidden imports».
Es normal en este tipo de empaquetado y se resuelve rápido.

**Sobre Python 3.14:** es una versión muy reciente y algunas herramientas de
empaquetado tardan en adaptarse. La ventana usa Edge (que Windows ya trae), así
que no depende de librerías que aún no soporten 3.14. Si aun así PyInstaller
diera problemas, la vía infalible es instalar Python 3.12 —la versión estable
anterior— y construir con ella; te acompaño si hace falta.
