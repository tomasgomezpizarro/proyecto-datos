"""
Grafico para la presentacion: accuracy vs CANTIDAD de variables agregadas.

La tesis que ilustra: el score NO sube por la cantidad de variables, sino por
el TIPO. La base apolitica ya tiene ~75 variables y se queda en 0.75; bastan
14 variables de issues (aborto, clima, armas) para saltar a 0.93; y las ~230
variables restantes solo suman 4 puntos.

Eje X = cantidad acumulada de variables; eje Y = accuracy (holdout x5, media+-
desvio). Cada punto anotado con el bloque de informacion que entra.

Genera: escalera_score_vs_variables.png
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

import exp_w2presvtwho as E
import exp_escenarios as S
import exp_escenarios4 as S4

# --- bloques acumulados de la escalera por explicitud politica ---
BLOQUES = [
    ("Apolítico real\n(demografía+salud+redes)", S4.BASE_APOL, "#4C72B0"),
    ("+ conducta\npolarizada",                   S4.CONDUCTA,   "#4C72B0"),
    ("+ afecto identitario\n(LGBT, musulmanes)",  S4.N3a,        "#55A868"),
    ("+ issues\n(aborto, clima, armas)",          S4.N3b,        "#C44E52"),
    ("+ ideología\nexplícita (lcself)",           S4.N3c,        "#C44E52"),
]


def correr(cols, y, df):
    X = S.prep(df, cols)
    accs = []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        m = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
        accs.append(accuracy_score(yte, m.predict(Xte)))
    return X.shape[1], np.mean(accs), np.std(accs)


def main():
    df, y = S.datos()
    Xfull, _ = E.build_X(df)

    nombres, nvars, medias, desvios = [], [], [], []
    acumulado = []
    for nom, cols, _ in BLOQUES:
        acumulado = acumulado + cols
        n, m, s = correr(acumulado, y, df)
        nombres.append(nom); nvars.append(n); medias.append(m); desvios.append(s)
        print(f"{nom.replace(chr(10),' '):42s} feats={n:3d}  acc={m:.3f}+-{s:.3f}")

    # punto final: todo pre-eleccion (near-leakage)
    accs = []
    for seed in range(5):
        Xtr, Xte, ytr, yte = train_test_split(Xfull, y, test_size=0.25,
                                              random_state=seed, stratify=y)
        mdl = XGBClassifier(**S.XGB_PARAMS).fit(Xtr, ytr)
        accs.append(accuracy_score(yte, mdl.predict(Xte)))
    nombres.append("+ actitudes a\ncandidatos (near-leak)")  # near-leakage
    nvars.append(Xfull.shape[1]); medias.append(np.mean(accs)); desvios.append(np.std(accs))
    print(f"{'+ near-leakage (todo pre-eleccion)':42s} feats={Xfull.shape[1]:3d}  "
          f"acc={np.mean(accs):.3f}+-{np.std(accs):.3f}")

    colores = [c for _, _, c in BLOQUES] + ["#8172B3"]

    # ---------------- grafico ----------------
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.plot(nvars, medias, "-", color="#999999", lw=1.5, zorder=1, alpha=0.7)
    ax.errorbar(nvars, medias, yerr=desvios, fmt="none", ecolor="#555555",
                capsize=4, lw=1.2, zorder=2)
    for x, ymed, c in zip(nvars, medias, colores):
        ax.scatter(x, ymed, s=140, color=c, zorder=3, edgecolor="white", linewidth=1.5)

    # etiquetas de bloque de cada punto (dx, dy, ha). issues queda sin texto:
    # la flecha roja ya lo identifica, asi evitamos el solapamiento.
    blq_off = [
        (10, -30, "left"),    # apolitico
        (12, -10, "left"),    # conducta
        (-14, 14, "right"),   # identitario
        None,                 # issues -> lo cubre la flecha roja
        (14, -6, "left"),     # ideologia
        (-14, 16, "right"),   # near-leak
    ]
    for x, ymed, nom, off in zip(nvars, medias, nombres, blq_off):
        if off is None:
            continue
        dx, dy, ha = off
        ax.annotate(nom, (x, ymed), textcoords="offset points", xytext=(dx, dy),
                    fontsize=8.5, ha=ha, color="#222222")

    # numeros de accuracy (posicionados a mano para los dos puntos pegados)
    num_off = [(0, 9, "center"), (0, 9, "center"), (0, 9, "center"),
               (-32, -3, "right"), (0, 10, "center"), (10, -12, "left")]
    for x, ymed, (dx, dy, ha) in zip(nvars, medias, num_off):
        ax.annotate(f"{ymed:.3f}", (x, ymed), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, fontsize=8, fontweight="bold",
                    color="#222222")

    # anotacion del mensaje central: el salto de los issues
    ax.annotate("14 variables de issues\n= +7,5 puntos",
                xy=(104, 0.926), xytext=(150, 0.86),
                fontsize=9.5, color="#C44E52", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#C44E52", lw=1.5))
    ax.annotate("+232 variables más\n= +4 puntos",
                xy=(342, 0.971), xytext=(250, 0.905),
                fontsize=9.5, color="#8172B3", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#8172B3", lw=1.5))

    ax.set_xlabel("Cantidad acumulada de variables", fontsize=11)
    ax.set_ylabel("Accuracy (Trump vs Biden, holdout ×5)", fontsize=11)
    ax.set_title("El score sube por el TIPO de información, no por la cantidad",
                 fontsize=13, fontweight="bold", pad=14)
    ax.set_ylim(0.70, 1.0)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig("escalera_score_vs_variables.png", dpi=150, bbox_inches="tight")
    print("\nguardado: escalera_score_vs_variables.png")


if __name__ == "__main__":
    main()
