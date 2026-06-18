"""
Compara LogReg, RandomForest y XGBoost en el nivel 1 (apolítico, 75 vars).

LogReg y RF no toleran NaN -> pipeline con imputacion (mediana); LogReg ademas
escala. XGBoost maneja NaN nativo. Mismo holdout x5 (75/25) para comparar.
"""
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

import exp_escenarios as S
import exp_escenarios4 as S4

RS = 42

MODELOS = {
    "LogReg": make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(max_iter=2000, random_state=RS)),
    "RandomForest": make_pipeline(
        SimpleImputer(strategy="median"),
        RandomForestClassifier(n_estimators=400, random_state=RS, n_jobs=-1)),
    "XGBoost": XGBClassifier(**S.XGB_PARAMS),
}


def main():
    df, y = S.datos()
    X = S.prep(df, S4.BASE_APOL)
    print(f"Nivel 1 apolítico — {X.shape[1]} variables, n={len(y)} (Trump vs Biden)")
    print("Holdout x5 (75/25 estratificado)\n")
    print(f"  {'modelo':14s} {'accuracy':>16s}   {'f1_macro':>8s}")
    print("  " + "-" * 44)
    for nombre, modelo in MODELOS.items():
        accs, f1s = [], []
        for seed in range(5):
            Xtr, Xte, ytr, yte = train_test_split(
                X, y, test_size=0.25, random_state=seed, stratify=y)
            modelo.fit(Xtr, ytr)
            p = modelo.predict(Xte)
            accs.append(accuracy_score(yte, p))
            f1s.append(f1_score(yte, p, average="macro"))
        a, f = np.array(accs), np.array(f1s)
        print(f"  {nombre:14s}   {a.mean():.3f} ± {a.std():.3f}      {f.mean():.3f}")


if __name__ == "__main__":
    main()
