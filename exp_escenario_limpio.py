"""
"Techo limpio con termometros": el nivel 4 (todo pre-eleccion) pero quitando:
  - PARADATA / datos no utiles: tiempos de respuesta (total_time_*) y orden de
    presentacion de los termometros (ft_order*).
  - LEAK directo del voto 2020: intencion de voto (vote20d1), voto a Camara
    (voterep), primaria (dempref1, primparty, primary, ran_vote2cand*),
    vote20cand, vote20_match, percent20.

Se MANTIENEN los termometros sustantivos (fttrump, ftjb, ftdem, ftrep, ftnra,
ftpp, ftblack, etc.). Holdout x5 + permutation importance top-12.
"""
import json
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

import exp_w2presvtwho as E
import exp_escenarios as S

RANDOM_STATE = 42

PARADATA = ([c for c in []] )  # se completa en runtime con total_time_* y ft_order*
LEAK = ["vote20d1", "voterep", "vote20cand", "vote20_match", "percent20",
        "dempref1", "primparty", "primary"] + [f"ran_vote2cand{i}" for i in range(1, 7)]


def construir(df):
    X, _ = E.build_X(df)
    paradata = [c for c in X.columns if c.startswith("total_time") or c.startswith("ft_order")]
    quitar = set(paradata) | set(LEAK)
    Xlimpio = X[[c for c in X.columns if c not in quitar]].copy()
    return X, Xlimpio, paradata


def evaluar(X, y, label):
    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p)); f1s.append(f1_score(yte, p, average="macro"))
    a, f = np.array(accs), np.array(f1s)
    print(f"  {label:38s} feats={X.shape[1]:3d}  acc={a.mean():.3f}±{a.std():.3f}  f1={f.mean():.3f}")
    return a.mean()


def main():
    df, y = S.datos()
    Xfull, Xlimpio, paradata = construir(df)

    print("XGBoost — Trump vs Biden (holdout x5)\n")
    evaluar(Xfull, y, "Nivel 4 original (con leaks+paradata)")
    evaluar(Xlimpio, y, "Nivel 4 LIMPIO (sin leaks/paradata)")
    print(f"\n  quitadas: {len(paradata)} paradata + {len(LEAK)} leak = "
          f"{Xfull.shape[1]-Xlimpio.shape[1]} variables")

    # permutation importance del escenario limpio
    Xtr, Xte, ytr, yte = train_test_split(Xlimpio, y, test_size=0.25,
                                          random_state=RANDOM_STATE, stratify=y)
    m = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
    r = permutation_importance(m, Xte, yte, n_repeats=10,
                               random_state=RANDOM_STATE, scoring="accuracy")
    orden = np.argsort(r.importances_mean)[::-1][:12]
    top = [(Xlimpio.columns[i], float(r.importances_mean[i]), float(r.importances_std[i]))
           for i in orden]
    print("\nTop-12 permutation importance (escenario limpio):")
    for v, mean, std in top:
        print(f"  {v:20s} {mean*100:+.2f} ± {std*100:.2f} pts")

    with open("perm_escenario_limpio.json", "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)
    print("\nguardado: perm_escenario_limpio.json")


if __name__ == "__main__":
    main()
