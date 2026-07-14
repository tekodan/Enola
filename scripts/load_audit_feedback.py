"""Carga el feedback de revisión humana a partir del reporte
`docs/auditoria-categorizaciones-2026-07-13.md`.

Para cada ``analysis_results.id`` evaluado:
- Si el veredicto del auditor es **DE ACUERDO**, se inserta feedback con
  ``agrees='true'`` (sin override).
- Si el veredicto es **RECATEGORIZAR**, se inserta feedback con
  ``agrees='false'`` y las etiquetas corregidas via ``corrected_labels``
  (tabla ``analysis_feedback_labels``) y los campos planos
  ``corrected_categoria/dimension/justificacion``.

Ejecutar con:
    source .venv/bin/activate && python scripts/load_audit_feedback.py
"""

from __future__ import annotations

from sqlalchemy import text

from src.storage.database import get_database

DB_URL = "sqlite:///data/tfm.db"
REVIEWER_USERNAME = "auditor-tfm"
REVIEWER_FULL_NAME = "Auditor TFM (revisión 2026-07-13)"
AUDIT_DOC = "docs/auditoria-categorizaciones-2026-07-13.md"


# ---------------------------------------------------------------------------
# Tabla de veredictos construida leyendo el documento de auditoría.
# Cada entrada: ar_id -> dict(verdict, reason, corrected_labels, severity).
# ``corrected_labels`` es la lista de LabelAssignment (post-auditoría).
# Cuando el veredicto es DE ACUERDO, la lista está vacía.
# ---------------------------------------------------------------------------
AUDIT_VERDICTS: dict[int, dict] = {
    # ---------- POSTS ----------
    1: {  # 0f3e884a8a124fd1_p0
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: 1.3 (Regla 3 doble estándar moral) + 2.3 (slut-shaming, leetspeak decodificado) + 4.2 (esencialismo) son correctos.",
    },
    2: {  # 0f3e884a8a124fd1_p1
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: sin referente femenino, sin marcadores VDG.",
    },
    3: {  # 0f3e884a8a124fd1_p2
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: triple carga manosférica 4.1 (taxonomías beta/del 1%) + 4.2 (esencialismo) + 4.3 (manual 'Fin del Chico Bueno') bien etiquetada.",
    },
    4: {  # dc8ae80a3ae35f92
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: 1.3 (desvalorización) + 2.3 (slut-shaming) + 4.1 (beta/tipo del KFC) son correctos.",
    },
    5: {  # d782af3f81de2512
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: sin referente femenino.",
    },
    6: {  # b0bcbbb5eb375a41
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: 1.3 + 2.3 + 4.1 + 4.2 multi correcto.",
    },
    7: {  # 3741fe9979b310c6
        "verdict": "DE ACUERDO",
        "reason": "Auditor 2026-07-13 §2.1: 'Muchos así...' sin referente femenino-objetivado.",
    },
    # ---------- COMENTARIOS (DE ACUERDO) ----------
    8: {
        "verdict": "DE ACUERDO",
        "reason": "§2.2: 'Ahora resulta que los hombres no engañan' — sin referente femenino-objetivado.",
    },
    9: {"verdict": "DE ACUERDO", "reason": "§2.2: nombre propio + GIPHY."},
    10: {"verdict": "DE ACUERDO", "reason": "§2.2: nombre propio + GIPHY."},
    11: {
        "verdict": "DE ACUERDO",
        "reason": "§2.2: 'Los ruquitos que no le hallan a la tecnología' — sin referente femenino.",
    },
    12: {"verdict": "DE ACUERDO", "reason": "§2.2: 'Manuel Lazo 12 h'."},
    13: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Desarrollar caracter y personalidad...' sin referente femenino.",
    },
    14: {"verdict": "DE ACUERDO", "reason": "§2.3: 'No se.'"},
    15: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Alguna gente se gusta poner...' sin referente femenino.",
    },
    16: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'No debes amar por completo ni confiar en una mujer' → Regla 3 / 1.3.",
    },
    17: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Honestidad, responsabilidad y respeto...' — frase motivacional neutra.",
    },
    18: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Que solo un poco de codicia, lujuria e ira...' sin referente femenino.",
    },
    19: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Nadie vendrá a salvarte...' — reclasificación correcta del falso positivo Cat. 1.2 de la auditoría 2026-07-12. Sugerencia: precisar sub-dim 5.3.",
    },
    20: {"verdict": "DE ACUERDO", "reason": "§2.3: 'Santa clos no existe'."},
    21: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'La gran mayoría de mujeres solo está contigo por conveniencia' → Regla 3 / 1.3 + 4.2.",
    },
    22: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Primero el trabajo y el dinero...' sin referente femenino-objetivado.",
    },
    23: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Y así hay muchas...' — sin referente explícito aislado.",
    },
    24: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'hombre deconstruide vs malandro' — jerga manosfera sin ataque.",
    },
    25: {  # 2020cf0150b86856
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.4 (ar_id=25): multi incompleta. La jerarquía 'actitudes de hombre blanco' es 4.2 pero el sesgo implícito hacia las mujeres como evaluadoras también activa 1.3 (doble estándar).",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.2",
        "corrected_justificacion": "Jerarquía masculina según 'actitudes de hombre blanco' (4.2) + sesgo implícito: las mujeres son público que rechaza/evalúa al varón (1.3 doble estándar).",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": "Taxonomía 'actitudes de hombre blanco' como ideal para el ligue.",
                "evidencia": "tienes más actitudes de hombre blanco, prácticamente ya valiste mergas para el ligue",
                "regla_disparada": "Regla 2 (4.2): desinformación victimista + taxonomías de dominación.",
                "marcadores_detectados": [
                    "actitudes de hombre blanco",
                    "valiste mergas para el ligue",
                ],
            },
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": "Doble estándar implícito: las mujeres son evaluadoras que rechazan/valoran al varón por sus actitudes.",
                "evidencia": "prácticamente ya valiste mergas para el ligue",
                "regla_disparada": "Regla 3 (1.3): doble estándar moral y desvalorización.",
                "marcadores_detectados": ["valiste mergas"],
            },
        ],
    },
    26: {  # ed489d3558a69eef
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.4 (ar_id=26): multi incompleta. 'aliade' + 'f3m1 nizta' son DOS marcadores Cat. 4.3 independientes (uno por cada colectivo atacado).",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "Doble troleo: 'aliade' (aliado emasculado) + 'f3m1 nizta' (feminazi). Dos entradas Cat. 4.3 independientes.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "'aliade' = aliado emasculado; jerga de emasculación manosférica contra varones que apoyan el feminismo.",
                "evidencia": "Para el aliade",
                "regla_disparada": "Regla 2 (4.3): jerga de emasculación y subculturas masculinistas.",
                "marcadores_detectados": ["aliade"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "'f3m1 nizta' = feminazi (leetspeak); troleo de género contra activistas feministas.",
                "evidencia": "y la f3m1 nizta",
                "regla_disparada": "Regla 3 (4.3): troleo de género y el mito Feminazi.",
                "marcadores_detectados": ["f3m1 nizta"],
            },
        ],
    },
    27: {"verdict": "DE ACUERDO", "reason": "§2.4: 'Edu Cordeiro' — nombre propio."},
    28: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Es chistoso por qué es cierto...' — sin marcador VDG.",
    },
    29: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'jajajaja' aislado; sugerencia: precisar como 5.3 si contexto apunta a crítica.",
    },
    30: {"verdict": "DE ACUERDO", "reason": "§2.4: 'Un clasico'."},
    31: {"verdict": "DE ACUERDO", "reason": "§2.4: sin texto."},
    32: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Los escenarios que tienen que crear en IA...' — sin referente femenino-objetivado.",
    },
    33: {"verdict": "DE ACUERDO", "reason": "§2.6: 'Gracias por tus consejos xd'."},
    34: {"verdict": "DE ACUERDO", "reason": "§2.6: 'Franky Velazquez' — nombre propio."},
    35: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Autor Mentalidad 1% Revisa el manual aquí...' — auto-promoción.",
    },
    36: {  # d09fd0fa741fd562
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.4 (ar_id=36): FALSO POSITIVO Cat. 1.1. Sin imperativo doméstico; el hablante agradece a las mujeres, no prescribe roles.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 1.1: 'ellas son las que me dan cariño y pagan todo' aparece en contexto de alivio del hablante varón, no de prescripción. Sin marcador de imperativo doméstico (a lavar / a limpiar / cuidar de sus hijos). Sugerencia primaria: ninguna. Cat. 4.2 baja sería admisible si se quiere registrar el esencialismo.",
        "corrected_labels": [],
    },
    37: {
        "verdict": "DE ACUERDO",
        "reason": "§2.3: 'Es un pendejo pero así las buscan xD...' — coloquial-crítico sin marcador.",
    },
    38: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Jajajajajaja, noo, ni madres!! La mía les cobraba.' + exclusion_label=VIOLENCIA_COMUN.",
    },
    39: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Todos los días sale un pendejo a la calle...' — sin referente femenino. Reclasificación correcta del falso positivo de la auditoría 2026-07-12.",
    },
    40: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Hola.correto.excelente.mensaje...' sin marcador VDG.",
    },
    41: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Victor Adrian Zambrano Tamayo GIPHY' — nombre propio.",
    },
    42: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Por eso un cafesito' + exclusion_label=VIOLENCIA_COMUN.",
    },
    43: {  # 9e768e369f38ae29
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.5 (ar_id=43): FALSO POSITIVO Cat. 1.3. La primera parte matiza el comentario previo; la segunda describe la dinámica del propio varón sin desvalorización genérica del colectivo femenino (sin marcadores Cat. 1 Regla 3: 'locas', 'ridículas', 'no se dan a respetar').",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 1.3: respuesta matizada del varón de 67 años. No aparece ningún adjetivo descalificador genérico sobre mujeres. 'si no colaboras con nada no se te acerca ninguna' describe la dinámica transaccional sin desvalorización colectiva.",
        "corrected_labels": [],
    },
    44: {"verdict": "DE ACUERDO", "reason": "§2.5: 'Jajajaja muy cierto suele suceder'."},
    45: {  # 6ac63c8dd7b3dbcd
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.5 (ar_id=45): corregir sub-dim Cat. 4. La cuarta etiqueta era 4.3 (troleo) y debe ser 4.2 (desinformación victimista + esencialismo mujeres-mercancía). No aparece jerga feminazi/aliade ni caricatura del feminismo.",
        "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "corrected_dimension": "1.3",
        "corrected_justificacion": "Doble estándar moral (1.3) + slut-shaming (2.3) + desinformación victimista (4.2) + humor hostil (5.2). Reemplaza 4.3 por 4.2: la división esencialista mujeres-mercancía no es troleo.",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "media",
                "justificacion": "Doble estándar moral y desvalorización colectiva: 'como son todas las mujeres', 'rompe las pelotas, se quejan, te piden', 'un negocio es un negocio', 'la más cara es una esposa'.",
                "evidencia": "como son todas las mujeres / rompe las pelotas, se quejan, te piden / un negocio es un negocio / la más cara es una esposa",
                "regla_disparada": "Regla 3 (1.3): doble estándar moral y desvalorización.",
                "marcadores_detectados": [
                    "como son todas las mujeres",
                    "rompe las pelotas",
                    "un negocio es un negocio",
                    "la más cara es una esposa",
                ],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "media",
                "justificacion": "Slut-shaming / doble estándar sexual: juicio moral a la sexualidad femenina.",
                "evidencia": "siempre están enculada o les duele la cabeza / una vieja más fea",
                "regla_disparada": "Regla 3 (2.3): doble estándar moral y castigo a la sexualidad.",
                "marcadores_detectados": ["enculada", "les duele la cabeza", "vieja más fea"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "Desinformación victimista + esencialismo femenino como mercancía: división esencialista mujeres-mercancía, varón como 'comprador' engañado.",
                "evidencia": "un negocio es un negocio / Nada es gratis en esta vida algo tiene que costar / la más cara es una esposa",
                "regla_disparada": "Regla 1 (4.2): esencialismo y desinformación de género.",
                "marcadores_detectados": [
                    "un negocio es un negocio",
                    "Nada es gratis",
                    "la más cara es una esposa",
                ],
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.2",
                "severidad": "media",
                "justificacion": "Humor hostil: múltiples 'jajaja' modulan toda la intervención como una broma misógina.",
                "evidencia": "jajaja si no colaboras con nada / jajajaja jajajaja",
                "regla_disparada": "Regla 2 (5.2): humor hostil que enmascara agresión.",
                "marcadores_detectados": ["jajaja"],
            },
        ],
    },
    46: {"verdict": "DE ACUERDO", "reason": "§2.5: 'he visto muchas personas así también'."},
    47: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Los ruquitos que no le hallan a la tecnología' — sin referente femenino.",
    },
    48: {"verdict": "DE ACUERDO", "reason": "§2.5: 'Manuel Lazo 13 h'."},
    49: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Tienen que trabajar' — sin referente femenino explícito.",
    },
    50: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Desarrollar caracter y personalidad lo mejor posible'.",
    },
    51: {"verdict": "DE ACUERDO", "reason": "§2.5: 'No se.'"},
    52: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Alguna gente se gusta poner...' sin referente femenino.",
    },
    53: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'No debes amar por completo ni confiar en una mujer' → Regla 3 / 1.3.",
    },
    54: {"verdict": "DE ACUERDO", "reason": "§2.5: 'Honestidad, responsabilidad y respeto...'"},
    55: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Que solo un poco de codicia, lujuria e ira...'",
    },
    56: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'Nadie vendrá a salvarte...' — reclasificación correcta del falso positivo 1.2 de la auditoría 2026-07-12.",
    },
    57: {"verdict": "DE ACUERDO", "reason": "§2.5: 'Santa clos no existe'."},
    58: {
        "verdict": "DE ACUERDO",
        "reason": "§2.5: 'La gran mayoría de mujeres solo está contigo por conveniencia' → Regla 3 / 1.3 + 4.2.",
    },
    59: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe' → 1.1 (Regla 1 imperativo doméstico) + 4.2.",
    },
    60: {  # 7e6c8887fea366de
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.4 (ar_id=60): multi incompleta. Faltó la etiqueta Cat. 5.2 ('jaja' como humor hostil) además de 4.3 + 6.1 ya asignados.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "Troleo de género (4.3) + deslegitimación ideológica del feminismo (6.1) + humor hostil (5.2) — tres cargas en una sola emisión.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "baja",
                "justificacion": "Troleo de género: minimización del colectivo feminista como táctica de burla memética.",
                "evidencia": "No que a las feministas no les hacen caso",
                "regla_disparada": "Regla 3 (4.3): troleo de género y el mito Feminazi.",
                "marcadores_detectados": ["las feministas", "no les hacen caso"],
            },
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.1",
                "severidad": "baja",
                "justificacion": "Deslegitimación ideológica: sugiere que los argumentos feministas son irrelevantes.",
                "evidencia": "No que a las feministas no les hacen caso",
                "regla_disparada": "Regla 1 (6.1): deslegitimación ideológica y encasillamiento extremista.",
                "marcadores_detectados": ["no les hacen caso"],
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.2",
                "severidad": "baja",
                "justificacion": "Humor hostil: 'jaja' final que enmascara la agresión.",
                "evidencia": "jaja",
                "regla_disparada": "Regla 2 (5.2): humor hostil que enmascara agresión.",
                "marcadores_detectados": ["jaja"],
            },
        ],
    },
    61: {  # b7aff28bc7d3c1de
        "verdict": "RECATEGORIZAR",
        "reason": "Auditor 2026-07-13 §2.4 (ar_id=61): FALSO POSITIVO Cat. 2.1. 'con mujer o sin mujer la paja no falta' no cosifica ni hipersexualiza; la mención femenina aparece como paréntesis, no como objeto. Sin adjetivo cosificador.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 2.1: el texto es coloquial vulgar sobre masturbación. No aparecen marcadores cosificadores del glosario Cat. 2 (putita obediente, packs, enseñando las nalgas, naquitas, buena). La presencia/ausencia de 'mujer' es un paréntesis, no cosificación.",
        "corrected_labels": [],
    },
    62: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Creo que Eva se golpeó la cabeza al momento de que Dios la creo' → 1.2 (inferioridad cognitiva) + 6.1 (esencialismo religioso).",
    },
    63: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse' → 1.3 (Regla 3 inversión de responsabilidad) + 4.2.",
    },
    64: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Ahí vienen los chicos buenos a proyectarse jajaja...' → 5.2 (humor hostil hacia varones).",
    },
    65: {"verdict": "DE ACUERDO", "reason": "§2.4: 'Se lo está diciendo al tipo.'"},
    66: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Eso es por qué el man no tiene energía masculina' → 4.1 (léxico 'energía masculina').",
    },
    67: {"verdict": "DE ACUERDO", "reason": "§2.4: 'oelo morado mas encima,,, noo gracias !'"},
    68: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Los hombres tienen que usar IA para únicamente representar escenarios imaginarios' — crítica al varón, no VDG.",
    },
    69: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'a lo que se ve ellas tienen más que el' — texto truncado, sin contexto completo.",
    },
    70: {"verdict": "DE ACUERDO", "reason": "§2.5: 'Alberto D. Díaz González' — nombre propio."},
    71: {
        "verdict": "DE ACUERDO",
        "reason": "§2.4: 'Ya saben muchachos si ven que alguien las agrade, asi la estén matando es mejor no meterse...' → 3.3 (apología al feminicidio) + 6.3 (tergiversación) + 5.2 (jaja). Reclasificación correcta del error grave 3.1 de la auditoría 2026-07-12.",
    },
    72: {"verdict": "DE ACUERDO", "reason": "§2.6: 'yo veo puros wasones jajajajaa'."},
    73: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'El patriarcado me da patriarcado??' → 6.1 (deslegitimación ideológica).",
    },
    74: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Ni la IA entiende el feminismo' — broma genérica sin marcador VDG.",
    },
    75: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Pues en los carteles veo cosas logicas, Quieren a una mujer controlada?...' → 5.3 (defensa feminista). Reclasificación correcta del falso positivo 2.1+1.2 de la auditoría 2026-07-12.",
    },
    76: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos.' → 5.3 (reapropiación positiva).",
    },
    77: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Suban a ponerle al jale acá las esperamos ....'",
    },
    78: {
        "verdict": "DE ACUERDO",
        "reason": "§2.6: 'Usando IA porque no puede encontrar un imagen real: Conservadores enojándose por cosas imaginarias'.",
    },
}


def main() -> None:
    db = get_database(DB_URL)

    with db.get_session() as session:
        reviewer_row = session.execute(
            text("SELECT id, username FROM users WHERE username = :u"),
            {"u": REVIEWER_USERNAME},
        ).first()
        if not reviewer_row:
            print(f"ERROR: usuario '{REVIEWER_USERNAME}' no existe en la tabla users.")
            return
        reviewer_id, reviewer_un = reviewer_row
        print(f"Reviewer: id={reviewer_id}, username={reviewer_un}")

        results = session.execute(
            text("""
            SELECT ar.id, ar.content_type, ar.content_id, ar.categoria, ar.dimension,
                   ar.severidad,
                   CASE WHEN ar.content_type = 'post' THEN p.text ELSE c.text END as texto
            FROM analysis_results ar
            LEFT JOIN posts p ON ar.post_id = p.id
            LEFT JOIN comments c ON ar.comment_id = c.id
            ORDER BY ar.id
        """)
        ).fetchall()

        rows_data: list = list(results)
        print(f"Resultados cargados: {len(rows_data)}")

    counts = {"agree": 0, "recategorize": 0, "missing": 0}
    inserted_ids: list[int] = []
    for r in rows_data:
        ar_id, content_type, content_id, ai_cat, ai_dim, ai_sev, texto = r
        verdict_entry = AUDIT_VERDICTS.get(ar_id)
        if verdict_entry is None:
            print(f"  WARN: ar_id={ar_id} ({content_id}) sin veredicto en la tabla.")
            counts["missing"] += 1
            continue

        verdict = verdict_entry["verdict"]
        reason = verdict_entry["reason"]
        text_snapshot = (texto or "")[:2000]

        if verdict == "DE ACUERDO":
            counts["agree"] += 1
            feedback_data = {
                "analysis_result_id": ar_id,
                "content_type": content_type,
                "content_id": content_id,
                "text_snapshot": text_snapshot,
                "agrees": "true",
                "reviewer": REVIEWER_FULL_NAME,
                "reviewer_user_id": reviewer_id,
                "reviewer_username": reviewer_un,
                "reason": reason,
            }
        elif verdict == "RECATEGORIZAR":
            counts["recategorize"] += 1
            feedback_data = {
                "analysis_result_id": ar_id,
                "content_type": content_type,
                "content_id": content_id,
                "text_snapshot": text_snapshot,
                "agrees": "false",
                "reviewer": REVIEWER_FULL_NAME,
                "reviewer_user_id": reviewer_id,
                "reviewer_username": reviewer_un,
                "reason": reason,
                "corrected_categoria": verdict_entry.get("corrected_categoria"),
                "corrected_dimension": verdict_entry.get("corrected_dimension"),
                "corrected_justificacion": verdict_entry.get("corrected_justificacion"),
                "corrected_labels": verdict_entry.get("corrected_labels", []),
            }
        else:
            print(f"  WARN: ar_id={ar_id} veredicto desconocido '{verdict}'.")
            continue

        fb_id = db.save_feedback(feedback_data)
        inserted_ids.append(fb_id)

    print("\n=== Resumen ===")
    print(f"DE ACUERDO:           {counts['agree']}")
    print(f"RECATEGORIZAR:        {counts['recategorize']}")
    print(f"Sin veredicto (WARN): {counts['missing']}")
    print(f"Filas feedback (ID):  {len(inserted_ids)}")
    print(f"Doc auditoría:        {AUDIT_DOC}")

    # Verificación post-inserción
    total_feedback = len(db.list_feedback())
    total_disagree = len(db.list_feedback(only_disagreements=True))
    print(f"\n[verificación] analysis_feedback total: {total_feedback}")
    print(f"[verificación] analysis_feedback disagrees: {total_disagree}")

    pending_index = len(db.list_feedback(only_pending_index=True))
    print(f"[verificación] pending ChromaDB index: {pending_index}")


if __name__ == "__main__":
    main()
