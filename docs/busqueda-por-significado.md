# Búsqueda por significado: qué motor empaquetar

La búsqueda por significado convierte cada versículo en un vector numérico.
Buscar una idea consiste en encontrar los vectores más cercanos, lo que permite
hallar pasajes afines aunque no compartan ni una palabra con la consulta.

El problema no es el algoritmo, sino **cuánto ocupa la maquinaria**.

## El malentendido que conviene deshacer

Los datos son pequeños. Los 61.000 versículos ocupan:

| Dimensiones | float32 | int8 |
|---|---|---|
| 384 | 94 MB | 23 MB |
| 256 | 62 MB | 16 MB |
| 128 | 31 MB | 8 MB |

Lo que pesa es el modelo que **fabrica** vectores. Pero el usuario final no
fabrica nada: solo necesita convertir su frase de búsqueda. Le estábamos
pidiendo instalar una fábrica entera para producir un tornillo.

## Los cuatro motores disponibles

| Preajuste | Descarga | Cómo funciona | Para qué sirve |
|---|---|---|---|
| `calidad` | ~3 GB | Red neuronal sobre PyTorch | Referencia y servidor |
| `ligero` | ~530 MB | Tabla de vectores (model2vec) | Escritorio |
| `ligero-256` | ~265 MB | Igual, mitad de dimensiones | Intermedio |
| `minimo` | ~130 MB | 128 dimensiones + int8 | **App publicada** |

Los tres ligeros usan `potion-multilingual-128M`, licencia MIT, entrenado en
101 idiomas —incluidos los seis de la interfaz—. Es imprescindible que sea
multilingüe: el corpus está en inglés y las consultas pueden venir en español,
árabe o hindi.

**Cómo funciona un modelo estático.** En vez de ejecutar una red neuronal por
cada consulta, guarda un vector fijo por palabra y promedia los de la frase.
Se pierde el contexto —una palabra vale lo mismo en cualquier frase— pero es
cientos de veces más rápido y no necesita PyTorch. Para descubrir pasajes
afines suele bastar.

## No decidas por intuición: mide

```bash
python scripts/build_embeddings.py --engine calidad
python scripts/build_embeddings.py --engine minimo
python scripts/comparar_motores.py --base calidad --contra minimo
```

Ambos índices conviven en la base de datos y se comparan sobre 15 consultas
reales, en español e inglés. Se miden tres cosas:

- **Solapamiento@10.** De los 10 mejores resultados del motor bueno, cuántos
  salen también en el ligero. Es lo que percibe el usuario.
- **Coincidencia del primero.** Si el resultado más relevante es el mismo.
  Pesa más que el resto: es el que la gente lee.
- **Correlación de orden.** Si además los ordena igual.

Como referencia orientativa: por encima del 70 % de solapamiento el cambio
apenas se nota; por debajo del 50 % los resultados difieren demasiado y
conviene el motor pesado en un servidor.

## Por qué no un servidor propio

Se valoró y se descartó, aunque sigue siendo una opción válida:

**A favor:** descarga cero para el usuario, calidad máxima, modelo actualizable
sin republicar la app.

**En contra:** entre 12 y 25 dólares al mes indefinidamente; si el servidor
cae, la función desaparece para todos; no funciona sin conexión; y las
búsquedas de los usuarios pasan por tu máquina, lo que obliga a declararlo en
la política de privacidad. En una app sobre religión, que la gente sepa que sus
búsquedas viajan a un servidor ajeno no es un detalle menor.

La opción local evita las cuatro cosas a cambio de unos 130 MB dentro de la
app, que es un tamaño normal para una aplicación móvil.
