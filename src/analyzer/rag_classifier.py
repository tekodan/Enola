"""RAG classifier for violence detection.

The classification taxonomy is **homogeneous**: alphabetic codes for
categories (``VDG_*``) and numeric codes for sub-dimensions
(``1.1``..``6.3``). The LLM is forced to pick from a closed set of 18
valid combinations defined in :mod:`src.analyzer.category_mapping`; any
output outside the set is rejected and normalized to ``"ninguna"`` with
a warning.

The only categorical field with a hardcoded scale is :class:`Severity`
(``baja``/``media``/``alta``/``ninguna``).
"""

import json
import logging
import unicodedata

from pydantic import BaseModel, Field

from src.analyzer.category_mapping import (
    map_gravedad,
    render_severidad_prompt,
    render_tabla_canonica_prompt,
    validate_codigo,
)
from src.analyzer.violence_types import Severity

logger = logging.getLogger(__name__)


def _remove_accents(text: str) -> str:
    """Remove accents from text for comparison."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class ClassificationResult(BaseModel):
    """Result of violence classification.

    ``categoria`` is a canonical alphabetic code (``VDG_*``) and
    ``dimension`` is a canonical numeric code (``1.1``..``6.3``). Both
    are validated against :mod:`src.analyzer.category_mapping`. The
    legacy free-form ``categoria``/``dimension`` strings are still
    accepted on input but normalized on parse.
    """

    tiene_violencia: bool = False
    categoria: str = "ninguna"
    dimension: str | None = None
    severidad: Severity = Severity.NINGUNA
    confianza: float | None = None
    justificacion: str = ""
    evidencia: str = ""
    fuente_chunks: list[dict] | None = None
    regla_disparada: str | None = None
    marcadores_detectados: list[str] = Field(default_factory=list)
    es_falso_positivo_probable: bool = False
    score_ajuste: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tiene_violencia": self.tiene_violencia,
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
        }

    @classmethod
    def from_llm_response(cls, response: str) -> "ClassificationResult":
        """Parse classification result from LLM response.

        The LLM is expected to return a strict JSON object. Category
        and dimension are validated and normalized against the canonical
        set; severity is mapped from the compound form
        (``"alta-extrema"`` etc.) to the closed enum.
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
                response = response.strip()

                data = json.loads(response)
            else:
                data = response

            categoria, dimension = validate_codigo(data.get("categoria"), data.get("dimension"))
            severidad = map_gravedad(data.get("severidad"))

            tiene = data.get("tiene_violencia", False)
            if isinstance(tiene, str):
                tiene = tiene.strip().lower() in {"true", "1", "yes", "si", "sí"}

            confianza_raw = data.get("confianza")
            confianza: float | None = None
            if isinstance(confianza_raw, (int, float)):
                confianza = float(confianza_raw)
            elif isinstance(confianza_raw, str):
                try:
                    confianza = float(confianza_raw)
                except ValueError:
                    confianza = None

            score_raw = data.get("score_ajuste")
            score_ajuste: float | None = None
            if isinstance(score_raw, (int, float)):
                score_ajuste = float(score_raw)
            elif isinstance(score_raw, str):
                try:
                    score_ajuste = float(score_raw)
                except ValueError:
                    score_ajuste = None

            marcadores_raw = data.get("marcadores_detectados") or []
            if isinstance(marcadores_raw, list):
                marcadores = [str(m) for m in marcadores_raw if m]
            elif isinstance(marcadores_raw, str):
                marcadores = [m.strip() for m in marcadores_raw.split(",") if m.strip()]
            else:
                marcadores = []

            fpp_raw = data.get("es_falso_positivo_probable", False)
            if isinstance(fpp_raw, str):
                es_fpp = fpp_raw.strip().lower() in {"true", "1", "yes", "si", "sí"}
            else:
                es_fpp = bool(fpp_raw)

            regla = data.get("regla_disparada")
            if regla is not None:
                regla = str(regla).strip() or None

            return cls(
                tiene_violencia=bool(tiene),
                categoria=categoria,
                dimension=dimension,
                severidad=severidad,
                confianza=confianza,
                justificacion=data.get("justificacion", "") or "",
                evidencia=data.get("evidencia", "") or "",
                regla_disparada=regla,
                marcadores_detectados=marcadores,
                es_falso_positivo_probable=es_fpp,
                score_ajuste=score_ajuste,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return cls(
                tiene_violencia=False,
                categoria="ninguna",
                dimension=None,
                severidad=Severity.NINGUNA,
                confianza=None,
                justificacion=f"Error parsing response: {str(e)}",
                evidencia="",
            )


class RAGClassifier:
    """RAG-based classifier for gender violence detection.

    Categories and sub-dimensions are NOT hardcoded. The classifier
    injects a **closed set of 18 valid combinations** (from
    :mod:`src.analyzer.category_mapping`) into the system prompt and
    forces the LLM to pick one. The output is validated and normalized
    on parse.
    """

    def __init__(
        self,
        llm_client=None,
        vector_store=None,
        context_chunks: int = 5,
        temperature: float = 0,
        few_shot_examples: list[dict] | None = None,
    ):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.context_chunks = context_chunks
        self.temperature = temperature
        self.few_shot_examples = few_shot_examples if few_shot_examples is not None else []

    def _build_prompt(self, text: str, context_chunks: list[dict[str, object]]) -> str:
        """Build the classification prompt.

        The canonical category/dimension table is always injected so
        the LLM has a closed set of valid answers.
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

        examples_text = ""
        if self.few_shot_examples:
            rendered = []
            for i, ex in enumerate(self.few_shot_examples, start=1):
                r = ex.get("result", {})
                rendered.append(
                    f"EJEMPLO {i}:\n"
                    f'TEXTO: "{ex.get("text", "")}"\n'
                    f'RESULTADO: {{"tiene_violencia": {r.get("tiene_violencia", False)}, '
                    f'"categoria": "{r.get("categoria", "ninguna")}", '
                    f'"dimension": {json.dumps(r.get("dimension"))}, '
                    f'"severidad": "{r.get("severidad", "ninguna")}", '
                    f'"confianza": {r.get("confianza", 0.0)}, '
                    f'"regla_disparada": {json.dumps(r.get("regla_disparada"))}, '
                    f'"marcadores_detectados": {json.dumps(r.get("marcadores_detectados", []))}, '
                    f'"es_falso_positivo_probable": {json.dumps(r.get("es_falso_positivo_probable", False))}, '
                    f'"score_ajuste": {r.get("score_ajuste", "null")}, '
                    f'"justificacion": "{r.get("justificacion", "")}", '
                    f'"evidencia": "{r.get("evidencia", "")}"}}'
                )
            examples_text = "\n\n".join(rendered)
        else:
            examples_text = "(Sin ejemplos few-shot)"

        tabla_canonica = render_tabla_canonica_prompt()
        escala_severidad = render_severidad_prompt()

        prompt = f"""Analizá el siguiente texto y determiná si contiene violencia de género digital según el marco teórico almacenado en la base vectorial ChromaDB (colección "violencia_genero").

{escala_severidad}

{tabla_canonica}

INSTRUCCIONES TAXONÓMICAS (IMPORTANTES):
- categoria: elegí EXCLUSIVAMENTE un código de la tabla de arriba. No inventes.
- dimension: elegí EXCLUSIVAMENTE un código de la tabla de arriba que corresponda a la categoria elegida. Si la categoria es "ninguna", dimension debe ser null.
- regla_disparada: nombre de la regla o sub-dimensión que justifican la clasificación (texto libre corto).
- marcadores_detectados: lista de palabras o frases textuales del input que sustentan la clasificación.
- es_falso_positivo_probable: true si hay marcadores mitigadores (sarcasmo, cita, denuncia, reapropiación endogrupal) que podrían invalidar la detección. En caso de duda, marcalo true.
- score_ajuste: número entre 0.0 y 1.0 que representa tu confianza ajustada considerando la salvaguarda de falsos positivos.

FRAGMENTOS RECUPERADOS DE ChromaDB (k={self.context_chunks}):
{context_text}

EJEMPLOS DE CLASIFICACIÓN:
{examples_text}

TEXTO A ANALIZAR:
"{text}"

RESPONDER EN FORMATO JSON ESTRICTO:
{{
  "tiene_violencia": true/false,
  "categoria": "<uno de los códigos VDG_* o 'ninguna'>",
  "dimension": "<código 'X.Y' de la tabla, o null>",
  "severidad": "baja|media|alta|ninguna",
  "confianza": 0.0,
  "regla_disparada": "...",
  "marcadores_detectados": ["...", "..."],
  "es_falso_positivo_probable": true/false,
  "score_ajuste": 0.0,
  "justificacion": "explicación breve de la clasificación",
  "evidencia": "cita o fragmento del texto que sustenta la clasificación"
}}

SOLO JSON, SIN TEXTO ADICIONAL."""

        return prompt

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
        """Classify a single text."""
        context_chunks = self._retrieve_context(text)
        prompt = self._build_prompt(text, context_chunks)

        if self.llm_client is None:
            return self._rule_based_classify(text, context_chunks)

        try:
            response = await self.llm_client.generate(prompt)
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
        Returns category/dimension in the canonical VDG_* / X.Y form.
        """
        text_lower = text.lower()
        text_unaccented = _remove_accents(text_lower)
        text_words = set(text_unaccented.split())

        builtin_indicators: dict[str, dict] = {
            "amenaza_muerte": {
                "keywords": ["matar", "mu3rt", "pvtos", "hdlp", "morir", "muere"],
                "severidad": Severity.ALTA,
                "score": 3,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
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
            },
            "insulto_sexual": {
                "keywords": ["zorra", "puta", "perra", "guarra"],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.2",
            },
            "amenaza_general": {
                "keywords": ["amenaza", "amenazar", "te voy a"],
                "severidad": Severity.MEDIA,
                "score": 2,
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
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
            },
        }

        marcadores: list[str] = []
        best_label: str | None = None
        best_info: dict | None = None
        best_score = 0

        for label, info in builtin_indicators.items():
            for kw in info["keywords"]:
                kw_unaccented = _remove_accents(kw.lower())
                found = False
                if kw_unaccented in text_unaccented:
                    found = True
                elif len(kw_unaccented) >= 4:
                    for w in text_words:
                        if w.startswith(kw_unaccented):
                            found = True
                            break
                if found:
                    marcadores.append(kw)
                    if info["score"] > best_score:
                        best_score = info["score"]
                        best_label = label
                        best_info = info
                    break

        if best_info is None:
            return ClassificationResult(
                tiene_violencia=False,
                categoria="ninguna",
                dimension=None,
                severidad=Severity.NINGUNA,
                justificacion="No se detectaron indicadores de violencia de género",
                evidencia="",
                fuente_chunks=context_chunks,
                marcadores_detectados=[],
                es_falso_positivo_probable=False,
                score_ajuste=None,
                regla_disparada=None,
            )

        if best_score >= 3:
            severidad = Severity.ALTA
        elif best_score >= 2:
            severidad = Severity.MEDIA
        else:
            severidad = Severity.BAJA

        return ClassificationResult(
            tiene_violencia=True,
            categoria=best_info["categoria"],
            dimension=best_info["dimension"],
            severidad=best_info["severidad"] or severidad,
            justificacion=(
                f"Fallback rule-based: bucket={best_label}, marcadores={', '.join(marcadores)}"
            ),
            evidencia=text[:200],
            fuente_chunks=context_chunks,
            regla_disparada=f"rule-based:{best_label}",
            marcadores_detectados=marcadores,
            es_falso_positivo_probable=False,
            score_ajuste=min(1.0, best_score / 3.0),
        )

    async def classify_batch(self, texts: list[str]) -> list[ClassificationResult]:
        """Classify multiple texts."""
        return [await self.classify(t) for t in texts]

    def classify_batch_sync(self, texts: list[str]) -> list[ClassificationResult]:
        """Synchronous version of batch classify."""
        return [self.classify_sync(t) for t in texts]
