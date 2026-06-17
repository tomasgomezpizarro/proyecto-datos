# Bitácora / Informe — ANES Social Media 2020-2022

> Predicción del voto presidencial 2020 (EE.UU.) a partir de perfil, uso de redes
> y actitudes. Material base para la presentación.
> Repositorio: https://github.com/tomasgomezpizarro/proyecto-datos

---

## 1. Resumen del proyecto

- **Objetivo:** predecir el **voto presidencial 2020 (Trump vs Biden)** a partir de
  las variables de la encuesta, y estudiar **qué tipo de información** lo determina.
- **Datos:** encuesta ANES Special Study 2020-2022 — **5.750 encuestados × 914 variables**
  (3 olas: pre-elección, post-elección y seguimiento 2021-22).
- **Label:** `w2presvtwho` ("¿A quién votó?"): Trump (1.801) · Biden (2.561) · Otro (171).

---

## 2. Identificación de la label (un hallazgo en sí mismo)

El primer candidato a label fue `vote20cand`, pero resultó ser la **primaria demócrata**
(Biden vs Sanders vs Warren…), no la general. Lo detectamos porque un modelo binario
"Biden vs Trump" daba apenas 86% y porque **los códigos no cerraban**: decodificando
con los termómetros de sentimiento (`ftjb`, `fttrump`) vimos que *todos* los grupos
eran pro-Biden. El codebook lo confirmó. Los votantes de Trump estaban en el código
"no aplica" que descartábamos.

La variable correcta de la **elección general** es `w2presvtwho`, verificada con
termómetros: código Trump → frío con Biden / cálido con Trump, y viceversa.

> **Lección:** desconfiar de un número que "hace ruido" y verificar el significado
> de las variables contra el codebook en vez de asumirlo por el nombre.

---

## 3. Metodología

### 3.1 Limpieza
- **Faltantes:** ANES codifica "no respondió / no aplica" con negativos (`-1`…`-9`)
  → convertidos a `NaN`.
- **Encoding:** las respuestas son códigos ordinales, no magnitudes → modelos de
  árboles los toleran; los lineales se usan como baseline.

### 3.2 Taxonomía de *leakage* (el corazón metodológico)
Con 914 variables, el problema central es separar predictores legítimos de **fugas**.
Lo decidimos por la pregunta *"¿es causa o consecuencia del voto?"*:

| Tipo | Ejemplos | Decisión |
|---|---|---|
| **Leakage directo** | a quién votó, voto a diputados/senadores | excluir |
| **Consecuencia del voto** | aprobación presidencial post, emociones del resultado | excluir |
| **Percepción partidaria** (causalidad inversa) | estado de la economía, confianza en instituciones/medios | excluir |
| **Proxy de preferencia** | "qué partido es mejor en X", intención de voto, termómetros a partidos/candidatos | excluir |
| **Leakage temporal** | toda variable de ola 2/3 (medida igual o después del voto) | excluir por defecto |
| **Predisposición estable** | valores, afecto a grupos sociales, ideología | **usar** |
| **Apolítico** | demografía, salud factual, uso de redes | **usar** |

> **Matiz clave:** "medido después de la elección" **no** es lo mismo que *leakage*.
> Una actitud estable (visión sobre capitalistas/gays, resentimiento racial) es
> **anterior y causal**, aunque se haya preguntado en la ola post-electoral.

### 3.3 Validación
- Métricas: **accuracy + `f1_macro`** (por el desbalance) + matriz de confusión.
- Estimación con **cross-validation / holdout repetido** (media ± desvío): nunca leer
  el tercer decimal de un único split (su error de muestreo es ≈ ±1,3%).
- Modelos comparados: Regresión Logística, LDA (Fisher), Random Forest, **XGBoost**
  (sustituido localmente por HistGradientBoosting, equivalente).

---

## 4. Resultados

### 4.1 Modelo principal — Trump vs Biden
Con el set pre-elección completo: **~0,97 de accuracy** (RF 0,970 · LDA/HGB 0,965 ·
LogReg 0,952). Clases balanceadas (41/59), errores parejos → modelo sano.

### 4.2 ¿Qué información determina el voto? (escalera por "explicitud política")
Validado por la correlación de cada bloque con el voto (XGBoost, holdout ×5):

| Información disponible | accuracy | aporte |
|---|---|---|
| Demografía + salud factual + redes (**apolítico real**) | 0,750 | piso |
| + conducta polarizada (pandemia, empatía) | 0,801 | +0,05 |
| + afecto identitario (LGBT, musulmanes…) | 0,851 | +0,05 |
| + posiciones de issues (aborto, clima, armas…) | 0,926 | **+0,075** |
| + ideología explícita (`lcself`, resentimiento…) | 0,933 | +0,01 |
| + actitudes a candidatos (near-leakage) | 0,971 | +0,04 |

**Conclusiones:**
- La **demografía sola predice poco** (0,72-0,75): saber edad, raza, educación y qué
  redes usás deja mucho sin explicar.
- **Casi nada es apolítico** en un clima polarizado: hasta el comportamiento en la
  pandemia o la empatía filtran señal política.
- El **salto grande** lo dan las **posiciones concretas de issues** (clima, aborto,
  armas), no la demografía.
- La **ideología auto-declarada es redundante** una vez que se conocen los issues
  (+1 punto): "soy conservador" es casi información duplicada de qué opina la persona.

### 4.3 Partidismo (`pid7x`) y robustez del label
Predecir **identidad partidaria** desde demografía da el **mismo techo (~0,72)** que el
voto. No es casualidad: voto y partidismo coinciden en el **94%** de las personas
(Spearman 0,78) → son casi la misma variable. El techo es una propiedad de la
**señal demográfica**, no del label elegido.

### 4.4 Importancia de features
- **MDI vs permutación:** el MDI inflaba `fttrump` (alta cardinalidad); la permutación
  lo degrada porque su información está **duplicada** en otros termómetros. La
  permutación es más honesta sobre la redundancia.
- **Desde la demografía**, los predictores top son **raza/etnia, religiosidad
  (evangélico) y educación** — la espina dorsal sociológica del voto en EE.UU.
- Las actitudes correlacionan fortísimo con el voto (|r| hasta 0,87) pero **débilmente
  con la demografía** (|r| ≤ 0,24): el eje político no es un reflejo de la demografía.

### 4.5 Multiclase y desbalance
- **Primaria demócrata (7 candidatos):** accuracy 0,70 pero `f1_macro` 0,23 — el modelo
  solo aprende **Biden y, a medias, Sanders**; los candidatos chicos (n<100) son
  inmodelables. La primaria *fue*, en los hechos, Biden vs Sanders.
- **General con "Otro":** 0,935 de accuracy pero la clase "Otro" (171) es impredecible
  (terceros partidos ≈ 1,8% del electorado). Justifica modelar el problema como
  **binario**.

> **Lección:** con clases minoritarias el accuracy engaña; el `f1_macro` y la matriz
> lo exponen. El techo es la **cantidad de casos**, no el método (ningún modelo ni
> hiperparámetro rescata una clase de 52 ejemplos solapada con la mayoría).

### 4.6 Ajuste de hiperparámetros
Búsqueda con **validation set** (split 60/20/20, reporte en test intacto): el tuning
mueve **1-2 milésimas** tanto en el techo alto (0,964→0,966) como en el bajo
(0,726→0,729). Confirma que el límite es la **señal**, no los hiperparámetros. El mejor
modelo resultó **shallow** (`depth=2`): con poca señal, simple gana.

---

## 5. Conclusiones para la presentación

1. **El voto se explica por las actitudes políticas, no por la demografía.** La
   demografía deja ~0,72; las posiciones sobre issues lo llevan a >0,93.
2. **La ideología vive en las posiciones concretas:** conocido el aborto/clima/armas,
   el rótulo izquierda-derecha no agrega nada.
3. **Disciplina metodológica:** distinguir leakage de predisposición; mirar `f1_macro`
   en desbalance; reportar con barras de error; no sobre-leer un split.
4. **El cuello de botella es la señal/los datos**, no el modelo ni los hiperparámetros.
