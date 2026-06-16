from tools import search_listings, suggest_outfit, create_fit_card
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


# ── create_fit_card tests ────────────────────────────────────────────────────

def test_create_fit_card_happy_path():
    item = _get_test_item()
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_empty_outfit():
    item = _get_test_item()
    result = create_fit_card("", item)
    assert result == "Couldn't generate a fit card — no outfit suggestion was provided."


def test_create_fit_card_whitespace_outfit():
    item = _get_test_item()
    result = create_fit_card("   ", item)
    assert result == "Couldn't generate a fit card — no outfit suggestion was provided."


def test_create_fit_card_mentions_item():
    item = _get_test_item()
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    result_lower = result.lower()
    assert item["platform"].lower() in result_lower, "Caption should mention the platform"


def test_create_fit_card_varies_output():
    item = _get_test_item()
    outfit = suggest_outfit(item, get_example_wardrobe())
    result1 = create_fit_card(outfit, item)
    result2 = create_fit_card(outfit, item)
    assert result1 != result2, "Captions should vary between runs (temperature > 0)"