"""Descriptive statistics for the Enola dashboard (Reglas 2, 3 y 4).

Implements:

* :func:`compute_frequency_distribution` — Regla 2: distribución de
  frecuencias con porcentaje válido (excluye CÓDIGO 99) y porcentaje
  acumulado. Devuelve una ``FrequencyTable`` con exactamente 4 columnas:
  Categoría, Frecuencia Absoluta, Porcentaje Válido y Porcentaje
  Acumulado.

* :func:`compute_mode` — Regla 3: la MODA es la única medida de
  tendencia central permitida para variables nominales. Detecta
  bimodalidad/multimodalidad y devuelve el texto automatizado del Paso
  3.4.

* :func:`compute_crosstabs` — Regla 4: tabulación cruzada
  (categoría × subdimensión | página | fecha). Calcula frecuencias
  observadas + porcentajes marginales de columna y emite la alerta
  descriptiva del Paso 4.4.

All three functions operate on multi-label rows: each analysis row may
contribute as many votes as labels it carries (via the ``labels`` side
key, falling back to the flat ``categoria``/``dimension`` when no
labels are present). Basura-digital (CÓDIGO 99) and Violencia Común
rows are explicitly excluded from the violence-incidence denominators.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.analyzer.category_mapping import CATEGORIAS_ORDENADAS
from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)

# ----- shared helpers -----


def _is_excluded(row: dict) -> bool:
    """``True`` when the row carries any exclusion sentinel."""
    excl = row.get("exclusion_label")
    return excl in {EXCLUSION_BASURA_DIGITAL, EXCLUSION_VIOLENCIA_COMUN}


def _iter_labels(row: dict) -> Iterable[dict]:
    """Yield each label of ``row`` (multi-label aware) or a single fallback dict."""
    labels = row.get("labels") or []
    if labels:
        for lbl in labels:
            yield {
                "categoria": lbl.get("categoria") or "ninguna",
                "dimension": lbl.get("dimension"),
            }
    else:
        yield {
            "categoria": row.get("categoria") or "ninguna",
            "dimension": row.get("dimension"),
        }


def _iter_violence_labels(rows: Sequence[dict]) -> Iterable[tuple[str, str | None]]:
    """Yield (categoria, dimension) for each valid violence label.

    Skips excluded rows (CODIGO_99 / VIOLENCIA_COMUN) and rows with no
    ``tiene_violencia="true"``. A row with multi-label contributes
    multiple tuples.
    """
    for row in rows:
        if _is_excluded(row):
            continue
        if row.get("tiene_violencia") != "true":
            continue
        for lbl in _iter_labels(row):
            cat = lbl["categoria"]
            if cat and cat != "ninguna":
                yield cat, lbl["dimension"]


# ----- Regla 2: Distribución de Frecuencias -----


@dataclass(frozen=True)
class FrequencyRow:
    """One row of the 4-column frequency distribution table."""

    categoria: str
    categoria_label: str
    frecuencia_absoluta: int
    porcentaje_valido: float
    porcentaje_acumulado: float


@dataclass(frozen=True)
class FrequencyTable:
    """Tabla de distribución de frecuencias (Paso 2.4 del documento)."""

    rows: list[FrequencyRow]
    total_validos: int
    n_excluidos: int

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Categoría": r.categoria_label,
                    "Código": r.categoria,
                    "Frecuencia Absoluta": r.frecuencia_absoluta,
                    "Porcentaje Válido": round(r.porcentaje_valido, 2),
                    "Porcentaje Acumulado": round(r.porcentaje_acumulado, 2),
                }
                for r in self.rows
            ]
        )


def _categoria_label(code: str) -> str:
    from src.ui.utils import label_for

    return label_for(code)


def compute_frequency_distribution(
    analysis: Sequence[dict],
    *,
    categoria_labels: dict[str, str] | None = None,
) -> FrequencyTable:
    """Calcular la distribución de frecuencias (Paso 2.1 - 2.4).

    * Excluye filas ``CODIGO_99`` / ``VIOLENCIA_COMUN`` del denominador
      (porcentaje válido).
    * Soporta multi-label: cada ``LabelAssignment`` cuenta como un voto
      independiente por categoría.
    * Devuelve la tabla con **4 columnas exactas** según el documento:
      Categoría / Frecuencia Absoluta / Porcentaje Válido / Porcentaje
      Acumulado.
    """
    counter: Counter[str] = Counter()
    for cat, _dim in _iter_violence_labels(analysis):
        counter[cat] += 1

    total = sum(counter.values())
    n_excluidos = sum(1 for a in analysis if _is_excluded(a))

    counts_per_cat: list[tuple[str, int]] = []
    for code in CATEGORIAS_ORDENADAS:
        counts_per_cat.append((code, counter.get(code, 0)))
    # ensure descending order by frequency (Paso 2.3)
    counts_per_cat.sort(key=lambda x: -x[1])

    label_map = categoria_labels or {}

    rows: list[FrequencyRow] = []
    acumulado = 0.0
    for code, n in counts_per_cat:
        pct = (n / total * 100.0) if total > 0 else 0.0
        acumulado += pct
        rows.append(
            FrequencyRow(
                categoria=code,
                categoria_label=label_map.get(code, _categoria_label(code)),
                frecuencia_absoluta=n,
                porcentaje_valido=round(pct, 2),
                porcentaje_acumulado=round(acumulado, 2),
            )
        )

    return FrequencyTable(rows=rows, total_validos=total, n_excluidos=n_excluidos)


# ----- Regla 3: Moda -----


@dataclass(frozen=True)
class ModeResult:
    """Resultado de la moda (Paso 3.2-3.4 del documento)."""

    frecuencias: dict[str, int]
    modas: list[str]
    es_multimodal: bool
    texto_descriptivo: str

    def to_dict(self) -> dict:
        return {
            "frecuencias": dict(self.frecuencias),
            "modas": list(self.modas),
            "es_multimodal": self.es_multimodal,
            "texto_descriptivo": self.texto_descriptivo,
        }


def _format_modas(modes: Sequence[str], label_map: dict[str, str]) -> str:
    if not modes:
        return ""
    nombres = [label_map.get(m, _categoria_label(m)) for m in modes]
    if len(nombres) == 1:
        return nombres[0]
    if len(nombres) == 2:
        return f"{nombres[0]} y {nombres[1]}"
    return ", ".join(nombres[:-1]) + f" y {nombres[-1]}"


def compute_mode(
    analysis: Sequence[dict],
    *,
    categoria_labels: dict[str, str] | None = None,
) -> ModeResult:
    """Calcular la moda de las categorías (Regla 3).

    Maneja bimodalidad (Paso 3.3): si dos o más categorías comparten la
    frecuencia máxima, devuelve la lista completa y marca
    ``es_multimodal=True``. El texto descriptivo del Paso 3.4 se
    construye a partir de las etiquetas legibles.
    """
    label_map = categoria_labels or {}

    counter: Counter[str] = Counter()
    for cat, _dim in _iter_violence_labels(analysis):
        counter[cat] += 1

    if not counter:
        return ModeResult(
            frecuencias={},
            modas=[],
            es_multimodal=False,
            texto_descriptivo=(
                "Sin etiquetas de violencia detectadas — no se puede calcular la moda."
            ),
        )

    max_freq = max(counter.values())
    modas = sorted(c for c, n in counter.items() if n == max_freq)

    if len(modas) >= 2:
        cualif = "bimodal" if len(modas) == 2 else "multimodal"
        nombres = _format_modas(modas, label_map)
        texto = (
            "Atendiendo a los principios de la estadística descriptiva, la "
            f"distribución de esta extracción es {cualif} con {len(modas)} "
            f"categorías empatadas en la frecuencia máxima ({max_freq} casos "
            f"cada una): {nombres}. Este empate refleja que múltiples "
            f"tácticas de ciberviolencia de género digital operan con la "
            f"misma intensidad en la presente muestra."
        )
    else:
        cat = modas[0]
        nombre = label_map.get(cat, _categoria_label(cat))
        texto = (
            "Atendiendo a los principios de la estadística descriptiva, la MODA "
            f"de esta extracción es la Categoría {nombre}, lo que demuestra "
            f"empíricamente que este es el patrón o táctica de ciberviolencia de "
            f"género digital que predomina y rige el discurso de odio en la "
            f"presente muestra ({max_freq} casos)."
        )

    return ModeResult(
        frecuencias=dict(counter),
        modas=modas,
        es_multimodal=len(modas) >= 2,
        texto_descriptivo=texto,
    )


# ----- Regla 4: Tablas de Contingencia -----


@dataclass(frozen=True)
class CrosstabResult:
    """Resultado de una tabulación cruzada."""

    dimension: str
    filas: list[str]
    columnas: list[str]
    frecuencias: list[list[int]]
    porcentajes_marginales_columna: list[list[float]]
    alerta_patron: str | None

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(
            self.frecuencias,
            index=self.filas,
            columns=self.columnas,
        )
        df.index.name = "Categoría"
        return df

    def to_porcentajes_dataframe(self) -> pd.DataFrame:
        rows = [
            {col: round(pct, 2) for col, pct in zip(self.columnas, fila)}
            for fila in self.porcentajes_marginales_columna
        ]
        return pd.DataFrame(rows, index=self.filas).rename_axis("Categoría")


def _labels_with_meta(
    rows: Sequence[dict],
    *,
    page_lookup: dict[str, str] | None = None,
    date_format: str = "%Y-%m",
) -> list[tuple[str, str, str | None]]:
    """Return [(categoria, dimension, cross_dim_value)] for each valid label.

    ``cross_dim_value`` depends on the crosstab target (subdimension /
    page title / date bucket). Caller filters by target.
    """
    out: list[tuple[str, str, str | None]] = []
    for row in rows:
        if _is_excluded(row):
            continue
        if row.get("tiene_violencia") != "true":
            continue

        labels = row.get("labels") or []
        if labels:
            label_iter = labels
        else:
            label_iter = [
                {
                    "categoria": row.get("categoria") or "ninguna",
                    "dimension": row.get("dimension"),
                }
            ]

        for lbl in label_iter:
            cat = lbl.get("categoria") or "ninguna"
            dim = lbl.get("dimension")
            if cat == "ninguna":
                continue
            out.append((cat, dim or "—", None))
    return out


def _date_bucket(value: object, fmt: str) -> str:
    """Return a YYYY-MM (or similar) bucket from a date value."""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime(fmt)
        except ValueError:
            return "Sin fecha"
    return "Sin fecha"


def compute_crosstabs(
    analysis: Sequence[dict],
    *,
    dimension: str = "subdimension",
    posts: Sequence[dict] | None = None,
    page_lookup: dict[str, str] | None = None,
    categoria_labels: dict[str, str] | None = None,
) -> CrosstabResult:
    """Cruzar la categoría de violencia contra una dimensión independiente.

    ``dimension`` puede ser:

    * ``"subdimension"`` — Regla 4 según confirmación del usuario:
      cruza cada ``(categoria, dimension)`` detectada con la categoría
      padre (default).
    * ``"pagina"`` — cruza contra el nombre de la página de Facebook
      (``pages.title``).
    * ``"fecha"`` — cruza contra el mes de publicación
      (``YYYY-MM``).

    Calcula frecuencias observadas y porcentajes marginales de
    **columna** (Paso 4.3): ``Del total de comentarios que recibió el
    Tema X, ¿qué porcentaje exacto corresponde a cada categoría de
    violencia?``
    """
    label_map = categoria_labels or {}

    if dimension == "subdimension":
        columnas_set: set[str] = set()
        filas_set: set[str] = set()
        cells: Counter[tuple[str, str]] = Counter()
        for row in analysis:
            if _is_excluded(row) or row.get("tiene_violencia") != "true":
                continue
            labels = row.get("labels") or []
            if labels:
                label_iter = labels
            else:
                label_iter = [
                    {
                        "categoria": row.get("categoria") or "ninguna",
                        "dimension": row.get("dimension"),
                    }
                ]
            for lbl in label_iter:
                cat = lbl.get("categoria") or "ninguna"
                dim = lbl.get("dimension") or "—"
                if cat == "ninguna":
                    continue
                filas_set.add(cat)
                columnas_set.add(dim)
                cells[(cat, dim)] += 1

        filas = sorted(filas_set, key=lambda c: -sum(cells[(c, d)] for d in columnas_set))
        columnas = sorted(columnas_set)
        freqs = [[cells[(f, c)] for c in columnas] for f in filas]
        col_totals = [sum(freqs[i][j] for i in range(len(filas))) for j in range(len(columnas))]
        pcts = [
            [
                (freqs[i][j] / col_totals[j] * 100.0) if col_totals[j] > 0 else 0.0
                for j in range(len(columnas))
            ]
            for i in range(len(filas))
        ]
        alerta = _emitir_alerta_patron(filas, columnas, freqs, pcts, label_map, "subdimension")

    elif dimension == "pagina":
        page_lookup = page_lookup or {}
        columnas_set = set()
        filas_set = set()
        cells = Counter()
        post_by_id = {p.get("id"): p for p in (posts or [])}
        for row in analysis:
            if _is_excluded(row) or row.get("tiene_violencia") != "true":
                continue
            post_id = row.get("post_id") or row.get("content_id")
            page_title = page_lookup.get(post_id) if post_id else None
            if not page_title:
                post = post_by_id.get(post_id or "")
                if post:
                    page_id = post.get("page_id")
                    page_title = (
                        (page_lookup.get(page_id or "") if page_id else None)
                        or page_id
                        or "Sin página"
                    )
            page_title = page_title or "Sin página"
            for lbl in _iter_labels(row):
                cat = lbl["categoria"]
                if cat == "ninguna":
                    continue
                filas_set.add(cat)
                columnas_set.add(page_title)
                cells[(cat, page_title)] += 1

        filas = sorted(filas_set, key=lambda c: -sum(cells[(c, d)] for d in columnas_set))
        columnas = sorted(columnas_set)
        freqs = [[cells[(f, c)] for c in columnas] for f in filas]
        col_totals = [sum(freqs[i][j] for i in range(len(filas))) for j in range(len(columnas))]
        pcts = [
            [
                (freqs[i][j] / col_totals[j] * 100.0) if col_totals[j] > 0 else 0.0
                for j in range(len(columnas))
            ]
            for i in range(len(filas))
        ]
        alerta = _emitir_alerta_patron(filas, columnas, freqs, pcts, label_map, "página")

    elif dimension == "fecha":
        columnas_set = set()
        filas_set = set()
        cells = Counter()
        post_by_id = {p.get("id"): p for p in (posts or [])}
        for row in analysis:
            if _is_excluded(row) or row.get("tiene_violencia") != "true":
                continue
            post_id = row.get("post_id") or row.get("content_id")
            post = post_by_id.get(post_id or "")
            date_str = None
            if post:
                date_str = post.get("date")
            bucket = _date_bucket(date_str, "%Y-%m")
            for lbl in _iter_labels(row):
                cat = lbl["categoria"]
                if cat == "ninguna":
                    continue
                filas_set.add(cat)
                columnas_set.add(bucket)
                cells[(cat, bucket)] += 1

        filas = sorted(filas_set, key=lambda c: -sum(cells[(c, d)] for d in columnas_set))
        columnas = sorted(columnas_set)
        freqs = [[cells[(f, c)] for c in columnas] for f in filas]
        col_totals = [sum(freqs[i][j] for i in range(len(filas))) for j in range(len(columnas))]
        pcts = [
            [
                (freqs[i][j] / col_totals[j] * 100.0) if col_totals[j] > 0 else 0.0
                for j in range(len(columnas))
            ]
            for i in range(len(filas))
        ]
        alerta = _emitir_alerta_patron(filas, columnas, freqs, pcts, label_map, "fecha")

    else:
        raise ValueError(
            f"dimension debe ser 'subdimension', 'pagina' o 'fecha' — recibido: {dimension!r}"
        )

    return CrosstabResult(
        dimension=dimension,
        filas=filas,
        columnas=columnas,
        frecuencias=freqs,
        porcentajes_marginales_columna=pcts,
        alerta_patron=alerta,
    )


def _emitir_alerta_patron(
    filas: Sequence[str],
    columnas: Sequence[str],
    freqs: Sequence[Sequence[int]],
    pcts: Sequence[Sequence[float]],
    label_map: dict[str, str],
    dimension_nombre: str,
) -> str | None:
    """Encontrar la celda con mayor % marginal de columna y emitir la alerta."""
    best: tuple[float, str, str, int] | None = None
    for i, fila in enumerate(filas):
        for j, col in enumerate(columnas):
            pct = pcts[i][j]
            if best is None or pct > best[0]:
                best = (pct, fila, col, freqs[i][j])

    if best is None or best[0] <= 0:
        return None

    pct, fila, col, n = best
    cat_nombre = label_map.get(fila, _categoria_label(fila))
    texto_col = (
        f"la subdimensión {col}"
        if dimension_nombre == "subdimension"
        else f"el {dimension_nombre} {col}"
    )
    return (
        f"Al ejecutar la tabulación cruzada, el sistema detecta que "
        f"{texto_col} detona principalmente la categoría de {cat_nombre} "
        f"({pct:.1f}% de los casos válidos de esa columna, n={n}), "
        f"evidenciando un patrón de comportamiento relacional en la muestra."
    )


__all__ = [
    "FrequencyRow",
    "FrequencyTable",
    "compute_frequency_distribution",
    "ModeResult",
    "compute_mode",
    "CrosstabResult",
    "compute_crosstabs",
]
