"""
Permutation importance por escenario acumulado (Trump vs Biden, XGBoost).

Para cada nivel de la escalera entrena XGBoost en train y mide la caida de
accuracy al permutar cada variable en test (n_repeats=10). Guarda el top-8 de
cada escenario en perm_escenarios.json para que el PDF lo lea.

Permutacion (no MDI) porque es honesta con la redundancia: una variable cuya
informacion esta duplicada en otra no recibe credito inflado.
"""
import json
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from xgboost import XGBClassifier

import exp_w2presvtwho as E
import exp_escenarios as S
import exp_escenarios4 as S4

RANDOM_STATE = 42
N_REPEATS = 10
TOP = 8

# escenarios acumulados (mismo orden que el PDF)
BLOQUES = [
    ("Apolítico real",          S4.BASE_APOL),
    ("+ conducta polarizada",   S4.BASE_APOL + S4.CONDUCTA),
    ("+ afecto identitario",    S4.BASE_APOL + S4.CONDUCTA + S4.N3a),
    ("+ posiciones de issues",  S4.BASE_APOL + S4.CONDUCTA + S4.N3a + S4.N3b),
    ("+ ideología explícita",   S4.BASE_APOL + S4.CONDUCTA + S4.N3a + S4.N3b + S4.N3c),
]


def top_perm(X, y, k=TOP):
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)
    m = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
    r = permutation_importance(m, Xte, yte, n_repeats=N_REPEATS,
                               random_state=RANDOM_STATE, scoring="accuracy")
    orden = np.argsort(r.importances_mean)[::-1][:k]
    return [(X.columns[i], float(r.importances_mean[i]),
             float(r.importances_std[i])) for i in orden]


def main():
    df, y = S.datos()
    Xfull, _ = E.build_X(df)
    salida = {}

    for nom, cols in BLOQUES:
        X = S.prep(df, cols)
        salida[nom] = top_perm(X, y)
        print(f"\n### {nom}  ({X.shape[1]} vars)")
        for v, mean, std in salida[nom]:
            print(f"  {v:22s}  {mean:+.4f} ± {std:.4f}")

    # nivel 4: near-leakage (todo pre-eleccion)
    nom = "+ actitudes a candidatos"
    salida[nom] = top_perm(Xfull, y)
    print(f"\n### {nom}  ({Xfull.shape[1]} vars)")
    for v, mean, std in salida[nom]:
        print(f"  {v:22s}  {mean:+.4f} ± {std:.4f}")

    with open("perm_escenarios.json", "w") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print("\nguardado: perm_escenarios.json")


if __name__ == "__main__":
    main()
