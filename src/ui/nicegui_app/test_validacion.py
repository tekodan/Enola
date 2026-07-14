"""Smoke tests for the /validacion page module.

The NiceGUI ``@ui.page`` registration runs at import time, so the
import itself is part of the contract we test. The form-validation
logic is plain Python, so we exercise it directly without booting a
server.
"""

from __future__ import annotations

import importlib

import pytest

from src.ui.nicegui_app.pages import validacion as validacion_module


def test_page_module_imports_cleanly():
    """Importing the page registers the route without crashing."""
    mod = importlib.import_module("src.ui.nicegui_app.pages.validacion")
    assert callable(mod.page_validacion)
    assert "page_validacion" in mod.__all__


class TestValidateForm:
    """``_validate_form`` must reject invalid (categoria, dimension) pairs."""

    def _state(self, **overrides):
        from src.ui.nicegui_app.pages.validacion import _RowFormState

        st = _RowFormState(ar_id=1, existing_fb=None)
        st.agrees = "no"
        st.labels = [
            {
                "categoria": "",
                "dimension": "",
                "severidad": "media",
            }
        ]
        for key, value in overrides.items():
            setattr(st, key, value)
        return st

    def test_agrees_yes_skips_label_validation(self):
        st = self._state(agrees="yes")
        st.labels = []  # empty list also fine when agrees=yes
        assert validacion_module._validate_form(st) is True
        assert st.feedback_msg is None

    def test_missing_categoria_in_row_is_rejected(self):
        st = self._state()
        st.labels = [{"categoria": "", "dimension": "", "severidad": "media"}]
        ok = validacion_module._validate_form(st)
        assert ok is False
        assert "categoría" in (st.feedback_msg or "").lower()

    def test_dimension_outside_category_is_rejected(self):
        st = self._state()
        st.labels = [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",  # valid
                "dimension": "3.1",  # belongs to VDG_HOSTILIDAD_FEMINICIDIO
                "severidad": "media",
            }
        ]
        ok = validacion_module._validate_form(st)
        assert ok is False
        assert st.feedback_kind == "error"

    def test_dimension_in_category_is_accepted(self):
        st = self._state()
        st.labels = [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "media",
            }
        ]
        assert validacion_module._validate_form(st) is True

    def test_empty_dimension_accepted(self):
        """When the reviewer doesn't care about a dimension, omit it."""
        st = self._state()
        st.labels = [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "",
                "severidad": "media",
            }
        ]
        assert validacion_module._validate_form(st) is True

    def test_multiple_valid_rows_pass(self):
        st = self._state()
        st.labels = [
            {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1", "severidad": "alta"},
            {"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.2", "severidad": "alta"},
        ]
        assert validacion_module._validate_form(st) is True


class TestRowFormState:
    def test_default_state_has_one_empty_row(self):
        from src.ui.nicegui_app.pages.validacion import _RowFormState

        st = _RowFormState(ar_id=42, existing_fb=None)
        assert st.agrees is None
        assert len(st.labels) == 1
        assert st.reason == ""

    def test_add_label_respects_max(self):
        from src.analyzer.category_mapping import MAX_LABELS
        from src.ui.nicegui_app.pages.validacion import _RowFormState

        st = _RowFormState(ar_id=42, existing_fb=None)
        for _ in range(MAX_LABELS + 5):
            st.add_label()
        assert len(st.labels) == MAX_LABELS

    def test_drop_last_label_floors_to_one(self):
        from src.ui.nicegui_app.pages.validacion import _RowFormState

        st = _RowFormState(ar_id=42, existing_fb=None)
        st.add_label()
        st.drop_last_label()
        st.drop_last_label()
        st.drop_last_label()
        assert len(st.labels) == 1

    def test_existing_flat_labels_normalized_into_list(self):
        from src.ui.nicegui_app.pages.validacion import _RowFormState

        flat = {
            "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
            "corrected_dimension": "1.1",
            "corrected_justificacion": "stereotype",
            "agrees": "false",
        }
        st = _RowFormState(ar_id=42, existing_fb=flat)
        assert len(st.labels) == 1
        assert st.labels[0]["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert st.agrees == "no"


@pytest.fixture
def _isolated_db(tmp_path, monkeypatch):
    """Bind the module's _feedback_store factory to a temp DB+vector dir."""
    from src.storage import database as db_module

    url = f"sqlite:///{tmp_path / 'validation-test.db'}"
    monkeypatch.setattr(db_module, "get_database", lambda: db_module.Database(url))
    return url


def test_persist_feedback_records_reviewer_user_id(_isolated_db):
    # Seed an analysis result to satisfy FK constraints.
    from datetime import datetime

    from src.storage import get_database as _
    from src.ui.nicegui_app.pages.validacion import _persist_feedback, _RowFormState

    db = _()
    db.save_post(
        {
            "id": "p1",
            "text": "x",
            "author": "x",
            "date": datetime(2024, 1, 1),
            "likes": 0,
            "comments_count": 0,
            "shares": 0,
            "url": "u",
            "page_id": "pg",
            "source": "facebook_page",
        }
    )
    rid = db.save_or_update_analysis_result(
        {
            "content_type": "post",
            "content_id": "p1",
            "post_id": "p1",
            "tiene_violencia": "true",
            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
            "severidad": "media",
        }
    )

    # Create the user that will be recorded as the reviewer.
    db.create_user("kim", "pw", role="reviewer", full_name="Kim")

    row = {
        "id": rid,
        "content_type": "post",
        "content_id": "p1",
        "text_snapshot": "x",
        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "labels": [],
    }
    user = {"id": 1, "username": "kim"}

    state = _RowFormState(ar_id=rid, existing_fb=None)
    state.agrees = "no"
    state.labels = [
        {"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1", "severidad": "alta"}
    ]

    # DB-only path — no ChromaDB push (pop-up would be triggered by the
    # second button, not this one).
    _persist_feedback(state=state, row=row, user=user, push_chromadb=False)

    stored = db.get_feedback_for_analysis(rid)
    assert stored is not None
    assert stored["reviewer_user_id"] == 1
    assert stored["reviewer_username"] == "kim"
    assert stored["agrees"] == "false"
    assert stored["corrected_categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
