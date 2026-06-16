"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq
from prompts import SUGGEST_OUTFIT_SYSTEM, SUGGEST_OUTFIT_WITH_WARDROBE, SUGGEST_OUTFIT_EMPTY_WARDROBE, CREATE_FIT_CARD_SYSTEM, CREATE_FIT_CARD_USER


from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────
def _size_matches(user_size, listing_size):
    user_size = user_size.lower()

    parts = listing_size.lower().replace("/", " ").replace("(", " ").replace(")", " ").split()
    return user_size in parts

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    # Replace this with your implementation
    listings = load_listings()

    # Filtering by max_price if available
    if max_price is not None:
        listings = [listing for listing in listings if listing["price"] <= max_price]

    # Filtering by sze if available
    if size is not None:
        listings = [listing for listing in listings if _size_matches(size, listing["size"])]
    
    # keyword matching
    keywords = description.lower().split()
    scored = []

    for listing in listings:
        # Build one big searchable string from relevant fields
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["brand"] or ""
        ]).lower()

        score = sum(1 for keyword in keywords if keyword in searchable)
        if score > 0:
            scored.append((score, listing))
    
    # Sorting by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [listing for score, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    item_fields = dict(
        title=new_item["title"],
        category=new_item["category"],
        colors=", ".join(new_item["colors"]),
        style_tags=", ".join(new_item["style_tags"]),
        condition=new_item["condition"],
        description=new_item["description"],
    )

    if wardrobe and wardrobe.get("items"):
        wardrobe_text = "\n".join(
            f"- {item['name']} ({item['category']}, {', '.join(item['colors'])})"
            for item in wardrobe['items']
            )

        user_prompt = SUGGEST_OUTFIT_WITH_WARDROBE.format(
            **item_fields, wardrobe_text=wardrobe_text
        )

    else:
        user_prompt = SUGGEST_OUTFIT_EMPTY_WARDROBE.format(**item_fields)
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SUGGEST_OUTFIT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception:
        return "Couldn't generate outfit suggestions right now. Please try again later."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)
    """
    if not outfit or not outfit.strip():
        return "Couldn't generate a fit card — no outfit suggestion was provided."

    client = _get_groq_client()

    user_prompt = CREATE_FIT_CARD_USER.format(
        title=new_item["title"],
        price=new_item["price"],
        platform=new_item["platform"],
        category=new_item["category"],
        colors=", ".join(new_item["colors"]),
        style_tags=", ".join(new_item["style_tags"]),
        condition=new_item["condition"],
        description=new_item["description"],
        outfit=outfit,
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CREATE_FIT_CARD_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception:
        return "Couldn't generate a fit card right now. Please try again later."
