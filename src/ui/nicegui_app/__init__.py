"""Enola Investigadora Digital — premium NiceGUI dashboard.

Replaces the legacy Streamlit landing with a multi-page interface
built on NiceGUI + Quasar + Tailwind + Plotly. The design system is
centralised in :mod:`src.ui.nicegui_app.theme`.

Run with: ``python -m src.ui.nicegui_app``

Module layout::

    src/ui/nicegui_app/
    ├── __init__.py     # package docstring + public exports
    ├── __main__.py     # ``python -m`` entry point (script)
    ├── theme.py        # palette, typography, Quasar color registration
    ├── layout.py       # header + drawer + footer primitives
    ├── components/
    │   ├── kpi_card.py # premium KPI grid
    │   ├── section.py  # section header
    │   └── charts.py   # Plotly builders
    └── pages/
        ├── inicio.py        # /inicio — hero + KPIs + Regla 1
        ├── estadistica.py   # /estadistica — Reglas 2, 3, 4
        ├── ia.py            # /ia — Regla 6
        ├── inspector.py     # /inspector
        └── conocimiento.py  # /conocimiento
"""

from __future__ import annotations

__all__: list[str] = []
