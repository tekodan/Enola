"""Tutorial / Manual de uso — página NiceGUI premium.

Presenta el manual completo de la plataforma como una página web
interactiva con secciones navegables, capturas de pantalla y
contenido estilizado con el design system 'Tinta y Rosa'.

Ruta: ``/tutorial`` — pública (no requiere autenticación).
"""

from __future__ import annotations

import logging
from pathlib import Path

from nicegui import ui

from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "static" / "screenshots_manual"


# ── Helpers ────────────────────────────────────────────────────────────────


def _info_box(title: str, body: str) -> None:
    """Cuadro informativo con estilo rose/brass."""
    with ui.card().classes("w-full enola-panel enola-panel--brass").style("margin: 1rem 0;"):
        with ui.row().classes("items-center gap-2 mb-1"):
            ui.icon("lightbulb", color=theme.BRASS, size="20px")
            ui.label(title).classes("font-semibold text-sm").style(f"color: {theme.BRASS_DEEP};")
        ui.label(body).classes("text-sm leading-relaxed").style(
            "color: var(--enola-charcoal); line-height: 1.6;"
        )


def _screenshot_card(image_name: str, caption: str) -> None:
    """Tarjeta con imagen de captura y pie de figura."""
    img_path = SCREENSHOTS_DIR / image_name
    with ui.card().classes("w-full enola-panel").style("margin: 1.25rem 0; padding: 1rem;"):
        if img_path.exists():
            ui.html(
                f'<img src="/static/screenshots_manual/{image_name}" '
                f'alt="{caption}" '
                f'style="width: 100%; border-radius: 0.5rem; '
                f"box-shadow: 0 4px 12px -2px rgba(35,30,46,0.12); "
                f'object-fit: contain; display: block;" />',
                sanitize=False,
            )
        else:
            ui.label(f"[Imagen no disponible: {image_name}]").classes("text-sm text-center").style(
                "color: var(--enola-charcoal-light); padding: 2rem;"
            )
        ui.label(caption).classes("text-xs text-center italic mt-2").style(
            "color: var(--enola-charcoal-light); font-style: italic;"
        )


def _step_card(number: str, title: str, body: str, icon: str = "check_circle") -> None:
    """Tarjeta de paso numerado."""
    with ui.card().classes("w-full enola-panel").style("margin: 0.75rem 0;"):
        with ui.row().classes("items-start gap-3"):
            with ui.element("div").style(
                f"min-width: 36px; height: 36px; border-radius: 10px; "
                f"background: linear-gradient(135deg, {theme.ROSE} 0%, {theme.PLUM} 100%); "
                f"display: flex; align-items: center; justify-content: center; "
                f"box-shadow: 0 2px 8px -2px rgba(0,0,0,0.25); flex-shrink: 0;"
            ):
                ui.label(number).classes("text-sm font-bold").style("color: white;")
            with ui.column().classes("gap-1 flex-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon, color=theme.PLUM, size="18px")
                    ui.label(title).classes("font-semibold text-sm").style(f"color: {theme.PLUM};")
                ui.label(body).classes("text-sm leading-relaxed").style(
                    "color: var(--enola-charcoal); line-height: 1.6;"
                )


def _bullet_list(items: list[str], bold_prefixes: list[str] | None = None) -> None:
    """Lista de viñetas."""
    for i, item in enumerate(items):
        prefix = bold_prefixes[i] if bold_prefixes and i < len(bold_prefixes) else ""
        with ui.row().classes("items-start gap-2 mb-1"):
            ui.label("•").classes("text-sm font-bold").style(
                f"color: {theme.ROSE}; min-width: 16px;"
            )
            with ui.row().classes("gap-1"):
                if prefix:
                    ui.label(prefix).classes("text-sm font-semibold").style(f"color: {theme.PLUM};")
                ui.label(item).classes("text-sm").style("color: var(--enola-charcoal);")


def _subtitle_heading(text: str) -> None:
    """Subtítulo de sección."""
    ui.label(text).classes("text-base font-semibold mt-6 mb-2").style(
        f"color: {theme.PLUM_DEEP}; font-family: var(--enola-font-display);"
    )


def _body_text(text: str) -> None:
    """Párrafo de cuerpo."""
    ui.label(text).classes("text-sm leading-relaxed").style(
        "color: var(--enola-charcoal); line-height: 1.65; max-width: 72ch;"
    )


# ── TOC anchors ────────────────────────────────────────────────────────────


def _toc_link(label: str, icon: str) -> None:
    with (
        ui.row()
        .classes("items-center gap-2 cursor-pointer")
        .style("padding: 0.5rem 0.75rem; border-radius: 0.5rem; transition: background 150ms;")
        .on("mouseenter", lambda e: e.sender.style("background: rgba(192,132,151,0.08);"))
        .on("mouseleave", lambda e: e.sender.style("background: transparent;"))
    ):
        ui.icon(icon, color=theme.PLUM, size="20px")
        ui.label(label).classes("text-sm font-medium").style("color: var(--enola-charcoal);")


# ── Page body ──────────────────────────────────────────────────────────────


def _render_body() -> None:
    # ── Hero ───────────────────────────────────────────────────────────
    with ui.element("div").classes("enola-hero").style("margin-bottom: 2rem;"):
        ui.label("Manual de Uso").classes("text-xs uppercase font-semibold enola-hero-badge")
        ui.html("<h1>Enola Investigadora Digital</h1>")
        ui.label(
            "Guía completa de la plataforma de detección de violencia "
            "de género digital basada en RAG."
        )

    # ── TOC rápido ─────────────────────────────────────────────────────
    with ui.card().classes("w-full enola-panel").style("margin-bottom: 2rem;"):
        ui.label("Contenido").classes("text-xs uppercase font-semibold mb-3").style(
            f"color: {theme.BRASS_DEEP}; letter-spacing: 0.15em;"
        )
        with ui.grid(columns=3).classes("w-full gap-2"):
            _toc_link("1. Introducción", "info")
            _toc_link("2. Acceso", "login")
            _toc_link("3. Dashboard", "dashboard")
            _toc_link("4. Validación", "task_alt")
            _toc_link("5. Estadística", "insights")
            _toc_link("6. IA & Confiabilidad", "psychology")
            _toc_link("7. Inspector", "search")
            _toc_link("8. Conocimiento", "menu_book")
            _toc_link("9. Chat RAG", "chat")
            _toc_link("10. Modo Oscuro", "dark_mode")
            _toc_link("11. Glosario", "book")

    # =================================================================
    # 1. INTRODUCCIÓN
    # =================================================================
    section_header("Sección 1", "Introducción", subtitle="Qué es y cómo funciona la plataforma")

    _body_text(
        "Enola Investigadora Digital es una plataforma académica diseñada para "
        "detectar contenido de violencia de género en publicaciones de Facebook. "
        "Utiliza técnicas de RAG (Retrieval-Augmented Generation) combinando "
        "un modelo de lenguaje local (Ollama) con una base de conocimiento "
        "indexada en ChromaDB."
    )
    _body_text(
        "Permite a investigadores y revisores analizar, validar y generar "
        "reportes estadísticos sobre la incidencia de violencia de género digital, "
        "siguiendo una taxonomía de 6 categorías principales con 19 subdimensiones."
    )

    _subtitle_heading("Stack Tecnológico")
    _bullet_list(
        [
            "Python 3.12",
            "NiceGUI (interface web)",
            "Ollama (modelos de lenguaje locales)",
            "ChromaDB (base de vectores para RAG)",
            "LangChain (orquestación LLM)",
            "SQLite (almacenamiento de análisis y feedback)",
            "Captura de datos de Facebook",
        ]
    )

    _subtitle_heading("Categorías de Violencia de Género")
    _bullet_list(
        [
            "Violencia simbólica",
            "Cosificación / Slut-shaming",
            "Hostilidad / Feminicidio",
            "Manosfera / Antifeminismo",
            "Desacreditación de activistas",
            "Falso positivo / Salvaguarda",
        ],
        [f"{i}." for i in range(1, 7)],
    )

    _info_box(
        "Filtro de exclusión",
        "Además, la plataforma detecta basura digital (CÓDIGO 99) y violencia común, "
        "que se separan del análisis principal para no contaminar los resultados.",
    )

    # =================================================================
    # 2. ACCESO
    # =================================================================
    section_header("Sección 2", "Acceso a la Plataforma", subtitle="Login y roles de usuario")

    _body_text(
        "Para acceder a Enola Investigadora Digital, abra su navegador web "
        "y diríjase a la dirección del servidor (por ejemplo, http://localhost:8080). "
        "La página de inicio se carga automáticamente."
    )

    _subtitle_heading("Inicio de Sesión")
    _body_text(
        "Al acceder a páginas que requieren autenticación, el sistema lo "
        "redirigirá a la página de login."
    )
    _bullet_list(
        [
            "Ingrese su nombre de usuario",
            "Ingrese su contraseña",
            "Haga clic en «Iniciar sesión»",
        ]
    )

    _info_box(
        "Tip",
        "Si no tiene cuenta, contacte al administrador de la plataforma. "
        "No existe registro público.",
    )

    _screenshot_card("02_login.png", "Figura 1: Pantalla de inicio de sesión")

    _subtitle_heading("Roles de Usuario")

    ui.table(
        columns=[
            {"name": "rol", "label": "Rol", "field": "rol", "align": "left"},
            {"name": "permisos", "label": "Permisos", "field": "permisos", "align": "left"},
        ],
        rows=[
            {
                "rol": "admin",
                "permisos": "Acceso total: crear/bloquear usuarios, cargar conocimiento, validar, ver estadísticas",
            },
            {
                "rol": "reviewer",
                "permisos": "Validar análisis, ver estadísticas, usar el inspector",
            },
        ],
    ).classes("w-full").style("border: none; background: transparent;")

    _subtitle_heading("Cerrar Sesión")
    _body_text(
        "Haga clic en «Salir» junto a su nombre de usuario en la barra "
        "superior. Al cerrar la pestaña del navegador, la sesión se "
        "cierra automáticamente."
    )

    # =================================================================
    # 3. DASHBOARD
    # =================================================================
    section_header(
        "Sección 3", "Panel de Inicio (Dashboard)", subtitle="Resumen general del análisis"
    )

    _body_text(
        "El panel de inicio es la página principal de la plataforma. "
        "Muestra un resumen general del estado del análisis de contenido."
    )

    _subtitle_heading("Banner de Bienvenida")
    _body_text(
        "En la parte superior se muestra el banner de Enola con la "
        "ilustración de la investigadora y una breve descripción."
    )

    _subtitle_heading("Indicadores Clave (KPIs)")
    _bullet_list(
        [
            "Total de publicaciones analizadas",
            "Total de comentarios analizados",
            "Porcentaje de contenido violento detectado",
            "Total de validaciones realizadas",
        ]
    )

    _subtitle_heading("Banner de Fiabilidad (Regla 1)")
    _body_text("Se muestra un banner con el nivel de fiabilidad del análisis:")
    _bullet_list(
        [
            "Nivel OK: menos del 5% de basura digital",
            "Nivel Preventivo: entre 5% y 10%",
            "Nivel Crítico: más del 10%",
        ],
        ["🟢 ", "🟡 ", "🔴 "],
    )

    _subtitle_heading("Chat con Enola")
    _body_text(
        "En la parte inferior se encuentra el chat interactivo con Enola, "
        "que responde preguntas sobre la taxonomía y el análisis utilizando RAG."
    )

    _screenshot_card("01_inicio.png", "Figura 2: Panel de inicio con KPIs y chat")

    # =================================================================
    # 4. VALIDACIÓN
    # =================================================================
    section_header(
        "Sección 4", "Validación Humana", subtitle="Corroborar o corregir análisis de la IA"
    )

    _body_text(
        "La validación humana es una de las funcionalidades centrales. "
        "Permite a los revisores corroborar o corregir los análisis "
        "realizados por la IA."
    )

    _subtitle_heading("Panel de KPIs")
    _bullet_list(
        [
            "Análisis pendientes de revisión",
            "Total de revisiones realizadas",
            "Porcentaje de acuerdo con la IA",
            "Correcciones realizadas",
            "Correcciones indexadas en ChromaDB",
        ]
    )

    _subtitle_heading("Filtros")
    _bullet_list(
        [
            "Tipo: posts, comentarios, o todos",
            "Estado: todos, pendientes, acuerdo, corregidos",
            "Solo violentos: mostrar únicamente contenido violento",
        ]
    )

    _subtitle_heading("Revisión de Análisis")
    _body_text("Cada análisis muestra:")
    _bullet_list(
        [
            "El texto original del post o comentario",
            "La clasificación de la IA (categoría, dimensión, severidad)",
            "La justificación y evidencia de la clasificación",
            "Los marcadores lingüísticos detectados",
        ]
    )

    _subtitle_heading("Formulario Multi-etiqueta")
    _body_text("Un mismo contenido puede llevar hasta 5 etiquetas de clasificación:")
    _bullet_list(
        [
            "Agree (estoy de acuerdo con la IA)",
            "Disagree (no estoy de acuerdo)",
            "Agregar/quitar etiquetas",
            "Modificar categoría, dimensión, severidad",
            "Agregar justificación y evidencia",
        ]
    )

    _subtitle_heading("Opciones de Guardado")
    _step_card("1", "Guardar", "Solo guarda los cambios en SQLite.")
    _step_card(
        "2",
        "Guardar e indexar",
        "Guarda en SQLite y envía las correcciones a ChromaDB para mejorar futuros análisis.",
    )

    _info_box(
        "Retroalimentación",
        "Las correcciones indexadas en ChromaDB se inyectan como ejemplos "
        "few-shot en el prompt del LLM, mejorando progresivamente la "
        "calidad de las clasificaciones.",
    )

    _screenshot_card("02_validacion.png", "Figura 3: Página de validación humana")

    # =================================================================
    # 5. ESTADÍSTICA
    # =================================================================
    section_header(
        "Sección 5", "Módulo de Estadística", subtitle="Reportes según reglas metodológicas"
    )

    _body_text(
        "El módulo de estadística genera reportes basados en las reglas "
        "metodológicas del protocolo de investigación."
    )

    _subtitle_heading("Regla 2: Distribución de Frecuencias")
    _body_text("Presenta una tabla con exactamente 4 columnas:")
    _bullet_list(
        [
            "Categoría",
            "Frecuencia Absoluta",
            "Porcentaje Válido (excluye basura digital y violencia común)",
            "Porcentaje Acumulado (llega al 100%)",
        ]
    )

    _subtitle_heading("Regla 3: Moda")
    _body_text(
        "Identifica la categoría con mayor frecuencia. Detecta "
        "distribuciones bimodales o multimodales cuando dos o más "
        "categorías comparten la frecuencia máxima."
    )

    _subtitle_heading("Regla 4: Análisis Bivariado")
    _body_text("Tablas de contingencia cruzando categoría contra:")
    _bullet_list(["Subdimensión", "Página de Facebook", "Fecha"])

    _subtitle_heading("Gráficos")
    _bullet_list(
        [
            "Gráfico de torta (distribución por categoría)",
            "Gráfico de barras (ordenado de mayor a menor)",
            "Tabla de frecuencias debajo de los gráficos",
        ]
    )

    _screenshot_card("03_estadistica.png", "Figura 4: Módulo de estadística")

    # =================================================================
    # 6. IA Y CONFIABILIDAD
    # =================================================================
    section_header(
        "Sección 6", "IA y Confiabilidad", subtitle="Métricas de rendimiento del clasificador"
    )

    _body_text(
        "Este módulo presenta las métricas de rendimiento del sistema "
        "de clasificación automática (Regla 6)."
    )

    _subtitle_heading("Métricas Principales")
    _step_card(
        "P",
        "Precisión",
        "Proporción de predicciones correctas sobre el total de predicciones positivas.",
        "gps_fixed",
    )
    _step_card(
        "R",
        "Sensibilidad (Recall)",
        "Proporción de positivos reales que fueron detectados correctamente.",
        "radar",
    )
    _step_card(
        "F1",
        "F1-Score",
        "Media armónica entre precisión y sensibilidad. Busca el balance entre ambas.",
        "balance",
    )

    _subtitle_heading("Matriz de Confusión")
    _bullet_list(
        [
            "Verdaderos Positivos (VP): contenido violento correctamente detectado",
            "Verdaderos Negativos (VN): contenido no violento correctamente identificado",
            "Falsos Positivos (FP): contenido no violento marcado como violento",
            "Falsos Negativos (FN): contenido violento no detectado",
        ]
    )

    _info_box(
        "Dato importante",
        "Las métricas se calculan usando scikit-learn y se actualizan "
        "en tiempo real a medida que se reciben validaciones de los revisores.",
    )

    _screenshot_card("04_ia.png", "Figura 5: Módulo de IA y Confiabilidad")

    # =================================================================
    # 7. INSPECTOR
    # =================================================================
    section_header(
        "Sección 7", "Inspector de Contenido", subtitle="Explorar y buscar publicaciones analizadas"
    )

    _body_text(
        "El inspector permite explorar y buscar en el contenido analizado. "
        "Es una herramienta para investigadores que necesitan examinar "
        "publicaciones específicas."
    )

    _subtitle_heading("Funcionalidades")
    _bullet_list(
        [
            "Buscar contenido por texto libre",
            "Filtrar por categoría de violencia",
            "Filtrar por página de Facebook",
            "Filtrar por rango de fechas",
            "Ver el análisis completo de cada publicación",
            "Navegar entre resultados con paginación",
            "Exportar resultados a CSV",
        ]
    )

    _screenshot_card("05_inspector.png", "Figura 6: Inspector de contenido")

    # =================================================================
    # 8. CONOCIMIENTO
    # =================================================================
    section_header(
        "Sección 8",
        "Base de Conocimiento",
        subtitle="Taxonomía, glosarios y documentos de referencia",
    )

    _body_text(
        "La base de conocimiento es el repositorio de información que "
        "alimenta al sistema RAG. Incluye la taxonomía, glosarios y "
        "documentos de referencia."
    )

    _subtitle_heading("Explorar Conocimiento")
    _body_text("Permite navegar por la estructura del conocimiento indexado:")
    _bullet_list(
        [
            "Taxonomía de categorías y subdimensiones",
            "Glosarios de términos",
            "Documentos de referencia metodológica",
            "Reglas de clasificación",
        ]
    )

    _subtitle_heading("Cargar Documentos (Admin)")
    _body_text(
        "Los administradores pueden cargar nuevos documentos a ChromaDB "
        "para enriquecer la base de conocimiento. Los documentos se "
        "dividen en fragmentos (chunks) y se indexan vectorialmente."
    )

    _subtitle_heading("Editor de Markdown (Admin)")
    _body_text(
        "Permite editar directamente los archivos markdown de la "
        "taxonomía y glosarios desde la interfaz web."
    )

    _screenshot_card("06_conocimiento.png", "Figura 7: Base de conocimiento")

    # =================================================================
    # 9. CHAT RAG
    # =================================================================
    section_header(
        "Sección 9",
        "Chat con Enola (RAG)",
        subtitle="Asistente interactivo basado en la base de conocimiento",
    )

    _body_text(
        "El chat interactivo es una de las funcionalidades más potentes. "
        "Utiliza RAG para responder preguntas basándose en la base de "
        "conocimiento indexada."
    )

    _subtitle_heading("Cómo Usar el Chat")
    _step_card(
        "1", "Escriba su pregunta", "Ingrese la consulta en el campo de texto del chat.", "edit"
    )
    _step_card(
        "2", "Envíe la consulta", "Presione Enter o haga clic en el botón de enviar.", "send"
    )
    _step_card(
        "3",
        "Reciba la respuesta",
        "Enola responderá basándose en la taxonomía y documentos indexados.",
        "quickreply",
    )
    _step_card(
        "4",
        "Revise las fuentes",
        "Las respuestas incluyen referencias a las fuentes utilizadas.",
        "source",
    )

    _subtitle_heading("Ejemplos de Preguntas")
    _bullet_list(
        [
            "¿Qué es la violencia simbólica?",
            "¿Cuáles son las subdimensiones de la categoría 3?",
            "¿Cómo se clasifica el slut-shaming?",
            "¿Qué marcadores lingüísticos indican hostilidad?",
        ]
    )

    _info_box(
        "Sobre el modelo",
        "El chat utiliza Ollama con el modelo qwen3.5:9b ejecutándose "
        "localmente. Las respuestas se generan en español argentino "
        "para mantener coherencia con el dominio de estudio.",
    )

    _screenshot_card("07_chat.png", "Figura 8: Chat interactivo con Enola")

    # =================================================================
    # 10. MODO OSCURO
    # =================================================================
    section_header(
        "Sección 10", "Modo Oscuro", subtitle="Tema alternativo para cómoda visualización"
    )

    _body_text(
        "La plataforma incluye un modo oscuro que se puede activar "
        "desde el interruptor en la barra superior."
    )

    _subtitle_heading("Activar Modo Oscuro")
    _bullet_list(
        [
            "Localice el interruptor «Modo oscuro» en la barra superior derecha",
            "Haga clic en el interruptor para alternar entre modo claro y oscuro",
            "La preferencia se guarda automáticamente para su sesión",
        ]
    )

    _body_text(
        "El modo oscuro adapta todos los elementos de la interfaz: "
        "fondos, textos, gráficos, tablas y el menú lateral."
    )

    # =================================================================
    # 11. GLOSARIO
    # =================================================================
    section_header("Sección 11", "Glosario", subtitle="Definiciones de términos técnicos")

    glossary = [
        (
            "RAG",
            "Retrieval-Augmented Generation — técnica que combina recuperación de información con generación de texto por LLM.",
        ),
        ("LLM", "Large Language Model — modelo de lenguaje grande."),
        ("Ollama", "Plataforma para ejecutar modelos de lenguaje localmente."),
        ("ChromaDB", "Base de datos vectorial para almacenar embeddings de texto."),
        ("KPI", "Key Performance Indicator — indicador clave de rendimiento."),
        (
            "FPP",
            "Falso Positivo Potencial — contenido que la IA marcó como violento pero que podría no serlo.",
        ),
        (
            "CÓDIGO 99",
            "Etiqueta de exclusión para basura digital (vacíos, enlaces huérfanos, ruido tipográfico, risas, reacciones cortas).",
        ),
        (
            "Taxonomía",
            "Sistema de clasificación de 6 categorías y 19 subdimensiones para violencia de género digital.",
        ),
        ("Few-shot", "Técnica de prompt que incluye ejemplos para guiar al LLM."),
        ("Severidad", "Nivel de gravedad de la violencia detectada (baja, media, alta)."),
        ("Subdimensión", "División específica dentro de cada categoría principal."),
        (
            "Basura digital",
            "Contenido sin valor semántico: stickers, GIFs, enlaces sueltos, muletillas, monosílabos.",
        ),
        (
            "Fiabilidad",
            "Nivel de calidad del análisis basado en la proporción de basura digital detectada.",
        ),
    ]

    ui.table(
        columns=[
            {"name": "termino", "label": "Término", "field": "termino", "align": "left"},
            {"name": "definicion", "label": "Definición", "field": "definicion", "align": "left"},
        ],
        rows=[{"termino": t, "definicion": d} for t, d in glossary],
    ).classes("w-full").style("border: none; background: transparent;")

    # ── Footer ─────────────────────────────────────────────────────────
    ui.separator().style("background: rgba(191,161,129,0.25); margin: 2rem 0 1rem;")
    with ui.column().classes("w-full items-center gap-2"):
        ui.label("Manual de Uso — Enola Investigadora Digital").classes("text-xs").style(
            "color: var(--enola-charcoal-light); font-style: italic;"
        )
        ui.label("Universidad de Granada — TFM 2026").classes("text-xs").style(
            "color: var(--enola-charcoal-light);"
        )


# ── Page registration ──────────────────────────────────────────────────────


@ui.page("/tutorial")
def page_tutorial() -> None:
    page_scaffold(
        "Tutorial / Manual de Uso",
        subtitle="Guía completa de la plataforma",
        current_path="/tutorial",
        body=_render_body,
        requires_auth=False,
    )
