"""
Experimentos Biden vs Trump con el target CORRECTO: w2presvtwho (voto general 2020).

  Exp A) Todos los candidatos:  1=Trump, 2=Biden, 3=Otro   (3 clases)
  Exp B) Solo Trump vs Biden:   1=Trump, 2=Biden           (binario)

Leakage temporal: w2presvtwho es de la OLA 2 (post-eleccion). Todas las columnas
w2*/w3* se midieron al mismo tiempo o despues del voto -> son leakage.
Predecimos SOLO con features pre-eleccion (sin prefijo w).

Corre local con sklearn (sin XGBoost/matplotlib). Sin la parte lenta
(permutation importance / SHAP / curva precision-vs-#features).
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
import warnings, re
warnings.filterwarnings("ignore")

RANDOM_STATE = 42
CSV = ("anes_specialstudy_2020-2022_socialmedia_csv_20230705/"
       "anes_specialstudy_2020-2022_socialmedia_csv_20230705.csv")
TARGET = "w2presvtwho"
MISSING_CODES = [-1, -2, -3, -4, -5, -6, -7, -8, -9]

# Codigos del target que NO son voto a un candidato -> se descartan
#  -7=sin respuesta, -6=no-respuesta unidad, -1=no aplica (no voto)
TARGET_DROP = [-7, -6, -1]

ADMIN_COLS = [
    "version", "caseid",
    "weight_pre", "weight_pre_nr", "weight_pre_spss",
    "weight_post", "weight_post_nr", "weight_post_spss",
    "w2qual", "start", "end", "duration", "surv_mode", "surv_lang",
    "device", "w1congdist", "w2congdist",
]

CAND_NAMES = {1: "Trump", 2: "Biden", 3: "Otro"}

# ---- Set "demografia + uso de redes" (whitelist explicita, SIN actitudes) ----
DEMO = [
    "profile_gender", "profile_age", "profile_racethnicity", "profile_educ5",
    "profile_marital", "profile_employ", "profile_income", "profile_state",
    "profile_region4", "profile_region9", "profile_metro", "profile_internet",
    "profile_housing", "profile_home_type", "profile_phoneservice", "profile_hhsize",
    "profile_hh01", "profile_hh25", "profile_hh612", "profile_hh1317", "profile_hh18ov",
    "profile_genhealth", "profile_veteran", "profile_lgbt", "profile_relig",
    "profile_born", "profile_lang_other1",
]
REDES = [
    # consumo de medios / noticias
    "profile_newstv", "profile_newsradio", "profile_newsonline",
    "profile_newsmobile", "profile_newskeepup",
    # uso de plataformas (t=twitter, f=facebook, i=instagram, s=snapchat)
    "profile_socmedia1_t", "profile_socmedia1_f", "profile_socmedia1_i", "profile_socmedia1_s",
    "profile_socmedia2_t", "profile_socmedia2_f", "profile_socmedia2_i", "profile_socmedia2_s",
    # usuario de Facebook (uso, no contenido politico)
    "fbuser",
]
DEMO_REDES = DEMO + REDES


def cargar():
    df = pd.read_csv(CSV, encoding="latin-1", low_memory=False)
    df = df[~df[TARGET].isin(TARGET_DROP)].copy()
    df = df.dropna(subset=[TARGET])
    df[TARGET] = df[TARGET].astype(int)
    return df


def build_X(df):
    """Features pre-eleccion: descarta w2*/w3* (leakage temporal), admin y target."""
    leak = set(ADMIN_COLS) | {TARGET}
    for c in df.columns:
        if re.match(r"^w[23]", c):          # ola 2 y 3 = post-eleccion
            leak.add(c)
    feature_cols = [c for c in df.columns if c not in leak]

    X = df[feature_cols].copy()
    # faltantes ANES (negativos) -> NaN  (mask evita el bug de .replace en pandas 3.x)
    X = X.mask(X.isin(MISSING_CODES))
    # texto residual -> codigos
    for c in X.select_dtypes(include="object").columns:
        X[c] = pd.factorize(X[c])[0]
        X[c] = X[c].mask(X[c] == -1)
    return X, feature_cols


def evaluar(nombre, modelo, Xtr, Xte, y_train, y_test, res):
    modelo.fit(Xtr, y_train)
    pred = modelo.predict(Xte)
    acc = accuracy_score(y_test, pred)
    f1 = f1_score(y_test, pred, average="macro")
    res[nombre] = {"acc": acc, "f1_macro": f1}
    print(f"  {nombre:24s} acc={acc:.3f}  f1_macro={f1:.3f}")
    return pred


def correr(df, clases, titulo, whitelist=None):
    print("\n" + "=" * 64)
    print(titulo)
    print("=" * 64)
    sub = df[df[TARGET].isin(clases)].copy()
    X, fcols = build_X(sub)
    if whitelist is not None:
        cols = [c for c in whitelist if c in X.columns]
        X = X[cols].copy()
        fcols = cols
    y_raw = sub[TARGET].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    dist = pd.Series(y_raw).map(CAND_NAMES).value_counts()
    print(f"Filas: {len(sub)} | Features pre-eleccion: {len(fcols)}")
    print("Distribucion:", dict(dist))

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)

    imp = SimpleImputer(strategy="most_frequent")
    X_tr_i = pd.DataFrame(imp.fit_transform(X_tr), columns=X.columns, index=X_tr.index)
    X_te_i = pd.DataFrame(imp.transform(X_te), columns=X.columns, index=X_te.index)

    res = {}
    print("Modelos:")
    logreg = Pipeline([("sc", StandardScaler()),
                       ("clf", LogisticRegression(max_iter=2000, n_jobs=-1))])
    evaluar("LogReg", logreg, X_tr_i, X_te_i, y_tr, y_te, res)
    evaluar("LDA (Fisher)", LinearDiscriminantAnalysis(), X_tr_i, X_te_i, y_tr, y_te, res)
    rf = RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=RANDOM_STATE)
    evaluar("RandomForest", rf, X_tr_i, X_te_i, y_tr, y_te, res)
    # HistGBM: boosting nativo de sklearn, tolera NaN (sustituto local de XGBoost)
    hgb = HistGradientBoostingClassifier(random_state=RANDOM_STATE)
    pred_hgb = evaluar("HistGradientBoosting", hgb, X_tr, X_te, y_tr, y_te, res)

    # baseline trivial: predecir siempre la clase mayoritaria
    maj = pd.Series(y_te).value_counts(normalize=True).iloc[0]
    print(f"  {'(baseline mayoritaria)':24s} acc={maj:.3f}")

    # matriz de confusion del mejor por f1_macro -> usamos HGB (suele ganar)
    print("\n  Matriz de confusion (HistGradientBoosting), filas=real, cols=pred:")
    labels_idx = sorted(np.unique(y_te))
    cm = confusion_matrix(y_te, pred_hgb, labels=labels_idx)
    names = [CAND_NAMES[le.classes_[i]] for i in labels_idx]
    cmdf = pd.DataFrame(cm, index=[f"real:{n}" for n in names],
                        columns=[f"pred:{n}" for n in names])
    print(cmdf.to_string().replace("\n", "\n  "))
    return res


if __name__ == "__main__":
    df = cargar()
    print("Dataset:", df.shape, "| target:", TARGET)
    correr(df, [1, 2, 3], "EXP A — Todos los candidatos (Trump / Biden / Otro)")
    correr(df, [1, 2], "EXP B — Solo Trump vs Biden (binario)")
    correr(df, [1, 2], "EXP C — Trump vs Biden SOLO demografia + uso de redes",
           whitelist=DEMO_REDES)
