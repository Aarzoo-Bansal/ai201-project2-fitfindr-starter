"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import json

from tools import search_listings, suggest_outfit, create_fit_card
from utils.llm_client import get_groq_client
from prompts import PARSE_QUERY_SYSTEM, PARSE_QUERY_USER

# ── parse user query ──────────────────────────────────────────────────────────
def _parse_user_query(query: str) -> dict:
    _client = get_groq_client()

    user_query = PARSE_QUERY_USER.format(query=query)

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": PARSE_QUERY_SYSTEM},
                {"role": "user", "content": user_query},
            ],
            temperature=0.0
        )
        print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "description": query,
            "size": None,
            "max_price": None,
        }



# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "search_note": None,         # set if search filters were loosened to find results
        "error": None,               # set if the interaction ended early
    }


# ── search with fallback ────────────────────────────────────────────────────────

def _search_with_fallback(parsed: dict) -> tuple[list[dict], str | None]:
    """
    Run search_listings, loosening constraints if the first attempt is empty.

    Only filters that were actually set get relaxed, and price is relaxed before
    size — size is a physical constraint (a wrong-size item won't fit) while price
    is a soft preference, so we keep the user in their real size as long as we can.

    Returns:
        (results, note) where note is None on an exact match, or a short sentence
        describing what was loosened. results is [] if nothing was found even after
        relaxing every set filter (or there were no filters to relax).
    """
    desc = parsed["description"]
    size = parsed.get("size")
    price = parsed.get("max_price")

    # Tier 1: full query as the user expressed it.
    results = search_listings(desc, size, price)
    if results:
        return results, None

    # Tier 2: drop the price ceiling (only if one was set).
    if price is not None:
        results = search_listings(desc, size, None)
        if results:
            where = f" in size {size}" if size else ""
            return results, f"No matches under ${price:.0f}{where} — showing items at all prices."

    # Tier 3: also drop the size filter (only if one was set).
    if size is not None:
        results = search_listings(desc, None, None)
        if results:
            return results, f"No matches in size {size} — showing all sizes and prices."

    # Nothing left to loosen, or still empty after loosening everything.
    return [], None


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    # Parsing User Query
    session["parsed"] = _parse_user_query(query=query)

    # Calling Tool1: search_listings (with fallback loosening on empty results)
    search_results, search_note = _search_with_fallback(session["parsed"])

    if not search_results:
        relaxed = session["parsed"].get("size") or session["parsed"].get("max_price")
        session["error"] = (
            "No listings matched even after removing your size and price filters. "
            "Try different keywords."
            if relaxed else
            f"No listings match '{session['parsed']['description']}'. Try different keywords."
        )
        return session

    session["search_results"] = search_results
    session["selected_item"] = search_results[0]
    session["search_note"] = search_note
    
    # Calling Tool2: suggest_outfit
    session["outfit_suggestion"] = suggest_outfit(new_item=session["selected_item"], wardrobe=session["wardrobe"])

    # Calling Tool3: create_fit_card
    session["fit_card"] = create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    # ── State flow verification ──
    print("\n=== State flow checks ===")
    print(f"selected_item is search_results[0]: {session['selected_item'] is session['search_results'][0]}")
    print(f"outfit_suggestion is non-empty: {bool(session['outfit_suggestion'])}")
    print(f"fit_card is non-empty: {bool(session['fit_card'])}")
    print(f"error is None: {session['error'] is None}")

    # ── No-results path ──
    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")
    print(f"outfit_suggestion is None: {session2['outfit_suggestion'] is None}")
    print(f"search_results is empty: {session2['search_results'] == []}")
