# Problemas frecuentes

## El antivirus bloquea un archivo durante la instalación

**Síntoma.** Norton (o Windows Defender, o Avast) avisa de una amenaza tipo
`EvoGen`, `Heur`, `Wacatac` o similar en un archivo llamado `output.exe`,
`conftest.exe` o parecido, con una ruta como:

```
C:\Users\TU_USUARIO\AppData\Local\Temp\pip-install-XXXX\numpy_XXXX\
   .mesonpy-XXXX\meson-private\tmpXXXX\output.exe
```

**Qué está pasando en realidad.** Es un falso positivo, y la ruta lo demuestra.
Cuando pip no encuentra una versión ya compilada de un paquete para tu versión
de Python, lo compila desde el código fuente. Para compilar numpy se usa Meson,
que antes de nada verifica que el compilador funciona: crea un programa
diminuto, lo compila con el nombre `output.exe` y lo ejecuta.

El antivirus ve aparecer de la nada un ejecutable sin firmar en una carpeta
temporal y lo bloquea por precaución. El comportamiento es legítimo por parte
del antivirus, pero el archivo es inofensivo.

**Cómo saber si es tu caso.** Mira la ruta en la pestaña *Actividad* del aviso.
Si contiene `Temp` y `pip-install`, es esto. Si está en Descargas o en
cualquier otro sitio, **no es esto** y conviene investigarlo en serio.

**Solución.** No hace falta desactivar el antivirus ni añadir excepciones. El
instalador actualizado usa `--only-binary=:all:`, que obliga a pip a descargar
solo paquetes ya compilados y no compila nada. Vuelve a ejecutar el instalador.

**Si aun así vuelve a ocurrir.** Significa que no existe versión precompilada
para tu Python, casi siempre porque tienes una versión recién salida que los
paquetes todavía no soportan. Instala la versión estable anterior de Python
(por ejemplo 3.12 si tienes 3.14) y vuelve a ejecutar el instalador.

> Regla general: **nunca añadas una excepción en el antivirus sin saber qué
> archivo es y de dónde salió.** La ruta del archivo casi siempre lo dice.

---

## Quiero analizar textos en español

El corpus que instala el instalador está **todo en inglés**, a propósito:
comparar frecuencias entre textos en idiomas distintos no es lingüísticamente
válido, porque cada idioma tiene su propia morfología y su propio vocabulario.
Para que la comparación signifique algo, las cuatro obras deben compartir
idioma.

Para añadir la Reina-Valera 1909 (español, dominio público):

```bash
cd backend
.venv\Scripts\activate          # en Windows
python scripts/fetch_corpus.py --source rv1909
```

Después reinicia el servidor. En la interfaz aparecerá «Textos en español (1)»
en el selector.

Ten en cuenta que con una sola obra en español no hay comparación posible
entre tradiciones: solo podrás explorar frecuencias dentro de la Biblia. Para
una comparación completa en español harían falta traducciones al español de
las cuatro obras, y no todas existen en dominio público con calidad
suficiente.

---

## Un botón dice «Not found» o «No se pudo cargar»

El servidor está ejecutando código antiguo. Cuando copias archivos nuevos, el
servidor que ya está encendido no se entera: mantiene en memoria la versión con
la que arrancó, y las funciones nuevas no existen para él.

**Solución:** cierra la ventana negra del servidor, vuelve a abrir
`INICIAR-Windows.bat` y recarga la página con F5.

Desde la versión 1.2.0 la interfaz lo detecta sola: compara su lista de
funciones necesarias con las que declara el servidor en `/health` y muestra un
aviso naranja explicando qué hacer, en lugar de dejar que aparezca un 404 sin
contexto.

*Nota para desarrollo:* si arrancas con `uvicorn --reload`, el servidor se
reinicia solo al detectar cambios y esto no ocurre. El `.bat` no usa `--reload`
a propósito, porque consume más memoria y vigila archivos constantemente.

---

## Se abre una ventana negra y se cierra al instante

Resuelto en la versión actual. Los archivos `.bat` se habían generado con
finales de línea de Unix; Windows los interpreta de forma errática y cierra la
ventana sin mostrar nada. Ya están convertidos, y además todos los scripts
terminan en `pause`, así que la ventana no se cierra sola pase lo que pase.

Si vuelve a ocurrir con cualquier `.bat`, la forma infalible de ver el error:
abre la carpeta, haz clic en la barra de direcciones, escribe `cmd`, pulsa
Intro, y desde esa ventana negra escribe el nombre del archivo. Está explicado
paso a paso en `COMO-EJECUTAR.txt`.

---

## «No he encontrado Python 3.10 o superior»

Ocurre casi siempre por no haber marcado **«Add Python to PATH»** al instalar
Python. Vuelve a lanzar el instalador de Python, elige *Modify* o reinstala
marcando esa casilla, y cierra y vuelve a abrir la ventana antes de reintentar.

---

## `tanaj-jps: FALLO -> HTTP Error 403: Forbidden`

Resuelto en la versión actual. Sefaria rechaza las peticiones de clientes que
no se identifican como navegador, y el script se identificaba con un nombre
propio. Ya envía una cabecera de navegador.

De paso se corrigió algo más serio: el punto de acceso antiguo devolvía por
defecto la edición JPS de 2023, que es **CC-BY-NC y no se puede
redistribuir**. Ahora se usa la API v3, se pide explícitamente la edición
JPS 1917 y **se comprueba la licencia de cada libro descargado**. Si Sefaria
devolviera una edición con copyright, la ingesta se detiene con un error en
lugar de continuar.

---

## Alguna otra fuente aparece como FALLO en la comprobación

Los textos se descargan de servicios públicos y gratuitos que a veces cambian
de dirección o están caídos temporalmente. El instalador omite los que fallen y
sigue con el resto.

Vuelve a ejecutarlo más tarde: recuerda lo ya descargado y solo reintenta lo
que falta. Si una fuente falla de forma persistente, hay que actualizar su
adaptador en `backend/scripts/fetch_corpus.py`.

---

## La app dice que no puede conectar con el servidor

1. Comprueba que la ventana del servidor sigue abierta
2. Abre <http://localhost:8000/health> en el navegador: debe devolver texto
3. Si usas la app en el móvil y el servidor en el ordenador, `localhost` no
   sirve: hay que poner la IP local del ordenador (algo como
   `http://192.168.1.40:8000`) en Ajustes, y ambos deben estar en la misma red

---

## «Error 500» al usar la búsqueda por significado

Corregido en la versión actual. Era un fallo de programación: la base de datos
guarda el identificador del índice (`static:potion-multilingual-128M`), pero el
código intentaba usarlo directamente como nombre de un modelo de HuggingFace,
que obviamente no existía con ese nombre.

Si aún lo ves, actualiza los archivos y reinicia el servidor. No hay que
reconstruir el índice: los vectores calculados siguen siendo válidos.

Desde esta versión, cualquier fallo de la búsqueda por significado muestra un
diagnóstico con qué índices hay, cuántos vectores tienen y qué falta, en lugar
de un número de error. También hay un endpoint `/semantic-status` que lo
resume.

---

## La búsqueda por significado dice que no está instalada

Es opcional y va aparte porque descarga entre 2 y 3 GB: el motor de cálculo
(PyTorch) y el modelo de lenguaje. En Windows, doble clic en
`INSTALAR-BUSQUEDA-Windows.bat`. A mano:

```bash
cd backend
pip install --only-binary=:all: -r requirements-semantic.txt
python scripts/build_embeddings.py
```

Luego reinicia el servidor.

**Si la instalación falla por la versión de Python.** PyTorch tarda meses en
dar soporte a cada versión nueva de Python. Si tienes una muy reciente puede
que aún no haya paquete precompilado. El instalador lo detecta y te lo dice en
lugar de intentar compilarlo, que tardaría horas y fallaría igual. La solución
es instalar la versión estable anterior de Python.

**Si el cálculo se interrumpe.** No pasa nada: guarda por lotes. Vuelve a
ejecutar el instalador y continuará donde lo dejó.

**Cuánto ocupa.** Unos 3 GB de programas más unos 90 MB de vectores dentro de
la base de datos, para los ~61.000 versículos del corpus.
