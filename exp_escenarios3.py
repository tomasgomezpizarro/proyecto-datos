"""
Tres niveles de predisposiciones estables (sobre demografia + redes):

  A   poco politicas: tolerancia a grupos sociales (gays, trans, ateos,
      musulmanes), empatia, conocimiento civico, factual/salud, uso de redes.
  INT temas concretos (dicen mucho, no son ideologia declarada): clima, policia,
      aborto, armas, inmigracion, Obamacare + afecto economico-partidario
      (socialistas, capitalistas, periodistas, feministas).
  B   ideologia/identidad explicita: autoubicacion izq-der (lcself) + escalas de
      cosmovision simbolica (resentimiento racial, sexismo).

Ladder XGBoost (Trump vs Biden), holdout x5. Reusa exp_escenarios / exp_modelo_d.
"""
import exp_w2presvtwho as E
import exp_modelo_d as D
import exp_escenarios as S
from exp_escenarios2 import NIVEL_A   # tolerancia social + factual + redes

# --- Nivel intermedio: temas concretos + afecto economico-partidario ---
TERM_B = [c for c in D.TERM_GRUPOS
          if not any(g in c for g in ["ftgay", "fttrans", "ftatheists", "ftmuslims"])]
ISSUES = ["w2gundiff", "w3gundiff", "w2c_self", "w3abortion", "w2aca", "w2deport"]
NIVEL_INT = TERM_B + ISSUES

# --- Nivel B: ideologia explicita + cosmovision simbolica ---
SIMBOLICA = ["w2rr1", "w2rr2", "w2w1", "w2w2"]      # resentimiento racial, sexismo
NIVEL_B = D.IDEOLOGIA + SIMBOLICA                    # lcself + simbolica


if __name__ == "__main__":
    df, y = S.datos()
    Xfull, _ = E.build_X(df)
    base = E.DEMO_REDES

    print("XGBoost — predisposiciones en 3 niveles (Trump vs Biden, holdout x5)")
    print(f"  A={len(NIVEL_A)}  INT={len(NIVEL_INT)}  B={len(NIVEL_B)} vars\n")
    S.evaluar("S1  Demografia",              S.prep(df, E.DEMO), y)
    S.evaluar("S2  + Uso de redes",          S.prep(df, base), y)
    S.evaluar("S3a + A: poco politicas",     S.prep(df, base + NIVEL_A), y)
    S.evaluar("S3i + INT: temas concretos",  S.prep(df, base + NIVEL_A + NIVEL_INT), y)
    S.evaluar("S3b + B: ideologia explicita", S.prep(df, base + NIVEL_A + NIVEL_INT + NIVEL_B), y)
    S.evaluar("S4  Todo pre-eleccion",       Xfull, y)
