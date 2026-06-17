"""
Parte el escenario S3 (predisposiciones estables) en DOS niveles:

  S3a  predisposiciones POCO POLITICAS: tolerancia a grupos sociales (gays,
       trans, ateos, musulmanes), empatia, conocimiento civico, factual/salud,
       uso de redes.
  S3b  + ideologico/policy: ideologia izq-der, posiciones de issues (armas,
       aborto, Obamacare, clima, inmigracion), resentimiento racial, sexismo,
       afecto economico-partidario (socialistas, capitalistas, policia, prensa).

Asi vemos cuanto predice "quien sos" socialmente vs cuanto agrega lo explicito
politico. XGBoost, holdout repetido x5. Reusa exp_escenarios.
"""
import exp_w2presvtwho as E
import exp_modelo_d as D
import exp_escenarios as S

# --- corte de los termometros a grupos: identidad-social (A) vs politico (B) ---
TERM_A = [c for c in D.TERM_GRUPOS
          if any(g in c for g in ["ftgay", "fttrans", "ftatheists", "ftmuslims"])]
TERM_B = [c for c in D.TERM_GRUPOS if c not in TERM_A]
VAL_B = [c for c in D.VALORES if c != "w2emp_place"]   # emp_place va a A

NIVEL_A = TERM_A + ["w2emp_place"] + D.CONOCIMIENTO + D.CIRCUNSTANCIA + D.USO_REDES
NIVEL_B = TERM_B + D.IDEOLOGIA + VAL_B


if __name__ == "__main__":
    df, y = S.datos()
    Xfull, _ = E.build_X(df)

    print("XGBoost — S3 partido en 2 niveles (Trump vs Biden, holdout x5)")
    print(f"  (Nivel A = {len(NIVEL_A)} vars poco politicas | "
          f"Nivel B = {len(NIVEL_B)} vars ideologicas/policy)\n")
    S.evaluar("S1  Demografia",                 S.prep(df, E.DEMO), y)
    S.evaluar("S2  + Uso de redes",             S.prep(df, E.DEMO_REDES), y)
    S.evaluar("S3a + Predisp. poco politicas",  S.prep(df, E.DEMO_REDES + NIVEL_A), y)
    S.evaluar("S3b + Ideologico/policy (todo)", S.prep(df, E.DEMO_REDES + NIVEL_A + NIVEL_B), y)
    S.evaluar("S4  Todo pre-eleccion",          Xfull, y)
