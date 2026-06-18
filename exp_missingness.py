"""
¿El patrón de NO-RESPUESTA aporta señal? (missingness as information)

Convertir los códigos negativos a NaN asume implícitamente que "no respondió"
no dice nada. Para testearlo, comparamos:
  - base: X con NaN (lo que hacemos hoy; XGBoost aprende una dirección default).
  - +indicadores: X + una columna binaria "_na" por variable con faltantes,
    que le da al modelo la señal EXPLÍCITA de "esta persona no respondió esto".

Si los indicadores mejoran el accuracy, el missingness es informativo (MNAR).
XGBoost, holdout x5. Escenarios: apolítico (75) y 3c legítimo (110).
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

import exp_escenarios as S
import exp_escenarios4 as S4


def aug(X):
    ind = X.isna().astype(int)
    ind = ind.loc[:, ind.sum() > 0]          # solo columnas con algún NaN
    ind.columns = [c + "_na" for c in ind.columns]
    return pd.concat([X, ind], axis=1)


def ev(X, y):
    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p)); f1s.append(f1_score(yte, p, average="macro"))
    return np.mean(accs), np.std(accs), np.mean(f1s)


def main():
    df, y = S.datos()
    escenarios = [
        ("Apolítico (75)", S4.BASE_APOL),
        ("3c legítimo (110)", S4.BASE_APOL + S4.CONDUCTA + S4.N3a + S4.N3b + S4.N3c),
    ]
    print("¿El missingness aporta señal? (XGBoost, holdout x5)\n")
    for nom, cols in escenarios:
        X = S.prep(df, cols)
        Xa = aug(X)
        n_ind = Xa.shape[1] - X.shape[1]
        a, s, f = ev(X, y)
        a2, s2, f2 = ev(Xa, y)
        print(f"== {nom} ==")
        print(f"  solo NaN           {X.shape[1]:3d} feats  acc={a:.3f}±{s:.3f}  f1={f:.3f}")
        print(f"  NaN + {n_ind} indicad. {Xa.shape[1]:3d} feats  acc={a2:.3f}±{s2:.3f}  f1={f2:.3f}")
        print(f"  Δ accuracy = {a2 - a:+.3f}\n")


if __name__ == "__main__":
    main()
