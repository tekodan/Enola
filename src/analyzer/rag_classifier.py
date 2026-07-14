"""RAG classifier for violence detection.

The classification taxonomy is **homogeneous**: alphabetic codes for
categories (``VDG_*``) and numeric codes for sub-dimensions
(``1.1``..``6.3``). The LLM is forced to pick from a closed set of 18
valid combinations defined in :mod:`src.analyzer.category_mapping`; any
output outside the set is rejected and normalized to ``"ninguna"`` with
a warning.

The classifier supports **multi-label** classification: a single
analyzed post/comment can carry up to ``MAX_LABELS`` (5) labels, each
with its own ``categoria``/``dimension``/``severidad``/
``justificacion``/``evidencia``/``marcadores``/etc. The schema is
backwards-compatible — old single-label JSON (with a single
``categoria``/``dimension`` pair) is auto-wrapped into a one-element
list so legacy few-shots keep working.

The only categorical field with a hardcoded scale is :class:`Severity`
(``baja``/``media``/``alta``/``ninguna``).

The classifier optionally consumes a ``feedback_store`` (a
:class:`~src.knowledge_base.feedback_store.FeedbackStore`) and uses the
corrections retrieved from it as dynamic few-shot examples. Each
example is preceded by a `[VALIDADO POR HUMANO]` note so the LLM
treats them with higher weight than static examples.
"""

import json
import logging
import unicodedata
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from src.analyzer.category_mapping import (
    MAX_LABELS,
    load_prompt_block,
    map_gravedad,
    max_severity,
    render_severidad_prompt,
    render_tabla_canonica_prompt,
    validate_clasificaciones,
    validate_codigo,
)
from src.analyzer.exclusion_filter import evaluar_exclusiones
from src.analyzer.violence_types import Severity

# Constantes que apuntan a los markdowns bajo glosario/. Las reglas
# viven en documentación — este código solo las carga.
_PROMPT_BLOCK_MARCADORES = load_prompt_block("glosario/marcadores-por-subdimension.md")
_PROMPT_BLOCK_LEETSPEAK = load_prompt_block("glosario/leetspeak-decoder.md")
_PROMPT_BLOCK_MITIGADORES = load_prompt_block("glosario/marcadores-mitigadores.md")
_PROMPT_BLOCK_COOCURRENCIA = load_prompt_block("glosario/referentes-femeninos.md")
_PROMPT_BLOCK_CAT5 = load_prompt_block("05-categoria-5-sarcasmo-falsos-positivos.md")

if TYPE_CHECKING:
    from src.knowledge_base.feedback_store import FeedbackStore

logger = logging.getLogger(__name__)


def _remove_accents(text: str) -> str:
    """Remove accents from text for comparison."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class LabelAssignment(BaseModel):
    """One label (categoria + dimension + per-label evidence) applied to a text.

    A single classification can have many of these — one per VDG_* category
    that applies. The per-label fields (justificacion, evidencia,
    marcadores, severidad, etc.) describe **why this specific label
    applies** in isolation; the flat ``analysis_results`` table only
    stores the primary (highest-severity) label, while the full list
    lives in ``analysis_labels``.
    """

    categoria: str
    dimension: str | None = None
    severidad: Severity = Severity.NINGUNA
    justificacion: str = ""
    evidencia: str = ""
    regla_disparada: str | None = None
    marcadores_detectados: list[str] = Field(default_factory=list)
    confianza: float | None = None
    score_ajuste: float | None = None
    es_falso_positivo_probable: bool = False

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-friendly dict."""
        return {
            "categoria": self.categoria,
            "dimension": self.dimension,
            "severidad": self.severidad.value,
            "justificacion": self.justificacion,
            "evidencia": self.evidencia,
            "regla_disparada": self.regla_disparada,
            "marcadores_detectados": list(self.marcadores_detectados),
            "confianza": self.confianza,
            "score_ajuste": self.score_ajuste,
            "es_falso_positivo_probable": self.es_falso_positivo_probable,
        }


class ClassificationResult(BaseModel):
    """Result of violence classification.

    ``clasificaciones`` is the full list of labels (1..N). The flat
    fields (``categoria``, ``dimension``, ``severidad``, ``justificacion``,
    ``evidencia``, ``regla_disparada``, ``marcadores_detectados``,
    ``es_falso_positivo_probable``, ``score_ajuste``) are all
    **derived** from the **primary** label (the first one) so legacy
    callers keep working. For single-label results these aliased
    fields behave exactly like the previous single-field API.
    """

    model_config = {"validate_assignment": True}

    tiene_violencia: bool = False
    severidad_global: Severity = Severity.NINGUNA
    clasificaciones: list[LabelAssignment] = Field(default_factory=list)
    confianza: float | None = None
    fuente_chunks: list[dict[str, Any]] | None = None
    exclusion_label: str | None = None
    exclusion_codigo: str | None = None
    exclusion_justificacion: str | None = None

    @property
    def excluded(self) -> bool:
        """``True`` when the entry was rejected by the pre-filter and
        bypassed classification entirely."""
        return self.exclusion_label is not None

    @model_validator(mode="before")
    @classmethod
    def _coerce_input(cls, data: Any) -> Any:
        """Accept either the new multi-label schema or the legacy flat schema.

        Legacy payloads (``categoria``/``dimension``/``severidad``/
        ``justificacion``/etc.) are wrapped into a one-element
        ``clasificaciones`` list so the downstream code path is
        uniform.
        """
        if isinstance(data, dict):
            data = dict(data)
            has_list = isinstance(data.get("clasificaciones"), list)
            if not has_list and (
                data.get("categoria")
                or data.get("categoria") == ""
                or data.get("justificacion")
                or data.get("evidencia")
            ):
                sev_raw = data.get("severidad", Severity.NINGUNA)
                if isinstance(sev_raw, Severity):
                    sev_val = sev_raw
                else:
                    sev_val = map_gravedad(sev_raw)
                single = {
                    "categoria": data.get("categoria", "ninguna"),
                    "dimension": data.get("dimension"),
                    "severidad": sev_val,
                    "justificacion": data.get("justificacion", "") or "",
                    "evidencia": data.get("evidencia", "") or "",
                    "regla_disparada": data.get("regla_disparada"),
                    "marcadores_detectados": data.get("marcadores_detectados", []) or [],
                    "confianza": data.get("confianza"),
                    "score_ajuste": data.get("score_ajuste"),
                    "es_falso_positivo_probable": data.get("es_falso_positivo_probable", False),
                }
                data["clasificaciones"] = [single]
            if "severidad_global" not in data and data.get("clasificaciones"):
                sevs: list[Severity] = []
                for lbl in data["clasificaciones"]:
                    if isinstance(lbl, dict):
                        sevs.append(map_gravedad(lbl.get("severidad")))
                    else:
                        # Already-validated Pydantic model.
                        sev_val = getattr(lbl, "severidad", Severity.NINGUNA)
                        if isinstance(sev_val, Severity):
                            sevs.append(sev_val)
                        else:
                            sevs.append(map_gravedad(sev_val))
                data["severidad_global"] = max_severity(sevs)
        return data

    def _primary(self) -> LabelAssignment | None:
        return self.clasificaciones[0] if self.clasificaciones else None

    @property
    def primary(self) -> LabelAssignment | None:
        """Return the primary label (first one) or ``None``."""
        return self._primary()

    # ----- backwards-compat properties delegated to the primary label -----

    @property
    def categoria(self) -> str:
        primary = self._primary()
        return primary.categoria if primary else "ninguna"

    @property
    def dimension(self) -> str | None:
        primary = self._primary()
        return primary.dimension if primary else None

    @property
    def severidad(self) -> Severity:
        primary = self._primary()
        return primary.severidad if primary else self.severidad_global

    @property
    def justificacion(self) -> str:
        primary = self._primary()
        return primary.justificacion if primary else ""

    @property
    def evidencia(self) -> str:
        primary = self._primary()
        return primary.evidencia if primary else ""

    @property
    def regla_disparada(self) -> str | None:
        primary = self._primary()
        return primary.regla_disparada if primary else None

    @property
    def marcadores_detectados(self) -> list[str]:
        primary = self._primary()
        return list(primary.marcadores_detectados) if primary else []

    @property
    def es_falso_positivo_probable(self) -> bool:
        primary = self._primary()
        return primary.es_falso_positivo_probable if primary else False

    @property
    def score_ajuste(self) -> float | None:
        primary = self._primary()
        return primary.score_ajuste if primary else None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary."""
        return {
            "tiene_violencia": self.tiene_violencia,
            "severidad_global": self.severidad_global.value,
            "clasificaciones": [c.to_dict() for c in self.clasificaciones],
            "categoria": self.categoria,
            "dimension": self.dimension,
            "severidad": self.severidad.value,
            "confianza": self.confianza,
            "justificacion": self.justificacion,
            "evidencia": self.evidencia,
            "fuente_chunks": self.fuente_chunks,
            "regla_disparada": self.regla_disparada,
            "marcadores_detectados": list(self.marcadores_detectados),
            "es_falso_positivo_probable": self.es_falso_positivo_probable,
            "score_ajuste": self.score_ajuste,
            "exclusion_label": self.exclusion_label,
            "exclusion_codigo": self.exclusion_codigo,
            "exclusion_justificacion": self.exclusion_justificacion,
        }

    @classmethod
    def from_llm_response(cls, response: str) -> "ClassificationResult":
        """Parse classification result from LLM response.

        The LLM is expected to return a strict JSON object whose body
        may use **either** the new multi-label schema
        (``clasificaciones: [...]``) or the legacy single-label schema
        (``categoria``/``dimension``/``justificacion``). Both are
        normalized into a :class:`LabelAssignment` list.
        """
        try:
            if isinstance(response, str):
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]

                # Extract JSON block first to handle LLM output interleaving
                import re

                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    response = response[json_start:json_end]

                # Strip LLM thinking tags (模型输出思考过程)

                response = re.sub(r"<think>[\s\S]*?</think>", "", response)
                response = re.sub(r"<tool_calls>[\s\S]*?</tool_calls>", "", response)
                response = re.sub(r"<system-reminder>[\s\S]*?</system-reminder>", "", response)
                response = re.sub(r"</?[^>]+>", "", response)
                response = response.strip()

                if not response:
                    logger.warning("LLM returned empty response")
                    return cls(
                        tiene_violencia=False,
                        severidad_global=Severity.NINGUNA,
                        clasificaciones=[],
                    )

                data = json.loads(response)
            else:
                data = response

            # --- multi-label preferred path ---
            labels: list[LabelAssignment]

            # Handle VIOLENCIA_COMUN specially - it's an exclusion label, not a category
            raw_cat = str(data.get("categoria", "")).strip()
            if raw_cat.upper() == "VIOLENCIA_COMUN":
                return cls(
                    tiene_violencia=False,
                    severidad_global=Severity.NINGUNA,
                    clasificaciones=[],
                    exclusion_label="VIOLENCIA_COMUN",
                    exclusion_codigo=data.get("codigo") or "VIOLENCIA_COMUN_LLM",
                    exclusion_justificacion=str(
                        data.get("justificacion") or "Violencia común / sin sesgo de género."
                    ),
                )

            if isinstance(data.get("clasificaciones"), list):
                labels = validate_clasificaciones(data["clasificaciones"])
                # Handle VIOLENCIA_COMUN in clasificaciones - it's an exclusion, not a category
                violencia_comun_labels = [
                    lbl for lbl in labels if lbl.categoria == "VIOLENCIA_COMUN"
                ]
                if violencia_comun_labels:
                    return cls(
                        tiene_violencia=False,
                        severidad_global=Severity.NINGUNA,
                        clasificaciones=[],
                        exclusion_label="VIOLENCIA_COMUN",
                        exclusion_codigo=violencia_comun_labels[0].regla_disparada
                        or "VIOLENCIA_COMUN_LLM",
                        exclusion_justificacion=violencia_comun_labels[0].justificacion
                        or "Violencia común / sin sesgo de género.",
                    )
            else:
                # --- legacy single-label path: wrap in 1-element list ---
                cat, dim = validate_codigo(data.get("categoria"), data.get("dimension"))
                sev = map_gravedad(data.get("severidad"))
                if cat == "ninguna":
                    labels = []
                else:
                    labels = [
                        LabelAssignment(
                            categoria=cat,
                            dimension=dim,
                            severidad=sev,
                            justificacion=str(data.get("justificacion") or ""),
                            evidencia=str(data.get("evidencia") or ""),
                            regla_disparada=(
                                str(data["regla_disparada"]).strip()
                                if data.get("regla_disparada") is not None
                                else None
                            ),
                            marcadores_detectados=_coerce_marcadores(
                                data.get("marcadores_detectados")
                            ),
                            confianza=_coerce_float(data.get("confianza")),
                            score_ajuste=_coerce_float(data.get("score_ajuste")),
                            es_falso_positivo_probable=_coerce_bool(
                                data.get("es_falso_positivo_probable", False)
                            ),
                        )
                    ]

            tiene_raw = data.get("tiene_violencia", bool(labels))
            if isinstance(tiene_raw, str):
                tiene = tiene_raw.strip().lower() in {"true", "1", "yes", "si", "sí"}
            else:
                tiene = bool(tiene_raw)

            if not labels:
                tiene = False

            sev_global_raw = data.get("severidad_global")
            if sev_global_raw is not None:
                sev_global = map_gravedad(sev_global_raw)
            else:
                sev_global = max_severity([lbl.severidad for lbl in labels])

            return cls(
                tiene_violencia=tiene,
                severidad_global=sev_global,
                clasificaciones=labels,
                exclusion_label=data.get("exclusion_label"),
                exclusion_codigo=data.get("exclusion_codigo"),
                exclusion_justificacion=data.get("exclusion_justificacion"),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            truncated_response = (
                response[:500] if isinstance(response, str) and len(response) > 500 else response
            )
            logger.warning(
                "LLM parsing error: %s | Response (truncated): %r",
                str(e),
                truncated_response,
            )
            return cls(
                tiene_violencia=False,
                severidad_global=Severity.NINGUNA,
                clasificaciones=[
                    LabelAssignment(
                        categoria="ninguna",
                        dimension=None,
                        severidad=Severity.NINGUNA,
                        justificacion=f"Error parsing response: {str(e)}",
                        evidencia="",
                    )
                ],
            )


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "si", "sí"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _coerce_marcadores(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(m) for m in value if m]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(m) for m in parsed if m]
        except (ValueError, TypeError):
            pass
        return [m.strip() for m in stripped.split(",") if m.strip()]
    return []


def _has_any_marker(text: str, markers: list[str]) -> list[str]:
    """Return the subset of ``markers`` (case-insensitive, accent-stripped) found in ``text``."""
    text_unaccented = _remove_accents(text.lower())
    text_words = set(text_unaccented.split())
    found: list[str] = []
    for marker in markers:
        marker_unaccented = _remove_accents(marker.lower())
        present = False
        if marker_unaccented in text_unaccented:
            present = True
        elif len(marker_unaccented) >= 4:
            for w in text_words:
                if w.startswith(marker_unaccented):
                    present = True
                    break
        if present:
            found.append(marker)
    return found


def _severity_rank_value(sev: Severity) -> int:
    """Numeric rank for sorting severities (alta=3, media=2, baja=1, ninguna=0)."""
    return {
        Severity.ALTA: 3,
        Severity.MEDIA: 2,
        Severity.BAJA: 1,
        Severity.NINGUNA: 0,
    }.get(sev, 0)


class RAGClassifier:
    """RAG-based classifier for gender violence detection.

    Categories and sub-dimensions are NOT hardcoded. The classifier
    injects a **closed set of 18 valid combinations** (from
    :mod:`src.analyzer.category_mapping`) into the system prompt and
    forces the LLM to pick up to ``MAX_LABELS`` of them per text. The
    output is validated and normalized on parse.

    If a ``feedback_store`` is provided, the classifier retrieves the
    top-k most relevant human-validated corrections from ChromaDB and
    injects them as additional few-shot examples (marked
    ``[VALIDADO POR HUMANO]``).
    """

    def __init__(
        self,
        llm_client=None,
        vector_store=None,
        feedback_store: "FeedbackStore | None" = None,
        context_chunks: int = 5,
        temperature: float = 0,
        few_shot_examples: list[dict] | None = None,
        feedback_n_results: int = 3,
        max_labels: int = MAX_LABELS,
    ):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.feedback_store = feedback_store
        self.context_chunks = context_chunks
        self.temperature = temperature
        self.few_shot_examples = few_shot_examples if few_shot_examples is not None else []
        self.feedback_n_results = max(0, int(feedback_n_results))
        self.max_labels = max(1, int(max_labels))

    def _build_prompt(
        self,
        text: str,
        context_chunks: list[dict[str, object]],
        feedback_chunks: list[dict[str, object]] | None = None,
    ) -> str:
        """Build the classification prompt.

        The canonical category/dimension table is always injected so
        the LLM has a closed set of valid answers. Human-validated
        corrections (when available) are prepended to the few-shot
        block with a ``[VALIDADO POR HUMANO]`` marker so the model
        treats them with higher weight.
        """
        if context_chunks:
            context_lines = []
            for i, c in enumerate(context_chunks, start=1):
                src = c.get("source", "?")
                idx = c.get("chunk_index", "?")
                dist = c.get("distance")
                dist_str = f" (dist={dist:.3f})" if isinstance(dist, (int, float)) else ""
                context_lines.append(
                    f"[{i}] fuente={src} chunk={idx}{dist_str}\n{c.get('text', '')}"
                )
            context_text = "\n\n".join(context_lines)
        else:
            context_text = "No hay fragmentos disponibles en ChromaDB."

        blocks: list[str] = []

        # --- human-validated corrections, if any ---
        for chunk in feedback_chunks or []:
            meta_raw = chunk.get("metadata") or {}
            meta: dict[str, object] = meta_raw if isinstance(meta_raw, dict) else {}
            cat = str(meta.get("corrected_categoria") or "")
            dim = str(meta.get("corrected_dimension") or "")
            # The ``text`` field of feedback docs is already a full
            # "TEXTO: … RESULTADO: {…}" block from
            # ``render_few_shot_doc``; pass it through verbatim.
            body = chunk.get("text", "")
            if cat:
                blocks.append(f"[VALIDADO POR HUMANO · {cat}/{dim}]\n{body}")

        # --- static examples ---
        if self.few_shot_examples:
            for i, ex in enumerate(self.few_shot_examples, start=1):
                r = ex.get("result", {})
                if isinstance(r.get("clasificaciones"), list) and r["clasificaciones"]:
                    payload = {
                        "tiene_violencia": r.get("tiene_violencia", True),
                        "severidad_global": r.get("severidad", "ninguna"),
                        "clasificaciones": r["clasificaciones"],
                    }
                else:
                    payload = {
                        "tiene_violencia": r.get("tiene_violencia", False),
                        "severidad_global": r.get("severidad", "ninguna"),
                        "clasificaciones": [
                            {
                                "categoria": r.get("categoria", "ninguna"),
                                "dimension": r.get("dimension"),
                                "severidad": r.get("severidad", "ninguna"),
                                "justificacion": r.get("justificacion", ""),
                                "evidencia": r.get("evidencia", ""),
                                "regla_disparada": r.get("regla_disparada"),
                                "marcadores_detectados": r.get("marcadores_detectados", []),
                                "es_falso_positivo_probable": r.get(
                                    "es_falso_positivo_probable", False
                                ),
                                "score_ajuste": r.get("score_ajuste"),
                            }
                        ]
                        if r.get("categoria") and r.get("categoria") != "ninguna"
                        else [],
                    }
                blocks.append(
                    f"EJEMPLO {i}:\n"
                    f'TEXTO: "{ex.get("text", "")}"\n'
                    f"RESULTADO: {json.dumps(payload, ensure_ascii=False)}"
                )

        examples_text = "\n\n".join(blocks) if blocks else "(Sin ejemplos few-shot)"

        tabla_canonica = render_tabla_canonica_prompt()
        escala_severidad = render_severidad_prompt()
        marcadores_bloque = _PROMPT_BLOCK_MARCADORES
        leetspeak_bloque = _PROMPT_BLOCK_LEETSPEAK
        mitigadores_bloque = _PROMPT_BLOCK_MITIGADORES
        coocurrencia_bloque = _PROMPT_BLOCK_COOCURRENCIA
        cat5_bloque = _PROMPT_BLOCK_CAT5

        prompt = f"""Analizá el siguiente texto y determiná si contiene violencia de género digital según el marco teórico almacenado en la base vectorial ChromaDB (colección "violencia_genero").

FILTRO DE EXCLUSIÓN PRÉVIO (INTENCIÓN PRAGMÁTICA, OBLIGATORIO):
- Antes de clasificar el texto en las seis dimensiones de ciberviolencia, evaluá la motivación central del ataque. Para que un mensaje agresivo, insultante o amenazante NO sea descartado como "Violencia Común", debés confirmar que la agresión ocurre estrictamente por la condición de ser mujer de la víctima.
- Si el texto contiene hostilidad pero NO busca imponer el predominio y control masculino, NO ataca la sexualidad o el cuerpo de la mujer, NO asume su inferioridad por su sexo, y NO utiliza el argot antifeminista de la manosfera, devolvé:
    {{
      "tiene_violencia": false,
      "severidad_global": "ninguna",
      "clasificaciones": [],
      "exclusion_label": "VIOLENCIA_COMUN",
      "justificacion": "Explicá por qué la agresividad detectada carece de sesgo de género"
    }}
- NO operes como un simple diccionario de malas palabras: un ataque motivado por conflictos políticos, quejas ciudadanas o disputas personales neutras al género debe clasificarse invariablemente como VIOLENCIA_COMUN, sin importar la cantidad o gravedad de las groserías que contenga.

{escala_severidad}

{tabla_canonica}

{marcadores_bloque}

{leetspeak_bloque}

{mitigadores_bloque}

{coocurrencia_bloque}

{cat5_bloque}

INSTRUCCIONES TAXONÓMICAS (IMPORTANTES):
- Devolvé una LISTA `clasificaciones` con 1..{self.max_labels} elementos (uno por cada categoría y subdimensión que aplique). NO repitas el mismo par (categoria, dimension).
- categoria: elegí EXCLUSIVAMENTE un código VDG_* de la tabla de arriba. No inventes.
- dimension: elegí EXCLUSIVAMENTE un código 'X.Y' de la tabla que corresponda a la categoria elegida. Si la categoria no tiene subdimensión útil, podés devolver null.
- Cada elemento de `clasificaciones` debe llevar su PROPIA `justificacion` (1-2 frases) explicando por qué ESA categoría/subdimensión aplica al texto. La justificación de cada etiqueta es OBLIGATORIA y debe ser específica de esa etiqueta.
- `evidencia` por etiqueta: cita textual del fragmento que sustenta ESA etiqueta.
- `regla_disparada` por etiqueta: nombre corto de la regla/sub-dimensión que justifican ESA etiqueta.
- `marcadores_detectados` por etiqueta: lista de palabras o frases textuales del input que sustentan ESA etiqueta.
- `severidad` por etiqueta: una de (baja|media|alta|ninguna).
- `es_falso_positivo_probable` por etiqueta: true si hay marcadores mitigadores (sarcasmo, cita, denuncia, reapropiación endogrupal) que podrían invalidar ESA detección en particular. En caso de duda, marcalo true.
- `score_ajuste` por etiqueta: número entre 0.0 y 1.0 que representa tu confianza ajustada para ESA etiqueta.
- `severidad_global`: la mayor severidad entre todas las etiquetas (p.ej. si hay 'baja' y 'alta' → "alta").
- `tiene_violencia`: true si la lista NO está vacía.
- Si el texto no encaja en ninguna categoría: `clasificaciones: []`, `tiene_violencia: false`, `severidad_global: "ninguna"`.
- Un mismo texto puede disparar múltiples categorías a la vez (p.ej. violencia simbólica + amenaza). Devolvé todas las que apliquen.

FRAGMENTOS RECUPERADOS DE ChromaDB (k={self.context_chunks}):
{context_text}

EJEMPLOS DE CLASIFICACIÓN:
{examples_text}

TEXTO A ANALIZAR:
"{text}"

RESPONDER EN FORMATO JSON ESTRICTO:
{{
  "tiene_violencia": true/false,
  "severidad_global": "baja|media|alta|ninguna",
  "clasificaciones": [
    {{
      "categoria": "<código VDG_*>",
      "dimension": "<código 'X.Y' o null>",
      "severidad": "baja|media|alta|ninguna",
      "confianza": 0.0,
      "regla_disparada": "...",
      "marcadores_detectados": ["...", "..."],
      "es_falso_positivo_probable": true/false,
      "score_ajuste": 0.0,
      "justificacion": "explicación breve de por qué esta etiqueta aplica al texto",
      "evidencia": "cita o fragmento del texto que sustenta esta etiqueta"
    }}
  ]
}}

SOLO JSON, SIN TEXTO ADICIONAL."""

        return prompt

    def _retrieve_feedback(self, text: str) -> list[dict[str, object]]:
        """Pull relevant human corrections from the feedback store."""
        if not self.feedback_store:
            return []
        try:
            return self.feedback_store.search_relevant_corrections(
                text, n_results=self.feedback_n_results
            )
        except Exception as e:
            logger.debug("Feedback retrieval skipped: %s", e)
            return []

    def _retrieve_context(self, text: str) -> list[dict[str, object]]:
        """Retrieve context chunks from the vector store."""
        if not self.vector_store:
            return []

        results = self.vector_store.search(text, n_results=self.context_chunks)
        chunks: list[dict[str, object]] = []
        for r in results:
            metadata: dict = r.get("metadata") or {}
            chunks.append(
                {
                    "text": r.get("text", ""),
                    "source": metadata.get("source", ""),
                    "chunk_index": metadata.get("chunk_index"),
                    "distance": r.get("distance"),
                    "id": r.get("id"),
                }
            )
        return chunks

    async def classify(self, text: str) -> ClassificationResult:
        """Classify a single text.

        The pre-filter (``exclusion_filter.evaluar_exclusiones``) runs
        FIRST. When it returns an exclusion sentinel (``CODIGO_99`` or
        ``VIOLENCIA_COMUN``) the LLM and ChromaDB retrievals are
        bypassed and the result is returned with ``exclusion_label``
        populated. The downstream caller (``batch_analyzer``) persists
        these rows so they participate in the missing-values report
        (Regla 1) and statistics (Reglas 2-4).
        """
        if not text or not text.strip():
            logger.warning("Empty text received for classification")
            return ClassificationResult(
                tiene_violencia=False,
                severidad_global=Severity.NINGUNA,
                clasificaciones=[],
            )

        exclusion = evaluar_exclusiones(text)
        if exclusion.excluded:
            logger.debug("Text excluded by pre-filter: %s", exclusion.etiqueta)
            return ClassificationResult(
                tiene_violencia=False,
                severidad_global=Severity.NINGUNA,
                clasificaciones=[],
                exclusion_label=exclusion.etiqueta,
                exclusion_codigo=exclusion.codigo,
                exclusion_justificacion=exclusion.justificacion,
            )

        context_chunks = self._retrieve_context(text)
        feedback_chunks = self._retrieve_feedback(text)
        prompt = self._build_prompt(text, context_chunks, feedback_chunks)

        logger.debug("Classifying text: %r (len=%d)", text[:100], len(text))

        if self.llm_client is None:
            return self._rule_based_classify(text, context_chunks)

        try:
            response = await self.llm_client.generate(prompt)
            logger.debug(
                "LLM response length: %d, first 200 chars: %r", len(response), response[:200]
            )
            result = ClassificationResult.from_llm_response(response)
            result.fuente_chunks = context_chunks
            return result
        except Exception as e:
            logger.warning("LLM call failed, falling back to rule-based: %s", e)
            return self._rule_based_classify(text, context_chunks)

    def classify_sync(self, text: str) -> ClassificationResult:
        """Synchronous version of classify."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.classify(text))

    def _rule_based_classify(self, text: str, context_chunks: list[dict]) -> ClassificationResult:
        """Rule-based classification fallback.

        Used when no LLM client is configured or the LLM call fails.
        Returns a :class:`ClassificationResult` whose ``clasificaciones``
        contains **one entry per bucket that matched** (multi-label
        friendly) — the previous single-best behaviour is gone.
        """
        builtin_indicators: dict[str, dict] = {
            "amenaza_muerte": {
                "keywords": ["matar", "mu3rt", "pvtos", "hdlp", "morir", "muere"],
                "severidad": Severity.ALTA,
                "score": 3,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
                "regla": "Cat 3 / Regla 3.1 — amenaza letal",
            },
            "agresion_fisica": {
                "keywords": [
                    "golpe",
                    "pegar",
                    "agredir",
                    "herida",
                    "moreton",
                    "moretón",
                    "pego",
                    "golpea",
                    "pega",
                ],
                "severidad": Severity.ALTA,
                "score": 3,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
                "regla": "Cat 3 / Regla 3.1 — amenaza de agresión",
            },
            "insulto_sexual": {
                "keywords": ["zorra", "puta", "perra", "guarra"],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.2",
                "regla": "Cat 2 / Regla 2.2 — insulto sexual",
            },
            "amenaza_general": {
                "keywords": ["amenaza", "amenazar", "te voy a"],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
                "regla": "Cat 3 / Regla 3.1 — amenaza general",
            },
            "sexual_explicito": {
                "keywords": [
                    "violacion",
                    "violación",
                    "abuso",
                    "acoso sexual",
                    "violar",
                    "cosificar",
                    "cosificacion",
                    "cosificación",
                    "para eso estás",
                    "para eso estas",
                    "mostrá las tetas",
                    "mostrame las tetas",
                    "si no accedés es tu culpa",
                    "si no accedes es tu culpa",
                ],
                "severidad": Severity.ALTA,
                "score": 3,
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.1",
                "regla": "Cat 2 / Regla 2.1 — sexualización explícita",
            },
            "psicologica": {
                "keywords": [
                    "no sos nada",
                    "no eres nada",
                    "no sirves para nada",
                    "estas loca",
                    "estás loca",
                    "me volves loco",
                    "me volvés loco",
                    "sin mi no vales",
                    "sin mí no vales",
                    "manipul",
                    "controlar",
                    "humill",
                ],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.2",
                "regla": "Cat 1 / Regla 1.2 — mandato de sumisión",
            },
            "estereotipo": {
                "keywords": [
                    "solo sirven",
                    "de cocina",
                    "las mujeres",
                    "los hombres no",
                    "rol de genero",
                    "rol de género",
                ],
                "severidad": Severity.BAJA,
                "score": 1,
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "regla": "Cat 1 / Regla 1.1 — estereotipo de género",
            },
            "control_economico": {
                "keywords": [
                    "no te doy plata",
                    "no te doy dinero",
                    "no trabajas",
                    "soy yo el que mantiene",
                ],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.2",
                "regla": "Cat 1 / Regla 1.2 — control económico",
            },
            "vicaria": {
                "keywords": [
                    "le hago dano a los hijos",
                    "le hago daño a los hijos",
                    "le pego al perro",
                    "le pego al gato",
                ],
                "severidad": Severity.ALTA,
                "score": 3,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
                "regla": "Cat 3 / Regla 3.1 — violencia vicaria",
            },
            "manosfera": {
                "keywords": [
                    "feminazi",
                    "foid",
                    "femoid",
                    "mangina",
                    "incel",
                    "mgtow",
                    "redpill",
                    "red pill",
                    "pastilla roja",
                    "hembrista",
                    "ideologia de genero",
                    "ideología de género",
                ],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.1",
                "regla": "Cat 4 / Regla 4.1 — jerga antifeminista",
            },
            "desacreditacion_activistas": {
                "keywords": [
                    "feminista radical",
                    "feministas radicales",
                    "feminazis",
                    "feminismo radical",
                    "viejas webonas",
                    "feministas de mierda",
                    "feministas son toxicas",
                    "feministas radicales son",
                ],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "6.1",
                "regla": "Cat 6 / Regla 6.1 — deslegitimación de feministas",
            },
        }

        # Dedupe by (categoria, dimension) — the first bucket wins
        # but the per-label marcadores list is the *union* of every
        # bucket that hit the same key (useful for evidence).
        merged: dict[tuple[str, str | None], dict] = {}
        for label_name, info in builtin_indicators.items():
            found_markers = _has_any_marker(text, info["keywords"])
            if not found_markers:
                continue
            score = info["score"]
            sev = Severity.ALTA if score >= 3 else Severity.MEDIA if score >= 2 else Severity.BAJA
            key = (info["categoria"], info["dimension"])
            existing = merged.get(key)
            if existing is None:
                merged[key] = {
                    "categoria": info["categoria"],
                    "dimension": info["dimension"],
                    "severidad": info["severidad"] or sev,
                    "bucket_names": [label_name],
                    "marcadores": list(found_markers),
                    "score": score,
                }
            else:
                existing["bucket_names"].append(label_name)
                for m in found_markers:
                    if m not in existing["marcadores"]:
                        existing["marcadores"].append(m)
                if _severity_rank_value(sev) > _severity_rank_value(existing["severidad"]):
                    existing["severidad"] = info["severidad"] or sev
                if score > existing["score"]:
                    existing["score"] = score

        labels: list[LabelAssignment] = []
        for info in merged.values():
            labels.append(
                LabelAssignment(
                    categoria=info["categoria"],
                    dimension=info["dimension"],
                    severidad=info["severidad"],
                    justificacion=(
                        f"Fallback rule-based: buckets={', '.join(info['bucket_names'])}; "
                        f"marcadores={', '.join(info['marcadores'])}"
                    ),
                    evidencia=text[:200],
                    regla_disparada="rule-based:" + ",".join(info["bucket_names"]),
                    marcadores_detectados=info["marcadores"],
                    confianza=min(1.0, info["score"] / 3.0),
                    score_ajuste=min(1.0, info["score"] / 3.0),
                    es_falso_positivo_probable=False,
                )
            )

        if not labels:
            return ClassificationResult(
                tiene_violencia=False,
                severidad_global=Severity.NINGUNA,
                clasificaciones=[],
                fuente_chunks=context_chunks,
            )

        # Cap at max_labels (high-severity first) — keeps the rule-based
        # path aligned with the LLM cap.
        labels.sort(key=lambda lbl: _severity_rank_value(lbl.severidad), reverse=True)
        if len(labels) > self.max_labels:
            labels = labels[: self.max_labels]

        return ClassificationResult(
            tiene_violencia=True,
            severidad_global=max_severity([lbl.severidad for lbl in labels]),
            clasificaciones=labels,
            fuente_chunks=context_chunks,
        )

    async def classify_batch(self, texts: list[str]) -> list[ClassificationResult]:
        """Classify multiple texts."""
        return [await self.classify(t) for t in texts]

    def classify_batch_sync(self, texts: list[str]) -> list[ClassificationResult]:
        """Synchronous version of batch classify."""
        return [self.classify_sync(t) for t in texts]


__all__ = [
    "LabelAssignment",
    "ClassificationResult",
    "RAGClassifier",
]
