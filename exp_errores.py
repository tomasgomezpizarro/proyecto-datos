"""
¿Qué casos hacen que el modelo NO dé 100%?

Analiza los votantes mal clasificados por el modelo legítimo (escenario 3c,
XGBoost, ~0.93). Cruza errores vs aciertos por:
  - partidismo (pid7x): ¿son "votantes cruzados" (Rep que votó Biden, etc.)?
  - independientes (pid7x == 4).
  - ideología (lcself): ¿coincide con su voto?
  - confianza del modelo: |p - 0.5| (¿son casos ambiguos o sorpresas?).
"""
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

import exp_w2presvtwho as E
import exp_escenarios as S
import exp_escenarios4 as S4

RS = 42
E_MISSING = E.MISSING_CODES


def grupo_pid(v):
    if 1 <= v <= 3:
        return "Dem"
    if v == 4:
        return "Indep"
    if 5 <= v <= 7:
        return "Rep"
    return "?"


def analizar(X, y, df, titulo):
    # metadatos externos (no son features): partidismo e ideologia declarada
    pid = df["pid7x"].mask(df["pid7x"].isin(E_MISSING)).values
    lc = df["w2lcself"].mask(df["w2lcself"].isin(E_MISSING)).values

    idx = np.arange(len(y))
    itr, ite = train_test_split(idx, test_size=0.25, random_state=RS, stratify=y)
    m = XGBClassifier(**S.XGB_PARAMS).fit(X.iloc[itr], y[itr])
    proba = m.predict_proba(X.iloc[ite])[:, 1]
    pred = (proba >= 0.5).astype(int)
    yte = y[ite]
    acc = accuracy_score(yte, pred)
    err = pred != yte
    print(f"{titulo} — {X.shape[1]} vars · test n={len(ite)} · acc={acc:.3f}")
    print(f"Errores: {err.sum()} de {len(ite)} ({err.mean()*100:.1f}%)\n")

    pid_te = pid[ite]
    lc_te = lc[ite]
    voto = yte  # 1=Biden, 0=Trump

    # --- voto cruzado vs partidismo ---
    g = np.array([grupo_pid(v) if not np.isnan(v) else "?" for v in pid_te])
    cruzado = ((g == "Rep") & (voto == 1)) | ((g == "Dem") & (voto == 0))
    indep = g == "Indep"
    print("== Partidismo (pid7x) ==")
    print(f"  votantes cruzados (Rep→Biden o Dem→Trump): "
          f"{cruzado.sum()} en test")
    print(f"    de ellos MAL clasificados: {(cruzado & err).sum()} "
          f"({(err[cruzado].mean()*100 if cruzado.sum() else 0):.0f}% de error)")
    print(f"  independientes (pid7x=4): {indep.sum()}, "
          f"error {(err[indep].mean()*100 if indep.sum() else 0):.0f}%")
    leales = ~cruzado & ~indep & (g != "?")
    print(f"  partidistas leales: {leales.sum()}, "
          f"error {(err[leales].mean()*100 if leales.sum() else 0):.0f}%")

    # cuanto del error total explican los cruzados+indep
    expl = (err & (cruzado | indep)).sum()
    print(f"\n  -> cruzados+independientes explican {expl}/{err.sum()} "
          f"= {expl/err.sum()*100:.0f}% de TODOS los errores")

    # --- confianza del modelo en los errores ---
    conf = np.abs(proba - 0.5)
    print("\n== Confianza del modelo ==")
    print(f"  |p-0.5| medio en aciertos: {conf[~err].mean():.3f}")
    print(f"  |p-0.5| medio en errores:  {conf[err].mean():.3f}")
    ambig = conf < 0.20   # proba entre 0.30 y 0.70
    print(f"  errores en zona ambigua (p∈[0.30,0.70]): "
          f"{(err & ambig).sum()}/{err.sum()} = {(err & ambig).sum()/err.sum()*100:.0f}%")
    sorpresa = err & (conf >= 0.35)   # el modelo estaba MUY seguro y fallo
    print(f"  'sorpresas' (modelo muy seguro y erró, |p-0.5|>=0.35): {sorpresa.sum()}")

    # --- ideologia cruzada ---
    print("\n== Ideología (w2lcself, 1=izq ... 7=der) ==")
    val = ~np.isnan(lc_te)
    ic = (((lc_te >= 5) & (voto == 1)) | ((lc_te <= 3) & (voto == 0))) & val
    print(f"  voto contrario a la ideología declarada: {ic.sum()}, "
          f"error {(err[ic].mean()*100 if ic.sum() else 0):.0f}%")


def main():
    df, y = S.datos()
    Xfull, _ = E.build_X(df)
    analizar(Xfull, y, df, "Nivel 4 (casi todo pre-elección, ~0.97)")


if __name__ == "__main__":
    main()
