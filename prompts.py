# prompts.py — All LLM prompts in one place for easy versioning and tuning.

# ── suggest_outfit prompts ────────────────────────────────────────────────────

# v1: basic system role + outfit suggestion prompts
SUGGEST_OUTFIT_SYSTEM = (
    "You are a personal stylist who specializes in thrifted and secondhand fashion. "
    "You give specific, practical outfit advice. Keep suggestions to 1-2 complete outfits. "
    "Be concise — no lengthy introductions or disclaimers."
)

# v2: switched to structured item format + added description field
SUGGEST_OUTFIT_WITH_WARDROBE = """I just found this thrifted item:

Item: {title}
Category: {category}
Colors: {colors}
Style: {style_tags}
Condition: {condition}
Description: {description}

Here's what I already own:
{wardrobe_text}

Suggest 1-2 complete outfits combining the new item with specific pieces from my wardrobe. Reference my pieces by name. For each outfit, describe the vibe in a few words."""

SUGGEST_OUTFIT_EMPTY_WARDROBE = """I just found this thrifted item:

Item: {title}
Category: {category}
Colors: {colors}
Style: {style_tags}
Condition: {condition}
Description: {description}

I don't have a wardrobe set up yet. Give me general styling advice — what kinds of pieces would pair well with this item, what vibe it suits, and how to style it."""


# ── create_fit_card prompts ───────────────────────────────────────────────────

# v1: Instagram/TikTok caption generation
CREATE_FIT_CARD_SYSTEM = (
    "You are an expert Gen-Z fashion content creator who writes Instagram and TikTok captions. "
    "You sound casual, authentic, and effortless — like a real person posting an OOTD, "
    "never a product description or ad."
)

CREATE_FIT_CARD_USER = """Write a short Instagram/TikTok caption for this outfit:

Item: {title}
Price: ${price}
Platform: {platform}
Category: {category}
Colors: {colors}
Style: {style_tags}
Condition: {condition}
Description: {description}
Outfit idea: {outfit}

Rules:
- Mention the item name, price, and platform naturally (once each)
- Capture the outfit vibe in specific terms
- 2-4 sentences max"""