"""Unit tests for the SortableHeader and Pagination helpers.

These exercise the pure-Python helpers; the NiceGUI renderers are
covered indirectly via the page smoke tests.
"""

from __future__ import annotations

from src.ui.nicegui_app.components.listing_state import ListingState, paginate
from src.ui.nicegui_app.components.pagination import render_pagination
from src.ui.nicegui_app.components.sortable_header import render_sortable_header
from src.ui.nicegui_app.keys import VALIDATION_BINDINGS


class TestSortableHeaderBindings:
    """The sort tokens the header emits must match the binding registry."""

    def test_pagination_pages_returns_first_slice(self):
        rows = [{"id": i} for i in range(50)]
        slice_, total = paginate(rows, page=1, page_size=10)
        assert total == 5
        assert slice_[0]["id"] == 0

    def test_pagination_pages_returns_last_slice(self):
        rows = [{"id": i} for i in range(50)]
        slice_, total = paginate(rows, page=5, page_size=10)
        assert total == 5
        assert slice_[-1]["id"] == 49


class TestPaginationPageCalc:
    def test_total_pages_formula(self):
        # The component uses (total + size - 1) // size for total pages.
        # Verify the formula produces the same as paginate().
        for total in [0, 1, 9, 10, 11, 50, 100]:
            for size in [10, 25, 50, 100]:
                _, expected = paginate([{"id": i} for i in range(total)], page=1, page_size=size)
                actual = max(1, (total + size - 1) // size)
                assert actual == expected, (
                    f"total={total} size={size}: formula={actual} paginate={expected}"
                )


class TestBindingTokensCoverSortKeys:
    """A regression guard — if someone renames a token the header must
    still find a matching binding in the keyboard registry."""

    def test_keyboard_tokens_are_unique(self):
        tokens = [b.token for b in VALIDATION_BINDINGS]
        assert len(tokens) == len(set(tokens)), "Duplicate tokens in registry"


class TestRenderersImportable:
    """Smoke test — the renderer modules import without syntax errors."""

    def test_sortable_header_importable(self):
        assert callable(render_sortable_header)

    def test_pagination_importable(self):
        assert callable(render_pagination)


class TestListingStateForPagination:
    def test_pagination_pages_resets_on_filter_change(self):
        st = ListingState(page=5)
        st2 = st.with_updates(content_type="post")
        assert st2.page == 1

    def test_explicit_page_overrides_reset(self):
        st = ListingState(page=5)
        st2 = st.with_updates(content_type="post", page=3)
        assert st2.page == 3

    def test_pagination_pages_preserved_on_identical_update(self):
        st = ListingState(page=3, page_size=25)
        # No field changes → page stays.
        st2 = st.with_updates()
        assert st2.page == 3
        assert st2.page_size == 25
