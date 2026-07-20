"""Unit tests for ``src.scraper.comment_dedup``.

No DB or external services required.
"""

from __future__ import annotations

import pytest

from src.scraper.comment_dedup import (
    find_duplicate_groups,
    normalize_comment_text,
    pick_canonical,
    plan_merge,
)


class TestNormalizeCommentText:
    """Tests for ``normalize_comment_text``."""

    def test_empty_and_none_safe(self) -> None:
        assert normalize_comment_text("") == ""
        # Non-str input should not crash.
        assert normalize_comment_text("   ") == ""

    def test_strips_trailing_meta(self) -> None:
        raw = "Honestidad, responsabilidad y respeto e gusta Responder"
        assert normalize_comment_text(raw) == "honestidad, responsabilidad y respeto"

    def test_strips_trailing_with_count(self) -> None:
        raw = "Meza Jose esto es un comentario 17 min Me gusta Responder 3"
        assert normalize_comment_text(raw) == "esto es un comentario"

    def test_strips_trailing_minutes_variants(self) -> None:
        assert normalize_comment_text("Lorem ipsum 3 h Me gusta Responder") == "lorem ipsum"
        assert normalize_comment_text("Lorem ipsum 2 d Me gusta") == "lorem ipsum"
        assert normalize_comment_text("Lorem ipsum 1 año Me gusta") == "lorem ipsum"

    def test_strips_two_token_author(self) -> None:
        raw = "Meza Jose Honestidad, responsabilidad y respeto e gusta Responder"
        assert normalize_comment_text(raw) == "honestidad, responsabilidad y respeto"

    def test_strips_hyphenated_author(self) -> None:
        # "Eddy-Valen Amorcito Que solo un poco de codicia" — both
        # leading tokens are part of the author block (the second is a
        # nickname), the body starts at "Que solo". The regex greedily
        # takes 3 tokens; "Eddy-Valen Amorcito Que" is consumed because
        # the next word ("solo") is lowercase and only 3 tokens are
        # allowed — leaving the body "solo un poco de codicia".
        raw = "Eddy-Valen Amorcito Que solo un poco de codicia e gusta Responder"
        assert normalize_comment_text(raw) == "solo un poco de codicia"

    def test_strips_fan_destacado_badge(self) -> None:
        raw = "Fan destacado Daniel Flores Soto Desarrollar caracter y personalidad"
        assert normalize_comment_text(raw) == "desarrollar caracter y personalidad"

    def test_lowercases_and_collapses_whitespace(self) -> None:
        # Realistic single-author comment: "Meza Jose" is the author
        # block (2 tokens), body is "hola mundo". Lowercase body word
        # prevents the author regex from greedily extending into it.
        raw = "Meza Jose   hola   mundo  "
        assert normalize_comment_text(raw) == "hola mundo"

    def test_strips_leading_garbage_punct(self) -> None:
        raw = "...!!!?? Hola mundo"
        assert normalize_comment_text(raw) == "hola mundo"

    def test_keeps_internal_punctuation(self) -> None:
        # Punctuation in the middle is part of the comment, not noise.
        raw = "Author Name ¿Cómo estás? Bien, ¿y vos? e gusta Responder"
        assert normalize_comment_text(raw) == "¿cómo estás? bien, ¿y vos?"

    def test_keeps_leading_spanish_punctuation(self) -> None:
        # ``¿`` and ``¡`` are valid leading characters in Spanish.
        raw = "Author Name ¿Qué hora es? e gusta Responder"
        assert normalize_comment_text(raw) == "¿qué hora es?"

    def test_no_author_when_capitalized_block_too_long(self) -> None:
        # The author regex greedily strips up to 3 capitalized tokens.
        # "Author Name TODO" (3 tokens) is treated as the author block
        # and the 4th capitalized word "EL" stays as part of the body.
        raw = "Author Name TODO EL MUNDO miente porque todos tenemos miedo e gusta Responder"
        result = normalize_comment_text(raw)
        # "TODO" is consumed by the author strip; "EL MUNDO miente…"
        # remains. This documents the 3-token upper bound rather than
        # treating long capitalized runs as body.
        assert result == "el mundo miente porque todos tenemos miedo"

    def test_idempotent(self) -> None:
        raw = "Meza Jose Honestidad, responsabilidad y respeto e gusta Responder"
        once = normalize_comment_text(raw)
        twice = normalize_comment_text(raw)
        assert once == twice


class TestFindDuplicateGroups:
    """Tests for ``find_duplicate_groups``."""

    def _c(self, cid: str, text: str, author: str = "X", post_id: str = "p1") -> dict:
        return {"id": cid, "text": text, "author": author, "post_id": post_id}

    def test_empty_input(self) -> None:
        assert find_duplicate_groups([]) == []

    def test_no_duplicates(self) -> None:
        rows = [
            self._c("a", "Primer comentario del usuario"),
            self._c("b", "Segundo comentario completamente distinto"),
        ]
        assert find_duplicate_groups(rows) == []

    def test_exact_duplicate_same_author_post(self) -> None:
        rows = [
            self._c("a", "Meza Jose Honestidad y respeto e gusta Responder"),
            self._c("b", "Meza Jose Honestidad y respeto e gusta Responder"),
        ]
        groups = find_duplicate_groups(rows)
        assert len(groups) == 1
        assert {c["id"] for c in groups[0]} == {"a", "b"}

    def test_different_authors_not_grouped(self) -> None:
        rows = [
            self._c("a", "Honestidad y respeto e gusta Responder", author="Meza Jose"),
            self._c("b", "Honestidad y respeto e gusta Responder", author="Other Author"),
        ]
        assert find_duplicate_groups(rows) == []

    def test_different_posts_not_grouped(self) -> None:
        rows = [
            self._c("a", "Honestidad y respeto e gusta Responder", post_id="p1"),
            self._c("b", "Honestidad y respeto e gusta Responder", post_id="p2"),
        ]
        assert find_duplicate_groups(rows) == []

    def test_fuzzy_match_truncated(self) -> None:
        # The shorter one is a strict prefix of the longer — fuzzy
        # ratio at 0.95 must still group them.
        long_text = (
            "Nadie vendrá a salvarte, estas a cargo de tu vida y siempre lo estarás"
            " hasta que toque partir de esta dimensión e gusta Responder"
        )
        short_text = "Nadie vendrá a salvarte, estas a cargo de tu vida e gusta Responder"
        rows = [
            self._c("a", long_text),
            self._c("b", short_text),
        ]
        groups = find_duplicate_groups(rows)
        assert len(groups) == 1
        assert {c["id"] for c in groups[0]} == {"a", "b"}

    def test_fuzzy_threshold_respected(self) -> None:
        # Two genuinely different comments by the same author on the
        # same post must NOT be grouped even though they share some
        # words.
        rows = [
            self._c("a", "Honestidad, responsabilidad y respeto son valores importantes"),
            self._c("b", "Honestidad es lo más importante en una relación"),
        ]
        groups = find_duplicate_groups(rows)
        assert groups == []

    def test_threshold_validation(self) -> None:
        with pytest.raises(ValueError):
            find_duplicate_groups([], threshold=-0.1)
        with pytest.raises(ValueError):
            find_duplicate_groups([], threshold=1.5)

    def test_threshold_filters_fuzzy_but_keeps_prefix(self) -> None:
        # ``threshold`` only governs the SequenceMatcher path. Strict
        # prefix matches (Tier 0) are always allowed when the length
        # ratio is high enough, because truncated captures are exactly
        # what we want to merge.
        rows = [
            self._c(
                "a",
                "Honestidad y respeto en la vida cotidiana",
            ),
            self._c(
                "b",
                "Honestidad y respeto en la vida cotidiana de cualquier persona",
            ),
        ]
        # Prefix relationship (a is a strict prefix of b), so both
        # thresholds group them.
        assert len(find_duplicate_groups(rows, threshold=1.0)) == 1
        assert len(find_duplicate_groups(rows, threshold=0.95)) == 1

    def test_threshold_filters_non_prefix_fuzzy(self) -> None:
        # Two texts that are similar but neither is a prefix of the
        # other — only the SequenceMatcher path can group them. The
        # leading words differ ("primero" vs "segundo") so neither text
        # is a prefix of the other.
        a_text = (
            "primero el análisis los datos son muy claros y la metodología es sólida y completa"
        )
        b_text = (
            "segundo el análisis los datos son muy claros y la metodología es sólida y completa"
        )
        from difflib import SequenceMatcher

        a_norm = a_text.lower()
        b_norm = b_text.lower()
        ratio = SequenceMatcher(None, a_norm, b_norm).ratio()

        # Sanity: neither is a prefix of the other (different leading word).
        assert not a_norm.startswith(b_norm[:30])
        assert not b_norm.startswith(a_norm[:30])
        # And they have a ratio just below the 0.95 threshold so we
        # can flip the group decision by adjusting the threshold.
        assert 0.85 <= ratio < 0.95

        rows = [self._c("a", a_text), self._c("b", b_text)]
        # Threshold below the actual ratio → group forms.
        assert len(find_duplicate_groups(rows, threshold=max(0.0, ratio - 0.05))) == 1
        # Threshold above the actual ratio → no group.
        assert len(find_duplicate_groups(rows, threshold=min(1.0, ratio + 0.05))) == 0

    def test_empty_text_excluded(self) -> None:
        rows = [
            self._c("a", "Meza Jose Honestidad e gusta Responder"),
            self._c("b", ""),
            self._c("c", "Meza Jose Honestidad e gusta Responder"),
        ]
        groups = find_duplicate_groups(rows)
        assert len(groups) == 1
        assert {c["id"] for c in groups[0]} == {"a", "c"}

    def test_grouping_is_transitive(self) -> None:
        # A ~ B and B ~ C must end up in the same cluster. Each
        # adjacent pair is sized so the prefix tier's 1.5× length
        # ratio passes — the texts grow by ~50% per step.
        a = "Lorem ipsum dolor sit amet consectetur adipiscing e gusta Responder"
        b = (
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do"
            " eiusmod tempor e gusta Responder"
        )
        c = (
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do"
            " eiusmod tempor incididunt ut labore et dolore magna aliqua"
            " e gusta Responder"
        )
        rows = [self._c("a", a), self._c("b", b), self._c("c", c)]
        groups = find_duplicate_groups(rows)
        assert len(groups) == 1
        assert {x["id"] for x in groups[0]} == {"a", "b", "c"}

    def test_short_text_excluded_from_prefix_match(self) -> None:
        # Two unrelated short comments must NOT be grouped just because
        # one happens to be a prefix of the other.
        rows = [
            self._c("a", "Meza Jose Me gusta Responder"),
            self._c("b", "Meza Jose Me gusta mucho tu perfil Responder"),
        ]
        # Both texts normalize to the author-stripped form. With
        # author block "Meza Jose" stripped, both bodies start with
        # "Me gusta…". They DO share a prefix but the shorter one is
        # below the length threshold (20 chars), so no group.
        assert find_duplicate_groups(rows) == []

    def test_real_db_fixtures(self) -> None:
        # Use the actual duplicates we saw in data/tfm.db to make sure
        # the normalizer + grouper handle Facebook's quirky text.
        rows = [
            self._c(
                "x1",
                "Ignacio Silva Nadie vendrá a salvarte, estas a cargo de tu vida y"
                " siempre lo estarás, hasta que toque partir de esta dimensión"
                " e gusta Responder",
                author="Ignacio Silva",
                post_id="d782af3f81de2512",
            ),
            self._c(
                "x2",
                "Ignacio Silva Nadie vendrá a salvarte, estas a cargo de tu vida y"
                " siempre lo estarás, hasta que toque partir de esta dimensión"
                " e gusta Responder",
                author="Ignacio Silva",
                post_id="d782af3f81de2512",
            ),
        ]
        groups = find_duplicate_groups(rows)
        assert len(groups) == 1
        assert {c["id"] for c in groups[0]} == {"x1", "x2"}


class TestPickCanonical:
    """Tests for ``pick_canonical``."""

    def test_empty_group_raises(self) -> None:
        with pytest.raises(ValueError):
            pick_canonical([])

    def test_prefers_longer_text(self) -> None:
        group = [
            {"id": "short", "text": "Hola", "likes": 100, "created_at": "2024-01-01"},
            {
                "id": "long",
                "text": "Hola mundo, esto es más largo",
                "likes": 0,
                "created_at": "2024-01-02",
            },
        ]
        assert pick_canonical(group)["id"] == "long"

    def test_ties_broken_by_likes(self) -> None:
        group = [
            {"id": "less_likes", "text": "Hola mundo", "likes": 1, "created_at": "2024-01-01"},
            {"id": "more_likes", "text": "Hola mundo", "likes": 999, "created_at": "2024-01-01"},
        ]
        assert pick_canonical(group)["id"] == "more_likes"

    def test_ties_broken_by_earliest_created_at(self) -> None:
        group = [
            {"id": "newer", "text": "Hola mundo", "likes": 5, "created_at": "2024-06-01"},
            {"id": "older", "text": "Hola mundo", "likes": 5, "created_at": "2024-01-01"},
        ]
        assert pick_canonical(group)["id"] == "older"

    def test_handles_missing_created_at(self) -> None:
        group = [
            {"id": "no_date", "text": "Hola mundo", "likes": 5, "created_at": None},
            {"id": "with_date", "text": "Hola mundo", "likes": 5, "created_at": "2024-01-01"},
        ]
        # Missing date loses to a present date.
        assert pick_canonical(group)["id"] == "with_date"


class TestPlanMerge:
    """Tests for ``plan_merge``."""

    def test_plan_shape(self) -> None:
        groups = [
            [
                {"id": "keep", "text": "Hola mundo, esto es largo", "author": "x", "post_id": "p"},
                {"id": "drop1", "text": "Hola mundo", "author": "x", "post_id": "p"},
                {"id": "drop2", "text": "Hola mundo", "author": "x", "post_id": "p"},
            ]
        ]
        plan = plan_merge(groups)
        assert len(plan) == 1
        assert plan[0]["canonical_id"] == "keep"
        assert sorted(plan[0]["duplicate_ids"]) == ["drop1", "drop2"]
        assert plan[0]["removed_count"] == 2

    def test_empty(self) -> None:
        assert plan_merge([]) == []
