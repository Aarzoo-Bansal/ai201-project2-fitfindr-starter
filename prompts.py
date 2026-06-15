# prompts.py — All LLM prompts in one place for easy versioning and tuning.

# ── suggest_outfit prompts ────────────────────────────────────────────────────

# v1: basic system role + outfit suggestion prompts
SUGGEST_OUTFIT_SYSTEM = (
    "You are a personal stylist who specializes in thrifted and secondhand fashion. "
    "You give specific, practical outfit advice. Keep suggestions to 1-2 complete outfits. "
    "Be concise — no lengthy introductions or disclaimers."
)

SUGGEST_OUTFIT_WITH_WARDROBE = """I just found this thrifted item: {item_desc}

Here's what I already own:
{wardrobe_text}

Suggest 1-2 complete outfits combining the new item with specific pieces from my wardrobe. Reference my pieces by name. For each outfit, describe the vibe in a few words."""

SUGGEST_OUTFIT_EMPTY_WARDROBE = """I just found this thrifted item: {item_desc}

I don't have a wardrobe set up yet. Give me general styling advice — what kinds of pieces would pair well with this item, what vibe it suits, and how to style it."""


