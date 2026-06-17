"""
Permutation importance (mas honesta que feature_importances_/MDI) sobre el TEST,
para los dos modelos de w2presvtwho (Trump vs Biden):

  Modelo B) full pre-eleccion (342 features)
  Modelo C) solo demografia + uso de redes (41 features)

Permutation importance: permuta cada columna y mide cuanto CAE la metrica en test.
No se infla por cardinalidad (a diferencia del MDI). Mismo algoritmo (RF) en ambos.
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score

import exp_w2presvtwho as E

RANDOM_STATE = 42
TOPN = 15


def run(whitelist, titulo):
    df = E.cargar()
    sub = df[df[E.TARGET].isin([1, 2])].copy()
    X, _ = E.build_X(sub)
    if whitelist is not None:
        X = X[[c for c in whitelist if c in X.columns]].copy()
    y = (sub[E.TARGET].values == 2).astype(int)   # 1=Biden, 0=Trump

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)

    imp = SimpleImputer(strategy="most_frequent")
    Xtr_i = pd.DataFrame(imp.fit_transform(Xtr), columns=X.columns, index=Xtr.index)
    Xte_i = pd.DataFrame(imp.transform(Xte),  columns=X.columns, index=Xte.index)

    rf = RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=RANDOM_STATE)
    rf.fit(Xtr_i, ytr)
    pred = rf.predict(Xte_i)

    print("\n" + "=" * 66)
    print(titulo + f"  ({X.shape[1]} features)")
    print("=" * 66)
    print(f"RF en test: acc={accuracy_score(yte, pred):.3f}  "
          f"f1_macro={f1_score(yte, pred, average='macro'):.3f}")

    perm = permutation_importance(rf, Xte_i, yte, n_repeats=15,
                                  random_state=RANDOM_STATE,
                                  scoring="f1_macro", n_jobs=-1)
    mdi = pd.Series(rf.feature_importances_, index=X.columns)
    pi = pd.DataFrame({
        "perm_mean": perm.importances_mean,
        "perm_std":  perm.importances_std,
        "mdi":       mdi.values,
    }, index=X.columns).sort_values("perm_mean", ascending=False)

    print(f"\nTop {TOPN} por PERMUTATION importance (caida de f1_macro al permutar):")
    top = pi.head(TOPN).copy()
    top["perm"] = top.apply(lambda r: f"{r['perm_mean']:.4f} ± {r['perm_std']:.4f}", axis=1)
    print(top[["perm", "mdi"]].to_string(float_format=lambda v: f"{v:.4f}"))
    return pi


if __name__ == "__main__":
    run(None, "MODELO B — full pre-eleccion")
    run(E.DEMO_REDES, "MODELO C — solo demografia + uso de redes")
