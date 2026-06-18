"""
Genera datos para dos secciones nuevas del PDF:

  A) MULTICLASE: agregar la clase "Otro" (general 3 clases) y usar la primaria
     democrata (vote20cand, 7 candidatos). Mostramos accuracy alto pero f1_macro
     bajo y el RECALL por clase, que expone por que no funciona: las clases
     minoritarias son inmodelables (recall ~0).

  B) PARTIDISMO vs VOTO (sin la clase Otro): con las MISMAS features
     (demografia+redes), comparar que tan predecible es el voto binario
     (Trump/Biden) frente al partidismo (pid7x). Misma señal -> mismo techo.

Salidas: multiclase_resultados.json, pid_vs_voto.json
"""
import json
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from xgboost import XGBClassifier

import exp_w2presvtwho as E
import exp_escenarios as S
from exp_multiclase import NOM_PRIM, NOM_GEN, LEAK_PRIM, LEAK_GEN, construir

RS = 42


# ---------------- A) multiclase ----------------
def multiclase(target, clases, nombres, leak):
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    df = df[df[target].isin(clases)].copy()
    X = construir(df, target, leak)
    y = df[target].astype(int).values
    dist = {nombres[c]: int((y == c).sum()) for c in clases}

    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = HistGradientBoostingClassifier(random_state=RS).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p)); f1s.append(f1_score(yte, p, average="macro"))

    # recall por clase en un split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=RS, stratify=y)
    m = HistGradientBoostingClassifier(random_state=RS).fit(Xtr, ytr)
    pred = m.predict(Xte)
    idx = sorted(np.unique(yte))
    cm = confusion_matrix(yte, pred, labels=idx)
    recall = {nombres[i]: float(cm[r, r] / cm[r].sum()) for r, i in enumerate(idx)}

    return {
        "n": len(df), "feats": int(X.shape[1]), "dist": dist,
        "acc": float(np.mean(accs)), "acc_std": float(np.std(accs)),
        "f1": float(np.mean(f1s)),
        "maj": max(dist.values()) / len(df),
        "recall": recall,
    }


# ---------------- B) partidismo vs voto ----------------
def a_grupo(v):
    return "Dem" if v in (1, 2, 3) else ("Indep" if v == 4 else "Rep")


def holdout_xgb(X, y, n_class):
    accs, f1s = [], []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        params = dict(S.XGB_PARAMS)
        if n_class > 2:
            params["objective"] = "multi:softprob"
        m = XGBClassifier(**params).fit(Xtr, ytr)
        p = m.predict(Xte)
        accs.append(accuracy_score(yte, p)); f1s.append(f1_score(yte, p, average="macro"))
    return float(np.mean(accs)), float(np.std(accs)), float(np.mean(f1s))


def pid_vs_voto():
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    feat = [c for c in E.DEMO_REDES]

    out = {}

    # voto binario Trump/Biden
    d = df[df["w2presvtwho"].isin([1, 2])].copy()
    Xv = S.prep(d, feat)
    yv = (d["w2presvtwho"].values == 2).astype(int)
    a, s, f = holdout_xgb(Xv, yv, 2)
    out["voto_bin"] = {"label": "Voto (Trump vs Biden)", "n": len(d),
                       "acc": a, "acc_std": s, "f1": f, "clases": 2}

    # partidismo binario Dem/Rep (sin independientes)
    dp = df[df["pid7x"].between(1, 7)].copy()
    dp["g"] = dp["pid7x"].astype(int).map(a_grupo)
    db = dp[dp["g"].isin(["Dem", "Rep"])].copy()
    Xb = S.prep(db, feat)
    yb = (db["g"].values == "Rep").astype(int)
    a, s, f = holdout_xgb(Xb, yb, 2)
    out["pid_bin"] = {"label": "Partidismo (Dem vs Rep)", "n": len(db),
                      "acc": a, "acc_std": s, "f1": f, "clases": 2}

    # partidismo 3 clases Dem/Indep/Rep
    X3 = S.prep(dp, feat)
    cod = {"Dem": 0, "Indep": 1, "Rep": 2}
    y3 = dp["pid7x"].astype(int).map(a_grupo).map(cod).values
    a, s, f = holdout_xgb(X3, y3, 3)
    out["pid_3"] = {"label": "Partidismo (Dem/Indep/Rep)", "n": len(dp),
                    "acc": a, "acc_std": s, "f1": f, "clases": 3}
    out["feats"] = int(Xv.shape[1])
    return out


if __name__ == "__main__":
    print("== A) multiclase ==")
    mc = {
        "primaria": multiclase("vote20cand", [1, 2, 3, 4, 5, 6, 7], NOM_PRIM, LEAK_PRIM),
        "general": multiclase("w2presvtwho", [1, 2, 3], NOM_GEN, LEAK_GEN),
    }
    for k, v in mc.items():
        print(f"\n{k}: n={v['n']} feats={v['feats']} acc={v['acc']:.3f} "
              f"f1={v['f1']:.3f} maj={v['maj']:.3f}")
        print("  dist:", v["dist"])
        print("  recall:", {c: round(r, 2) for c, r in v["recall"].items()})
    with open("multiclase_resultados.json", "w", encoding="utf-8") as f:
        json.dump(mc, f, ensure_ascii=False, indent=2)

    print("\n== B) partidismo vs voto ==")
    pv = pid_vs_voto()
    for k in ["voto_bin", "pid_bin", "pid_3"]:
        v = pv[k]
        print(f"  {v['label']:30s} n={v['n']:5d} acc={v['acc']:.3f}±{v['acc_std']:.3f} f1={v['f1']:.3f}")
    with open("pid_vs_voto.json", "w", encoding="utf-8") as f:
        json.dump(pv, f, ensure_ascii=False, indent=2)

    print("\nguardados: multiclase_resultados.json, pid_vs_voto.json")
