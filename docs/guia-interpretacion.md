# Guía de interpretación

Esta guía explica qué significa cada cifra de la aplicación y, sobre todo, qué
conclusiones **no** se pueden sacar de ella. Es la parte del manual que no
caducará: los métodos son estándar en lingüística de corpus y no van a cambiar
aunque cambie la interfaz.

Si solo vas a leer un apartado, lee el último.

---

## 1. Frecuencia por 10.000 palabras

**Qué es.** Cuántas veces aparece un término por cada 10.000 palabras del
texto.

**Por qué no se usan conteos brutos.** Los corpus tienen tamaños muy distintos:

| Obra | Palabras |
|---|---|
| Biblia (King James) | 791.689 |
| Tanaj (JPS 1917) | 610.463 |
| Corán (Palmer) | 78.245 |
| Bhagavad Gita (Arnold) | 19.369 |

La Biblia es cuarenta veces más extensa que el Gita. Decir «la Biblia menciona
*amor* 300 veces y el Gita 40» no informa de nada: la Biblia menciona más de
todo, porque es más larga. La tasa normalizada corrige eso y permite comparar.

**Cómo leerla.** «250 por 10.000» significa que 25 de cada 1.000 palabras del
texto pertenecen a ese concepto. Es una densidad, no un total.

**Cuidado.** Una tasa alta en un corpus pequeño es menos fiable que la misma
tasa en uno grande. Para eso está la significación estadística.

---

## 2. Significación estadística (G²)

**Qué es.** El log-likelihood de Dunning, el contraste estándar en lingüística
de corpus desde 1993. Responde a una pregunta concreta: *esta diferencia de
frecuencia, ¿es real o puede deberse al azar?*

**El umbral.** La aplicación marca como distintivo solo lo que supera
**G² > 15,13**, que equivale a p < 0,0001: menos de una posibilidad entre diez
mil de que la diferencia sea casualidad. Es un umbral deliberadamente exigente.

**Cómo leerlo.**

| G² | Lectura |
|---|---|
| menos de 3,8 | Sin evidencia. Puede ser azar. |
| 3,8 – 15,1 | Indicio débil. No lo presentes como hallazgo. |
| más de 15,1 | Diferencia sólida. La app lo marca. |
| más de 100 | Diferencia muy marcada. |

**Cuidado.** G² crece con el tamaño de la muestra. En corpus grandes,
diferencias mínimas salen significativas. Por eso la app muestra también el
**tamaño del efecto**: cuántas veces más frecuente es. Una diferencia puede ser
estadísticamente segura y a la vez irrelevante en la práctica.

Mira siempre las dos cifras juntas: G² dice *si* la diferencia es real, el
tamaño del efecto dice *si importa*.

---

## 3. Dispersión

**Qué es.** En cuántas divisiones —libros, suras, capítulos— aparece el
término, sobre el total.

**Por qué importa.** Cincuenta apariciones concentradas en un solo capítulo no
dicen lo mismo que cincuenta repartidas por toda la obra. Lo primero indica un
pasaje concreto sobre el tema; lo segundo, una preocupación que recorre el
texto entero.

**Cómo leerla.** «presente en 45/66 libros» es un término que caracteriza la
obra. «presente en 2/66» es un término local, por muy alta que sea su tasa.

---

## 4. Campos semánticos

**Qué son.** Grupos de palabras que expresan un mismo concepto. El campo
«misericordia» reúne *mercy*, *merciful*, *compassion*, *clemency*, *kindness*,
*forgive* y otras.

**Por qué existen.** Buscar una palabra suelta produce comparaciones falsas.
Si un traductor prefirió *compassion* y otro *mercy*, contar solo *mercy*
haría parecer que la segunda tradición habla más del tema. El campo semántico
es la unidad de comparación honesta.

**Cuidado.** Los campos los definí yo. Están en `backend/data/lexicon.json` y
puedes editarlos. Un campo mal construido produce cifras mal construidas: si
metes *justicia* dentro del campo *guerra*, los resultados lo reflejarán.
Revisa qué contiene un campo antes de citar sus resultados.

---

## 5. Desglose por forma de palabra

**Qué es.** De todas las apariciones contadas, cuáles corresponden a cada forma
concreta.

**Por qué es útil.** Dos textos pueden empatar en frecuencia total y usar
palabras muy distintas. Si uno se apoya en el sustantivo (*mercy*) y otro en el
adjetivo (*merciful*), la diferencia importa: hablar de la misericordia como
cualidad divina no es lo mismo que hablar de ella como acción exigida.

---

## 6. Comparación entre secciones

**Qué es.** Frecuencias comparadas entre las partes de una misma obra: suras de
La Meca frente a las de Medina, Antiguo frente a Nuevo Testamento, Torá frente
a Profetas y Escritos.

**Por qué es la comparación más sólida de la aplicación.** Dentro de una misma
obra, **el traductor es el mismo**. Las diferencias de vocabulario proceden del
texto original, no de decisiones de traducción. Eso elimina la principal fuente
de ruido de todas las demás comparaciones.

Si vas a citar un solo dato de esta aplicación, que sea de aquí.

---

## 7. Vocabulario distintivo

**Qué es.** Las palabras que aparecen en una obra con frecuencia anormalmente
alta comparada con el resto del corpus.

**Qué no es.** No son las palabras más frecuentes. *Dios* es frecuentísima en
las cuatro tradiciones, y precisamente por eso no distingue a ninguna. Lo
distintivo es lo que una obra usa y las demás no.

---

## 8. Colocaciones

**Qué son.** Palabras que aparecen cerca del término buscado dentro del mismo
versículo.

**Para qué sirven.** Revelan el marco conceptual. Si junto a *guerra* aparece
*justicia* en un texto y *castigo* en otro, la palabra es la misma pero el
contexto la sitúa en universos morales distintos.

---

## 9. Búsqueda por significado

**Qué es.** Cada versículo se convierte en un vector numérico que representa su
contenido. Buscar una idea consiste en encontrar los vectores más cercanos.

**Qué mide el porcentaje.** Proximidad lingüística. **No** equivalencia
doctrinal. Dos pasajes con un 85 % de parecido pueden significar cosas
opuestas dentro de sus tradiciones, porque el modelo compara cómo se dice, no
qué se cree.

Es una herramienta para **descubrir** pasajes que no habrías encontrado
buscando palabras. No es una prueba de nada.

---

## 10. Lo que esta aplicación no puede decirte

Este es el apartado importante.

**No compara religiones, compara traducciones.** Todo el corpus son
traducciones al inglés hechas entre 1611 y 1930 por traductores con sus propias
convenciones. Que la KJV use *charity* donde otra usaría *love* es un dato
sobre la KJV, no sobre el cristianismo.

**No mide importancia.** Que un concepto aparezca poco no significa que
importe poco. Puede ser central y expresarse mediante narraciones en vez de
mediante una palabra concreta. La frecuencia léxica capta una capa del texto,
no su teología.

**No detecta el sentido.** El motor cuenta formas, no significados. «No
matarás» y «matarás» contienen la misma palabra. La negación, la ironía y la
cita de un adversario cuentan igual que la afirmación.

**No corrige el desequilibrio de los corpus.** El Gita tiene 19.369 palabras
frente a las 791.689 de la Biblia. La normalización hace comparables las tasas,
pero un texto corto da estimaciones menos estables: un solo pasaje puede mover
mucho su porcentaje.

**No sustituye el contexto.** Un versículo aislado de su época, su género
literario y su tradición interpretativa puede sostener casi cualquier lectura.
La concordancia te da el pasaje; entenderlo requiere lo demás.

**No es neutral por ser cuantitativa.** La elección de qué contar —qué palabras
forman cada campo semántico— es una decisión interpretativa. Los números que
salen dependen de decisiones que tomó una persona.

---

## Cómo citar un resultado

Mal:

> El Corán habla más de misericordia que la Biblia.

Bien:

> En la traducción de Palmer (1880), el campo semántico de la misericordia
> aparece con una densidad de 250 por 10.000 palabras, frente a 114 en la
> King James (1611). La diferencia es estadísticamente significativa
> (G² = 19,3; p < 0,0001). Ambas cifras se refieren a estas traducciones
> concretas, no a los textos originales.

La segunda versión es más larga y menos rotunda. También es la única
defendible.
