"""
Importancia + correlacion sobre w2presvtwho (binario Trump vs Biden).

Idea: la importancia ELIGE las variables que mas pesan; la correlacion
explica COMO se relacionan (signo/fuerza) con el voto y con demografia/redes.

  Paso 1) Top features por importancia (modelo full, 342 features pre-eleccion).
  Paso 2) Correlacion (Spearman) de esas top con el VOTO (y: 1=Biden, 0=Trump).
  Paso 3) Correlacion de esas top (actitudes) con DEMOGRAFIA + REDES.

Spearman: las respuestas son codigos ordinales, no continuos -> rango, no Pearson.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
import warnings, re
warnings.filterwarnings("ignore")

import exp_w2presvtwho as E   # reusa carga / build_X / listas

RANDOM_STATE = 42
pd.set_option("display.width", 140, "display.max_columns", 30)


def main():
    df = E.cargar()
    sub = df[df[E.TARGET].isin([1, 2])].copy()        # binario Trump/Biden
    X, fcols = E.build_X(sub)
    y = (sub[E.TARGET].values == 2).astype(int)        # 1=Biden, 0=Trump

    # ---- Paso 1: importancia (RF sobre las 342, imputando para entrenar) ----
    imp = SimpleImputer(strategy="most_frequent")
    Xi = pd.DataFrame(imp.fit_transform(X), columns=X.columns, index=X.index)
    rf = RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=RANDOM_STATE)
    rf.fit(Xi, y)
    importancia = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
    TOPN = 15
    top = importancia.head(TOPN)
    print("=" * 70)
    print(f"PASO 1 — Top {TOPN} features por importancia (RF, modelo full)")
    print("=" * 70)
    print(top.to_string())

    # ---- Paso 2: correlacion de las top con el VOTO ----
    # Spearman de cada top con y (usa los datos crudos con NaN; corr ignora NaN par a par)
    dfc = X.copy()
    dfc["__voto_biden"] = y
    corr_voto = dfc[list(top.index) + ["__voto_biden"]].corr(method="spearman")["__voto_biden"]
    corr_voto = corr_voto.drop("__voto_biden").sort_values()
    print("\n" + "=" * 70)
    print("PASO 2 — Correlacion (Spearman) de las top con el voto (+=hacia Biden)")
    print("=" * 70)
    print(corr_voto.to_string())

    # ---- Paso 3: correlacion top (actitudes) vs DEMOGRAFIA + REDES ----
    demo_redes = [c for c in E.DEMO_REDES if c in X.columns]
    # matriz cruzada: filas = top, columnas = demo/redes
    juntas = X[list(top.index) + demo_redes]
    M = juntas.corr(method="spearman").loc[top.index, demo_redes]
    print("\n" + "=" * 70)
    print("PASO 3 — Corr (Spearman) top-features  vs  demografia+redes")
    print("=" * 70)
    # mostramos solo las relaciones notables (|r| >= 0.15) para que se lea
    print("\nPares notables (|r| >= 0.15), ordenados por |r|:")
    pares = (M.stack().rename("r").reset_index()
             .rename(columns={"level_0": "feature_top", "level_1": "demo_red"}))
    pares["abs"] = pares["r"].abs()
    pares = pares[pares["abs"] >= 0.15].sort_values("abs", ascending=False)
    if len(pares):
        print(pares[["feature_top", "demo_red", "r"]].to_string(index=False,
              float_format=lambda v: f"{v:+.2f}"))
    else:
        print("  (ninguno supera 0.15)")

    # resumen: cuanto se 'explica' cada top desde demo/redes (max |r|)
    print("\nMaxima |correlacion| de cada top con alguna demo/red:")
    maxabs = M.abs().max(axis=1).sort_values(ascending=False)
    print(maxabs.to_string(float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
