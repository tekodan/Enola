"""Discovery utilities for the ChromaDB taxonomy of digital gender violence.

The vector store (ChromaDB collection ``violencia_genero``) holds the
authoritative theoretical framework (``CATEGORIAS TFM CONSOLIDADO.md``).
This module extracts its categories and sub-dimensions in two modes:

- ``--no-llm`` (pure retrieval): pulls the top-k chunks for an umbrella
  query and returns them. No model is required.
- LLM mode (default): sends the retrieved chunks to the LLM with a
  structured-extraction prompt that returns a JSON taxonomy.

The legacy ``ViolenceType`` enum (fisica/psicologica/sexual/economica/
simbolica/vicaria/verbal) is preserved here **only** as a constant
to compute a diff between the legacy hardcoded taxonomy and what is
actually in ChromaDB. It is not used by the classifier.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DEFAULT_DISCOVERY_QUERY = (
    "taxonomía violencia de género digital categorías niveles dimensiones códigos"
)


LEGACY_VIOLENCE_TYPES: dict[str, str] = {
    "fisica": "Agresiones físicas, golpes, heridas, quemaduras",
    "psicologica": "Humillaciones, insultos, control, manipulación emocional",
    "sexual": "Abuso sexual, acoso, violación, comentarios sexuales no deseados",
    "economica": "Control financiero, privación de recursos económicos",
    "simbolica": "Estereotipos, representaciones degradantes, sexismo",
    "vicaria": "Violencia hacia seres queridos (hijos, mascotas) como venganza",
    "verbal": "Amenazas, gritos, lenguaje denigrante, palabras ofensivas",
}


class LLMClientProtocol(Protocol):
    """Minimal protocol for the LLM client used in LLM-mode discovery."""

    async def generate(self, prompt: str) -> str: ...


def retrieve_discovery_chunks(
    vector_store: Any,
    n_results: int = 30,
    query: str | None = None,
) -> list[dict]:
    """Retrieve a sample of chunks from ChromaDB for taxonomy discovery.

    Args:
        vector_store: An object with a ``search(query, n_results)`` method.
        n_results: Number of chunks to retrieve.
        query: Umbrella query. Defaults to a broad Spanish query.

    Returns:
        A list of dicts: ``{text, source, chunk_index, distance, id}``.
    """
    if vector_store is None:
        return []

    q = query or DEFAULT_DISCOVERY_QUERY
    raw = vector_store.search(q, n_results=n_results)
    chunks: list[dict] = []
    for r in raw:
        metadata = r.get("metadata") or {}
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


def build_discovery_prompt(chunks: list[dict]) -> str:
    """Build the LLM prompt that extracts the taxonomy from the chunks.

    The prompt instructs the model to output a strict JSON structure
    describing the discovered categories, sub-dimensions and codes.
    """
    if not chunks:
        context_text = "(No hay fragmentos disponibles)"
    else:
        lines = []
        for i, c in enumerate(chunks, start=1):
            src = c.get("source", "?")
            idx = c.get("chunk_index", "?")
            lines.append(f"[{i}] fuente={src} chunk={idx}\n{c.get('text', '')}")
        context_text = "\n\n".join(lines)

    return f"""Analizá los siguientes fragmentos del marco teórico sobre violencia de género digital y listá de forma exhaustiva todas las categorías de Nivel 1, sus sub-dimensiones numeradas y códigos programáticos que aparezcan explícitamente en los fragmentos.

INSTRUCCIONES:
- Devolvé EXCLUSIVAMENTE lo que aparece en los fragmentos. No inventes categorías.
- Cada categoría de Nivel 1 puede tener sub-dimensiones numeradas (1.1, 1.2, 1.2.1, etc.) y/o un código programático (VDG_*, VDG\\DOBLE\\ESTANDAR, etc.).
- Mantené la nomenclatura exacta del marco (códigos, números, mayúsculas).
- Si un fragmento menciona un código sin dimensión, igual listalo.

FRAGMENTOS DEL MARCO TEÓRICO (ChromaDB):
{context_text}

RESPONDER EN FORMATO JSON ESTRICTO:
{{
  "fuente": "nombre del archivo fuente principal",
  "niveles": [
    {{
      "codigo": "1.x o categoría",
      "nombre": "nombre de la categoría de Nivel 1",
      "subdimensiones": [
        {{"codigo": "1.x.y", "nombre": "...", "definicion": "..."}}
      ],
      "codigos_programaticos": ["VDG_...", "VDG\\\\DOBLE\\\\ESTANDAR"]
    }}
  ],
  "categorias_programaticas": [
    {{"codigo": "VDG_...", "nombre": "...", "dimension": "..."}}
  ],
  "perfiles_constitucionales": [
    {{"nombre": "T-140/2021 - ...", "descripcion": "..."}}
  ],
  "total_categorias_nivel_1": 0,
  "total_subdimensiones": 0
}}

SOLO JSON, SIN TEXTO ADICIONAL."""


def parse_discovery_response(response: str) -> dict:
    """Parse the LLM response into a taxonomy dict.

    Returns the parsed dict on success, or ``{"_error": ..., "_raw": ...}``
    on failure.
    """
    if not isinstance(response, str):
        return {"_error": "response is not a string", "_raw": response}

    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result: dict[str, object] = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        return {"_error": f"JSON decode error: {e}", "_raw": response}


async def discover_categories(
    vector_store: Any,
    llm_client: LLMClientProtocol | None = None,
    n_results: int = 30,
    query: str | None = None,
) -> dict:
    """Discover the categories of digital gender violence in ChromaDB.

    Args:
        vector_store: Vector store with a ``search()`` method.
        llm_client: Async LLM client with ``generate(prompt) -> str``.
            If ``None``, returns the chunks in retrieval-only mode.
        n_results: Number of chunks to retrieve.
        query: Optional umbrella query.

    Returns:
        A dict with keys:

        - ``chunks``: the retrieved chunks (always present)
        - ``taxonomy``: parsed taxonomy dict (only when llm_client is set
          and the response parses)
        - ``raw_response``: raw LLM text (only when llm_client is set)
        - ``mode``: ``"llm"`` or ``"retrieval-only"``
    """
    chunks = retrieve_discovery_chunks(vector_store, n_results=n_results, query=query)

    if llm_client is None:
        return {"mode": "retrieval-only", "chunks": chunks, "n_results": n_results}

    prompt = build_discovery_prompt(chunks)
    try:
        response = await llm_client.generate(prompt)
    except Exception as e:
        logger.error("LLM call failed during discovery: %s", e)
        return {
            "mode": "llm",
            "chunks": chunks,
            "taxonomy": None,
            "error": str(e),
        }

    taxonomy = parse_discovery_response(response)
    return {
        "mode": "llm",
        "chunks": chunks,
        "taxonomy": taxonomy,
        "raw_response": response,
        "n_results": n_results,
    }


def diff_with_legacy_enum(taxonomy: dict | None) -> dict:
    """Compare a discovered taxonomy against the legacy ``ViolenceType`` enum.

    Returns a dict with:

    - ``legacy_types``: list of legacy type codes
    - ``legacy_in_taxonomy``: legacy codes that appear (by substring match)
      in the discovered taxonomy
    - ``legacy_missing``: legacy codes not found in the taxonomy
    - ``discovered_niveles``: count of Nivel 1 categories found
    - ``discovered_subdimensiones``: count of sub-dimensions found
    """
    legacy = sorted(LEGACY_VIOLENCE_TYPES.keys())
    taxonomy_str = json.dumps(taxonomy or {}, ensure_ascii=False).lower()

    legacy_found: list[str] = []
    legacy_missing: list[str] = []
    for code in legacy:
        if code in taxonomy_str:
            legacy_found.append(code)
        else:
            legacy_missing.append(code)

    niveles: list[dict] = []
    subdimensiones: list[dict] = []
    categorias_prog: list[dict] = []
    if isinstance(taxonomy, dict):
        niveles = taxonomy.get("niveles") or []
        for n in niveles:
            subdimensiones.extend(n.get("subdimensiones") or [])
        categorias_prog = taxonomy.get("categorias_programaticas") or []

    return {
        "legacy_types": legacy,
        "legacy_in_taxonomy": legacy_found,
        "legacy_missing": legacy_missing,
        "discovered_niveles_count": len(niveles),
        "discovered_subdimensiones_count": len(subdimensiones),
        "discovered_categorias_programaticas_count": len(categorias_prog),
        "niveles": niveles,
        "categorias_programaticas": categorias_prog,
    }


def render_discovery_report(discovery_result: dict, diff: dict | None = None) -> str:
    """Render the discovery output as a human-readable text report."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("TAXONOMÍA DE VIOLENCIA DE GÉNERO DIGITAL — ChromaDB")
    lines.append("=" * 70)

    mode = discovery_result.get("mode", "?")
    n_results = discovery_result.get("n_results", 0)
    chunks = discovery_result.get("chunks", [])
    lines.append(f"Modo: {mode}")
    lines.append(f"Chunks muestreados: {len(chunks)} (n_results pedido: {n_results})")
    lines.append("")

    if not chunks:
        lines.append("(No se recuperaron chunks — ¿está la colección vacía?)")
        if diff is not None:
            lines.append("")
            lines.append("(Diff omitido: no hay taxonomía para comparar.)")
        return "\n".join(lines)

    sources = sorted({c.get("source", "?") for c in chunks})
    lines.append(f"Fuentes en la muestra: {', '.join(sources)}")
    lines.append("")

    taxonomy = discovery_result.get("taxonomy")
    if taxonomy and not taxonomy.get("_error"):
        lines.append("--- Taxonomía detectada por LLM ---")
        niveles = taxonomy.get("niveles") or []
        for n in niveles:
            codigo = n.get("codigo", "?")
            nombre = n.get("nombre", "?")
            lines.append(f"[{codigo}] {nombre}")
            for sd in n.get("subdimensiones") or []:
                sd_codigo = sd.get("codigo", "?")
                sd_nombre = sd.get("nombre", "?")
                lines.append(f"    • {sd_codigo} — {sd_nombre}")
            for cp in n.get("codigos_programaticos") or []:
                lines.append(f"    ◆ código: {cp}")
        cats_prog = taxonomy.get("categorias_programaticas") or []
        if cats_prog:
            lines.append("")
            lines.append("Categorías programáticas sueltas:")
            for cp in cats_prog:
                lines.append(f"  • {cp.get('codigo', '?')} — {cp.get('nombre', '?')}")
        perfiles = taxonomy.get("perfiles_constitucionales") or []
        if perfiles:
            lines.append("")
            lines.append("Perfiles constitucionales / jurisprudencia:")
            for p in perfiles:
                lines.append(f"  • {p.get('nombre', '?')}")
    elif taxonomy and taxonomy.get("_error"):
        lines.append(f"(Error parseando taxonomía: {taxonomy['_error']})")
    else:
        lines.append("--- Muestra de chunks (modo retrieval-only) ---")
        for i, c in enumerate(chunks, start=1):
            txt = (c.get("text") or "").replace("\n", " ")
            if len(txt) > 220:
                txt = txt[:220] + "..."
            lines.append(f"[{i}] {c.get('source', '?')} chunk={c.get('chunk_index', '?')}")
            lines.append(f"    {txt}")

    if diff is not None:
        lines.append("")
        lines.append("=" * 70)
        lines.append("DIFF vs enum hardcoded legacy (ViolenceType)")
        lines.append("=" * 70)
        lines.append(f"Categorías Nivel 1 descubiertas: {diff.get('discovered_niveles_count', 0)}")
        lines.append(
            f"Sub-dimensiones descubiertas:    {diff.get('discovered_subdimensiones_count', 0)}"
        )
        lines.append(
            f"Categorías programáticas:        "
            f"{diff.get('discovered_categorias_programaticas_count', 0)}"
        )
        lines.append("")
        if diff.get("legacy_in_taxonomy"):
            lines.append(
                "Tipos del enum legacy que SÍ aparecen en el marco: "
                + ", ".join(diff["legacy_in_taxonomy"])
            )
        if diff.get("legacy_missing"):
            lines.append(
                "Tipos del enum legacy que NO aparecen explícitamente: "
                + ", ".join(diff["legacy_missing"])
            )
        lines.append(
            "Conclusión: el enum hardcoded es incompleto; el clasificador "
            "debe guiarse por la taxonomía descubierta en ChromaDB."
        )

    return "\n".join(lines)
