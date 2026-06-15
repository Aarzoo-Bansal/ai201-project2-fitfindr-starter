from tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size="L", max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit tests ─────────────────────────────────────────────────────

def _get_test_item():
    results = search_listings("vintage graphic tee", size=None, max_price=30)
    return results[0]


def test_suggest_outfit_with_wardrobe():
    result = suggest_outfit(_get_test_item(), get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe():
    result = suggest_outfit(_get_test_item(), get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_references_wardrobe_pieces():
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(_get_test_item(), wardrobe)
    result_lower = result.lower()
    has_reference = any(
        item["name"].lower().split(",")[0] in result_lower
        for item in wardrobe["items"]
    )
    assert has_reference, "Output should reference at least one wardrobe piece by name"