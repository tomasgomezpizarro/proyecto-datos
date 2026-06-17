"""
Ajuste de hiperparametros de XGBoost con VALIDATION SET (Trump vs Biden).

Split 60/20/20 (train/val/test):
  - se buscan combinaciones de hiperparametros al azar,
  - cada candidato se entrena en TRAIN con early stopping sobre VAL,
  - se elige el mejor por accuracy en VAL,
  - el numero final se reporta en TEST (intacto, nunca tocado en la busqueda).

Tesis a verificar: como el limite es la SENAL (techo de datos), el tuning mueve
decimas, no puntos. Se compara default vs tuneado, en dos sets de features.
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

import exp_w2presvtwho as E

RANDOM_STATE = 42
rng = np.random.RandomState(RANDOM_STATE)

DEFAULT = dict(n_estimators=500, max_depth=4, learning_rate=0.05,
               subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
               reg_lambda=2.0, eval_metric="logloss", tree_method="hist",
               random_state=RANDOM_STATE)

ESPACIO = dict(
    max_depth=[2, 3, 4, 6, 8],
    learning_rate=[0.01, 0.03, 0.05, 0.1],
    min_child_weight=[1, 3, 5, 10],
    subsample=[0.6, 0.8, 1.0],
    colsample_bytree=[0.6, 0.8, 1.0],
    reg_lambda=[0.0, 1.0, 2.0, 5.0],
    reg_alpha=[0.0, 0.5, 1.0],
)
N_ITER = 40


def muestra():
    p = {k: rng.choice(v) for k, v in ESPACIO.items()}
    p.update(eval_metric="logloss", tree_method="hist", random_state=RANDOM_STATE,
             n_estimators=2000)            # alto: early stopping define el real
    return p


def tunear(nombre, X, y):
    # 60/20/20 estratificado
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(
        X, y, test_size=0.40, random_state=RANDOM_STATE, stratify=y)
    X_val, X_te, y_val, y_te = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_tmp)

    # baseline: config fija (default), entrenada en train
    base = XGBClassifier(**DEFAULT).fit(X_tr, y_tr)
    acc_def = accuracy_score(y_te, base.predict(X_te))

    # busqueda aleatoria, seleccion por accuracy en VAL (con early stopping en val)
    mejor, mejor_val, mejor_p = None, -1, None
    for _ in range(N_ITER):
        p = muestra()
        m = XGBClassifier(early_stopping_rounds=50, **p)
        m.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        v = accuracy_score(y_val, m.predict(X_val))
        if v > mejor_val:
            mejor, mejor_val, mejor_p = m, v, p
    acc_tun = accuracy_score(y_te, mejor.predict(X_te))
    f1_tun = f1_score(y_te, mejor.predict(X_te), average="macro")

    print(f"\n### {nombre}  (train={len(X_tr)} val={len(X_val)} test={len(X_te)})")
    print(f"  default      -> test acc = {acc_def:.3f}")
    print(f"  tuneado(val) -> test acc = {acc_tun:.3f}  f1={f1_tun:.3f}  "
          f"(val acc {mejor_val:.3f})")
    print(f"  delta tuning = {acc_tun - acc_def:+.3f}")
    print(f"  mejores params: depth={mejor_p['max_depth']} lr={mejor_p['learning_rate']} "
          f"mcw={mejor_p['min_child_weight']} sub={mejor_p['subsample']} "
          f"col={mejor_p['colsample_bytree']} lambda={mejor_p['reg_lambda']} "
          f"alpha={mejor_p['reg_alpha']} n_est={mejor.best_iteration + 1}")


if __name__ == "__main__":
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    df = df[df["w2presvtwho"].isin([1, 2])].copy()
    y = (df["w2presvtwho"].values == 2).astype(int)
    Xfull, _ = E.build_X(df)
    Xdemo = Xfull[[c for c in E.DEMO_REDES if c in Xfull.columns]]

    print(f"Busqueda aleatoria: {N_ITER} candidatos, seleccion por VAL, reporte en TEST")
    tunear("FULL pre-eleccion (techo alto ~0.97)", Xfull, y)
    tunear("Demografia+redes (techo bajo ~0.72)", Xdemo, y)
