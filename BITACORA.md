# Bitácora del Proyecto — ANES Social Media 2020-2022

> Registro cronológico del trabajo para usar en la presentación.
> Dataset: ANES Special Study 2020-2022 (uso de redes sociales y política, EE.UU.)

---

## Resumen del proyecto

- **Objetivo:** _(a definir — ej. predecir voto / identidad partidaria a partir de perfil y uso de redes)_
- **Datos:** encuesta ANES — **5.750 encuestados** × **914 variables**
- **Repositorio:** https://github.com/tomasgomezpizarro/proyecto-datos
- **Label (variable objetivo):** _(pendiente de elegir — candidatas: `vote20cand`, `pid7x`, participación)_

---

## Timeline

### 2026-06-14 — Día 1: Setup y exploración inicial

| Paso | Qué hicimos | Resultado |
|---|---|---|
| 1 | Exploramos la estructura del dataset | 5.750 filas (encuestados) × 914 columnas (preguntas/perfil) |
| 2 | Identificamos los grupos de variables | Identificación, pesos muestrales, perfil/demografía (`profile_*`), comportamiento político (`vote*`, `pid*`, `ft*`) |
| 3 | Analizamos posibles labels | No hay label predefinida (es una encuesta); candidatas: `vote20cand`, `pid7x`, participación |
| 4 | Definimos estrategia de algoritmos | Baseline (Reg. Logística) → Random Forest → Gradient Boosting (LightGBM/XGBoost) |

**Hallazgos clave / decisiones a tener en cuenta:**
- ⚠️ **Fuga de información (leakage):** con 914 columnas, varias replican la label → hay que filtrarlas a mano.
- ⚠️ **Códigos de faltantes:** `-1`, `-7`, `-9` significan "no respondió / no aplica", no son valores numéricos → convertir a `NaN`.
- ⚠️ **Variables categóricas:** la mayoría son códigos (no magnitudes) → tratar con encoding adecuado.
- El significado de cada código está en el **codebook PDF** del repo.

---

## Próximos pasos

- [ ] Elegir la **label** definitiva.
- [ ] Script de carga + limpieza (faltantes, leakage, categóricas).
- [ ] Entrenar y comparar modelos (Reg. Logística vs Random Forest vs LightGBM).
- [ ] Evaluar (accuracy / F1 / matriz de confusión).
- [ ] Conclusiones para la presentación.
