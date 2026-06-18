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
    ("+ actitudes a candidatos",  172, 282, "0,971", "+0,04",  C_LEAK),
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
     "Las actitudes más explícitas hacia los candidatos, <b>depurando de entrada</b> "
     "la paradata (tiempos de respuesta, orden de ítems) y el leak directo del voto "
     "(intención de voto, voto a otros cargos, primaria):"
     "<br/>• termómetros a Trump / Biden / partidos, aprobación presidencial, "
     "“qué partido es mejor en X”.",
     "Son 282 variables (172 más que el nivel anterior) que aportan apenas +4 puntos: "
     "confirma que la señal útil ya estaba en los issues. Estas actitudes son "
     "<i>proxies de preferencia</i> (sentir calor por Trump es casi declarar el voto), "
     "así que el nivel se usa como <b>techo de referencia, no en el modelo final</b>."),
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
    # nivel 4 limpio
    "apppres": "Aprobación a Trump (presidente)",
    "appcorona": "Aprobación a Trump (coronavirus)",
    "remove": "Destitución de Trump (impeachment)",
    "dtcare": "“Trump se preocupa por mí”", "dsmart": "Estereotipo: ¿demócratas inteligentes?",
    "covid_us": "Manejo del COVID en EE.UU.", "ftimmig": "Term. a inmigrantes",
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


# ---------------- pie de pagina (numeracion) ----------------
def _numero_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawCentredString(A4[0] / 2, 1.0 * cm, str(doc.page))
    canvas.restoreState()


def _sin_numero(canvas, doc):
    pass


# ---------------- portada ----------------
def portada(el, ss):
    from reportlab.platypus import PageBreak
    from reportlab.lib.enums import TA_CENTER
    cen = ParagraphStyle("cen", parent=ss["Normal"], alignment=TA_CENTER)
    titulo = ParagraphStyle("ptit", parent=cen, fontSize=22, leading=27,
                            spaceAfter=10, textColor=colors.HexColor("#1A1A1A"))
    subt = ParagraphStyle("psub", parent=cen, fontSize=12.5, leading=17,
                          textColor=colors.HexColor("#555555"))
    meta = ParagraphStyle("pmeta", parent=cen, fontSize=11, leading=16)
    chico = ParagraphStyle("pchico", parent=cen, fontSize=9.5,
                           textColor=colors.HexColor("#777777"))

    el.append(Spacer(1, 4.5 * cm))
    el.append(Paragraph("¿Qué determina el voto?", titulo))
    el.append(Paragraph("Predicción del voto presidencial 2020 (EE.UU.) a partir de "
                        "perfil, uso de redes y actitudes", subt))
    el.append(Spacer(1, 0.6 * cm))
    el.append(Paragraph("— ANES Special Study 2020-2022 (Social Media) —", chico))
    el.append(Spacer(1, 3.5 * cm))
    el.append(Paragraph("<b>Tomás Gómez Pizarro · Mikael Rodríguez</b>", meta))
    el.append(Spacer(1, 0.3 * cm))
    el.append(Paragraph("Ciencia de Datos 2026 — FAMAF, Universidad Nacional de "
                        "Córdoba", meta))
    el.append(Spacer(1, 0.2 * cm))
    el.append(Paragraph("Junio de 2026", meta))
    el.append(Spacer(1, 4.0 * cm))
    el.append(Paragraph("github.com/tomasgomezpizarro/proyecto-datos", chico))
    el.append(PageBreak())


# ---------------- resumen ejecutivo ----------------
def seccion_resumen(el, ss, h1, intro, sec_t, body, cap):
    el.append(Paragraph("Resumen", h1))
    el.append(Paragraph(
        "Predecimos el <b>voto presidencial 2020 (Trump vs Biden)</b> sobre la "
        "encuesta ANES Special Study 2020-2022 (5.750 encuestados, 914 variables) y, "
        "más que maximizar el acierto, estudiamos <b>qué tipo de información</b> lo "
        "determina. El desafío central es metodológico: separar predictores "
        "legítimos de <i>fugas</i> (<i>leakage</i>) en cientos de variables. "
        "Construimos una <b>escalera de escenarios</b> ordenada por “explicitud "
        "política” y medimos cuánto aporta cada bloque de información.", body))
    el.append(Paragraph(
        "Hallazgo principal: la <b>demografía sola predice poco</b> (~0,75); el salto "
        "decisivo lo dan las <b>posiciones sobre issues</b> (aborto, clima, armas), "
        "que llevan el accuracy a <b>0,93</b>. La ideología auto-declarada resulta "
        "redundante una vez conocidos los issues. El <b>tuning de hiperparámetros, la "
        "elección de algoritmo y la cantidad de datos casi no mueven la aguja</b>: el "
        "cuello de botella es la información, no el modelo. El error remanente (~3-6%) "
        "es irreducible —los <b>votantes cruzados</b>, que votan contra su propio "
        "perfil—.", body))


# ---------------- datos y metodologia ----------------
def seccion_metodologia(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Datos y metodología", h1))

    el.append(Paragraph("Los datos", sec_t))
    el.append(Paragraph(
        "<b>ANES Special Study 2020-2022 (Social Media)</b>: 5.750 encuestados × 914 "
        "variables, en tres olas (pre-elección, post-elección y seguimiento 2021-22). "
        "Los faltantes vienen codificados con negativos (−1…−9) → convertidos a "
        "<i>NaN</i>. Las respuestas son códigos ordinales, no magnitudes: los modelos "
        "de árboles los toleran; los lineales se usan como baseline. Por defecto se "
        "excluyen las variables de las olas 2 y 3 (medidas igual o después del voto).", body))

    el.append(Paragraph("Un hallazgo previo: la label estaba mal identificada", sec_t))
    el.append(Paragraph(
        "El primer candidato a variable objetivo, <i>vote20cand</i>, resultó ser la "
        "<b>primaria demócrata</b> (Biden vs Sanders vs Warren…), no la elección "
        "general. Lo detectamos porque un binario “Biden vs Trump” daba apenas 86% y "
        "porque los códigos no cerraban: al decodificarlos con los termómetros de "
        "sentimiento, <i>todos</i> los grupos resultaban pro-Biden. La variable "
        "correcta es <b>w2presvtwho</b> (Trump 1.801 · Biden 2.561 · Otro 171), "
        "verificada con termómetros. <b>Lección: desconfiar de un número que “hace "
        "ruido” y verificar el significado contra el codebook.</b>", body))

    el.append(Paragraph("La taxonomía de leakage (el corazón metodológico)", sec_t))
    el.append(Paragraph(
        "Con 914 variables, el problema central es separar predictores legítimos de "
        "<i>fugas</i>. Lo decidimos por la pregunta: <i>“¿es causa o consecuencia del "
        "voto?”</i>", body))
    tax = [
        ["Tipo", "Ejemplos", "Decisión"],
        ["Leakage directo", "a quién votó, voto a diputados/senadores", "excluir"],
        ["Consecuencia del voto", "aprobación post, emociones del resultado", "excluir"],
        ["Percepción partidaria", "estado de la economía, confianza en instituciones", "excluir"],
        ["Proxy de preferencia", "“qué partido es mejor en X”, termómetros a candidatos", "excluir"],
        ["Leakage temporal", "toda variable de la ola 2/3", "excluir"],
        ["Predisposición estable", "valores, afecto a grupos, ideología", "USAR"],
        ["Apolítico", "demografía, salud factual, uso de redes", "USAR"],
    ]
    tt = Table(tax, colWidths=[3.8 * cm, 8.4 * cm, 2.3 * cm])
    estilo = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]
    # filas "USAR" en verde, "excluir" en rojo tenue
    for i in range(1, len(tax)):
        dec = tax[i][2]
        c = colors.HexColor("#1E8449") if dec == "USAR" else colors.HexColor("#B03A2E")
        estilo.append(("TEXTCOLOR", (2, i), (2, i), c))
        estilo.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
    tt.setStyle(TableStyle(estilo))
    el.append(tt)
    el.append(Paragraph(
        "<b>Matiz clave:</b> “medido después de la elección” <b>no</b> es lo mismo que "
        "<i>leakage</i>. Una actitud estable (visión sobre capitalistas/gays, "
        "resentimiento racial) es <b>anterior y causal</b>, aunque se haya preguntado "
        "en la ola post-electoral.", cap))

    el.append(Paragraph("Validación", sec_t))
    el.append(Paragraph(
        "Métricas: <b>accuracy + f1_macro</b> (por el desbalance) y matriz de "
        "confusión / recall por clase. Estimación con <b>holdout repetido ×5</b> "
        "(media ± desvío): no se lee el tercer decimal de un único split (su error de "
        "muestreo es ≈ ±0,6-1,3%). Modelo principal: <b>XGBoost</b>; se comparan "
        "Regresión Logística, LDA y Random Forest como referencia.", body))


# ---------------- referencias ----------------
def seccion_referencias(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Referencias", h1))
    ref = ParagraphStyle("ref", parent=body, leftIndent=14, firstLineIndent=-14,
                         spaceAfter=8)
    el.append(Paragraph(
        "American National Election Studies (2023). <i>ANES 2020-2022 Social Media "
        "Study</i> [dataset y user guide / codebook]. www.electionstudies.org.", ref))
    el.append(Paragraph(
        "Bergstra, J. &amp; Bengio, Y. (2012). <i>Random Search for Hyper-Parameter "
        "Optimization.</i> Journal of Machine Learning Research, 13, 281–305.", ref))
    el.append(Paragraph(
        "Chen, T. &amp; Guestrin, C. (2016). <i>XGBoost: A Scalable Tree Boosting "
        "System.</i> Proceedings of KDD ’16, 785–794.", ref))
    el.append(Paragraph(
        "Pedregosa, F. et al. (2011). <i>Scikit-learn: Machine Learning in Python.</i> "
        "Journal of Machine Learning Research, 12, 2825–2830.", ref))


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

    from reportlab.platypus import PageBreak
    el = []

    # ===== portada + resumen + metodologia =====
    portada(el, ss)
    seccion_resumen(el, ss, h1, intro, sec_t, body, cap)
    seccion_metodologia(el, ss, h1, intro, sec_t, body, cap)

    # ===== cuerpo: escenarios por tipo de informacion =====
    el.append(PageBreak())
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
    with open("perm_escenario_limpio.json", encoding="utf-8") as f:
        perm_limpio = json.load(f)   # nivel 4 depurado (sin paradata ni leak directo)

    perm_lbl = ParagraphStyle("perm_lbl", parent=ss["Normal"], fontSize=9, leading=11)
    perm_bar = ParagraphStyle("perm_bar", parent=ss["Normal"], fontSize=8.5,
                              fontName="Courier", leading=11)

    for nom, _, _, acc, _, col in FILAS:
        if nom == "+ actitudes a candidatos":
            items = perm_limpio[:8]          # top depurado, interpretable
        else:
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
        "<b>control de armas</b> pasan al frente. En el nivel <b>near-leakage</b> "
        "domina el <b>termómetro a Trump</b> (−1,4 pts) y la <b>aprobación "
        "presidencial</b>: son actitudes hacia los candidatos, casi sinónimos del "
        "voto — por eso este nivel es solo <b>techo de referencia</b>.", cap))

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

    # ---- A) multiclase: por que no funciona ----
    seccion_multiclase(el, ss, h1, intro, sec_t, body, cap)
    # ---- B) partidismo vs voto ----
    seccion_pid_voto(el, ss, h1, intro, sec_t, body, cap)
    # ---- C) optimizacion de hiperparametros ----
    seccion_hiperparametros(el, ss, h1, intro, sec_t, body, cap)
    # ---- D) conclusiones ----
    seccion_conclusiones(el, ss, h1, intro, sec_t, body, cap)
    # ---- E) referencias ----
    seccion_referencias(el, ss, h1, intro, sec_t, body, cap)

    doc.build(el, onFirstPage=_sin_numero, onLaterPages=_numero_pagina)
    print("guardado: escenarios_por_tipo.pdf")


def seccion_conclusiones(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Conclusiones", h1))
    el.append(Paragraph(
        "El proyecto no buscó solo “predecir el voto”, sino entender <b>qué tipo de "
        "información</b> lo determina y dónde está el límite de lo predecible. Los "
        "resultados convergen en cinco ideas:", intro))

    puntos = [
        ("El voto se explica por las actitudes políticas, no por la demografía.",
         "Saber edad, raza, educación y qué redes usás deja ~0,72-0,75. Lo que lleva "
         "el accuracy a >0,93 son las <b>posiciones concretas sobre issues</b> "
         "(aborto, clima, armas): el salto grande lo dan 14 variables, no la masa de "
         "datos sociodemográficos."),
        ("La ideología vive en las posiciones, no en la etiqueta.",
         "Conocidas las opiniones sobre los issues, agregar la autoubicación "
         "izquierda-derecha aporta apenas +1 punto: “soy conservador” es casi "
         "información redundante de lo que la persona ya opina."),
        ("El cuello de botella es la información, no el modelo.",
         "El tuning de hiperparámetros mueve milésimas; LogReg, RandomForest y "
         "XGBoost convergen cuando hay señal; y reducir el train de 75% a 60% no "
         "cambia el resultado. Lo único que movió la aguja fue <b>sumar información "
         "de otro tipo</b>."),
        ("Hay un techo irreducible: los votantes “incoherentes”.",
         "El ~3-6% de error no es azar ni falla del modelo: son <b>votantes "
         "cruzados</b> (votan contra su partido e ideología), que explican hasta el "
         "76% de los errores. Su voto no es función de las actitudes medidas, así que "
         "<b>ningún modelo puede llegar a 100%</b>."),
        ("Disciplina metodológica.",
         "Distinguir <i>leakage</i> de predisposición estable; mirar f1_macro y recall "
         "por clase ante el desbalance (las minorías son inmodelables); reportar con "
         "barras de error y no sobre-leer un único split. Modelamos el problema como "
         "<b>binario</b> (Trump vs Biden) por estas razones, no por comodidad."),
    ]
    for i, (tit, txt) in enumerate(puntos, start=1):
        el.append(Paragraph(f"<b>{i} · {tit}</b>", body))
        el.append(Paragraph(txt, ParagraphStyle(
            "cc", parent=body, leftIndent=12, spaceAfter=8)))

    el.append(Spacer(1, 0.2 * cm))
    el.append(Paragraph(
        "<b>En una frase:</b> en un electorado polarizado, el voto es casi un "
        "sinónimo de las actitudes políticas —tanto que conocerlas alcanza para "
        "predecirlo con >0,93—, y lo que queda sin explicar no es ignorancia del "
        "modelo sino la parte genuinamente idiosincrática de la decisión humana.",
        intro))


def _cfg_str(p):
    return (f"depth={p['max_depth']}, lr={p['learning_rate']}, "
            f"min_child={p['min_child_weight']}, sub={p['subsample']}, "
            f"col={p['colsample_bytree']}, λ={p['reg_lambda']}, "
            f"α={p['reg_alpha']}, árboles={p['n_estimators']}")


def seccion_hiperparametros(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Optimización de hiperparámetros", h1))
    el.append(Paragraph(
        "Los <b>parámetros</b> los aprende el modelo de los datos (los cortes de los "
        "árboles); los <b>hiperparámetros</b> se fijan antes y controlan <i>cómo</i> "
        "aprende (profundidad, regularización…). Optimizarlos = probar "
        "combinaciones y quedarse con la que mejor generaliza.", intro))

    # protocolo
    el.append(Paragraph("El protocolo: split 60 / 20 / 20", sec_t))
    el.append(Paragraph(
        "Partimos en <b>tres</b>: <b>train (60%)</b> para entrenar cada candidato, "
        "<b>validation (20%)</b> para elegir el mejor, y <b>test (20%)</b> para el "
        "número final. <b>El test no se toca durante la búsqueda.</b> Si eligiéramos "
        "los hiperparámetros mirando el test, nos sobreajustaríamos a él y el "
        "resultado saldría optimista; el <i>validation</i> es el “test de mentira” "
        "que sí podemos mirar, y el test real queda virgen para un reporte honesto.", body))

    # busqueda
    el.append(Paragraph("La búsqueda: random search + early stopping", sec_t))
    el.append(Paragraph(
        "Probamos <b>40 combinaciones al azar</b> del espacio (no todas: el grid "
        "completo son 8.640). El <i>random search</i> es más eficiente que el grid "
        "porque muchos hiperparámetros casi no influyen. El número de árboles no se "
        "busca a mano: se fija alto (2.000) y el <b>early stopping</b> lo corta solo "
        "cuando el error en <i>validation</i> deja de mejorar (50 rondas).", body))

    esp = [
        ["Hiperparámetro", "Valores probados", "Qué controla"],
        ["max_depth", "2, 3, 4, 6, 8", "profundidad → interacciones que capta"],
        ["learning_rate", "0,01 – 0,1", "cuánto aporta cada árbol"],
        ["min_child_weight", "1, 3, 5, 10", "mínimo de datos por hoja (poda)"],
        ["subsample", "0,6 / 0,8 / 1,0", "fracción de filas por árbol"],
        ["colsample_bytree", "0,6 / 0,8 / 1,0", "fracción de columnas por árbol"],
        ["reg_lambda", "0, 1, 2, 5", "regularización L2"],
        ["reg_alpha", "0, 0,5, 1", "regularización L1"],
    ]
    te = Table(esp, colWidths=[3.8 * cm, 3.6 * cm, 8.0 * cm])
    te.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    el.append(te)
    el.append(Spacer(1, 0.4 * cm))

    # resultados
    with open("tuning_resultados.json", encoding="utf-8") as f:
        tr = json.load(f)
    full, demo = tr["full"], tr["demo"]
    el.append(Paragraph("Resultados (XGBoost, reporte en test intacto)", sec_t))
    data = [
        ["Set de features", "default", "tuneado", "val", "Δ"],
        ["Completo (techo ~0,97)", f"{full['acc_def']:.3f}", f"{full['acc_tun']:.3f}",
         f"{full['val_acc']:.3f}", f"{full['acc_tun']-full['acc_def']:+.3f}"],
        ["Demografía+redes (~0,72)", f"{demo['acc_def']:.3f}", f"{demo['acc_tun']:.3f}",
         f"{demo['val_acc']:.3f}", f"{demo['acc_tun']-demo['acc_def']:+.3f}"],
    ]
    tt = Table(data, colWidths=[6.2 * cm, 2.3 * cm, 2.3 * cm, 2.0 * cm, 2.0 * cm])
    tt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
    ]))
    el.append(tt)
    el.append(Paragraph(
        f"Mejor config completo: {_cfg_str(full['params'])}.<br/>"
        f"Mejor config demo+redes: {_cfg_str(demo['params'])}.", cap))
    el.append(Spacer(1, 0.3 * cm))

    # conclusiones
    el.append(Paragraph("Tres conclusiones", sec_t))
    el.append(Paragraph(
        "<b>1 · El tuning mueve milésimas (+0,002).</b> En el techo alto y en el bajo "
        "por igual: el límite es la <b>señal de los datos</b>, no los "
        "hiperparámetros.", body))
    el.append(Paragraph(
        f"<b>2 · La búsqueda eligió sola el modelo más simple</b> (max_depth = "
        f"{full['params']['max_depth']} en ambos sets). Con poca estructura que "
        "exprimir, los árboles chatos ganan — y el early stopping bajó los árboles de "
        f"500 a {full['params']['n_estimators']}/{demo['params']['n_estimators']}.", body))
    el.append(Paragraph(
        f"<b>3 · Validation sobreestima.</b> En el set completo, validation dio "
        f"<b>{full['val_acc']:.3f}</b> pero el test honesto fue "
        f"<b>{full['acc_tun']:.3f}</b> (~{(full['val_acc']-full['acc_tun'])*100:.0f} "
        "punto de diferencia). El val está “elegido” (es el máximo de 40 candidatos), "
        "así que infla; por eso se reporta el <b>test intacto</b>. Esto es justo lo "
        "que el protocolo 60/20/20 está diseñado para evitar.", body))


def _tabla_clases(datos, recall, dist, ss):
    """Tabla distribución + recall por clase, con recall bajo en rojo."""
    cab = ["Clase", "n (casos)", "% del total", "Recall (acierto)"]
    filas = [cab]
    total = sum(dist.values())
    estilo = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]
    for i, (clase, n) in enumerate(sorted(dist.items(), key=lambda kv: -kv[1]), start=1):
        r = recall.get(clase, 0.0)
        filas.append([clase, str(n), f"{n/total*100:.1f}%", f"{r:.2f}"])
        if r < 0.10:
            estilo.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor("#C0392B")))
            estilo.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    t = Table(filas, colWidths=[5.0 * cm, 3.0 * cm, 3.5 * cm, 4.0 * cm])
    t.setStyle(TableStyle(estilo))
    return t


def seccion_multiclase(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("¿Y si el voto tiene más de dos clases?", h1))
    el.append(Paragraph(
        "Hasta acá modelamos <b>Trump vs Biden</b> (binario). Probamos dos variantes "
        "multiclase y <b>ninguna funciona bien</b> — por la misma razón: el "
        "<b>desbalance de clases</b>. El <i>accuracy</i> engaña (queda cerca de "
        "“adivinar siempre la mayoría”); el <b>f1_macro</b> y el <b>recall por "
        "clase</b> lo exponen. Modelo: HistGradientBoosting, holdout ×5.", intro))

    with open("multiclase_resultados.json", encoding="utf-8") as f:
        mc = json.load(f)

    # general con Otro
    g = mc["general"]
    el.append(Paragraph("1 · Voto general con la clase “Otro” (3 clases)", sec_t))
    el.append(Paragraph(
        f"Trump / Biden / Otro. accuracy <b>{g['acc']:.3f}</b> · f1_macro "
        f"<b>{g['f1']:.3f}</b> · baseline “siempre la mayoría” {g['maj']:.3f}.", body))
    el.append(_tabla_clases(g, g["recall"], g["dist"], ss))
    el.append(Paragraph(
        "El accuracy alto (0,935) es un <b>espejismo</b>: viene de que Trump y Biden "
        "se predicen casi perfecto. La clase <b>“Otro” (171 casos, 3,8%) tiene recall "
        "0,07</b> — el modelo casi nunca la acierta. Los terceros partidos son "
        "~2% del electorado y no tienen un perfil propio: se reparten entre los dos "
        "grandes. <b>Por eso modelamos el problema como binario.</b>", cap))
    el.append(Spacer(1, 0.4 * cm))

    # primaria
    p = mc["primaria"]
    el.append(Paragraph("2 · Primaria demócrata (vote20cand, 7 candidatos)", sec_t))
    el.append(Paragraph(
        f"Biden / Sanders / Warren / Buttigieg / Klobuchar / Bloomberg / Otro. "
        f"accuracy <b>{p['acc']:.3f}</b> · f1_macro <b>{p['f1']:.3f}</b> · "
        f"baseline {p['maj']:.3f}.", body))
    el.append(_tabla_clases(p, p["recall"], p["dist"], ss))
    el.append(Paragraph(
        "Acá el f1_macro se <b>derrumba a 0,23</b>. El modelo solo aprende "
        "<b>Biden</b> (recall 0,93) y a medias <b>Sanders</b> (0,55); "
        "<b>Bloomberg, Buttigieg y Klobuchar tienen recall 0,00</b> — con &lt;90 "
        "casos cada uno, no hay con qué aprenderlos. La primaria <i>fue</i>, en los "
        "hechos, Biden vs Sanders. <b>Ninguna técnica rescata una clase de 52 "
        "ejemplos solapada con una mayoría de 1.628.</b>", cap))
    el.append(Spacer(1, 0.3 * cm))
    el.append(Paragraph(
        "<b>Lección:</b> con clases minoritarias el accuracy miente; hay que mirar "
        "f1_macro y recall por clase. El cuello de botella es la <b>cantidad de "
        "casos</b>, no el método.", body))


def seccion_pid_voto(el, ss, h1, intro, sec_t, body, cap):
    from reportlab.platypus import PageBreak
    el.append(PageBreak())
    el.append(Paragraph("Predecir el voto vs predecir el partidismo", h1))
    el.append(Paragraph(
        "¿Es más fácil predecir <b>a quién votó</b> o <b>con qué partido se "
        "identifica</b> (pid7x)? Con las <b>mismas features</b> (solo "
        "demografía + uso de redes, sin actitudes políticas) y el mismo modelo "
        "(XGBoost, holdout ×5), comparamos. <i>Sin</i> la clase “Otro” del voto.", intro))

    with open("pid_vs_voto.json", encoding="utf-8") as f:
        pv = json.load(f)

    cab = ["Qué se predice", "Clases", "n", "Accuracy", "f1_macro"]
    filas = [cab]
    for k in ["voto_bin", "pid_bin", "pid_3"]:
        v = pv[k]
        filas.append([v["label"], str(v["clases"]), str(v["n"]),
                      f"{v['acc']:.3f} ± {v['acc_std']:.3f}", f"{v['f1']:.3f}"])
    t = Table(filas, colWidths=[6.3 * cm, 1.8 * cm, 1.8 * cm, 3.3 * cm, 2.3 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 1), (-1, 2), colors.HexColor("#EAF1F7")),
    ]))
    el.append(t)
    el.append(Paragraph(f"(features = {pv['feats']} variables de demografía + redes)", cap))
    el.append(Spacer(1, 0.4 * cm))

    el.append(Paragraph(
        "<b>Voto (0,727) y partidismo binario (0,718) dan prácticamente lo mismo</b> "
        "—la diferencia cae dentro del desvío—. No es casualidad: <b>voto e "
        "identidad partidaria coinciden en ~94% de las personas</b> (correlación de "
        "Spearman 0,78), así que para un modelo son <b>casi la misma variable</b>. "
        "El techo de ~0,72 no es una propiedad “del voto” ni “del partidismo”: es el "
        "<b>límite de lo que la demografía sola puede decir</b>.", body))
    el.append(Paragraph(
        "Cuando se agregan los <b>independientes</b> (3 clases), el accuracy cae a "
        "<b>0,641</b> y el f1_macro a 0,49: los independientes no tienen un perfil "
        "demográfico propio (están “en el medio”), así que son los más difíciles de "
        "clasificar — el mismo fenómeno que veíamos en los votantes cruzados.", cap))


if __name__ == "__main__":
    build()
