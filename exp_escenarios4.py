"""
Ladder FINAL, validado por correlacion con el voto (Trump vs Biden).

Tras descubrir que "tolerancia LGBT" NO es apolitico (corr ~0.45) y que la
"base factual" estaba contaminada por conducta que en 2020 se polarizo, queda
un gradiente limpio de "explicitud politica":

  BASE_APOL   apolitico real (corr ~0): demografia + uso de redes + salud factual.
  CONDUCTA    parece apolitico pero no (corr 0.2-0.3): conducta en pandemia
              (juntarse/salir), empatia, discernimiento de noticias, consumo
              politico.
  3a          afecto identitario / cultura (corr 0.4-0.5): LGBT, musulmanes,
              ateos, feministas.
  3b          posiciones de issues (corr 0.5-0.66): aborto, clima, armas,
              inmigracion, Obamacare + afecto economico-institucional.
  3c          identidad ideologica (corr 0.6-0.73): lcself + cosmovision
              simbolica (resentimiento racial, sexismo).
  N4          actitudes fuertes / near-leakage: todo pre-eleccion.

XGBoost, holdout x5. Resultado: 0.727 -> 0.749 -> 0.819 -> 0.861 -> 0.926 ->
0.933 -> 0.971.
"""
import exp_w2presvtwho as E
import exp_modelo_d as D
import exp_escenarios as S

# --- BASE apolitica real (corr ~0): demo + redes + salud factual + uso de redes ---
SALUD = ["w2covid_work", "w2covid_fin", "w2covid_sick", "w2covid_know",
         "w3genhealth", "w3hl032", "w3phq92"]
REDES_PURO = [c for c in D.USO_REDES if c not in ["w2discern", "w3discern", "w2p5", "w3pe"]]
BASE_APOL = E.DEMO_REDES + SALUD + REDES_PURO

# --- CONDUCTA que parece apolitica pero se polarizo (corr 0.2-0.3) ---
CONDUCTA = ["w2emp_place", "w2covid_gather", "w2covid_out",
            "w2discern", "w3discern", "w2p5", "w3pe"]

# --- 3a identitario / cultura ---
N3a = [c for c in D.TERM_GRUPOS
       if any(g in c for g in ["ftgay", "fttrans", "ftatheists", "ftmuslims", "ftfeminists"])]

# --- 3b issues + afecto economico-institucional ---
N3b = [c for c in D.TERM_GRUPOS
       if any(g in c for g in ["ftsocialists", "ftcapitalists", "ftpolice", "ftjournal"])] \
    + ["w2gundiff", "w3gundiff", "w2c_self", "w3abortion", "w2aca", "w2deport"]

# --- 3c ideologia explicita + simbolica ---
N3c = D.IDEOLOGIA + ["w2rr1", "w2rr2", "w2w1", "w2w2"]


if __name__ == "__main__":
    df, y = S.datos()
    Xfull, _ = E.build_X(df)
    acc = BASE_APOL
    print("XGBoost — ladder final por explicitud politica (Trump vs Biden, holdout x5)\n")
    S.evaluar("BASE apolitica real",            S.prep(df, acc), y); acc = acc + CONDUCTA
    S.evaluar("+ conducta polarizada",          S.prep(df, acc), y); acc = acc + N3a
    S.evaluar("+ 3a identitario (LGBT...)",      S.prep(df, acc), y); acc = acc + N3b
    S.evaluar("+ 3b issues (aborto, clima...)",  S.prep(df, acc), y); acc = acc + N3c
    S.evaluar("+ 3c ideologia (lcself...)",      S.prep(df, acc), y)
    S.evaluar("+ N4 actitudes fuertes (todo)",   Xfull, y)
