"""
Modelo C aplicado a otro label: predecir PARTIDISMO (pid7x) desde
demografia + uso de redes (mismo feature-set limpio, sin actitudes).

pid7x (decodificado con termometros): 1=Dem fuerte ... 4=Independiente ... 7=Rep fuerte.

  Exp P3) 3 clases: Democrata (1-3) / Independiente (4) / Republicano (5-7)
  Exp P2) binario:  Democrata (1-3) vs Republicano (5-7)  (sin independientes)

Compara contra el techo del voto (Modelo C daba ~0.72 acc para Trump/Biden).
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

import exp_w2presvtwho as E

RANDOM_STATE = 42
PID = "pid7x"


def a_grupo(v):
    if v in (1, 2, 3):
        return "Dem"
    if v == 4:
        return "Indep"
    if v in (5, 6, 7):
        return "Rep"
    return None


def correr(modo, titulo):
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    df = df[df[PID].between(1, 7)].copy()
    df["grupo"] = df[PID].astype(int).map(a_grupo)
    if modo == "bin":
        df = df[df["grupo"].isin(["Dem", "Rep"])].copy()

    # X = SOLO demografia + redes (whitelist limpia, sin actitudes ni party id)
    X, _ = E.build_X(df)
    X = X[[c for c in E.DEMO_REDES if c in X.columns]].copy()

    clases = sorted(df["grupo"].unique())
    cod = {c: i for i, c in enumerate(clases)}
    y = df["grupo"].map(cod).values

    print("\n" + "=" * 64)
    print(titulo)
    print("=" * 64)
    print(f"Filas: {len(df)} | Features: {X.shape[1]} | "
          f"Distribucion: {dict(df['grupo'].value_counts())}")

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)
    imp = SimpleImputer(strategy="most_frequent")
    Xtr_i = pd.DataFrame(imp.fit_transform(Xtr), columns=X.columns, index=Xtr.index)
    Xte_i = pd.DataFrame(imp.transform(Xte),  columns=X.columns, index=Xte.index)

    def ev(n, m, a, b):
        m.fit(a, ytr); p = m.predict(b)
        print(f"  {n:24s} acc={accuracy_score(yte,p):.3f}  f1_macro={f1_score(yte,p,average='macro'):.3f}")
        return p

    print("Modelos:")
    ev("LogReg", Pipeline([("sc", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, n_jobs=-1))]), Xtr_i, Xte_i)
    ev("LDA (Fisher)", LinearDiscriminantAnalysis(), Xtr_i, Xte_i)
    ev("RandomForest", RandomForestClassifier(n_estimators=400, n_jobs=-1,
        random_state=RANDOM_STATE), Xtr_i, Xte_i)
    pred = ev("HistGradientBoosting", HistGradientBoostingClassifier(
        random_state=RANDOM_STATE), Xtr, Xte)
    maj = pd.Series(yte).value_counts(normalize=True).iloc[0]
    print(f"  {'(baseline mayoritaria)':24s} acc={maj:.3f}")

    inv = {i: c for c, i in cod.items()}
    idx = sorted(np.unique(yte))
    cm = confusion_matrix(yte, pred, labels=idx)
    cmdf = pd.DataFrame(cm, index=[f"real:{inv[i]}" for i in idx],
                        columns=[f"pred:{inv[i]}" for i in idx])
    print("\n  Matriz de confusion (HistGradientBoosting):")
    print("  " + cmdf.to_string().replace("\n", "\n  "))


if __name__ == "__main__":
    correr("3", "EXP P3 — Partidismo 3 clases (Dem / Indep / Rep) — demografia+redes")
    correr("bin", "EXP P2 — Partidismo binario (Dem vs Rep) — demografia+redes")
