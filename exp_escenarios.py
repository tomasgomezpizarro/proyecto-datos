"""
Escenarios por TIPO de variable disponible (Trump vs Biden, w2presvtwho 1/2),
con XGBoost. La idea: cuanto podemos predecir segun que clase de datos tengamos.

  S1  Demografia pura
  S2  + Uso de redes / consumo de medios
  S3  + Predisposiciones estables (valores, afecto a grupos: ftcapitalists, etc.)
  S4  Todo pre-eleccion (incluye actitudes politicas fuertes; ojo near-leakage)

Modelo: XGBoost (mismos hiperparametros fijos en todos -> SIN tuning).
En Colab con GPU: agregar device='cuda'. Metrica: holdout repetido x5.
Ademas: feature importance (gain) del escenario S3.
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

import exp_w2presvtwho as E
from exp_modelo_d import VERDES, AMARILLAS

RANDOM_STATE = 42
USE_GPU = False   # poner True en Colab con GPU

XGB_PARAMS = dict(
    n_estimators=500, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=5, reg_lambda=2.0,
    eval_metric="logloss", tree_method="hist", random_state=RANDOM_STATE,
)
if USE_GPU:
    XGB_PARAMS["device"] = "cuda"


def prep(df, cols):
    cols = [c for c in cols if c in df.columns]
    X = df[cols].copy().mask(df[cols].isin(E.MISSING_CODES))
    for c in X.select_dtypes(include="object").columns:
        X[c] = pd.factorize(X[c])[0]
        X[c] = X[c].mask(X[c] == -1)
    return X


def datos():
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    df = df[df["w2presvtwho"].isin([1, 2])].copy()
    y = (df["w2presvtwho"].values == 2).astype(int)   # 1=Biden, 0=Trump
    return df, y


def evaluar(nombre, X, y):
    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = XGBClassifier(**XGB_PARAMS).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p)); f1s.append(f1_score(yte, p, average="macro"))
    a, f = np.array(accs), np.array(f1s)
    print(f"  {nombre:34s} feats={X.shape[1]:3d}  acc={a.mean():.3f}±{a.std():.3f}  f1={f.mean():.3f}")


if __name__ == "__main__":
    df, y = datos()
    Xfull, _ = E.build_X(df)          # todo pre-eleccion (sin w2/w3 ni admin)

    S1 = prep(df, E.DEMO)
    S2 = prep(df, E.DEMO_REDES)
    S3 = prep(df, E.DEMO_REDES + VERDES + AMARILLAS)
    S4 = Xfull

    print("XGBoost — escenarios por tipo de variable (Trump vs Biden, holdout x5)")
    evaluar("S1 Demografia pura", S1, y)
    evaluar("S2 + Uso de redes/medios", S2, y)
    evaluar("S3 + Predisposiciones estables", S3, y)
    evaluar("S4 Todo pre-eleccion (near-leakage)", S4, y)

    # feature importance (gain) del escenario S3
    Xtr, Xte, ytr, yte = train_test_split(S3, y, test_size=0.25,
                                          random_state=RANDOM_STATE, stratify=y)
    m = XGBClassifier(**XGB_PARAMS).fit(Xtr, ytr)
    gain = m.get_booster().get_score(importance_type="gain")
    imp = pd.Series(gain).sort_values(ascending=False)
    print("\nFeature importance (XGBoost gain) — escenario S3:")
    for c in imp.head(18).index:
        print(f"  {c:26s} {imp[c]:7.2f}")
