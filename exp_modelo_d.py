"""
Modelo D = demografia + redes (Modelo C) + predisposiciones ESTABLES rescatadas
de las olas 2/3, que no son leakage del voto.

Motivacion: la regla "tirar todo w2*/w3*" es conservadora. Una actitud estable
(vision sobre capitalistas/gays/policia, valores morales, ideologia) o un dato
factual (perdiste el trabajo por covid, tu salud) NO es consecuencia del voto
presidencial -> se puede usar sin que "dicte la respuesta".

Listas explicitas y curadas a mano contra el codebook. Se excluye TODO lo que
codifica o es consecuencia del voto: a quien votaste, aprobacion presidencial,
emociones post, percepcion partidaria de la economia, confianza en instituciones,
"que partido maneja mejor X", composicion partidaria de la red, y pid* post.
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import cross_validate, StratifiedKFold, train_test_split
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score

import exp_w2presvtwho as E

RANDOM_STATE = 42

# ---- VERDES: predisposiciones estables (no causadas por el voto) ----
TERM_GRUPOS = [  # termometros a grupos sociales (NO partido/candidato/institucion)
    "w2ftgay", "w2ftsocialists", "w2ftcapitalists", "w2ftpolice", "w2ftjournal",
    "w2fttrans", "w2ftfeminists",
    "w3ftgay", "w3ftsocialists", "w3ftcapitalists", "w3ftpolice", "w3ftjournal",
    "w3fttrans", "w3ftfeminists", "w3ftatheists", "w3ftmuslims",
]
VALORES = [  # valores / posiciones de issues estables
    "w2gundiff", "w3gundiff", "w2c_self", "w2rr1", "w2rr2", "w2emp_place",
    "w2w1", "w2w2", "w3abortion", "w2aca", "w2deport",
]
IDEOLOGIA = ["w2lcself", "w3lcself"]            # autoubicacion izq-der (no pid*)
CONOCIMIENTO = ["w2pk_cjus_correct", "w2pk_speaker_correct", "w2pk_samoa_correct"]
VERDES = TERM_GRUPOS + VALORES + IDEOLOGIA + CONOCIMIENTO

# ---- AMARILLAS con pinzas: factuales / conductuales (no dictan el voto) ----
CIRCUNSTANCIA = [  # hechos personales / salud, no opiniones partidarias
    "w2covid_work", "w2covid_fin", "w2covid_know", "w2covid_gather", "w2covid_out",
    "w3covid_sick", "w3covid_vacc", "w3genhealth", "w3hl032", "w3phq92",
]
USO_REDES = [  # comportamiento de uso (frecuencia/plataformas/noticias), no actitud
    "w2fbuser", "w3fbuser", "w2fb2", "w2fb3", "w2fb4", "w2fb5",
    "w3fb2", "w3fb3", "w3fb4", "w3fb5", "w3inst", "w3red", "w3tik", "w3tube", "w3twit",
    "w3newstv", "w3newsradio", "w3newsonline", "w3newsmobile", "w3newskeepup",
    "w3socmedia1_f", "w3socmedia1_i", "w3socmedia1_s", "w3socmedia1_t",
    "w3socmedia2_f", "w3socmedia2_i", "w3socmedia2_s", "w3socmedia2_t",
    "w2discern", "w3discern", "w2p5", "w3pe",
]
AMARILLAS = CIRCUNSTANCIA + USO_REDES

EXTRA = VERDES + AMARILLAS


def build_modelo_d(df):
    """Demo+redes (whitelist) + columnas rescatadas, con missing -> NaN."""
    cols = [c for c in (E.DEMO_REDES + EXTRA) if c in df.columns]
    X = df[cols].copy()
    X = X.mask(X.isin(E.MISSING_CODES))
    for c in X.select_dtypes(include="object").columns:
        X[c] = pd.factorize(X[c])[0]
        X[c] = X[c].mask(X[c] == -1)
    return X


def datos(target):
    df = pd.read_csv(E.CSV, encoding="latin-1", low_memory=False)
    if target == "voto":
        df = df[df["w2presvtwho"].isin([1, 2])].copy()
        y = (df["w2presvtwho"].values == 2).astype(int)   # 1=Biden
    else:  # partidismo
        df = df[df["pid7x"].isin([1, 2, 3, 5, 6, 7])].copy()
        y = (df["pid7x"].values >= 5).astype(int)         # 1=Rep
    return df, y


def _prep(X):
    X = X.mask(X.isin(E.MISSING_CODES))
    for c in X.select_dtypes(include="object").columns:
        X[c] = pd.factorize(X[c])[0]
        X[c] = X[c].mask(X[c] == -1)
    return X


def cv(target):
    df, y = datos(target)
    Xc = _prep(df[[c for c in E.DEMO_REDES if c in df.columns]].copy())
    Xd = build_modelo_d(df)
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=RANDOM_STATE)
    for nombre, X in [("C  demo+redes", Xc), ("D  + estables/factuales", Xd)]:
        r = cross_validate(HistGradientBoostingClassifier(random_state=RANDOM_STATE),
                           X, y, cv=skf, scoring=["accuracy", "f1_macro"])
        a, f = r["test_accuracy"], r["test_f1_macro"]
        print(f"  {nombre:26s} feats={X.shape[1]:3d}  "
              f"acc={a.mean():.3f}±{a.std():.3f}  f1={f.mean():.3f}±{f.std():.3f}")


def importancia_d(target="voto"):
    df, y = datos(target)
    X = build_modelo_d(df)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                          random_state=RANDOM_STATE, stratify=y)
    imp = SimpleImputer(strategy="most_frequent")
    Xtr_i = pd.DataFrame(imp.fit_transform(Xtr), columns=X.columns, index=Xtr.index)
    Xte_i = pd.DataFrame(imp.transform(Xte),  columns=X.columns, index=Xte.index)
    rf = RandomForestClassifier(n_estimators=400, n_jobs=-1,
                                random_state=RANDOM_STATE).fit(Xtr_i, ytr)
    perm = permutation_importance(rf, Xte_i, yte, n_repeats=15,
                                  random_state=RANDOM_STATE, scoring="f1_macro", n_jobs=-1)
    pi = pd.Series(perm.importances_mean, index=X.columns).sort_values(ascending=False)
    print(f"\nTop 15 permutation importance — Modelo D ({target}):")
    for c in pi.head(15).index:
        tag = "  <-- RESCATADA" if c in EXTRA else ""
        print(f"  {c:24s} {pi[c]:.4f}{tag}")


if __name__ == "__main__":
    print(f"Rescatadas: {len([c for c in EXTRA])} columnas "
          f"(verdes={len(VERDES)}, amarillas={len(AMARILLAS)})")
    print("\n=== VOTO (Trump vs Biden) — 10-fold CV ===")
    cv("voto")
    print("\n=== PARTIDISMO (Dem vs Rep) — 10-fold CV ===")
    cv("partidismo")
    importancia_d("voto")
