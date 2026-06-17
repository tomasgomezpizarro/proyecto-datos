"""
Dos modelos MULTICLASE de "a quien voto":

  M1) vote20cand  -> primaria democrata, 7 candidatos con nombre
        (Biden/Bloomberg/Buttigieg/Klobuchar/Sanders/Warren/Otro)
  M2) w2presvtwho -> general 2020, 3 clases CON "Otro" (Trump/Biden/Otro)

Features: set pre-eleccion completo (build_X ya saca w2*/w3* y admin), menos el
leakage ESPECIFICO de cada target (en la primaria, preferencia de candidato dem;
en la general, la intencion de voto). Desbalance fuerte -> miramos f1_macro y
matriz de confusion, no solo accuracy. 10-fold CV.
"""
import numpy as np
import pandas as pd
import warnings, re
warnings.filterwarnings("ignore")
from sklearn.model_selection import cross_validate, StratifiedKFold, train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

import exp_w2presvtwho as E

RANDOM_STATE = 42

NOM_PRIM = {1: "Biden", 2: "Bloomberg", 3: "Buttigieg", 4: "Klobuchar",
            5: "Sanders", 6: "Warren", 7: "Otro"}
NOM_GEN = {1: "Trump", 2: "Biden", 3: "Otro"}

# leakage especifico de cada target (ademas de lo que ya saca build_X)
LEAK_PRIM = ["vote20", "ran_vote2cand", "voterep", "primparty", "dempref",
             "primary", "percent20"]          # todo lo que dicta la primaria
LEAK_GEN = ["vote20d1", "vote20_match"]        # intencion de voto general


def construir(df, target, leak_prefixes):
    X, fcols = E.build_X(df)               # pre-eleccion, sin w2*/w3* ni admin
    drop = {c for c in X.columns
            if c == target or any(c.startswith(p) for p in leak_prefixes)}
    X = X.drop(columns=[c for c in drop if c in X.columns])
    return X


def correr(target, clases, nombres, leak, titulo):
    print("\n" + "=" * 66)
    print(titulo)
    print("=" * 66)
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    df = df[df[target].isin(clases)].copy()
    X = construir(df, target, leak)
    y = df[target].astype(int).values

    dist = {nombres[c]: int((y == c).sum()) for c in clases}
    print(f"Filas: {len(df)} | Features: {X.shape[1]} | Clases: {len(clases)}")
    print("Distribucion:", dist)

    # holdout repetido (robusto a clases minusculas, donde StratifiedKFold rompe
    # el binning interno de HistGradientBoosting). 5 particiones 75/25.
    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = HistGradientBoostingClassifier(random_state=RANDOM_STATE).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p))
        f1s.append(f1_score(yte, p, average="macro"))
    a, f = np.array(accs), np.array(f1s)
    maj = max(dist.values()) / len(df)
    print(f"\nHistGradientBoosting (holdout repetido x5):")
    print(f"  accuracy = {a.mean():.3f} ± {a.std():.3f}   (baseline mayoritaria {maj:.3f})")
    print(f"  f1_macro = {f.mean():.3f} ± {f.std():.3f}")

    # matriz de confusion en un split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                          random_state=RANDOM_STATE, stratify=y)
    m = HistGradientBoostingClassifier(random_state=RANDOM_STATE).fit(Xtr, ytr)
    pred = m.predict(Xte)
    idx = sorted(np.unique(yte))
    cm = confusion_matrix(yte, pred, labels=idx)
    cmdf = pd.DataFrame(cm, index=[f"real:{nombres[i]}" for i in idx],
                        columns=[f"pr:{nombres[i]}" for i in idx])
    print("\nMatriz de confusion (un split, filas=real):")
    print("  " + cmdf.to_string().replace("\n", "\n  "))


if __name__ == "__main__":
    correr("vote20cand", [1, 2, 3, 4, 5, 6, 7], NOM_PRIM, LEAK_PRIM,
           "M1 — PRIMARIA democrata (vote20cand), 7 candidatos")
    correr("w2presvtwho", [1, 2, 3], NOM_GEN, LEAK_GEN,
           "M2 — GENERAL 2020 (w2presvtwho), 3 clases CON Otro")
