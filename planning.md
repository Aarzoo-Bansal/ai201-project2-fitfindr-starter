# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given user input, this tool will do a keyword matching against all the listings in the database.
- Filters through price, if given.
- Filters through size, if given.
- Match the description to all the other attributes - style tag, description, color, etc.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords describing what the user is looking for (e.g., "vintage graphic tee")
- `size` (str): optional; the size of the garment/shoe that the user wants
- `max_price` (float): option; the max price that user wants to spend on the new item.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
- A list of matching listings sorted by relevance (most matched first)
- An empty list if there is no match

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
- When `search_listings` returns nothing, the planning loop does **not** stop immediately. It retries with loosened constraints (see the "Stretch Feature: Retry with fallback" section): first it drops the price ceiling, then the size filter, re-calling `search_listings` each time. Only the filters that were actually set get relaxed.
- If a retry succeeds, the agent records a short note (e.g. "No matches under $30 in size M — showing items at all prices.") that is shown to the user above the listing.
- Only if every set filter has been removed and there are still no results (or there were no filters to relax) does the agent set `session["error"]` and stop without calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given the new listing matched with user's preference and user's wardrobe, `suggest_outfit` tries to match new listing with items in the wardrobe to create an outfit suggestion.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The top matched listing from `search_listings` that matches user's preference.
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty. When wardrobe is empty, the tool is supposed to provide a general styling advice.

**What it returns:**
<!-- Describe the return value -->
- A non-empty string with outfit suggestions.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
- The tool `suggest_outfit` is designed to not fail on an empty wardrobe. When the wardrobe is empty, the LLM is required to offer general advice.
- In case of an LLM error, send a friendly message to the user stating "couldn't generate at the moment. Please try again later" and skip caption creation step.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates Instagram/Tiktok ready to share caption for suggested outfit.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion created by the tool `suggest_outfit`
- `new_item` (dict): The top matched listing from `search_listings` that matches user's preference.

**What it returns:**
<!-- Describe the return value -->
- A string output of 2-4 sentences that is a ready-to-use Instagram/TikTok caption

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- The tool returns a friendly message: "Couldn't generate a fit card — no outfit suggestion was provided."

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
#### *The application starts when user enters input. The agent first parses the query, then runs the planning loop.*

0. **Query Parsing** — The agent calls `_parse_user_query()`, which sends the raw query to the Groq LLM (`llama-3.3-70b-versatile`, temperature 0.0) with few-shot examples. The LLM extracts three fields: `description` (keywords only), `size` (normalized — e.g., "medium" → "M"), and `max_price` (as a number). The result is stored in `session["parsed"]`. If the LLM fails or returns invalid JSON, the fallback uses the raw query as `description` with `size` and `max_price` set to `null`.

1. Tool `search_listings` is called with the parsed fields (`description`, `size`, `max_price`).
     - If a match is found, the results are stored in *session.search_results*, the top result in *session.selected_item*, and the next tool is called.
     - If no match is found, the loop retries with loosened constraints — first dropping the price ceiling, then the size filter (only filters that were actually set). If a retry succeeds, a note explaining what was relaxed is stored in *session.search_note* and the loop continues.
     - Only if every set filter has been removed and there are still no results does the agent set *session.error* and stop without calling the next tools.
2. If the tool `suggest_outfit` is called with the new_item as well as user's wardrobe.
     - If the wardrobe is empty, then the tool is supposed to provide a general styling advice, otherwise it matches the new_item with the wardrobe to suggest the outfit.
     - If the LLM fails, then that means the tool call has failed and we stop the loop. Otherwise the next tool is called.
3. Now the tool `create_fit_card` is called with new_item as well as outfit. 
     - If there is not outfit, send user friendly message that outfit is empty.
     - With all the valid inputs, the tool provides a caption which can be used on instagram or tiktok.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
- All state for a single interaction is stored in a session dict, created fresh by `_new_session()` at the start of every query. Each tool reads from earlier fields and writes to its own field. If any step fails, `error` is set and the remaining fields stay `None`.

- **Session fields and data flow:**

| Field | Set by | Read by | Initial value |
|-------|--------|---------|---------------|
| `query` | `_new_session()` | Query parser | User's raw input string |
| `parsed` | Query parser (Step 2) | `search_listings` | `{}` |
| `search_results` | `search_listings` (Step 3) | Item selection (Step 4) | `[]` |
| `selected_item` | Step 4 (`results[0]`) | `suggest_outfit`, `create_fit_card` | `None` |
| `wardrobe` | `_new_session()` | `suggest_outfit` | Passed in from UI |
| `outfit_suggestion` | `suggest_outfit` (Step 5) | `create_fit_card` | `None` |
| `fit_card` | `create_fit_card` (Step 6) | Final output to user | `None` |
| `search_note` | `search_listings` retry (Step 3) | `handle_query()` in app.py | `None` |
| `error` | Any step that fails | `handle_query()` in app.py | `None` |

- The session dict is the **single source of truth**. No data is passed between tools directly — every tool writes to the session, and the next tool reads from it.
     

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Retry with loosened constraints (drop price, then size — see "Stretch Feature: Retry with fallback"). If a retry finds results, store a note in `session["search_note"]` and continue. Only if every set filter has been removed and still nothing matches, set `session["error"]` to "No listings matched even after removing your size and price filters. Try different keywords." and return early — tools 2 and 3 are **not called**. |
| suggest_outfit | Wardrobe is empty | Not a failure — the tool handles this internally by asking the LLM for general styling advice instead of wardrobe-specific outfits. The loop continues normally. |
| suggest_outfit | Groq API call fails (timeout, rate limit, bad key) | The tool catches the exception internally and returns a friendly message string: "Couldn't generate outfit suggestions right now. Please try again later." No exception is raised to the agent. |
| create_fit_card | Outfit input is empty or whitespace | The tool returns a descriptive error message string: "Couldn't generate a fit card — no outfit suggestion was provided." No exception is raised. |
| create_fit_card | Groq API call fails (timeout, rate limit, bad key) | The tool catches the exception internally and returns a friendly message string: "Couldn't generate a fit card right now. Please try again later." No exception is raised to the agent. |

---

## Architecture

```mermaid
flowchart TD
    Start([Start]) --> UQ[User Query]
    UQ -- "output: user_query" --> INIT["session.query = user_query\nsession.wardrobe = wardrobe"]
    INIT --> PARSE[LLM Parser]
    PARSE -- "output: parsed_query" --> STORE_PARSED["session.parsed = parsed_query"]
    STORE_PARSED --> T1["Tool 1: search_listings\n(description + size + price)"]
    T1 --> D1{found listing?}
    D1 -- "yes" --> STORE_SEARCH["session.search_results = results\nsession.selected_item = results[0]\nsession.search_note = note"]
    D1 -- "no, price was set" --> T1B["retry: search_listings\n(drop price)"]
    D1 -- "no, no filters to loosen" --> ERR["session.error = error"]
    T1B --> D1B{found listing?}
    D1B -- "yes" --> STORE_SEARCH
    D1B -- "no, size was set" --> T1C["retry: search_listings\n(drop size + price)"]
    D1B -- "no, size not set" --> ERR
    T1C --> D1C{found listing?}
    D1C -- "yes" --> STORE_SEARCH
    D1C -- "no" --> ERR
    STORE_SEARCH --> T2[Tool 2: suggest_outfit]
    T2 --> D2{got output?}
    D2 -- "yes" --> STORE_OUTFIT["session.outfit_suggestion = outfit"]
    D2 -- "no" --> ERR
    STORE_OUTFIT --> T3[Tool 3: create_fit_card]
    T3 --> D3{got output?}
    D3 -- "yes" --> STORE_CARD["session.fit_card = fit_card"]
    D3 -- "no" --> ERR
    STORE_CARD --> END_OK([End])
    ERR --> END_ERR([End])
```

*The Mermaid diagram above is the source of truth. `assets/architecture.excalidraw` is a hand-drawn visual of the base happy-path flow and does not show the retry-with-fallback tiers added later (drop price → drop size); see the "Stretch Feature: Retry with fallback" section for those.*

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

- **Tool 1 (`search_listings`):** I'll give Claude Code the Tool 1 spec from this planning.md (inputs, return value, failure mode) and ask it to implement `search_listings()` in `tools.py` using `load_listings()` from `utils/data_loader.py`. Before trusting it, I'll verify:
  - It filters by `max_price` and `size` when provided
  - It scores listings by keyword overlap with `description` against fields like `title`, `description`, `style_tags`, `colors`
  - It drops zero-score results and sorts by score descending
  - It returns `[]` for impossible queries (e.g., "designer ballgown", size="XXS", max_price=5)
  - I'll test with 3 queries: a happy-path match, a no-results query, and a price-only filter

- **Tool 2 (`suggest_outfit`):** I'll give Claude Code the Tool 2 spec and ask it to implement `suggest_outfit()` using the Groq client (`llama-3.3-70b-versatile`). Before trusting it, I'll verify:
  - It checks if `wardrobe["items"]` is empty and switches to a general-advice prompt
  - It wraps the Groq API call in a try/except and returns a friendly error string on failure
  - I'll test with both `get_example_wardrobe()` and `get_empty_wardrobe()` to confirm both paths work

- **Tool 3 (`create_fit_card`):** I'll give Claude Code the Tool 3 spec and ask it to implement `create_fit_card()` using the Groq client with a higher temperature for variety. Before trusting it, I'll verify:
  - It guards against an empty/whitespace `outfit` string and returns an error message
  - It wraps the Groq API call in a try/except
  - I'll run it twice on the same input to confirm outputs vary (not identical)

**Milestone 4 — Planning loop and state management:**

- I'll give Claude Code the Planning Loop section, State Management table, Error Handling table, and the Architecture diagram from this planning.md, and ask it to implement `run_agent()` in `agent.py`. Before trusting it, I'll verify:
  - It creates a fresh session with `_new_session()`
  - It parses the query to extract `description`, `size`, and `max_price`
  - It branches on empty `search_results` — sets `session["error"]` and returns early without calling tools 2 and 3
  - It stores each tool's output in the correct session field
  - I'll test with the happy-path query from the Complete Interaction section and the no-results query ("designer ballgown size XXS under $5") to confirm both paths work

- For `handle_query()` in `app.py`, I'll ask Claude Code to wire it up using the session dict. I'll verify it maps `session["error"]` to panel 1 with empty panels 2 and 3, and on success maps `selected_item`, `outfit_suggestion`, and `fit_card` to the three panels.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
- User input is first parsed to extract the useful information - such as description, size, and max price.
- Then agent calls the tool `search_listings`, to get matching data. Input to the tool is: description (required), size (optional) and max_price (optional).
- Out of everything matched, the top listing is selected.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
- Once we get a valid non-empty result from `search_listings`, the agent calls `suggest_outfit` tool is called. Input to this tool is: result of tool1 + user's wardrobe.
- In this tool, we use LLM to suggest an outfit out of the given user's wardrobe that goes with the result of tool1.
- The output of this tool is going to be a style advice.

**Step 3:**
<!-- Continue until the full interaction is complete -->
- Once we receive an non-empty output from `suggest_outfit`, the tool `create_fit_card` is called. Input to this tool is the result of tool1 and tool2.
- The output is an Instagram/Tiktok caption for the output.

**Final output to user:**
<!-- What does the user actually see at the end? -->
- The user on the screen sees the top matching listing from `search_listings`, outfit idea from `suggest_outfit`, and the Instagram caption from the last tool `create_fit_card`.

---

## Stretch Feature: Retry with fallback

**Goal:** When `search_listings` returns nothing, the agent should not give up at the first empty result. Instead it loosens one constraint and tries again, telling the user exactly what it changed — turning a dead end into a reaction the planning loop makes based on the tool's result.

**Where it lives:** A helper `_search_with_fallback(parsed)` in `agent.py`. The `search_listings` tool itself is unchanged — all retry logic stays in the planning loop. The helper returns `(results, note)`, where `note` is `None` on an exact match or a sentence describing what was relaxed. `run_agent` stores `note` in `session["search_note"]`, and `app.py` prepends it (with an ℹ️) above the listing panel.

**Loosening order — price first, then size.** Size is a physical constraint (a wrong-size item won't fit); price is a soft preference. Relaxing price first keeps the user in their real size as long as possible. Only filters that were *actually set* get relaxed — if the query had no size and no price, there is nothing to loosen, so the agent gives up immediately rather than mangling the description keywords.

| Tier | Query | Fires when | User-facing note |
|------|-------|------------|------------------|
| 1 | description + size + max_price | always | none (exact match) |
| 2 | description + size, **price dropped** | a `max_price` was set | "No matches under $X in size {size} — showing items at all prices." |
| 3 | description, **size + price dropped** | a `size` was set | "No matches in size {size} — showing all sizes and prices." |
| fail | — | nothing left to loosen, or still empty | "No listings matched even after removing your size and price filters. Try different keywords." |

**Edge cases:**
- No size, no price → tiers 2/3 skipped → immediate, honest give-up.
- Price set, size None → tier 2 fires (drops price); tier 3 is a no-op.
- Size set, price None → tier 2 skipped; tier 3 fires (drops size).

**Tests:** `tests/test_agent.py` covers all four branches by calling `_search_with_fallback` directly (no LLM/network): exact match (no note), price-dropped, size-dropped, and the no-filter give-up.
