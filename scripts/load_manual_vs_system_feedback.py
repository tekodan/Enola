"""Carga el feedback de validación humana desde la comparación
``docs/clasificacion-manua-vs-sistema.md``.

Para cada una de las 57 unidades de análisis del manual:

- Si el veredicto es **ACUERDO** (35 casos): se inserta feedback con
  ``agrees='true'`` (sin override).
- Si el veredicto es **PARCIAL** (6 casos) o **DESACUERDO** (16 casos):
  se inserta feedback con ``agrees='false'`` y los overrides de la
  taxonomía manual (categoría, dimensión, justificación, etiquetas).

Las etiquetas corregidas se almacenan también en la tabla side
``analysis_feedback_labels`` (multi-label). El campo flat
``corrected_categoria/dimension`` refleja la etiqueta primaria
(severidad más alta) según el manual.

Ejecutar con:
    source .venv/bin/activate && python scripts/load_manual_vs_system_feedback.py

Resultado esperado:
- 57 filas nuevas en ``analysis_feedback``
- ~22 filas nuevas en ``analysis_feedback_labels`` (sólo para los 22
  no-acuerdos)
"""

from __future__ import annotations

from sqlalchemy import text

from src.storage.database import get_database

DB_URL = "sqlite:///data/tfm.db"
REVIEWER_USERNAME = "auditor-tfm"
REVIEWER_FULL_NAME = "Auditor TFM (manual vs sistema 2026-07-15)"
AUDIT_DOC = "docs/clasificacion-manua-vs-sistema.md"


# ---------------------------------------------------------------------------
# Tabla de veredictos
# Cada entrada: ar_id -> dict(verdict, reason, corrected_labels, severity)
# veredictos: "DE ACUERDO" | "RECATEGORIZAR"
# corrected_labels: lista de LabelAssignment (manual / ground truth)
# ---------------------------------------------------------------------------
FEEDBACK: dict[int, dict] = {
    # ---------- POSTS ----------
    # Unidad 51: 0f3e884a8a124fd1_p0 — ar_id=1
    1: {
        "verdict": "RECATEGORIZAR",
        "reason": "U51 §auditoría manual: 'Confiar en la lealtad de una muj3r moderna...' — Manual: 2.3 + 4.1 + 4.2. Sistema disparó 1.3 + 2.3 + 4.2 + 1.1 (parcialmente acertó 2.3 y 4.2; faltó 4.1 e introdujo 1.3/1.1 erróneos). Override multi-label según manual.",
        "corrected_categoria": "VDG_COSIFICACION_SLUTSHAMING",
        "corrected_dimension": "2.3",
        "corrected_justificacion": "Doble estándar sexual + slut-shaming (2.3): el agresor castiga moralmente 'acost4rs3 con var1os' como 'degenerac18n' carente de 'vergüenza' — autonomía sexual femenina estigmatizada. Complementa con 4.1 (manosfera: determinismo biológico 'como esperar que un león se vuelva vegetariano') y 4.2 (ataque a 'lógica feminista absurd4' como deslegitimación del feminismo).",
        "corrected_labels": [
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "media",
                "justificacion": "Slut-shaming / doble estándar sexual: 'acost4rs3 con var1os' como 'degenerac18n' y 'no tener vergüenza' — castigo moral a la autonomía sexual femenina.",
                "evidencia": "acost4rs3 con var1os y no tener vergüenza / Las mvjeres modernas crecen en un entorno que incentiva la degenerac18n",
                "regla_disparada": "Regla 3 (2.3): doble estándar moral y castigo a la sexualidad.",
                "marcadores_detectados": [
                    "degenerac18n",
                    "acost4rs3 con var1os",
                    "no tener vergüenza",
                ],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Determinismo biológico / subcultura masculinista: analogía 'como esperar que un león se vuelva vegetariano' para argumentar que las mujeres modernas son incapaces de lealtad por naturaleza.",
                "evidencia": "Confiar en la lealtad de una muj3r moderna es como esperar que un león se vuelva vegetariano",
                "regla_disparada": "Regla 1 (4.1): esencialismo biológico y deshumanización.",
                "marcadores_detectados": ["león vegetariano", "determinismo biológico"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "Victimismo hegemónico / deslegitimación del feminismo: 'alguna lógica feminista absurd4' caricaturiza el movimiento igualitario como irracional.",
                "evidencia": "Para ellas, engañar no es malo porque pueden justificarlo con alguna lógica feminista absurd4",
                "regla_disparada": "Regla 2 (4.2): desinformación victimista y ataque ideológico.",
                "marcadores_detectados": ["lógica feminista absurd4"],
            },
        ],
    },
    # Unidad 52: 0f3e884a8a124fd1_p1 — ar_id=2
    2: {
        "verdict": "DE ACUERDO",
        "reason": "U52 §auditoría manual: 'La forma más fácil de hacer las cosas es seguir una lista de tareas...' — consejo de productividad, sin marcador VDG. Sistema ninguna. ✓",
    },
    # Unidad 53: 0f3e884a8a124fd1_p2 — ar_id=3
    3: {
        "verdict": "RECATEGORIZAR",
        "reason": "U53 §auditoría manual: 'El beta se entera o sospecha que ella está hablando con otro...' — Manual: 1.1 + 2.3 + 4.1 + 4.3 (todo el aparato Alpha/Beta). Sistema disparó 'ninguna' + VIOLENCIA_COMUN — perdió TODA la narrativa manosférica. Error grave: 'beta' es jerga endémica documentada en glosario 4.3.",
        "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "corrected_dimension": "1.1",
        "corrected_justificacion": "Aparato completo Alpha vs. Beta: (1.1) asume por defecto la falta de lealtad de la mujer; (2.3) slut-shaming al estigmatizar su autonomía afectiva ('hablando con otro / viéndose con alguien más'); (4.1) determinismo biológico + manifiesto manosférico; (4.3) troleo/emasculación del varón 'beta' que permanece en la relación.",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": "Roles tradicionales / asume por defecto la falta de lealtad: la mujer es 'alguien que claramente lo está traicionando'.",
                "evidencia": "alguien que claramente lo está traicionando / ella sigue haciendo lo que le da la gana",
                "regla_disparada": "Regla 1 (1.1): roles tradicionales y deslealtad asumida.",
                "marcadores_detectados": [
                    "claramente lo está traicionando",
                    "lo que le da la gana",
                ],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "media",
                "justificacion": "Slut-shaming: juicio punitivo sobre la autonomía afectiva/sexual de la mujer por 'hablando con otro' o 'viéndose con alguien más'.",
                "evidencia": "hablando con otro, que se está viendo con alguien más o que directamente lo está engañando",
                "regla_disparada": "Regla 3 (2.3): doble estándar sexual.",
                "marcadores_detectados": [
                    "hablando con otro",
                    "viéndose con alguien más",
                    "engañando",
                ],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Manifiesto Alpha vs. Beta: 'El del 1% no se queda' / 'lo que le da la gana' — dinámica de control implacable y deshumanización ('despojándolas de cualquier humanidad o capacidad de lealtad').",
                "evidencia": "El del 1% no se queda / El beta sigue invirtiendo tiempo, energía y recursos en alguien",
                "regla_disparada": "Regla 2 (4.1): subcultura masculinista y jerarquía Alpha/Beta.",
                "marcadores_detectados": ["El del 1%", "El beta", "El beta sigue invirtiendo"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo / emasculación del varón 'beta' que permanece en la relación — neologismo humillante jerga manosférica.",
                "evidencia": "El beta / El beta se convence de que si no digo nada... / perdió todo el respeto y la dignidad",
                "regla_disparada": "Regla 2 (4.3): emasculación vía 'beta'.",
                "marcadores_detectados": ["El beta", "perdió todo el respeto"],
            },
        ],
    },
    # Unidad 54: dc8ae80a3ae35f92 (post) — ar_id=4
    4: {
        "verdict": "RECATEGORIZAR",
        "reason": "U54 §auditoría manual: 'Ella te vende la imagen de la chica buena...' — Manual: 1.1 + 2.3 + 4.1 + 4.3. Sistema disparó 2.3 + 4.3 + 1.3 — parcial: acertó 2.3 y 4.3; faltó 1.1 y 4.1.",
        "corrected_categoria": "VDG_COSIFICACION_SLUTSHAMING",
        "corrected_dimension": "2.3",
        "corrected_justificacion": "Multi-label: (2.3) escrutinio moral brutal de la sexualidad femenina ('se la ha c8g1d8 con otros hombres', 'se la f8ll9 en el asiento trasero') + (4.1) PUA / técnicas de engaño + deshumanización + (4.3) emasculación del 'beta' + (1.1) asume deslealtad por defecto ('su decencia es solo una actuación').",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": "Roles tradicionales / asume por defecto la falta de lealtad: 'su decencia es solo una actuación'.",
                "evidencia": "Ella te vende la imagen de la chica buena, correcta / Y mientras tú esperas pacientemente... ella ya se la ha c8g1d8",
                "regla_disparada": "Regla 1 (1.1): roles tradicionales y deslealtad asumida.",
                "marcadores_detectados": ["vende la imagen", "actuación", "esperas pacientemente"],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "alta",
                "justificacion": "Slut-shaming brutal: escrutinio moral punitivo sobre la sexualidad femenina con leetspeak para evadir filtros.",
                "evidencia": "se la ha c8g1d8 con otros hombres / El que la montó en su coche y se la f8ll9 en el asiento trasero",
                "regla_disparada": "Regla 3 (2.3): doble estándar sexual + leetspeak.",
                "marcadores_detectados": ["c8g1d8", "f8ll9", "asiento trasero"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Tácticas PUA / técnicas de engaño y manipulación ('El tipo del KFC que le dijo que era empresario. Vio el juego y jugó mejor') + deshumanización ('Ella te vende la imagen').",
                "evidencia": "El tipo del KFC que le dijo que era empresario / Vio el juego y jugó mejor / Ella te vende la imagen",
                "regla_disparada": "Regla 2 (4.1): PUA y técnicas de manipulación.",
                "marcadores_detectados": ["El tipo del KFC", "Vio el juego", "vende la imagen"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo/emasculación del varón 'beta' respetuoso y paciente — jerga manosférica de castigo.",
                "evidencia": "El beta / El beta que se cree la actuación / El beta se pasa semanas o meses siendo respetuoso, paciente",
                "regla_disparada": "Regla 2 (4.3): emasculación vía 'beta'.",
                "marcadores_detectados": ["El beta", "respetuoso", "paciente"],
            },
        ],
    },
    # Unidad 55: d782af3f81de2512 (post) — ar_id=5
    5: {
        "verdict": "DE ACUERDO",
        "reason": "U55 §auditoría manual: 'DEJA DE PREOCUPARTE COMO UN GvS4N8...' — consejo de autoayuda agresivo con leetspeak. Manual: 'Libre/Común'. Sistema ninguna. ✓",
    },
    # Unidad 56: b0bcbbb5eb375a41 (post) — ar_id=6
    6: {
        "verdict": "RECATEGORIZAR",
        "reason": "U56 §auditoría manual: post b0bcbbb5eb375a41 (con varios comentarios violentos: U14, U15, U16, U33, U36, U37, U38, U40, U41, U42, U43). Manual sobre el post en sí: 1.1 + 2.3 + 4.1 + 4.3. Sistema disparó 2.3 + 4.3 — parcial: acertó 2.3 y 4.3; faltó 1.1 y 4.1.",
        "corrected_categoria": "VDG_COSIFICACION_SLUTSHAMING",
        "corrected_dimension": "2.3",
        "corrected_justificacion": "Post público con alta carga manosférica. Multi-label: (1.1) roles tradicionales (U33: 'a la mujer es quien le toca cocinar y criar al bebe'); (2.3) slut-shaming (U16: 'f3m1 nizta', U40: 'energía masculina'); (4.1) determinismo biológico / masculinidad hegemónica; (4.3) jerga 'beta' / 'aliade' / 'deconstruide'.",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": "Roles tradicionales y de sumisión — U33: 'No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe'.",
                "evidencia": "a la mujer es quien le toca cocinar y criar al bebe",
                "regla_disparada": "Regla 1 (1.1): roles tradicionales e imperativo doméstico.",
                "marcadores_detectados": ["cocinar y criar al bebe", "el papel de mujer"],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "media",
                "justificacion": "Slut-shaming / doble estándar sexual — U16: 'f3m1 nizta' ataca la autonomía sexual de las feministas.",
                "evidencia": "Para el aliade y la f3m1 nizta",
                "regla_disparada": "Regla 3 (2.3): doble estándar + leetspeak.",
                "marcadores_detectados": ["f3m1 nizta"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Masculinidad hegemónica / jerarquía de dominación — U37: 'Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse'.",
                "evidencia": "Les gusta el desafío, la aventura Y la imagen de bandido",
                "regla_disparada": "Regla 2 (4.1): masculinidad hegemónica y determinismo biológico.",
                "marcadores_detectados": ["imagen de bandido", "para después quejarse"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo/emasculación — U14: 'hombre deconstruide vs malandro'; U16: 'aliade'; U38: 'chicos buenos'; U40: 'energía masculina'.",
                "evidencia": "hombre deconstruide vs malandro / Para el aliade / chicos buenos a proyectarse / no tiene energía masculina",
                "regla_disparada": "Regla 2 (4.3): emasculación jerga manosférica.",
                "marcadores_detectados": [
                    "deconstruide",
                    "aliade",
                    "chicos buenos",
                    "energía masculina",
                ],
            },
        ],
    },
    # Unidad 57: 3741fe9979b310c6 (post) — ar_id=7
    7: {
        "verdict": "DE ACUERDO",
        "reason": "U57 §auditoría manual: post 3741fe9979b310c6 (sobre protesta feminista). Manual 'Libre' a nivel post; contiene un comentario grave (U48: banalización del feminicidio). Sistema ninguna. ✓",
    },
    # ---------- COMENTARIOS ----------
    # Unidad 1: f787d814b5a47750 — ar_id=9
    9: {
        "verdict": "DE ACUERDO",
        "reason": "U1 §auditoría manual: 'Ahora resulta que los hombres no engañan' — sin referente femenino-objetivado. Sistema ninguna. ✓",
    },
    # Unidad 2: 449e8848a2128407 — ar_id=12
    12: {
        "verdict": "DE ACUERDO",
        "reason": "U2 §auditoría manual: 'Los ruquitos que no le hallan a la tecnología' — sin referente femenino. Sistema ninguna. ✓",
    },
    # Unidad 3: d145c2f9deb89f18 — ar_id=14
    14: {
        "verdict": "DE ACUERDO",
        "reason": "U3 §auditoría manual: 'Desarrollar caracter y personalidad lo mejor posible' — sin referente femenino. Sistema ninguna. ✓",
    },
    # Unidad 4: cbd632532f03b1fe — ar_id=15
    15: {
        "verdict": "DE ACUERDO",
        "reason": "U4 §auditoría manual: 'No se.' — muletilla. Sistema ninguna. ✓",
    },
    # Unidad 5: d6352dd38d58eb51 — ar_id=16
    16: {
        "verdict": "DE ACUERDO",
        "reason": "U5 §auditoría manual: 'Alguna gente se gusta poner en una posición importante...' — queja genérica sin referente femenino-objetivado. Sistema ninguna. ✓",
    },
    # Unidad 6: 2effd62b3d4cbac5 — ar_id=17
    17: {
        "verdict": "RECATEGORIZAR",
        "reason": "U6 §auditoría manual: 'No debes amar por completo ni confiar en una mujer' — Manual: 1.1 (Roles tradicionales, asume deslealtad por defecto) + 4.1 (Manosfera, MGTOW-style 'renuncia a relacionarse con mujeres'). Sistema disparó 1.3 (Castigo moral) — categoría operativa 1 ok pero dimensión incorrecta; faltó categoría 4.",
        "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "corrected_dimension": "1.1",
        "corrected_justificacion": "(1.1) Roles tradicionales / asume por defecto la falta de lealtad: 'No debes amar por completo ni confiar en una mujer'. (4.1) Táctica masculinista de aislamiento y distanciamiento emocional, equivalente MGTOW.",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": "Roles tradicionales y de sumisión: asume dogmáticamente que la mujer es inherentemente traicionera, generando desconfianza sobre ella bajo la premisa de falta de lealtad por defecto.",
                "evidencia": "No debes amar por completo ni confiar en una mujer",
                "regla_disparada": "Regla 1 (1.1): roles tradicionales + asume deslealtad.",
                "marcadores_detectados": ["ni confiar en una mujer", "no debes amar por completo"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Subcultura masculinista / MGTOW-style: táctica de aislamiento y distanciamiento emocional, negando la capacidad de lealtad femenina.",
                "evidencia": "No debes amar por completo ni confiar en una mujer",
                "regla_disparada": "Regla 2 (4.1): MGTOW, aislamiento emocional.",
                "marcadores_detectados": ["no debes amar por completo"],
            },
        ],
    },
    # Unidad 7: cc5db2110f4ab014 — ar_id=18
    18: {
        "verdict": "DE ACUERDO",
        "reason": "U7 §auditoría manual: 'Honestidad, responsabilidad y respeto...' — mensaje positivo de autoayuda. Sistema ninguna. ✓",
    },
    # Unidad 8: 7bbc336cbd9531f4 — ar_id=19
    19: {
        "verdict": "DE ACUERDO",
        "reason": "U8 §auditoría manual: 'Que solo un poco de codicia, lujuria e ira...' — aforismo genérico sin referente femenino. Sistema ninguna. ✓",
    },
    # Unidad 9: a1478d1dd8727dd4 — ar_id=20
    20: {
        "verdict": "DE ACUERDO",
        "reason": "U9 §auditoría manual: 'Nadie vendrá a salvarte...' — frase de resiliencia sin marcador VDG. Sistema ninguna. ✓",
    },
    # Unidad 10: ff3b966d76f7f46c — ar_id=21
    21: {
        "verdict": "DE ACUERDO",
        "reason": "U10 §auditoría manual: 'Santa clos no existe' — ironía neutral sin sesgo de género. Sistema ninguna. ✓",
    },
    # Unidad 11: 6983ada882e8a729 — ar_id=22
    22: {
        "verdict": "RECATEGORIZAR",
        "reason": "U11 §auditoría manual: 'La gran mayoría de mujeres solo está contigo por conveniencia' — Manual: 1.1 (Roles tradicionales, asume deslealtad) + 4.1 (Manosfera, hipergamia). Sistema disparó 2.3 (Slut-shaming) + 1.3 (Castigo moral) — categorías distintas, ningún match con manual.",
        "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "corrected_dimension": "1.1",
        "corrected_justificacion": "(1.1) Roles tradicionales / asume por defecto la falta de lealtad ('solo por conveniencia' como definición). (4.1) Hipergamia manosférica / deshumanización ('organismos calculadores que seleccionan a los hombres puramente por interés material o genético').",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": "Roles tradicionales y de sumisión: la mujer etiquetada como 'interesada' desde una perspectiva tradicional que exige fidelidad — asume deslealtad por defecto.",
                "evidencia": "La gran mayoría de mujeres solo está contigo por conveniencia",
                "regla_disparada": "Regla 1 (1.1): roles tradicionales + asume deslealtad.",
                "marcadores_detectados": ["por conveniencia", "interesada"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Manosfera / mito de la hipergamia: reduce a la mujer a 'ente calculador movido exclusivamente por el interés económico o material'.",
                "evidencia": "La gran mayoría de mujeres solo está contigo por conveniencia",
                "regla_disparada": "Regla 2 (4.1): hipergamia y esencialismo biológico.",
                "marcadores_detectados": ["solo por conveniencia"],
            },
        ],
    },
    # Unidad 12: f0d0660ea97b4f6f — ar_id=23
    23: {
        "verdict": "DE ACUERDO",
        "reason": "U12 §auditoría manual: 'Primero el trabajo y el dinero, es lo más importante...' — consejo genérico sin carga de género. Sistema ninguna. ✓",
    },
    # Unidad 13: e2cd4ab277182465 — ar_id=24
    24: {
        "verdict": "DE ACUERDO",
        "reason": "U13 §auditoría manual: 'Y así hay muchas...' — muletilla ambigua. Sistema ninguna. ✓",
    },
    # Unidad 14: fcd0b54ed754a540 — ar_id=25
    25: {
        "verdict": "RECATEGORIZAR",
        "reason": "U14 §auditoría manual: 'claro claro no se trata de música, se trata de hombre deconstruide vs malandro' — Manual: 4.3 (Trolleo/Emasculación). Falso Negativo CRÍTICO: el neologismo 'deconstruide' es jerga manosférica documentada (equivalente de 'aliade'). Sistema disparó 'ninguna'.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "Troleo / emasculación: 'deconstruide' es variación sarcástica de 'deconstruido'/'aliade' para ridiculizar al varón que se aparta del pacto patriarcal. Al contrastarlo con 'malandro' opera como troleo táctico para castigar la disidencia masculina.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo/emasculación vía neologismo 'deconstruide' (variación sarcástica de 'deconstruido'/'aliade') dirigido al varón que se aparta del modelo hegemónico.",
                "evidencia": "se trata de hombre deconstruide vs malandro",
                "regla_disparada": "Regla 2 (4.3): jerga de emasculación manosférica.",
                "marcadores_detectados": ["deconstruide", "malandro"],
            },
        ],
    },
    # Unidad 15: 2020cf0150b86856 — ar_id=26
    26: {
        "verdict": "RECATEGORIZAR",
        "reason": "U15 §auditoría manual: 'En mi experiencia si eres mestizo café con leche...' — Manual: VIOLENCIA_COMUN (racismo hacia hombres mestizos, sin sesgo de género). Falso Positivo de criterio: sistema disparó SAFEGUARD 6.1 (Micromachismos) — no aplica ni como subdim de cat 6.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo. El contenido es 'violencia genérica o común' (racismo hacia hombres mestizos por color de piel), no violencia de género. La jerarquía 'actitudes de hombre blanco' no involucra sesgo de género. Sugerencia primaria: ninguna (con etiqueta de auditoría VIOLENCIA_COMUN si el campo existiera en analysis_feedback).",
        "corrected_labels": [],
    },
    # Unidad 16: ed489d3558a69eef — ar_id=27
    27: {
        "verdict": "RECATEGORIZAR",
        "reason": "U16 §auditoría manual: 'Para el aliade y la f3m1 nizta' — Manual: 4.2 (Victimismo) + 4.3 (Trolleo). Sistema disparó 4.3 + 4.3 (parcial: acertó 4.3, faltó 4.2). Multi-label parcial.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "(4.3) Doble troleo: 'aliade' (varón emasculado) + 'f3m1 nizta' (feminazi leetspeak). (4.2) Ataque simultáneo al varón aliado y al movimiento feminista — caricaturización e invalidación con 'f3m1 nizta'.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo/emasculación vía 'aliade' (varón emasculado por defender derechos de mujeres).",
                "evidencia": "Para el aliade",
                "regla_disparada": "Regla 2 (4.3): emasculación jerga 'aliade'.",
                "marcadores_detectados": ["aliade"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "Victimismo / deslegitimación del feminismo: 'f3m1 nizta' = feminazi, caricatura e invalidación del movimiento igualitario.",
                "evidencia": "y la f3m1 nizta",
                "regla_disparada": "Regla 2 (4.2): deslegitimación ideológica feminazi.",
                "marcadores_detectados": ["f3m1 nizta"],
            },
        ],
    },
    # Unidad 17: d00e75474ff087a6 — ar_id=29
    29: {
        "verdict": "DE ACUERDO",
        "reason": "U17 §auditoría manual: 'Es chistoso por qué es cierto...' — risa genérica sin carga de género. Sistema ninguna. ✓",
    },
    # Unidad 18: a4305690f1e373f9 — ar_id=30
    30: {
        "verdict": "DE ACUERDO",
        "reason": "U18 §auditoría manual: 'El Chacalon jajajaja' — risa pura sin blanco de género (basura digital condicional). Sistema ninguna. ✓",
    },
    # Unidad 19: 8b70afaf7ae522f0 — ar_id=31
    31: {
        "verdict": "DE ACUERDO",
        "reason": "U19 §auditoría manual: 'Un clasico' — reacción genérica ambigua. Sistema ninguna. ✓",
    },
    # Unidad 20: 06a914582038bc43 — ar_id=33
    33: {
        "verdict": "DE ACUERDO",
        "reason": "U20 §auditoría manual: 'Los escenarios que tienen que crear en IA para sus fantasías están bien raros' — crítica al uso de IA, sin marcador VDG. Sistema ninguna. ✓",
    },
    # Unidad 21: b7d6c7e6ce7a0402 — ar_id=34
    34: {
        "verdict": "DE ACUERDO",
        "reason": "U21 §auditoría manual: 'Gracias por tus consejos xd' — agradecimiento genérico. Sistema ninguna. ✓",
    },
    # Unidad 22: ad4a9baac6f43142 — ar_id=35
    35: {
        "verdict": "DE ACUERDO",
        "reason": "U22 §auditoría manual: 'año' — monosílabo, basura digital condicional. Sistema ninguna. ✓",
    },
    # Unidad 23: d09fd0fa741fd562 — ar_id=37
    37: {
        "verdict": "DE ACUERDO",
        "reason": "U23 §auditoría manual: 'no te go ese problema por que ellas son las que me dan cariño y pagan todo' — sin marcador VDG (alivio del hablante varón). Sistema ninguna. ✓",
    },
    # Unidad 24: 956858f99fe0f7fe — ar_id=38
    38: {
        "verdict": "RECATEGORIZAR",
        "reason": "U24 §auditoría manual: 'Es un pendejo pero así las buscan xD...' — Manual: VIOLENCIA_COMUN (insulto 'pendejo' sin sesgo de género). Falso Positivo Severo: sistema disparó 2.3 (Slut-shaming) + 6.2 — categoriza como violencia de género algo que NO lo es.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 2.3 + 6.2. El insulto 'pendejo' va dirigido a un hombre en el contexto de una narración coloquial ('así las buscan'); no hay marcador cosificador ni slut-shaming. Sugerencia: ninguna (con etiqueta de auditoría VIOLENCIA_COMUN).",
        "corrected_labels": [],
    },
    # Unidad 25: 3dfe60c1fbf2e1a8 — ar_id=39
    39: {
        "verdict": "RECATEGORIZAR",
        "reason": "U25 §auditoría manual: 'Jajajajajaja, noo, ni madres!! La mía les cobraba.' — Manual: Libre de violencia (risa + mención de cobro monetario, sin marcador VDG). Falso Positivo: sistema disparó SAFEGUARD 6.2 (Humor hostil) sin justificación.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 6.2. 'La mía les cobraba' es referencia jocosa a una transacción económica propia; no se dirige contra mujeres ni usa sarcasmo como enmascaramiento de agresión misógina. Sin referente femenino-objetivado.",
        "corrected_labels": [],
    },
    # Unidad 26: 94a5252cf77e41e6 — ar_id=40
    40: {
        "verdict": "RECATEGORIZAR",
        "reason": "U26 §auditoría manual: 'Todos los días sale un pendejo a la calle el que lo atrape es de el' — Manual: VIOLENCIA_COMUN (refrán popular con insulto 'pendejo' sin sesgo de género). Acuerdo parcial: sistema coincide en NO violencia de género, pero faltó marca VIOLENCIA_COMUN.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Acuerdo operativo (no es violencia de género) pero faltó etiqueta de auditoría. El refrán usa 'pendejo' sin blanco femenino ni marcador de agresión sexista. Sugerencia: ninguna (con etiqueta de auditoría VIOLENCIA_COMUN).",
        "corrected_labels": [],
    },
    # Unidad 27: b9a25039be6c7770 — ar_id=41
    41: {
        "verdict": "DE ACUERDO",
        "reason": "U27 §auditoría manual: 'Hola.correto.excelente.mensaje.maestro.me.reflejo.cracias' — saludo genérico sin marcador VDG. Sistema ninguna. ✓",
    },
    # Unidad 28: c5be7323a435b26c — ar_id=43
    43: {
        "verdict": "DE ACUERDO",
        "reason": "U28 §auditoría manual: 'Por eso un cafesito' — muletilla. Sistema ninguna. ✓",
    },
    # Unidad 29: 8cd4924a57e945dc — ar_id=45
    45: {
        "verdict": "DE ACUERDO",
        "reason": "U29 §auditoría manual: 'Jajajaja muy cierto suele suceder' — risa genérica sin carga de género. Sistema ninguna. ✓",
    },
    # Unidad 30: 6ac63c8dd7b3dbcd — ar_id=46
    46: {
        "verdict": "RECATEGORIZAR",
        "reason": "U30 §auditoría manual: 'No es tan así si tenés más de años...' — Manual: 2.1 (Cosificación), 2.2 (Body-shaming), 4.1 (Manosfera), 6.2 (Humor hostil). Sistema disparó 1.3 + 2.3 + 6.2 — parcial: acertó 6.2, erró 2.1/2.2/4.1.",
        "corrected_categoria": "VDG_COSIFICACION_SLUTSHAMING",
        "corrected_dimension": "2.1",
        "corrected_justificacion": "(2.1) Cosificación/hipersexualización: 'un negocio es un negocio', 'algo tiene que costar' — la mujer reducida a mercancía de consumo masculino. (2.2) Body-shaming: 'vieja mas fea que vos'. (4.1) Hipergamia / deshumanización. (6.2) Humor hostil: 'jajaja' modula toda la intervención como broma misógina.",
        "corrected_labels": [
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.1",
                "severidad": "media",
                "justificacion": "Cosificación/hipersexualización: la mujer reducida a producto/servicio transaccional ('un negocio es un negocio', 'algo tiene que costar', 'la más cara es una esposa').",
                "evidencia": "un negocio es un negocio / Nada es gratis en esta vida algo tiene que costar / la más cara es una esposa",
                "regla_disparada": "Regla 1 (2.1): cosificación transaccional.",
                "marcadores_detectados": [
                    "un negocio es un negocio",
                    "algo tiene que costar",
                    "la más cara es una esposa",
                ],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.2",
                "severidad": "media",
                "justificacion": "Escrutinio corporal / body-shaming: 'vieja mas fea que vos... a ningún hombre le interesa'.",
                "evidencia": "andar con una vieja mas fea que vos / a ningún hombre le interesa",
                "regla_disparada": "Regla 3 (2.2): escrutinio corporal punitivo.",
                "marcadores_detectados": ["vieja mas fea", "a ningún hombre le interesa"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Manosfera / hipergamia: 'como son todas las mujeres', 'te consumen tiempo, salud y dinero' — esencialismo mujer=mercancía.",
                "evidencia": "como son todas las mujeres / te consumen tiempo, salud y dinero",
                "regla_disparada": "Regla 2 (4.1): hipergamia y esencialismo.",
                "marcadores_detectados": ["como son todas las mujeres"],
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "6.2",
                "severidad": "media",
                "justificacion": "Humor hostil: múltiples 'jajaja' modulan toda la intervención como una broma misógina.",
                "evidencia": "jajaja si no colaboras con nada / jajajaja jajajaja",
                "regla_disparada": "Regla 2 (6.2): humor hostil enmascarador.",
                "marcadores_detectados": ["jajaja", "jajajaja jajajaja"],
            },
        ],
    },
    # Unidad 31: 780240cbc59d00c2 — ar_id=47
    47: {
        "verdict": "DE ACUERDO",
        "reason": "U31 §auditoría manual: 'he visto muchas personas así también' — observación genérica. Sistema ninguna. ✓",
    },
    # Unidad 32: a4782c5cfd1d08c5 — ar_id=49
    49: {
        "verdict": "DE ACUERDO",
        "reason": "U32 §auditoría manual: 'Tienen que trabajar' — afirmación neutra. Sistema ninguna. ✓",
    },
    # Unidad 33: e355f12847ca56e7 — ar_id=50
    50: {
        "verdict": "DE ACUERDO",
        "reason": "U33 §auditoría manual: 'No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe' — Manual 1.1. Sistema disparó 1.1 / media. Match exacto. ✓",
    },
    # Unidad 34: 7e6c8887fea366de — ar_id=51
    51: {
        "verdict": "RECATEGORIZAR",
        "reason": "U34 §auditoría manual: 'No que a las feministas no les hacen caso jaja' — Manual: Libre (burla genérica, no alcanza umbral). Falso Positivo Severo: sistema disparó 5.1 (Desacreditación) + 6.2 (Humor hostil) — sobre-flageo.",
        "corrected_categoria": "ninguna",
        "corrected_dimension": None,
        "corrected_justificacion": "Falso positivo Cat. 5.1 + 6.2. 'No que a las feministas no les hacen caso jaja' es una burla genérica que no emplea adjetivos de patologización orientados a silenciarlas en el debate público, ni asume discurso de victimismo masculino para argumentar misandria. No alcanza el umbral de las métricas de clasificación.",
        "corrected_labels": [],
    },
    # Unidad 35: b7aff28bc7d3c1de — ar_id=52
    52: {
        "verdict": "DE ACUERDO",
        "reason": "U35 §auditoría manual: 'A mí me da igual con mujer o sin mujer la paja no falta' — coloquial vulgar sin cosificación. Manual 'Libre'. Sistema ninguna + VIOLENCIA_COMUN — acuerdo operativo en no-violencia de género. ✓",
    },
    # Unidad 36: d160eac77321b71d — ar_id=53
    53: {
        "verdict": "RECATEGORIZAR",
        "reason": "U36 §auditoría manual: 'Creo que Eva se golpeó la cabeza al momento de que Dios la creo' — Manual: 1.2 (Inferioridad intelectual) + 6.2 (Humor hostil). Falso Negativo: sistema disparó 'ninguna', perdiendo el marcador bíblico + el sarcasmo enmascarador.",
        "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "corrected_dimension": "1.2",
        "corrected_justificacion": "(1.2) Inferioridad intelectual asumida: Eva como representación original de la mujer con 'daño cognitivo de origen'. (6.2) Humor hostil: formato de chiste bíblico para enmascarar la agresión y eludir filtros.",
        "corrected_labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.2",
                "severidad": "media",
                "justificacion": "Incompetencia/inferioridad intelectual: asume un daño cognitivo de origen para descalificar la inteligencia femenina.",
                "evidencia": "Eva se golpeó la cabeza al momento de que Dios la creo",
                "regla_disparada": "Regla 1 (1.2): inferioridad cognitiva.",
                "marcadores_detectados": ["Eva se golpeó la cabeza"],
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "6.2",
                "severidad": "media",
                "justificacion": "Humor hostil: formato de chiste bíblico para enmascarar la agresión.",
                "evidencia": "Eva se golpeó la cabeza al momento de que Dios la creo",
                "regla_disparada": "Regla 2 (6.2): humor hostil enmascarador.",
                "marcadores_detectados": ["broma bíblica"],
            },
        ],
    },
    # Unidad 37: 5fbccd33967c9c0b — ar_id=54
    54: {
        "verdict": "RECATEGORIZAR",
        "reason": "U37 §auditoría manual: 'Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse' — Manual: 4.1 (Determinismo biológico / masculinidad hegemónica). Falso Negativo: sistema disparó 'ninguna', perdiendo el tropo misógino clásico.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.1",
        "corrected_justificacion": "Manosfera / masculinidad hegemónica: asume dogmáticamente que las mujeres están genéticamente programadas para buscar hombres tóxicos ('la imagen de bandido') + culpabilización de la víctima ('para después quejarse').",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": "Determinismo biológico / masculinidad hegemónica: 'les gusta... la imagen de bandido' + culpabilización de la víctima 'para después quejarse'.",
                "evidencia": "Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse",
                "regla_disparada": "Regla 1 (4.1): esencialismo biológico y masculinidad hegemónica.",
                "marcadores_detectados": ["imagen de bandido", "para después quejarse"],
            },
        ],
    },
    # Unidad 38: 9a56c48901821349 — ar_id=55
    55: {
        "verdict": "RECATEGORIZAR",
        "reason": "U38 §auditoría manual: 'Ahí vienen los \"chicos buenos\" a proyectarse jajaja...' — Manual: 4.3 (Trolleo/Emasculación). Falso Negativo: sistema disparó 'ninguna', el sarcasmo enmascaró la regla.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "Troleo/emasculación: 'chicos buenos' en comillas irónicas opera como equivalente de 'betas' / 'aliados' / 'blandengues' para ridiculizar a los varones que no se ajustan a la masculinidad hegemónica.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "baja",
                "justificacion": "Troleo/emasculación: 'chicos buenos' en comillas irónicas = jerga manosférica de emasculación.",
                "evidencia": "Ahí vienen los chicos buenos a proyectarse jajaja",
                "regla_disparada": "Regla 2 (4.3): emasculación vía 'chicos buenos' irónicos.",
                "marcadores_detectados": ["chicos buenos", "proyectarse"],
            },
        ],
    },
    # Unidad 39: e94db76c3e610017 — ar_id=56
    56: {
        "verdict": "DE ACUERDO",
        "reason": "U39 §auditoría manual: 'Se lo está diciendo al tipo.' — acotación sin carga. Sistema ninguna. ✓",
    },
    # Unidad 40: 247eade36a76b5ad — ar_id=57
    57: {
        "verdict": "RECATEGORIZAR",
        "reason": "U40 §auditoría manual: 'Eso es por qué el man no tiene energía masculina' — Manual: 4.3 (Trolleo/Emasculación). Falso Negativo: sistema disparó 'ninguna', el término 'energía masculina' no fue detectado como marcador emasculador.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.3",
        "corrected_justificacion": "Troleo/emasculación: 'energía masculina' como insulto al varón que no encaja en estándares de rudeza, control o dominio de la masculinidad hegemónica.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "Troleo/emasculación: castigo disciplinario al varón que no encaja en estándares de masculinidad hegemónica.",
                "evidencia": "el man no tiene energía masculina",
                "regla_disparada": "Regla 2 (4.3): emasculación vía 'energía masculina'.",
                "marcadores_detectados": ["energía masculina"],
            },
        ],
    },
    # Unidad 41: c559ec3ef418584a — ar_id=58
    58: {
        "verdict": "DE ACUERDO",
        "reason": "U41 §auditoría manual: 'oelo morado mas encima,,, noo gracias !' — referencia coloquial sin blanco de género. Sistema ninguna. ✓",
    },
    # Unidad 42: 52dda3c28962f918 — ar_id=59
    59: {
        "verdict": "DE ACUERDO",
        "reason": "U42 §auditoría manual: 'Los hombres tienen que usar IA para únicamente representar escenarios imaginarios' — crítica al varón, sin marcador VDG. Sistema ninguna. ✓",
    },
    # Unidad 43: 6caefde6d4c0bc54 — ar_id=60
    60: {
        "verdict": "DE ACUERDO",
        "reason": "U43 §auditoría manual: 'a lo que se ve ellas tienen más que el' — observación neutra. Sistema 1.1 baja — sobre-flageo leve pero la palabra 'ellas' como referente femenino-objetivado es ambigua. Sugerencia: ninguna, pero tolerable.",
    },
    # Unidad 44: d33f19d5eac7c764 — ar_id=65
    65: {
        "verdict": "RECATEGORIZAR",
        "reason": "U44 §auditoría manual: 'Ni la IA entiende el feminismo' — Manual: 4.2 (Victimismo / ataque al feminismo). Falso Negativo: sistema disparó 'ninguna', perdiendo el ataque ideológico.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.2",
        "corrected_justificacion": "Victimismo / deslegitimación del feminismo: caricaturiza el movimiento presentándolo como 'ideología completamente incoherente, absurda o carente de razonamiento lógico'.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "Deslegitimación ideológica: caricaturiza el feminismo como absurdo e incomprensible.",
                "evidencia": "Ni la IA entiende el feminismo",
                "regla_disparada": "Regla 2 (4.2): desinformación victimista y ataque ideológico.",
                "marcadores_detectados": ["Ni la IA entiende"],
            },
        ],
    },
    # Unidad 45: 4d828911cabce8cd — ar_id=63
    63: {
        "verdict": "DE ACUERDO",
        "reason": "U45 §auditoría manual: 'yo veo puros wasones jajajajaa' — risa genérica sin carga de género específica. Sistema ninguna. ✓",
    },
    # Unidad 46: 74da4732a892ce97 — ar_id=64
    64: {
        "verdict": "RECATEGORIZAR",
        "reason": "U46 §auditoría manual: 'El patriarcado me da patriarcado??' — Manual: 4.2 (Victimismo) o 6.2 (Humor hostil), excluyentes. Falso Negativo: sistema disparó 'ninguna'. Se selecciona 4.2 como override primario.",
        "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
        "corrected_dimension": "4.2",
        "corrected_justificacion": "Victimismo / deslegitimación: ataca directamente los conceptos del propio movimiento feminista (en este caso 'patriarcado') para deslegitimarlo, disfrazado de pregunta retórica irónica.",
        "corrected_labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": "Deslegitimación del feminismo: pregunta irónica sobre 'patriarcado' que busca caricaturizar e invalidar el concepto.",
                "evidencia": "El patriarcado me da patriarcado??",
                "regla_disparada": "Regla 2 (4.2): ataque a conceptos del feminismo.",
                "marcadores_detectados": ["patriarcado me da patriarcado"],
            },
        ],
    },
    # Unidad 47: 804fbd6335aab52c — ar_id=66
    66: {
        "verdict": "RECATEGORIZAR",
        "reason": "U47 §auditoría manual: 'Pues en los carteles veo cosas logicas...' — Manual: 6.3 (Salvaguarda / Defensa feminista). Falso Positivo SEVERO: sistema disparó 3.2 (violencia letal ALTA) + 2.2 + 1.1 + 1.2 — TOTALMENTE ERRADO. La regla 6.3 debió anular las alertas.",
        "corrected_categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
        "corrected_dimension": "6.3",
        "corrected_justificacion": "Salvaguarda / defensa feminista: el emisor defiende activamente las consignas de protesta ('en los carteles veo cosas lógicas') y usa pregunta retórica de defensa ('¿Quieren a una mujer controlada?'). La subdimensión 6.3 se activa obligatoriamente para proteger este texto como crítica feminista legítima.",
        "corrected_labels": [
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "6.3",
                "severidad": "ninguna",
                "justificacion": "Salvaguarda: defensa feminista explícita con pregunta retórica de defensa.",
                "evidencia": "en los carteles veo cosas logicas / Quieren a una mujer controlada? / Yo creo que todos pensamos lo mismo que dicen los carteles",
                "regla_disparada": "Regla 6.3: pregunta retórica de defensa / crítica feminista.",
                "marcadores_detectados": [
                    "en los carteles veo cosas logicas",
                    "Quieren a una mujer controlada",
                ],
            },
        ],
    },
    # Unidad 48: 32cffa6031670f8e — ar_id=67
    67: {
        "verdict": "RECATEGORIZAR",
        "reason": "U48 §auditoría manual: 'Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos.' — Manual: 3.3 (Apología al feminicidio) + 4.2 (Victimismo) + 6.2 (Humor hostil). Falso Negativo CRÍTICO: banalización letal no detectada.",
        "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
        "corrected_dimension": "3.3",
        "corrected_justificacion": "(3.3) Apología al feminicidio: se apropia de 'ni una menos, vivas las queremos' (consigna principal contra femicidios) y la reemplaza por 'nutrias' — trivializa/banaliza la crisis de violencia letal. (4.2) Caricaturización del feminismo. (6.2) Humor hostil enmascarador.",
        "corrected_labels": [
            {
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.3",
                "severidad": "alta",
                "justificacion": "Apología al feminicidio: trivializa el asesinato de mujeres por razones de género al reemplazar 'mujeres' por 'nutrias' en la consigna 'ni una menos'.",
                "evidencia": "Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos",
                "regla_disparada": "Regla 1 (3.3): banalización del feminicidio.",
                "marcadores_detectados": ["por las nutrias", "ni una menos"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "Victimismo / deslegitimación del feminismo: ataca uno de los conceptos fundamentales del feminismo usándolo de forma absurda para caricaturizar la lucha.",
                "evidencia": "por las nutrias, ni una menos",
                "regla_disparada": "Regla 2 (4.2): caricatura del feminismo.",
                "marcadores_detectados": ["por las nutrias"],
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "6.2",
                "severidad": "media",
                "justificacion": "Humor hostil: toda la banalización del feminicidio disfrazada bajo el formato de chiste irónico.",
                "evidencia": "Yo por las únicas que lucho, es por las nutrias",
                "regla_disparada": "Regla 2 (6.2): humor hostil enmascarador.",
                "marcadores_detectados": ["vivas las queremos"],
            },
        ],
    },
    # Unidad 49: df44aa3a18434718 — ar_id=68
    68: {
        "verdict": "DE ACUERDO",
        "reason": "U49 §auditoría manual: 'Suban a ponerle al jale acá las esperamos ....' — convocatoria genérica sin blanco de género. Sistema ninguna. ✓",
    },
    # Unidad 50: f9703d6d41e170d1 — ar_id=69
    69: {
        "verdict": "DE ACUERDO",
        "reason": "U50 §auditoría manual: 'Usando IA porque no puede encontrar un imagen real: Conservadores enojándose por cosas imaginarias' — crítica política genérica. Sistema ninguna. ✓",
    },
}

# Drop placeholder / conflicting keys
assert len(FEEDBACK) == 57, f"FEEDBACK debe tener 57 entradas, tiene {len(FEEDBACK)}"


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
            SELECT ar.id, ar.content_type, ar.content_id,
                   CASE WHEN ar.content_type = 'post' THEN p.text ELSE c.text END as texto
            FROM analysis_results ar
            LEFT JOIN posts p ON ar.post_id = p.id
            LEFT JOIN comments c ON ar.comment_id = c.id
            ORDER BY ar.id
        """)
        ).fetchall()

        rows_data = list(results)
        print(f"Resultados cargados: {len(rows_data)}")

    counts = {"agree": 0, "recategorize": 0, "missing": 0, "skipped": 0}
    inserted_ids: list[int] = []
    for r in rows_data:
        ar_id, content_type, content_id, texto = r
        verdict_entry = FEEDBACK.get(ar_id)
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
            counts["skipped"] += 1
            continue

        fb_id = db.save_feedback(feedback_data)
        inserted_ids.append(fb_id)

    print("\n=== Resumen ===")
    print(f"DE ACUERDO:           {counts['agree']}")
    print(f"RECATEGORIZAR:        {counts['recategorize']}")
    print(f"Sin veredicto (WARN): {counts['missing']}")
    print(f"Skipped (err):        {counts['skipped']}")
    print(f"Filas feedback (ID):  {len(inserted_ids)}")
    print(f"Doc comparación:      {AUDIT_DOC}")

    total_feedback = len(db.list_feedback())
    total_disagree = len(db.list_feedback(only_disagreements=True))
    print(f"\n[verificación] analysis_feedback total: {total_feedback}")
    print(f"[verificación] analysis_feedback disagrees: {total_disagree}")
    pending_index = len(db.list_feedback(only_pending_index=True))
    print(f"[verificación] pending ChromaDB index: {pending_index}")


if __name__ == "__main__":
    main()
