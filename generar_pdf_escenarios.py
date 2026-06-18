"""
Genera un PDF con la tabla de escenarios por tipo de informacion y una
explicacion de que incluye cada nivel (con ejemplos de variables reales).

Salida: escenarios_por_tipo.pdf
"""
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, KeepTogether)

# colores por tipo (mismos del grafico)
C_BASE = colors.HexColor("#4C72B0")
C_IDENT = colors.HexColor("#55A868")
C_ISSUE = colors.HexColor("#C44E52")
C_LEAK = colors.HexColor("#8172B3")
GRIS = colors.HexColor("#F2F2F2")

# (nombre, +vars, acumulado, accuracy, aporte, color)
FILAS = [
    ("Apolítico real",            75,  75, "0,750", "piso",    C_BASE),
    ("+ conducta polarizada",      7,  82, "0,801", "+0,05",   C_BASE),
    ("+ afecto identitario",       8,  90, "0,851", "+0,05",   C_IDENT),
    ("+ posiciones de issues",    14, 104, "0,926", "+0,075",  C_ISSUE),
    ("+ ideología explícita",      6, 110, "0,933", "+0,01",   C_ISSUE),
    ("+ actitudes a candidatos",  232, 342, "0,971", "+0,04",  C_LEAK),
]

# explicaciones: (titulo, color, accuracy, contenido_html, porque_html)
SECCIONES = [
    ("1 · Apolítico real", C_BASE, "0,750",
     "Información de <b>“quién sos”</b> sin contenido político, en tres familias:"
     "<br/>• <b>Demografía</b>: edad, género, raza/etnia, educación, ingreso, "
     "estado civil, región, religión, si es evangélico <i>(profile_age, "
     "profile_racethnicity, profile_educ5, profile_income, profile_relig, "
     "profile_born)</i>."
     "<br/>• <b>Salud factual</b>: impacto del COVID en trabajo/finanzas/salud, "
     "salud general autopercibida, escala de depresión <i>(w2covid_work, "
     "w2covid_fin, w3genhealth, w3phq92)</i>."
     "<br/>• <b>Uso de redes y medios</b>: qué plataformas usa (Facebook, "
     "Instagram, TikTok, Twitter, YouTube) y por dónde se informa <i>(fbuser, "
     "w3twit, w3tube, w3newsonline, w3newskeepup)</i>.",
     "Es el piso “honesto”: su correlación con el voto es ≈ 0. Saber edad, raza, "
     "educación y qué redes usás deja <b>mucho sin explicar</b> (0,75)."),

    ("2 · + conducta polarizada", C_BASE, "0,801",
     "Comportamiento que <b>parece</b> apolítico pero en 2020 se politizó:"
     "<br/>• <b>Conducta en pandemia</b>: cuánto se juntaba con gente / salía "
     "<i>(w2covid_gather, w2covid_out)</i>."
     "<br/>• <b>Empatía</b>: tendencia a ponerse en el lugar del otro "
     "<i>(w2emp_place)</i>."
     "<br/>• <b>Discernimiento de noticias</b> y consumo de información política "
     "<i>(w2discern, w3discern, w2p5, w3pe)</i>.",
     "No es ideología declarada, pero en el clima de 2020 estas conductas "
     "correlacionan 0,2–0,3 con el voto (el comportamiento frente al COVID se "
     "volvió señal partidaria). Suma +5 puntos."),

    ("3a · + afecto identitario / cultura", C_IDENT, "0,851",
     "Termómetros de sentimiento (0–100) hacia <b>grupos sociales y culturales</b>:"
     "<br/>• gays, personas trans, feministas, ateos, musulmanes "
     "<i>(w2ftgay, w2fttrans, w2ftfeminists, w3ftatheists, w3ftmuslims)</i>.",
     "Actitudes culturales estables —no “política” en sentido estricto— pero "
     "correlacionan 0,4–0,5. Cómo te sentís hacia grupos identitarios ya "
     "predice bastante. Suma +5 puntos."),

    ("3b · + posiciones de issues", C_ISSUE, "0,926",
     "Opiniones <b>concretas sobre temas de política pública</b>:"
     "<br/>• <b>Termómetros económico-institucionales</b>: socialistas, "
     "capitalistas, policía, periodistas <i>(w2ftsocialists, w2ftcapitalists, "
     "w2ftpolice, w2ftjournal)</i>."
     "<br/>• <b>Posiciones</b>: control de armas, cambio climático, aborto, "
     "Obamacare/ACA, deportación-inmigración <i>(w2gundiff, w2c_self, "
     "w3abortion, w2aca, w2deport)</i>.",
     "<b>Acá está el salto grande: +7,5 puntos con apenas 14 variables.</b> "
     "Correlación 0,5–0,66 con el voto. Las opiniones sobre issues concretos "
     "son el predictor decisivo, no la demografía."),

    ("3c · + ideología explícita", C_ISSUE, "0,933",
     "La etiqueta ideológica más directa:"
     "<br/>• <b>Autoubicación izquierda–derecha</b> <i>(w2lcself, w3lcself)</i>."
     "<br/>• <b>Cosmovisión simbólica</b>: resentimiento racial y sexismo moderno "
     "<i>(w2rr1, w2rr2, w2w1, w2w2)</i>.",
     "Correlación altísima (lcself ≈ 0,73), pero <b>redundante</b>: solo +1 punto "
     "sobre los issues. “Soy conservador” ya está implícito en qué opina la "
     "persona sobre aborto, clima y armas."),

    ("4 · + actitudes a candidatos (near-leakage)", C_LEAK, "0,971",
     "Todo el resto de variables pre-elección, incluidas las que están "
     "<b>peligrosamente cerca</b> de preguntar el voto:"
     "<br/>• termómetros a Trump / Biden / partidos, intención de voto, "
     "“qué partido es mejor en X”, aprobación presidencial.",
     "Se incluye solo como <b>techo de referencia</b>. Son 232 variables "
     "adicionales que aportan apenas +4 puntos: confirma que la señal útil ya "
     "estaba en los issues. <b>No se usan en el modelo final</b> por riesgo de "
     "leakage."),
]


# nombres legibles para las variables (clave = nombre sin prefijo w2/w3)
ETIQUETAS = {
    "profile_racethnicity": "Raza / etnia", "profile_born": "Evangélico (born-again)",
    "profile_relig": "Religión", "profile_educ5": "Educación", "profile_age": "Edad",
    "profile_income": "Ingreso", "profile_gender": "Género",
    "profile_marital": "Estado civil", "profile_region4": "Región",
    "profile_region9": "Región (9)", "profile_metro": "Zona metropolitana",
    "profile_lgbt": "Se identifica LGBT", "profile_employ": "Situación laboral",
    "profile_genhealth": "Salud general (perfil)",
    "ftgay": "Term. a gays", "fttrans": "Term. a personas trans",
    "ftfeminists": "Term. a feministas", "ftatheists": "Term. a ateos",
    "ftmuslims": "Term. a musulmanes", "ftsocialists": "Term. a socialistas",
    "ftcapitalists": "Term. a capitalistas", "ftpolice": "Term. a la policía",
    "ftjournal": "Term. a periodistas", "fttrump": "Term. a Trump",
    "ftjb": "Term. a Biden", "ftbiden": "Term. a Biden",
    "ftdem": "Term. a Demócratas", "ftrep": "Term. a Republicanos",
    "gundiff": "Control de armas", "c_self": "Cambio climático",
    "abortion": "Aborto", "aca": "Obamacare (ACA)", "deport": "Deportación / inmigración",
    "lcself": "Autoubicación izq–der", "rr1": "Resentimiento racial (1)",
    "rr2": "Resentimiento racial (2)", "w1": "Sexismo moderno (1)",
    "w2": "Sexismo moderno (2)", "emp_place": "Empatía",
    "covid_gather": "Juntarse (COVID)", "covid_out": "Salir (COVID)",
    "covid_work": "COVID: trabajo", "covid_fin": "COVID: finanzas",
    "covid_sick": "COVID: enfermó", "covid_know": "COVID: conoce casos",
    "discern": "Discernir noticias", "p5": "Consumo info política",
    "pe": "Consumo info política", "genhealth": "Salud general",
    "phq92": "Depresión (PHQ)", "hl032": "Salud (HL032)",
    "pid7x": "Identificación partidaria", "pid1r": "Identificación partidaria",
    "pidstr": "Fuerza partidaria",
    # near-leakage / ola 2-3
    "vote20d1": "Voto declarado (leak)", "econnow": "Estado de la economía",
    "con_house": "Confianza en el Congreso", "ftbs": "Term. a Sanders",
    "dempref1": "Preferencia primaria Dem", "ran_vote2cand5": "Voto en primaria",
    "total_time_pk_cjus": "Tiempo de respuesta (admin)",
    "profile_hh18ov": "Adultos en el hogar", "newskeepup": "Se mantiene al día",
    "marital": "Estado civil", "fb3": "Uso de Facebook (3)",
    "fb4": "Uso de Facebook (4)",
}


def legible(var):
    base = var
    for p in ("w2", "w3", "profile_"):
        if var.startswith(p) and var[len(p):] in ETIQUETAS:
            base = var[len(p):]
            break
    et = ETIQUETAS.get(base, ETIQUETAS.get(var))
    if et:
        # marcar la ola w3 (post-eleccion) para desambiguar duplicados w2/w3
        return et + (" (w3)" if var.startswith("w3") else "")
    return var


def build():
    doc = SimpleDocTemplate(
        "escenarios_por_tipo.pdf", pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Escenarios por tipo de información", author="Proyecto Datos")

    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=17, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=9.5,
                         textColor=colors.HexColor("#666666"), spaceAfter=12)
    intro = ParagraphStyle("intro", parent=ss["Normal"], fontSize=10,
                           leading=14, alignment=TA_JUSTIFY, spaceAfter=10)
    sec_t = ParagraphStyle("sec_t", parent=ss["Heading2"], fontSize=12,
                           spaceBefore=10, spaceAfter=3)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.5,
                          leading=13.5, alignment=TA_JUSTIFY, spaceAfter=4)
    porque = ParagraphStyle("porque", parent=body, leftIndent=10,
                            textColor=colors.HexColor("#333333"),
                            borderColor=colors.HexColor("#DDDDDD"))
    cap = ParagraphStyle("cap", parent=ss["Normal"], fontSize=8.5,
                         textColor=colors.HexColor("#666666"), spaceBefore=4)

    el = []
    el.append(Paragraph("Escenarios por tipo de información", h1))
    el.append(Paragraph("Predicción del voto presidencial 2020 (Trump vs Biden) — "
                        "ANES Social Media 2020-2022", sub))
    el.append(Paragraph(
        "Cada escenario agrega un <b>tipo</b> de información, ordenado por su "
        "“explicitud política” (validado por la correlación de cada bloque con el "
        "voto). La métrica es <b>accuracy con XGBoost, holdout repetido ×5</b>. "
        "La idea central: el score sube por el <b>tipo</b> de información, no por "
        "la cantidad de variables.", intro))

    # ---- tabla resumen ----
    head = ["Escenario", "+vars", "Σ vars", "Accuracy", "Aporte"]
    data = [head]
    for nom, nv, ac, acc, ap, _ in FILAS:
        data.append([nom, f"+{nv}", str(ac), acc, ap])
    t = Table(data, colWidths=[6.6 * cm, 1.7 * cm, 1.7 * cm, 2.4 * cm, 2.4 * cm])
    estilo = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
    ]
    for i, (_, _, _, _, _, col) in enumerate(FILAS, start=1):
        estilo.append(("LINEBEFORE", (0, i), (0, i), 4, col))
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), GRIS))
    # resaltar la fila del salto (issues)
    estilo.append(("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FBE9EA")))
    t.setStyle(TableStyle(estilo))
    el.append(t)
    el.append(Paragraph("Σ vars = variables acumuladas. El modelo final llega "
                        "hasta el nivel 3c (110 variables); el nivel 4 es solo "
                        "referencia (near-leakage).", cap))
    el.append(Spacer(1, 0.5 * cm))

    # ---- secciones ----
    for tit, col, acc, cont, pq in SECCIONES:
        bloque = [
            Paragraph(f'<font color="#{col.hexval()[2:]}">■</font> '
                      f'<b>{tit}</b>  ·  accuracy {acc}', sec_t),
            Paragraph(cont, body),
            Paragraph(f"<b>Por qué:</b> {pq}", porque),
            Spacer(1, 0.25 * cm),
        ]
        el.append(KeepTogether(bloque))

    # ---- permutation importance por escenario ----
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Variables más importantes por escenario", h1))
    el.append(Paragraph(
        "Importancia por <b>permutación</b> (no MDI): se mide cuántos puntos de "
        "accuracy se <b>pierden</b> al desordenar al azar cada variable en el "
        "conjunto de test. Es honesta con la redundancia —una variable cuya "
        "información ya está en otra no recibe crédito—. XGBoost, n_repeats=10. "
        "La barra es relativa al máximo de cada escenario.", intro))

    with open("perm_escenarios.json", encoding="utf-8") as f:
        perm = json.load(f)

    perm_lbl = ParagraphStyle("perm_lbl", parent=ss["Normal"], fontSize=9, leading=11)
    perm_bar = ParagraphStyle("perm_bar", parent=ss["Normal"], fontSize=8.5,
                              fontName="Courier", leading=11)

    for nom, _, _, acc, _, col in FILAS:
        items = perm.get(nom, [])
        if not items:
            continue
        mx = max(m for _, m, _ in items) or 1.0
        filas = []
        for v, mean, std in items:
            n = max(1, round(10 * mean / mx)) if mean > 0 else 0
            bar = "█" * n
            pts = f"{mean*100:.1f}"
            filas.append([Paragraph(legible(v), perm_lbl),
                          Paragraph(f'<font color="#{col.hexval()[2:]}">{bar}</font> '
                                    f"{pts}", perm_bar)])
        tt = Table(filas, colWidths=[7.0 * cm, 8.5 * cm])
        tt.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LINEBEFORE", (0, 0), (0, -1), 3, col),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        bloque = [
            Paragraph(f'<font color="#{col.hexval()[2:]}">■</font> '
                      f"<b>{nom}</b>  ·  accuracy {acc}", sec_t),
            tt,
            Spacer(1, 0.3 * cm),
        ]
        el.append(KeepTogether(bloque))

    el.append(Paragraph(
        "Lectura: en el nivel <b>apolítico</b> mandan el ser <b>evangélico</b> y la "
        "<b>raza/etnia</b> (la espina dorsal sociológica del voto). Al sumar issues, "
        "los <b>termómetros a policía, periodistas y socialistas</b> y el "
        "<b>control de armas</b> pasan al frente. En <b>near-leakage</b> las "
        "importancias se <b>desploman</b> (~0,3 pts): con 342 variables todo está "
        "tan duplicado que permutar una sola casi no mueve el accuracy.", cap))

    # ---- grafico embebido ----
    el.append(Spacer(1, 0.3 * cm))
    img = Image("escalera_score_vs_variables.png")
    maxw = 17 * cm
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = maxw, maxw * ratio
    el.append(KeepTogether([
        Paragraph("Resumen visual", sec_t),
        img,
        Paragraph("La pendiente es empinada al pasar a issues (pocas variables, "
                  "gran salto) y casi plana después (muchas variables, poco "
                  "aporte).", cap),
    ]))

    doc.build(el)
    print("guardado: escenarios_por_tipo.pdf")


if __name__ == "__main__":
    build()
