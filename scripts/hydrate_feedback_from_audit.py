"""Hydrate ``analysis_feedback`` from the 2026-07-12 audit.

Run with the project venv:

    .venv/bin/python scripts/hydrate_feedback_from_audit.py

The script:

1. Ensures an ``auditor-tfm`` admin user exists (idempotent — re-uses an
   existing row if any).
2. Reads every row in ``analysis_results`` once to know the original
   ``analysis_result_id``, ``content_type``, ``content_id`` and a copy of
   the source text (used as ``text_snapshot``).
3. For each of the 27 disagreements catalogued in
   ``docs/auditoria-categorizaciones-2026-07-12.md`` builds a
   ``build_feedback_payload`` with a humanised reason + the corrected
   labels, and calls ``Database.save_feedback`` so the side tables
   ``analysis_feedback`` and ``analysis_feedback_labels`` get populated
   consistently.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.storage.database import get_database
from src.ui.validacion import build_feedback_payload

DB_PATH = Path("data/tfm.db")
DB_URL = f"sqlite:///{DB_PATH}"
REVIEWER_USERNAME = "auditor-tfm"
REVIEWER_PASSWORD = "Auditor2026!"
REVIEWER_FULLNAME = "Auditor TFM (revisión 2026-07-12)"
REVIEWER_ROLE = "admin"


CORRECTIONS: list[dict] = [
    {
        "content_id": "0f3e884a8a124fd1_p0",
        "reason": (
            "El sistema la puso en 1.1 (roles tradicionales) pero el texto no da "
            'imperativos del estilo "vayan a lavar" — más bien descalifica a las '
            'mujeres como colectivo ("degeneradas", "no es malo porque lo justifican '
            'con lógica feminista"). Para mí la lectura que mejor encaja es la '
            "Regla 3 de Cat. 1 (1.3 doble estándar moral + inversión de "
            'responsabilidad). El léxico "degenerac18n / acost4rs3" también es '
            "slut-shaming (2.3), no cosificación estética como dijo el modelo. La "
            "etiqueta 5.1 sobra — el ataque es explícito, no implícito."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "media",
                "justificacion": (
                    "Acá lo que veo es una descalificación colectiva de las mujeres "
                    'como "degeneradas" e "infieles por naturaleza", más la '
                    "inversión de responsabilidad típica de la Regla 3. No encuentro "
                    "imperativos hacia el ámbito privado, por eso no es 1.1."
                ),
                "evidencia": "pueden justificarlo con alguna lógica feminista absurd4",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["degeneradas", "lógica feminista"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "media",
                "justificacion": (
                    'El léxico mutado "acost4rs3 con var1os" y la condena moral de '
                    "la sexualidad femenina caen en slut-shaming directo, no en "
                    "cosificación estética."
                ),
                "evidencia": "acost4rs3 con var1os y no tener vergüenza",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["acostarse con varios", "no tener vergüenza"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": (
                    'El discurso esencialista sobre "mujeres modernas" como '
                    "categoría moralmente inferior encaja con desinformación "
                    "victimista de la manosfera (4.2)."
                ),
                "evidencia": "Las mvjeres modernas crecen en un entorno que incentiva la degenerac18n",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["mujeres modernas", "degeneración"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "0f3e884a8a124fd1_p2",
        "reason": (
            "Acá el sistema tiró la alarma más alta (Cat. 3 / 3.1) pero no hay "
            "ninguna amenaza física ni léxico letal — es la retórica clásica de "
            '"el beta vs el del 1%". Para mí eso va a manosfera (4.1 por la '
            "taxonomía beta/Chad y 4.2 por la narrativa de la mujer infiel por "
            "naturaleza), más un componente de doble estándar moral (1.3)."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    'El texto despotrica contra las mujeres que "traicionan" como '
                    "si fuera un hecho universal; eso es doble estándar moral, no "
                    "hostilidad física."
                ),
                "evidencia": "mientras tanto ella sigue haciendo lo que le da la gana",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["traición", "engañar"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": (
                    'Aparece explícitamente la taxonomía manosférica "el beta" '
                    'frente a "el del 1%". Cat. 4.1 pide detectar estos arquetipos.'
                ),
                "evidencia": "el beta vs. el del 1%",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["beta", "del 1%"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": (
                    'La narrativa "la mujer engaña por naturaleza, no tiene '
                    'solución" es desinformación victimista pura de la manosfera.'
                ),
                "evidencia": "pierde respeto propio cada día",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["desinformación de género", "victimismo masculino"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "dc8ae80a3ae35f92",
        "reason": (
            "Mismo patrón que los dos posts anteriores: el modelo etiquetó 1.1 "
            "(roles) pero no hay imperativos domésticos — lo que hay es la "
            'desvalorización de la "chica buena" como máscara y vocabulario '
            'manosférico ("beta", "tipo del KFC"), más 4.2.'
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "media",
                "justificacion": (
                    'El texto construye a la mujer como manipuladora que "vende" '
                    "una imagen. Eso es descalificar al colectivo femenino, no "
                    "prescribirle roles (1.1 no aplica)."
                ),
                "evidencia": "Ella te vende la imagen de la chica buena",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["actuación", "chica buena", "manipulación"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "media",
                "justificacion": (
                    'Taxonomía manosférica pura: "beta", "chico bueno", "tipo '
                    'del KFC". Marcadores explícitos del glosario manosférico.'
                ),
                "evidencia": "El beta que se cree la actuación",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["beta", "chico bueno"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": (
                    "La lectura de la mujer como calculadora interesada es la "
                    "desinformación típica de la manosfera."
                ),
                "evidencia": "se la ha c8g1d8 con otros hombres",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["hipergamia", "mujer interesada"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "b0bcbbb5eb375a41",
        "reason": (
            "Otra vez 1.1/2.2 sin base: el texto no prescribe roles ni habla del "
            'cuerpo, habla de que "soltera" significa en realidad "acostándose '
            'con varios". Es 1.3 (inversión de responsabilidad) + 2.3 (slut-shaming '
            "por conducta sexual) + 4.2 (manosfera)."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    'Acá lo que hay es una generalización desvalorizante: "soltera" '
                    'equivale a "está con varios". Inversión de responsabilidad '
                    "típica de la Regla 3."
                ),
                "evidencia": 'Para la mayoría de mujeres, "soltera" solo significa que no tiene novio formal',
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["soltera", "inversión de responsabilidad"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "baja",
                "justificacion": (
                    "El texto critica la conducta sexual de las mujeres, no su "
                    "apariencia — eso es slut-shaming, no body-shaming."
                ),
                "evidencia": "Puede estar f8ll4nd8 regularmente con uno o varios tipos",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["acostándose con varios", "slut-shaming"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": (
                    'Vuelve a aparecer la narrativa del "del 1% no se deja engañar".'
                ),
                "evidencia": "el del 1% no se deja engañar por esa palabra",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["del 1%"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "2effd62b3d4cbac5",
        "reason": (
            'Comentario corto y muy claro: "No debes amar por completo ni confiar '
            'en una mujer". El modelo lo puso en 1.2 (incompetencia) pero no '
            "habla de capacidades intelectuales — es una prescripción moral "
            "desvalorizante hacia todas las mujeres, o sea 1.3 (doble estándar)."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    "El imperativo negativo va contra todas las mujeres como "
                    'colectivo ("una mujer"). No invalida capacidades — descalifica '
                    "moralmente. Regla 3."
                ),
                "evidencia": "No debes amar por completo ni confiar en una mujer",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["confiar", "mujer"],
                "es_falso_positivo_probable": False,
            }
        ],
    },
    {
        "content_id": "a1478d1dd8727dd4",
        "reason": (
            "Falso positivo claro: el comentario es una frase motivacional neutra "
            '("Nadie vendrá a salvarte, estás a cargo de tu vida…"). No hay ni '
            "un pronombre ni un sustantivo femenino — el protocolo exige "
            "coocurrencia con un referente femenino y no se cumple."
        ),
        "labels": [
            {
                "categoria": "ninguna",
                "dimension": None,
                "severidad": "ninguna",
                "justificacion": (
                    "Frase sin referente femenino; no aplica ninguna regla de las categorías 1–6."
                ),
                "evidencia": "Nadie vendrá a salvarte",
                "regla_disparada": None,
                "marcadores_detectados": [],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "6983ada882e8a729",
        "reason": (
            '"La gran mayoría de mujeres solo está contigo por conveniencia" — '
            "el sistema dijo 1.1 pero no prescribe ningún rol, despotrica contra "
            "las mujeres en general. Va a 1.3 por ser generalización misógina y a "
            "4.2 como desinformación."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    "Es una descalificación del colectivo femenino. No hay "
                    "imperativo doméstico, por eso no es 1.1."
                ),
                "evidencia": "La gran mayoría de mujeres solo está contigo por conveniencia",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["mayoría de mujeres", "conveniencia"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": ("Axioma misógino genérico, típico del victimismo manosférico."),
                "evidencia": "la gran mayoría",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["axioma misógino"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "c6cf703c604b5599",
        "reason": "Duplicado de 2effd62b3d4cbac5.",
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    "Mismo imperativo genérico contra las mujeres. No habla de "
                    "capacidades, así que no es 1.2."
                ),
                "evidencia": "No debes amar por completo ni confiar en una mujer",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["confiar", "mujer"],
                "es_falso_positivo_probable": False,
            }
        ],
    },
    {
        "content_id": "1f09dfc016268ce8",
        "reason": "Duplicado del falso positivo a1478d1dd8727dd4.",
        "labels": [
            {
                "categoria": "ninguna",
                "dimension": None,
                "severidad": "ninguna",
                "justificacion": ("Otra vez la frase sin referente femenino. No hay VDG."),
                "evidencia": "Nadie vendrá a salvarte",
                "regla_disparada": None,
                "marcadores_detectados": [],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "ef23be21d6c07448",
        "reason": "Duplicado de 6983ada882e8a729.",
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": ("Generalización desvalorizante del colectivo femenino."),
                "evidencia": "La gran mayoría de mujeres solo está contigo por conveniencia",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["mayoría de mujeres"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": ("Axioma victimista propio de la manosfera."),
                "evidencia": "la gran mayoría",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["axioma misógino"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "2020cf0150b86856",
        "reason": (
            '"Si eres mestizo café con leche pero tienes más actitudes de hombre '
            'blanco prácticamente ya valiste" — el sistema lo puso en 1.1 '
            "(roles) pero no hay nada sobre roles femeninos. Lo que hay es una "
            "jerarquía masculina internalizada y una lectura de la mujer como "
            "trofeo: eso es 1.3 + 4.2."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    'La mujer aparece como objeto a "valuar" en función de las '
                    "actitudes del varón. Doble estándar + cosificación implícita."
                ),
                "evidencia": "ya valiste mergas para el ligue",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["valorar", "actitudes de hombre"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": (
                    'Construye una jerarquía de "actitudes" para medir el valor '
                    "ante las mujeres — vocabulario típico de la manosfera."
                ),
                "evidencia": "actitudes de hombre blanco",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["hombre blanco", "actitudes"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "ed489d3558a69eef",
        "reason": (
            'Acá está el hallazgo más fuerte: "f3m1 nizta" es leetspeak directo '
            'de "feminazi" (marcador Cat. 4.3 según glosario manosférico). Y '
            '"aliade" es la versión emasculada de "aliado" — también Cat. 4.3. '
            "No hay nada de body-shaming ni violencia simbólica acá."
        ),
        "labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": (
                    '"f3m1 nizta" es feminazi en leetspeak — marcador directo '
                    "de Cat. 4.3 (troleo de género)."
                ),
                "evidencia": "f3m1 nizta",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["feminazi", "f3m1 nizta", "leetspeak"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "baja",
                "justificacion": (
                    '"aliade" es la forma emasculada de "aliado" — jerga de '
                    "castigo a varones que apoyan feminismo (Cat. 4.3)."
                ),
                "evidencia": "aliade",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["aliade", "emasculación"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "a4305690f1e373f9",
        "reason": (
            'Solo es "jajajaja" — no es violencia, es una risa suelta. Sugiero '
            "mantener la marca de salvaguarda pero explícita: 5.3 (falso "
            "potencial). Si les parece mejor, directamente ninguna."
        ),
        "labels": [
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.3",
                "severidad": "ninguna",
                "justificacion": (
                    "Risa sin contenido. Marcador típico de un 5.3 que el sistema "
                    "no debería disparar como VDG."
                ),
                "evidencia": "jajajaja",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["jajaja"],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "e355f12847ca56e7",
        "reason": (
            'Falso negativo importante: "a la mujer es quien le toca cocinar y '
            'criar al bebé". Esto es la Regla 1 de Cat. 1 literal — imperativo de '
            "reclusión doméstica. También carga 4.2 por la lectura esencialista "
            'del "papel de mujer".'
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
                "justificacion": (
                    "Imperativo de reclusión doméstica explícito: cocinar y criar. "
                    "Es exactamente el marcador canónico de la Regla 1."
                ),
                "evidencia": "a la mujer es quien le toca cocinar y criar al bebe",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["cocinar", "criar", "mujer"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": (
                    'La división esencialista "papel de mujer" vs "hombre de '
                    'hoy" es narrativa manosférica de victimismo.'
                ),
                "evidencia": "el hombre hoy día quiere hacer el papel de mujer",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["papel de mujer", "esencialismo"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "7e6c8887fea366de",
        "reason": (
            '"No que a las feministas no les hacen caso jaja" — el sistema lo '
            "dejó en ninguna pero el comentario minimiza/deslegitima al colectivo "
            "feminista. Para mí es Cat. 6 (desacreditación de activistas, 6.1 por "
            'caricatura) más un troleo manosférico (4.3) y el "jaja" final como '
            "humor hostil (5.2)."
        ),
        "labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "baja",
                "justificacion": (
                    'El "jaja" final y la minimización del feminismo entran en troleo de género.'
                ),
                "evidencia": "no les hacen caso jaja",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["jaja", "troleo"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.1",
                "severidad": "baja",
                "justificacion": (
                    "Minimiza al colectivo de feministas como irrelevante, que es "
                    "la caricatura típica que pide detectar la Cat. 6."
                ),
                "evidencia": "a las feministas no les hacen caso",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["feministas", "caricatura"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "d160eac77321b71d",
        "reason": (
            '"Creo que Eva se golpeó la cabeza al momento de que Dios la creó" — '
            "otro falso negativo. La atribución de inferioridad cognitiva a la "
            "mujer (Eva como arquetipo) es la Regla 2 / 1.2. Y el marco bíblico "
            "esencialista también es Cat. 6.1 (deslegitimación)."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.2",
                "severidad": "media",
                "justificacion": (
                    "Equivale a decir que las mujeres son cognitivamente inferiores. "
                    "Eva representa a todas. Regla 2."
                ),
                "evidencia": "Eva se golpeó la cabeza al momento de que Dios la creo",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["Eva", "inferioridad cognitiva"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.1",
                "severidad": "baja",
                "justificacion": (
                    "Usa el esencialismo bíblico como marco para deslegitimar "
                    "posiciones feministas."
                ),
                "evidencia": "al momento de que Dios la creo",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["esencialismo religioso"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "5fbccd33967c9c0b",
        "reason": (
            '"Les gusta el desafío, la aventura Y la imagen de bandido... Para '
            'después quejarse" — falso negativo. Hay tres lecturas misóginas: (a) '
            'generalización del "les gusta", (b) esencialismo hipersexual, (c) '
            '"para después quejarse" invierte la responsabilidad. Va a 1.3 + 4.2.'
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": (
                    "Generalización desvalorizante del colectivo femenino. La "
                    'expresión "para después quejarse" es la inversión de '
                    "responsabilidad típica de la Regla 3."
                ),
                "evidencia": "Para después quejarse",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["quejarse", "después"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": (
                    'El imaginario de la mujer a la que le gustan "los bandidos" '
                    "es desinformación manosférica típica."
                ),
                "evidencia": "Les gusta el desafío, la aventura Y la imagen de bandido",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["mujeres gustan bandidos"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "9a56c48901821349",
        "reason": (
            "\"Ahí vienen los 'chicos buenos' a proyectarse jajaja\" — el sistema "
            "lo marcó como 5.1 pero no hay ataque directo a mujeres; lo que hay es "
            'humor hostil hacia la masculinidad "chico bueno". Lo más honesto es '
            "5.2, o ninguna si el contexto del hilo es una crítica feminsta al "
            "discurso manosférico."
        ),
        "labels": [
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.2",
                "severidad": "ninguna",
                "justificacion": (
                    'El blanco son los "chicos buenos", no las mujeres. El "jajaja" '
                    "califica como humor hostil (5.2) pero no veo VDG directo."
                ),
                "evidencia": 'Ahí vienen los "chicos buenos" a proyectarse jajaja',
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["chicos buenos", "proyectarse", "jajaja"],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "247eade36a76b5ad",
        "reason": (
            '"Eso es por qué el man no tiene energía masculina" — el modelo lo '
            "puso en 1.1 pero no prescribe roles femeninos. Lo que hay es "
            'concepto manosférico de "energía masculina" + patologización del '
            "varón que no encaja. Va a Cat. 4."
        ),
        "labels": [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "severidad": "baja",
                "justificacion": (
                    '"Energía masculina" es léxico propio de las subculturas '
                    "masculinistas. El comentario invoca esa taxonomía."
                ),
                "evidencia": "energía masculina",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["energía masculina", "man"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "baja",
                "justificacion": ("Patologiza al varón que no encaja — victimismo invertido."),
                "evidencia": "el man no tiene",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["victimismo masculino"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "52dda3c28962f918",
        "reason": (
            '"Los hombres tienen que usar IA para únicamente representar '
            'escenarios imaginarios" — falso positivo claro. El comentario es '
            "una crítica al varón, no a la mujer. No hay ningún marcador VDG."
        ),
        "labels": [
            {
                "categoria": "ninguna",
                "dimension": None,
                "severidad": "ninguna",
                "justificacion": (
                    "El blanco son los hombres. Sin referente femenino ni marcador de Cat. 1–6."
                ),
                "evidencia": "Los hombres tienen que usar IA",
                "regla_disparada": None,
                "marcadores_detectados": [],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "6caefde6d4c0bc54",
        "reason": (
            '"a lo que se ve ellas tienen más que el" — texto truncado, sin '
            "contexto suficiente. La propia base marca tiene_violencia=false; "
            "coincido en que no hay VDG detectable."
        ),
        "labels": [
            {
                "categoria": "ninguna",
                "dimension": None,
                "severidad": "ninguna",
                "justificacion": (
                    "Texto incompleto y sin marcadores. Coherente con tiene_violencia=false."
                ),
                "evidencia": "ellas tienen más que el",
                "regla_disparada": None,
                "marcadores_detectados": [],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "b177ef1b0bf960bf",
        "reason": (
            'Error grave. El comentario dice "es mejor no meterse […] asi la '
            'estén matando" — eso es APOLOGÍA AL FEMINICIDIO (Cat. 3.3), no '
            'hostilidad física (3.1). Además la coletilla "es consejo de ellas '
            'mismas" invierte la responsabilidad y el cierre lo usa como '
            'pretexto para atacar a las feministas (Cat. 6.3). El "jajaja" es '
            "humor hostil (5.2)."
        ),
        "labels": [
            {
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.3",
                "severidad": "alta",
                "justificacion": (
                    'Normaliza/desensibiliza la violencia letal: "es mejor no '
                    'meterse aunque la estén matando". Es la Regla 3 de Cat. 3, '
                    "no la Regla 1 (no hay amenaza física explícita)."
                ),
                "evidencia": "asi la estén matando es mejor no meterse",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["matando", "no meterse", "normalización"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.3",
                "severidad": "media",
                "justificacion": (
                    '"Es consejo de ellas mismas" y "que lo demande por '
                    'ayudarla" tergiversan el feminismo como perseguidor del '
                    "varón."
                ),
                "evidencia": "no vaya a ser qur lo demande a usted por ayudarla sin su consentimiento",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["demande", "feminismo como perseguidor"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.2",
                "severidad": "baja",
                "justificacion": ('El "jajaja" final oculta la agresión bajo humor hostil.'),
                "evidencia": "jajaja",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["jajaja", "humor hostil"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
    {
        "content_id": "74da4732a892ce97",
        "reason": (
            '"El patriarcado me da patriarcado??" — el sistema lo dejó en 1.1 '
            "pero no prescribe roles. Lo que hay es ironía que minimiza el "
            "concepto de patriarcado — encaja con Cat. 6.1 (deslegitimación "
            "ideológica) o Cat. 4.2."
        ),
        "labels": [
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.1",
                "severidad": "baja",
                "justificacion": (
                    "Ironiza y descarta el concepto de patriarcado, que es la "
                    "caricatura del feminismo propia de la Regla 1 de Cat. 6."
                ),
                "evidencia": "El patriarcado me da patriarcado??",
                "regla_disparada": "Regla 1",
                "marcadores_detectados": ["patriarcado", "ironía"],
                "es_falso_positivo_probable": False,
            }
        ],
    },
    {
        "content_id": "804fbd6335aab52c",
        "reason": (
            'Falso positivo. El comentario "¿Quieren una mujer controlada? '
            '¿Quieren que las mujeres mueran?" es una DEFENSA feminista del '
            "derecho a protestar. Las preguntas retóricas y el rechazo del "
            "escrutinio corporal son marcadores mitigadores de Cat. 5.3. No "
            "hay VDG."
        ),
        "labels": [
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.3",
                "severidad": "ninguna",
                "justificacion": (
                    "Las preguntas retóricas funcionan como denuncia feminista, "
                    "no como ataque. Son los marcadores mitigadores canónicos de "
                    "Cat. 5.3."
                ),
                "evidencia": "Quieren una mujer controlada? Quieren que las mujeres mueran?",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["denuncia", "preguntas retóricas"],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "3dfe60c1fbf2e1a8",
        "reason": (
            '"La mía les cobraba jajaja" — chiste coloquial de un varón sobre su '
            'esposa, sin marcadores VDG. El "jajaja" solo puede leerse como '
            "reapropiación/halago coloquial (5.3) o directamente ninguna. No es "
            "5.1 (sexismo implícito)."
        ),
        "labels": [
            {
                "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "dimension": "5.3",
                "severidad": "ninguna",
                "justificacion": (
                    "Broma de un varón sobre su esposa. No hay sexismo implícito "
                    'ni ataque. El "jajaja" es halago coloquial.'
                ),
                "evidencia": "La mía les cobraba",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["jajaja", "halago coloquial"],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "94a5252cf77e41e6",
        "reason": (
            '"Todos los días sale un pendejo a la calle el que lo atrape es de '
            'el" — la propia justificación dice que no hay motivación de género. '
            "Es violencia común: insulto genérico sin referente femenino. Va a "
            "exclusión por violencia común, no a Cat. 1."
        ),
        "labels": [
            {
                "categoria": "VIOLENCIA_COMUN",
                "dimension": None,
                "severidad": "ninguna",
                "justificacion": (
                    "Insulto genérico sin referente femenino ni marcador de las "
                    "categorías 1–6. Regla de exclusión de violencia común."
                ),
                "evidencia": "Todos los días sale un pendejo a la calle",
                "regla_disparada": None,
                "marcadores_detectados": ["pendejo", "violencia común"],
                "es_falso_positivo_probable": True,
            }
        ],
    },
    {
        "content_id": "6ac63c8dd7b3dbcd",
        "reason": (
            'Error grave. El comentario dice "como son todas las mujeres", '
            '"rompe las pelotas", "un negocio es un negocio", "siempre están '
            'enculada o les duele la cabeza". Es una generalización '
            "desvalorizante del colectivo femenino, NO una amenaza de daño "
            "físico. Va a 1.3 (doble estándar moral + inversión de "
            "responsabilidad), 4.2 (manosfera victimista) y 2.3 (slut-shaming "
            "por la frase sexual)."
        ),
        "labels": [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "media",
                "justificacion": (
                    'Desvaloriza a las mujeres como colectivo ("como son '
                    'todas las mujeres", "rompe las pelotas", "te consumen '
                    'tiempo, salud y dinero"). Regla 3.'
                ),
                "evidencia": "como son todas las mujeres",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["todas las mujeres", "rompe las pelotas"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": (
                    'La metáfora de la mujer como "negocio" y "la más cara es '
                    'una esposa" es victimismo manosférico puro.'
                ),
                "evidencia": "un negocio es un negocio",
                "regla_disparada": "Regla 2",
                "marcadores_detectados": ["mujer mercancía", "victimismo"],
                "es_falso_positivo_probable": False,
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.3",
                "severidad": "baja",
                "justificacion": (
                    '"Siempre están enculada o les duele la cabeza" es '
                    "doble estándar sexual y slut-shaming clásico."
                ),
                "evidencia": "siempre están enculada o les duele la cabeza",
                "regla_disparada": "Regla 3",
                "marcadores_detectados": ["doble estándar sexual"],
                "es_falso_positivo_probable": False,
            },
        ],
    },
]


def ensure_reviewer(db) -> int:
    """Create the auditor user if missing. Returns its id."""
    existing = db.find_user_by_username(REVIEWER_USERNAME)
    if existing:
        return int(existing["id"])
    return db.create_user(
        username=REVIEWER_USERNAME,
        password=REVIEWER_PASSWORD,
        role=REVIEWER_ROLE,
        full_name=REVIEWER_FULLNAME,
    )


def load_content_texts() -> dict[str, str]:
    """Return a {content_id: text} map for both posts and comments."""
    out: dict[str, str] = {}
    conn = sqlite3.connect(DB_PATH)
    try:
        for table in ("posts", "comments"):
            cur = conn.execute(f"SELECT id, text FROM {table}")
            for cid, text in cur.fetchall():
                if cid:
                    out[cid] = text or ""
    finally:
        conn.close()
    return out


def main() -> int:
    db = get_database(DB_URL)
    reviewer_id = ensure_reviewer(db)
    print(f"[ok] reviewer user id = {reviewer_id} ({REVIEWER_USERNAME!r})")

    texts = load_content_texts()
    print(f"[ok] loaded {len(texts)} texts (posts + comments)")

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT id, content_type, content_id FROM analysis_results").fetchall()
    finally:
        conn.close()

    cid_to_ar = {cid: (ar_id, ctype) for ar_id, ctype, cid in rows}
    print(f"[ok] {len(cid_to_ar)} analysis_results indexed by content_id")

    inserted = 0
    skipped = 0
    for entry in CORRECTIONS:
        cid = entry["content_id"]
        if cid not in cid_to_ar:
            print(f"[skip] {cid} — no analysis_result with that content_id")
            skipped += 1
            continue
        ar_id, ctype = cid_to_ar[cid]
        payload = build_feedback_payload(
            analysis_result_id=ar_id,
            content_type=ctype,
            content_id=cid,
            text_snapshot=texts.get(cid, "")[:1000],
            agrees=False,
            reason=entry["reason"],
            corrected_labels=entry["labels"],
            reviewer=REVIEWER_USERNAME,
        )
        payload["reviewer_user_id"] = reviewer_id
        payload["reviewer_username"] = REVIEWER_USERNAME
        new_id = db.save_feedback(payload)
        inserted += 1
        print(f"[ok] {cid:36s}  ar={ar_id:>3}  -> feedback_id={new_id}")

    print(f"\nDone. inserted={inserted}  skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
