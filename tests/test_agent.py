"""
Tests for the planning loop's retry-with-fallback logic (agent.py).

These exercise _search_with_fallback directly: it calls only search_listings
(no LLM / network), so the tests are deterministic and fast.
"""

from agent import _search_with_fallback


def test_exact_match_no_loosening():
    """A query that matches as-is returns results and NO relaxation note."""
    results, note = _search_with_fallback(
        {"description": "vintage graphic tee", "size": None, "max_price": 50}
    )
    assert len(results) > 0
    assert note is None


def test_fallback_drops_price():
    """Impossibly low price -> tier 1 empty -> drop price -> results + price note."""
    results, note = _search_with_fallback(
        {"description": "vintage graphic tee", "size": None, "max_price": 1}
    )
    assert len(results) > 0, "Should find tees once the price ceiling is dropped"
    assert note is not None and "price" in note.lower()


def test_fallback_drops_size():
    """Price None, impossible size -> tier 2 skipped -> drop size -> results + size note."""
    results, note = _search_with_fallback(
        {"description": "vintage graphic tee", "size": "XXS", "max_price": None}
    )
    assert len(results) > 0, "Should find tees once the size filter is dropped"
    assert note is not None and "size" in note.lower()


def test_gives_up_no_filters():
    """Unmatchable description with no size/price -> nothing to loosen -> empty, no note."""
    results, note = _search_with_fallback(
        {"description": "qwerty zzz unmatchable", "size": None, "max_price": None}
    )
    assert results == []
    assert note is None
