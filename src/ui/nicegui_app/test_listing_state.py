"""Unit tests for the centralised :class:`ListingState` helper.

These are pure-Python tests — they don't boot NiceGUI. The goal is
to lock down the URL/storage round-trip and the sort/paginate helpers
so refactors of ``validacion.py`` can't silently regress them.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.ui.nicegui_app.components.listing_state import (
    CONTENT_TYPE_ALL,
    CONTENT_TYPE_POST,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_KEY,
    PAGE_SIZE_CHOICES,
    REVIEW_AGREED,
    REVIEW_PENDING,
    ListingState,
    apply_sort,
    default,
    from_query,
    from_storage,
    paginate,
    save_to_storage,
)


class TestListingStateDefaults:
    def test_default_returns_pending_filter(self):
        st = default()
        assert st.content_type == CONTENT_TYPE_ALL
        assert st.review_state == REVIEW_PENDING
        assert st.only_violent is False
        assert st.sort_key == DEFAULT_SORT_KEY
        assert st.sort_dir == "asc"
        assert st.page == 1
        assert st.page_size == DEFAULT_PAGE_SIZE

    def test_state_is_frozen(self):
        st = default()
        with pytest.raises(FrozenInstanceError):
            st.content_type = CONTENT_TYPE_POST  # type: ignore[misc]

    def test_with_updates_returns_new_instance(self):
        st = default()
        st2 = st.with_updates(content_type=CONTENT_TYPE_POST)
        assert st is not st2
        assert st.content_type == CONTENT_TYPE_ALL
        assert st2.content_type == CONTENT_TYPE_POST

    def test_filter_changes_reset_page(self):
        st = default().with_updates(page=5)
        st2 = st.with_updates(content_type=CONTENT_TYPE_POST)
        assert st2.page == 1

    def test_sort_changes_reset_page(self):
        st = default().with_updates(page=5)
        st2 = st.with_updates(sort_key="categoria")
        assert st2.page == 1

    def test_pagesize_changes_reset_page(self):
        st = default().with_updates(page=5)
        st2 = st.with_updates(page_size=50)
        assert st2.page == 1

    def test_explicit_page_override_is_honoured(self):
        st = default()
        st2 = st.with_updates(content_type=CONTENT_TYPE_POST, page=3)
        assert st2.page == 3


class TestQueryRoundTrip:
    def test_from_query_empty_returns_default(self):
        assert from_query("") == default()

    def test_from_query_strips_leading_question_mark(self):
        st = from_query("?ct=post&st=agreed&ov=1")
        assert st.content_type == CONTENT_TYPE_POST
        assert st.review_state == REVIEW_AGREED
        assert st.only_violent is True

    def test_from_query_unknown_values_fall_back_to_default(self):
        st = from_query("ct=banana&st=pineapple&ov=42")
        assert st.content_type == CONTENT_TYPE_ALL
        assert st.review_state == REVIEW_PENDING
        assert st.only_violent is False

    def test_from_query_invalid_int_falls_back(self):
        st = from_query("p=abc&ps=lima")
        assert st.page == 1
        assert st.page_size == DEFAULT_PAGE_SIZE

    def test_from_query_negative_page_clamps_to_one(self):
        st = from_query("p=-3")
        assert st.page == 1

    def test_roundtrip_preserves_state(self):
        original = ListingState(
            content_type=CONTENT_TYPE_POST,
            review_state=REVIEW_AGREED,
            only_violent=True,
            sort_key="categoria",
            sort_dir="desc",
            page=4,
            page_size=50,
        )
        encoded = original.to_query()
        restored = from_query(encoded)
        assert restored == original


class TestStorageRoundTrip:
    def test_from_storage_none_returns_default(self):
        assert from_storage(None) == default()

    def test_from_storage_missing_key_returns_default(self):
        assert from_storage({}) == default()

    def test_from_storage_corrupt_dict_uses_defaults(self):
        saved = {"listing_state": {"content_type": "post", "sort_key": "nonsense", "page": -99}}
        st = from_storage(saved)
        assert st.content_type == CONTENT_TYPE_POST
        assert st.sort_key == DEFAULT_SORT_KEY
        assert st.page == 1

    def test_save_to_storage_persists_full_state(self):
        storage: dict = {}
        st = ListingState(
            content_type=CONTENT_TYPE_POST,
            only_violent=True,
            sort_key="categoria",
            page=3,
        )
        save_to_storage(storage, st)
        assert "listing_state" in storage
        restored = from_storage(storage)
        assert restored == st

    def test_save_to_storage_none_is_noop(self):
        save_to_storage(None, default())


class TestSort:
    def _rows(self):
        return [
            {
                "content_type": "post",
                "categoria": "A",
                "severidad": "alta",
                "feedback_status": "pending",
            },
            {
                "content_type": "comment",
                "categoria": "B",
                "severidad": "baja",
                "feedback_status": "agreed",
            },
            {
                "content_type": "post",
                "categoria": "C",
                "severidad": "media",
                "feedback_status": "disagreed",
            },
        ]

    def test_sort_unknown_key_returns_copy(self):
        rows = self._rows()
        out = apply_sort(rows, sort_key="not_a_field", sort_dir="asc")
        assert out == rows
        assert out is not rows

    def test_sort_by_content_type_asc(self):
        out = apply_sort(self._rows(), sort_key="content_type", sort_dir="asc")
        assert [r["content_type"] for r in out] == ["comment", "post", "post"]

    def test_sort_by_severidad_desc(self):
        out = apply_sort(self._rows(), sort_key="severidad", sort_dir="desc")
        assert [r["severidad"] for r in out] == ["alta", "media", "baja"]

    def test_sort_by_estado_groups_pending_first(self):
        out = apply_sort(self._rows(), sort_key="estado", sort_dir="asc")
        assert [r["feedback_status"] for r in out] == [
            "pending",
            "disagreed",
            "agreed",
        ]

    def test_sort_by_estado_desc_flips_order(self):
        out = apply_sort(self._rows(), sort_key="estado", sort_dir="desc")
        assert [r["feedback_status"] for r in out] == [
            "agreed",
            "disagreed",
            "pending",
        ]


class TestPaginate:
    def _rows(self, n: int = 10):
        return [{"id": i} for i in range(n)]

    def test_paginate_first_page(self):
        rows, total = paginate(self._rows(30), page=1, page_size=10)
        assert total == 3
        assert [r["id"] for r in rows] == list(range(0, 10))

    def test_paginate_last_partial_page(self):
        rows, total = paginate(self._rows(25), page=3, page_size=10)
        assert total == 3
        assert [r["id"] for r in rows] == [20, 21, 22, 23, 24]

    def test_paginate_empty_returns_total_one(self):
        rows, total = paginate([], page=1, page_size=10)
        assert rows == []
        assert total == 1

    def test_paginate_page_below_range_clamps_to_one(self):
        rows, total = paginate(self._rows(10), page=0, page_size=5)
        assert total == 2
        assert [r["id"] for r in rows] == list(range(0, 5))

    def test_paginate_page_above_range_clamps_to_last(self):
        rows, total = paginate(self._rows(7), page=99, page_size=5)
        assert total == 2
        assert [r["id"] for r in rows] == [5, 6]

    def test_paginate_returns_new_list(self):
        rows, _ = paginate(self._rows(3), page=1, page_size=10)
        assert rows is not self._rows(3)


class TestPageSizeChoices:
    def test_choices_contain_default(self):
        assert DEFAULT_PAGE_SIZE in PAGE_SIZE_CHOICES

    def test_choices_are_positive(self):
        assert all(p > 0 for p in PAGE_SIZE_CHOICES)
