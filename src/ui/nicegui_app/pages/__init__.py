"""Multi-page routes for the Enola NiceGUI dashboard.

Each module in this package registers one or more ``@ui.page`` routes
when imported. :mod:`src.ui.nicegui_app.__main__` imports them in bulk
right before ``ui.run()`` so the routes are registered exactly once.

Rutas disponibles:

* ``/`` (legacy → /inicio)
* ``/inicio`` — landing pública.
* ``/login`` — formulario de autenticación.
* ``/conocimiento`` — taxonomía canónica + ZIP (pública).
* ``/conocimiento/cargar`` — upload .md/.txt/.pdf a ChromaDB (admin).
* ``/conocimiento/explorar`` — visualizador de la colección (admin).
* ``/conocimiento/editor`` — CRUD sobre ``knowledge/*.md`` (admin).
* ``/validacion`` — revisión humana del análisis (autenticada).
* ``/inspector``, ``/estadistica``, ``/ia`` — páginas analíticas.
"""
