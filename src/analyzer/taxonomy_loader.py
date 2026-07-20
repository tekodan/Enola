"""Loader for the canonical taxonomy of digital gender violence.

The taxonomy lives as a single Markdown file with strict YAML
frontmatter at ``knowledge/taxonomia/TAXONOMIA.md``. This module:

- Parses the frontmatter into a typed :class:`Taxonomy` model.
- Caches the result (singleton, process-wide).
- Exposes derived structures (``ordered_codes``,
  ``subdims_by_category``, ``descripcion_subdim``,
  ``gravedad_por_categoria``) consumed by the rest of the
  classifier / UI / reporting code via
  :mod:`src.analyzer.category_mapping`.
- Exposes the :data:`ExclusionCategoriaMD` collection (pseudo-categories
  such as ``EXC_BASURA_DIGITAL`` / ``EXC_VIOLENCIA_COMUN``) consumed by
  :mod:`src.analyzer.exclusion_filter`. Exclusions do NOT participate
  in the invariant of 6 operational categories.

Design notes
------------
- The MD is the **single source of truth**: editing the MD and
  reloading the process is enough to change the closed taxonomy used
  throughout.
- The Pydantic model enforces the invariants (exactly 6 operational categories,
  3 sub-dimensions for categories 1, 2, 3, 5 and 6, 4 for category 4,
  severity in the closed set, codes unique and ordered).
- Display-only data (UI labels, color hexes) lives in code and is
  *not* governed by the MD (see ``src/ui/utils.py`` and
  ``src/ui/nicegui_app/theme.py``).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# Allowed severity tokens (closed set). Compared against
# :class:`src.analyzer.violence_types.Severity` after mapping.
GRAVEDAD_TOKENS: frozenset[str] = frozenset(
    {
        "baja",
        "baja-media",
        "media",
        "media-alta",
        "alta",
        "alta-extrema",
        "extrema",
        "ortogonal",
    }
)


# Default MD path, resolved relative to this file so nothing depends
# on the current working directory.
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY_PATH: Path = _PROJECT_ROOT / "knowledge" / "taxonomia" / "TAXONOMIA.md"


class TaxonomyFormatError(ValueError):
    """Raised when TAXONOMIA.md has an unparseable structure."""


class MarcadorOverlapMD(BaseModel):
    marker: str
    subdim_secundaria: str
    regla: str


class ReglaDesempateMD(BaseModel):
    id: str
    frontera: str
    subdim_ganadora: str
    disparador_primario: list[str] = Field(default_factory=list)
    disparador_obligatorio: list[str] = Field(default_factory=list)
    fallback: str = ""


class BasuraDigitalPatternMD(BaseModel):
    id: str
    pattern: str


class SubdimensionMD(BaseModel):
    """One numbered sub-dimension (e.g., ``1.1``) inside a category."""

    code: str
    descripcion: str
    marcadores_canonicos: list[str] = Field(default_factory=list)
    marcadores_overlap: list[MarcadorOverlapMD] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def _check_code(cls, v: str) -> str:
        s = str(v).strip()
        if not re.fullmatch(r"[1-6]\.[1-4]", s):
            raise ValueError(f"subdimension code must match [1-6].[1-4], got {v!r}")
        return s

    @field_validator("descripcion")
    @classmethod
    def _check_descripcion(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("descripcion must be non-empty")
        return s


class CategoriaMD(BaseModel):
    """One alphabetic category (e.g., ``VDG_VIOLENCIA_SIMBOLICA``)."""

    code: str
    label: str = ""
    orden: int = Field(ge=1, le=6)
    gravedad: str
    subdimensiones: list[SubdimensionMD]

    @field_validator("code")
    @classmethod
    def _check_code(cls, v: str) -> str:
        s = (v or "").strip()
        if not s.startswith("VDG_"):
            raise ValueError(f"category code must start with VDG_, got {v!r}")
        return s

    @field_validator("gravedad")
    @classmethod
    def _check_gravedad(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in GRAVEDAD_TOKENS:
            raise ValueError(f"gravedad must be one of {sorted(GRAVEDAD_TOKENS)}, got {v!r}")
        return s

    @model_validator(mode="after")
    def _check_subdimensions(self) -> CategoriaMD:
        expected_count = 4 if self.orden == 4 else 3
        if len(self.subdimensiones) != expected_count:
            raise ValueError(
                f"category {self.code} must have exactly {expected_count} sub-dimensions, "
                f"got {len(self.subdimensiones)}"
            )
        expected_codes = [f"{self.orden}.{i}" for i in range(1, expected_count + 1)]
        got_codes = [d.code for d in self.subdimensiones]
        if got_codes != expected_codes:
            raise ValueError(
                f"Category {self.code} (orden={self.orden}) has dims {got_codes}, "
                f"expected {expected_codes}"
            )
        return self


class ExclusionCategoriaMD(BaseModel):
    """One pseudo-category (pre-classification exclusion).

    Documented in the ``categorias_exclusion`` block of
    ``TAXONOMIA.md``. Distinct from ``CategoriaMD`` because:

    - there is no ``orden`` / ``gravedad`` / ``subdimensiones``;
    - the canonical enum value (``codigo_canonico``) is the real
      identity used by ``analysis_results.exclusion_label`` (e.g.
      ``CODIGO_99``).

    The ``code`` field uses the ``EXC_*`` namespace to make it visually
    distinct in the MD; the actual exclusion label stored in the DB
    is the canonical ``codigo_canonico`` (``CODIGO_99`` /
    ``VIOLENCIA_COMUN``).
    """

    code: str
    codigo_canonico: str
    descripcion: str = ""

    @field_validator("code")
    @classmethod
    def _check_code(cls, v: str) -> str:
        s = str(v or "").strip()
        if not s.startswith("EXC_"):
            raise ValueError(f"exclusion code must start with EXC_, got {v!r}")
        return s

    @field_validator("codigo_canonico")
    @classmethod
    def _check_codigo_canonico(cls, v: str) -> str:
        s = str(v or "").strip()
        if not s or not s.replace("_", "").isalnum():
            raise ValueError(f"codigo_canonico must be a non-empty alphanumeric token, got {v!r}")
        return s


class Taxonomy(BaseModel):
    """The closed taxonomy of digital gender violence."""

    version: str = "1.0.0"
    schema_version: str = Field(default="taxonomia-v1", alias="schema")
    descripcion: str = ""
    categorias: list[CategoriaMD] = Field(default_factory=list)
    categorias_exclusion: list[ExclusionCategoriaMD] = Field(default_factory=list)
    reglas_desempate: list[ReglaDesempateMD] = Field(default_factory=list)
    leetspeak_global: dict[str, str] = Field(default_factory=dict)
    referentes_femeninos: list[str] = Field(default_factory=list)
    marcadores_de_genero: list[str] = Field(default_factory=list)
    patrones_violencia_comun: list[str] = Field(default_factory=list)
    multi_etiqueta_instruccion: str = ""

    @model_validator(mode="after")
    def _validate_invariants(self) -> Taxonomy:
        if len(self.categorias) != 6:
            raise ValueError(
                f"Taxonomy must declare exactly 6 categories, got {len(self.categorias)}"
            )
        codes = [c.code for c in self.categorias]
        if len(set(codes)) != 6:
            raise ValueError(f"Category codes must be unique, got {codes}")
        ordens = [c.orden for c in self.categorias]
        if ordens != [1, 2, 3, 4, 5, 6]:
            raise ValueError(f"Category orden must be [1..6] in order, got {ordens}")
        dim_codes = [d.code for c in self.categorias for d in c.subdimensiones]
        if len(set(dim_codes)) != 19:
            raise ValueError(f"Sub-dimension codes must be unique (got {len(set(dim_codes))}/19)")
        for c in self.categorias:
            expected_count = 4 if c.orden == 4 else 3
            expected = [f"{c.orden}.{i}" for i in range(1, expected_count + 1)]
            got = [d.code for d in c.subdimensiones]
            if got != expected:
                raise ValueError(
                    f"Category {c.code} (orden={c.orden}) has dims {got}, expected {expected}"
                )
        excl_codes = [e.code for e in self.categorias_exclusion]
        if len(set(excl_codes)) != len(excl_codes):
            raise ValueError(f"Exclusion codes must be unique, got {excl_codes}")
        excl_canon = [e.codigo_canonico for e in self.categorias_exclusion]
        if len(set(excl_canon)) != len(excl_canon):
            raise ValueError(f"Exclusion codigo_canonico values must be unique, got {excl_canon}")
        return self

    def ordered_codes(self) -> list[str]:
        return [c.code for c in sorted(self.categorias, key=lambda c: c.orden)]

    def subdims_by_category(self) -> dict[str, list[str]]:
        return {c.code: [d.code for d in c.subdimensiones] for c in self.categorias}

    def descripcion_subdim(self) -> dict[str, str]:
        return {d.code: d.descripcion for c in self.categorias for d in c.subdimensiones}

    def gravedad_por_categoria(self) -> dict[str, str]:
        return {c.code: c.gravedad for c in self.categorias}

    def category_labels(self) -> dict[str, str]:
        return {c.code: c.label or c.code for c in self.categorias}

    def subdimension_labels(self) -> dict[str, str]:
        return {d.code: d.descripcion for c in self.categorias for d in c.subdimensiones}

    def ordered_subdimensions(self) -> list[str]:
        out: list[str] = []
        for c in sorted(self.categorias, key=lambda c: c.orden):
            for d in c.subdimensiones:
                out.append(d.code)
        return out

    def categoria_por_subdimension(self) -> dict[str, str]:
        return {d.code: c.code for c in self.categorias for d in c.subdimensiones}

    def markers_by_subdimension(self) -> dict[str, list[str]]:
        return {
            d.code: list(d.marcadores_canonicos) for c in self.categorias for d in c.subdimensiones
        }

    def all_canonical_markers(self) -> frozenset[str]:
        return frozenset(
            marker for markers in self.markers_by_subdimension().values() for marker in markers
        )

    def leetspeak_map(self) -> dict[str, str]:
        return dict(self.leetspeak_global)

    def referentes_femeninos_set(self) -> frozenset[str]:
        return frozenset(self.referentes_femeninos)

    def marcadores_de_genero_set(self) -> frozenset[str]:
        return frozenset(self.marcadores_de_genero)

    def patrones_violencia_comun_set(self) -> frozenset[str]:
        return frozenset(self.patrones_violencia_comun)

    def mitigadores_set(self) -> frozenset[str]:
        return frozenset(
            {
                "arcaica",
                "retrógrada",
                "patriarcal",
                "machista",
                "denunciar",
                "repudiar",
                "visibilizar",
                "criticar",
                "no es verdad que",
                "en realidad",
                "sin embargo",
                "#NiUnaMenos",
                "#8M",
                "#VivasNosQueremos",
            }
        )

    def patrones_basura_digital_dict(self) -> dict[str, BasuraDigitalPatternMD]:
        path = (
            _PROJECT_ROOT
            / "knowledge"
            / "categorias-violencia-genero-digital"
            / "glosario"
            / "patrones-basura-digital.md"
        )
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}
        match = re.search(r"```plain\n(.*?)```", text, re.DOTALL)
        if not match:
            return {}
        out: dict[str, BasuraDigitalPatternMD] = {}
        for index, line in enumerate(match.group(1).splitlines(), start=1):
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            pattern, _, annotation = raw.partition(" #")
            pattern = pattern.strip()
            condition = annotation.strip().split()[0] if annotation.strip() else "PATTERN"
            pattern_id = f"{condition}_{index}"
            out[pattern_id] = BasuraDigitalPatternMD(id=pattern_id, pattern=pattern)
        return out

    def desempate_rules(self) -> list[ReglaDesempateMD]:
        return list(self.reglas_desempate)

    def exclusion_codes(self) -> dict[str, str]:
        """Return the ``{EXC_*: CODIGO_*}`` mapping from the MD.

        Used by callers that need to translate a documented
        pseudo-category (e.g. ``EXC_BASURA_DIGITAL``) to the canonical
        exclusion label that lives in
        ``analysis_results.exclusion_label``.
        """
        return {e.code: e.codigo_canonico for e in self.categorias_exclusion}

    def canonical_exclusion_labels(self) -> frozenset[str]:
        """Return the canonical ``CODIGO_*`` codes for every documented exclusion."""
        return frozenset(e.codigo_canonico for e in self.categorias_exclusion)


# ---------------------------------------------------------------------------
# Minimal YAML frontmatter parser for the narrow dialect used by TAXONOMIA.md
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


def _split_frontmatter(md_text: str) -> tuple[str, str]:
    """Return (frontmatter_yaml, body). Raise if frontmatter is absent."""
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        raise TaxonomyFormatError(
            "TAXONOMIA.md must start with a YAML frontmatter block delimited by '---'"
        )
    return m.group(1), md_text[m.end() :]


def _coerce_scalar(token: str) -> Any:
    """Coerce a YAML scalar token to int / str (best-effort)."""
    s = token.strip()
    if not s:
        return s
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_yaml_dict_lines(
    lines: list[str], base_indent: int, start: int
) -> tuple[dict[str, Any], int]:
    """Parse a YAML mapping whose keys are indented at ``base_indent``.

    Handles two child forms under each ``key:``:

    - ``key: scalar`` → scalar value
    - ``key:`` followed by an indented block → nested dict or list

    Returns (parsed_dict, next_line_index).
    """
    out: dict[str, Any] = {}
    i = start
    n = len(lines)
    current_indent: int | None = None
    while i < n:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if current_indent is None:
            current_indent = indent
            if indent < base_indent:
                break
        if indent != current_indent:
            break
        stripped = line.strip()
        if stripped.startswith("-"):
            break
        if ":" not in stripped:
            raise TaxonomyFormatError(f"Malformed YAML line {i + 1}: missing ':' in {stripped!r}")
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j >= n:
                raise TaxonomyFormatError(f"Key {key!r} at line {i + 1} has no value")
            nxt = lines[j]
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_indent <= indent:
                raise TaxonomyFormatError(
                    f"Key {key!r} at line {i + 1} not followed by indented content"
                )
            if nxt.lstrip().startswith("-"):
                sublist, consumed = _parse_yaml_list_lines(lines, nxt_indent, j)
                out[key] = sublist
                i = consumed
                continue
            subdict, consumed = _parse_yaml_dict_lines(lines, nxt_indent, j)
            out[key] = subdict
            i = consumed
            continue
        out[key] = _coerce_scalar(rest)
        i += 1
    return out, i


def _parse_yaml_list_lines(lines: list[str], base_indent: int, start: int) -> tuple[list[Any], int]:
    """Parse a YAML list whose items are inline mappings.

    Each item is ``- key: value`` followed by optional continuation
    lines at indent ``> base_indent`` with the same shape. A value
    containing its own nested ``key:`` (block scalar) is supported
    only when its continuation is itself a list — used for the
    ``subdimensiones:`` field.
    """
    out: list[Any] = []
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent < base_indent:
            break
        stripped_leading = line.lstrip()
        if not stripped_leading.startswith("-"):
            break
        rest = stripped_leading[2:] if stripped_leading.startswith("- ") else stripped_leading[1:]
        first_key, _, first_val = rest.partition(":")
        first_key = first_key.strip()
        first_val = first_val.strip()
        item: dict[str, Any] = {}
        if not first_key:
            raise TaxonomyFormatError(f"Bare list item not supported at line {i + 1}: {line!r}")
        item[first_key] = _coerce_scalar(first_val) if first_val else ""
        j = i + 1
        cont_indent: int | None = None
        while j < n:
            ln = lines[j]
            if ln.strip() == "":
                j += 1
                continue
            ind = len(ln) - len(ln.lstrip())
            if ind <= base_indent:
                break
            if cont_indent is None:
                cont_indent = ind
            if ind != cont_indent:
                break
            lstripped = ln.strip()
            if lstripped.startswith("-"):
                break
            k2, _, v2 = lstripped.partition(":")
            k2 = k2.strip()
            v2 = v2.strip()
            if v2 == "":
                # Nested block (list expected, e.g. subdimensiones).
                k = j + 1
                while k < n and lines[k].strip() == "":
                    k += 1
                if k >= n or len(lines[k]) - len(lines[k].lstrip()) <= ind:
                    raise TaxonomyFormatError(
                        f"Key {k2!r} at line {j + 1} has empty value and no nested block"
                    )
                nxt = lines[k]
                nxt_indent = len(nxt) - len(nxt.lstrip())
                if not nxt.lstrip().startswith("-"):
                    raise TaxonomyFormatError(
                        f"Key {k2!r} at line {j + 1}: nested block must be a list"
                    )
                sub, consumed = _parse_yaml_list_lines(lines, nxt_indent, k)
                item[k2] = sub
                j = consumed
                continue
            item[k2] = _coerce_scalar(v2)
            j += 1
        i = j
        out.append(item)
    return out, i


def _parse_frontmatter_yaml(text: str) -> dict[str, Any]:
    """Parse the strict YAML frontmatter dialect used by TAXONOMIA.md.

    Grammar:

    - top-level scalars: ``key: value``
    - top-level list of mappings: ``key:\\n  - subkey: value\\n    subkey2: value2``
    - nested list of mappings under a list item: ``key:\\n      - subkey: value``

    Anything else raises :class:`TaxonomyFormatError`.
    """
    lines = text.splitlines()
    if not lines:
        raise TaxonomyFormatError("Empty frontmatter block")

    out: dict[str, Any] = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent != 0:
            raise TaxonomyFormatError(f"Top-level keys must be unindented (line {i + 1}: {line!r})")
        stripped = line.strip()
        if ":" not in stripped:
            raise TaxonomyFormatError(f"Missing ':' at line {i + 1}: {stripped!r}")
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j >= n:
                raise TaxonomyFormatError(f"Key {key!r} at line {i + 1} has no value")
            nxt = lines[j]
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_indent <= 0:
                raise TaxonomyFormatError(
                    f"Key {key!r} at line {i + 1} not followed by an indented block"
                )
            if nxt.lstrip().startswith("-"):
                out[key], i = _parse_yaml_list_lines(lines, nxt_indent, j)
            else:
                out[key], i = _parse_yaml_dict_lines(lines, nxt_indent, j)
            continue
        out[key] = _coerce_scalar(rest)
        i += 1
    return out


def load_taxonomy_from_string(text: str) -> Taxonomy:
    """Parse a Markdown string with our frontmatter dialect into a :class:`Taxonomy`."""
    yaml_text, _body = _split_frontmatter(text)
    raw = _parse_frontmatter_yaml(yaml_text)
    return Taxonomy.model_validate(raw)


def load_taxonomy(path: Path | str | None = None) -> Taxonomy:
    """Load the taxonomy from disk.

    Args:
        path: Explicit path to TAXONOMIA.md. Defaults to
            :data:`DEFAULT_TAXONOMY_PATH`.
    """
    target = Path(path) if path is not None else DEFAULT_TAXONOMY_PATH
    text = target.read_text(encoding="utf-8")
    taxonomy = load_taxonomy_from_string(text)
    logger.debug(
        "Loaded taxonomy v%s (%d categories) from %s",
        taxonomy.version,
        len(taxonomy.categorias),
        target,
    )
    return taxonomy


_lock = Lock()
_cached: Taxonomy | None = None


def get_taxonomy() -> Taxonomy:
    """Return the process-wide cached :class:`Taxonomy` (loads on first call)."""
    global _cached
    if _cached is not None:
        return _cached
    with _lock:
        if _cached is None:
            _cached = load_taxonomy()
        return _cached


def reload_taxonomy(path: Path | str | None = None) -> Taxonomy:
    """Force-reload the taxonomy and replace the cache."""
    global _cached
    with _lock:
        _cached = load_taxonomy(path)
        return _cached


def reset_cache() -> None:
    """Drop the cached :class:`Taxonomy` without reloading (test helper)."""
    global _cached
    with _lock:
        _cached = None


__all__ = [
    "CategoriaMD",
    "DEFAULT_TAXONOMY_PATH",
    "ExclusionCategoriaMD",
    "GRAVEDAD_TOKENS",
    "SubdimensionMD",
    "Taxonomy",
    "TaxonomyFormatError",
    "get_taxonomy",
    "load_taxonomy",
    "load_taxonomy_from_string",
    "reload_taxonomy",
    "reset_cache",
]
