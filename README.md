# FitFindr 🛍️

A multi-tool AI agent that helps you find secondhand clothing and figure out how to wear it. Given a natural-language request, FitFindr searches a mock listings dataset, suggests an outfit using your existing wardrobe, and writes a shareable "fit card" caption — orchestrating three tools through a planning loop that reacts to what each tool returns (including loosening the search when nothing matches).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Mac/Linux  (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## Running

```bash
python app.py        # launch the Gradio UI (open the localhost URL it prints)
python agent.py      # run the happy-path + no-results demo from the terminal
pytest tests/        # run the tool + planning-loop tests
```

## Project Structure

```
ai201-project2-fitfindr-starter/
├── agent.py                  # Planning loop (run_agent) + retry-with-fallback
├── tools.py                  # The three tools
├── prompts.py                # All LLM prompts (parsing, outfit, fit card)
├── app.py                    # Gradio UI (handle_query wires UI -> run_agent)
├── data/
│   ├── listings.json         # 40 mock secondhand listings
│   └── wardrobe_schema.json  # Wardrobe format + example/empty wardrobes
├── utils/
│   ├── data_loader.py        # load_listings(), get_example_wardrobe(), get_empty_wardrobe()
│   └── llm_client.py         # Groq client factory
├── tests/
│   ├── test_tools.py         # Each tool tested in isolation, incl. failure modes
│   └── test_agent.py         # Retry-with-fallback branches
├── planning.md               # Spec written before implementation
└── requirements.txt
```

---

## Tool Inventory

### 1. `search_listings`
- **Signature:** `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`
- **Inputs:**
  - `description` (`str`): keywords describing the item, e.g. `"vintage graphic tee"`.
  - `size` (`str | None`): size to filter by (case-insensitive, e.g. `"M"` matches `"S/M"`); `None` skips size filtering.
  - `max_price` (`float | None`): inclusive price ceiling; `None` skips price filtering.
- **Returns:** `list[dict]` — matching listing dicts sorted by relevance (most keyword matches first). Each dict has `id, title, description, category, style_tags, size, condition, price, colors, brand, platform`. Returns `[]` (never raises) when nothing matches.
- **Purpose:** Find candidate items in the dataset. Filters by price and size when given, then scores by keyword overlap across the title, description, category, style tags, colors, and brand.

### 2. `suggest_outfit`
- **Signature:** `suggest_outfit(new_item: dict, wardrobe: dict) -> str`
- **Inputs:**
  - `new_item` (`dict`): a listing dict (the item being considered, typically `search_listings()` top result).
  - `wardrobe` (`dict`): a wardrobe dict with an `"items"` key (a list of wardrobe-item dicts). May be empty.
- **Returns:** `str` — 1–2 outfit ideas. When the wardrobe has items, the suggestion names specific pieces from it; when empty, it gives general styling advice instead.
- **Purpose:** Turn a found item into wearable outfit ideas grounded in what the user already owns. Calls Groq `llama-3.3-70b-versatile` (temperature 0.7).

### 3. `create_fit_card`
- **Signature:** `create_fit_card(outfit: str, new_item: dict) -> str`
- **Inputs:**
  - `outfit` (`str`): the outfit suggestion string from `suggest_outfit()`.
  - `new_item` (`dict`): the listing dict for the found item.
- **Returns:** `str` — a casual 2–4 sentence Instagram/TikTok-style caption that mentions the item name, price, and platform once each. Returns a descriptive error string (not an exception) if `outfit` is empty/whitespace.
- **Purpose:** Produce a shareable caption for the look. Calls Groq `llama-3.3-70b-versatile` (temperature 0.9) so output varies between runs.

*(Internal helper, not a tool: `_search_with_fallback(parsed: dict) -> tuple[list[dict], str | None]` in `agent.py` implements the retry logic described below.)*

---

## How the Planning Loop Works

The loop lives in `run_agent(query: str, wardrobe: dict) -> dict` (`agent.py`). It does **not** call all three tools unconditionally — each step branches on what the previous tool returned.

0. **Parse** — `_parse_user_query()` sends the raw query to the LLM (temperature 0.0, few-shot) and extracts `description`, `size`, and `max_price` into `session["parsed"]`. If the LLM fails or returns invalid JSON, it falls back to using the raw query as `description` with `size`/`max_price` set to `None`.

1. **Search with fallback** — `_search_with_fallback(parsed)` calls `search_listings`:
   - **Tier 1:** full query (`description` + `size` + `max_price`). If results → use them.
   - **Tier 2:** if empty *and a `max_price` was set* → retry without the price ceiling. Price is relaxed first because it's a soft preference.
   - **Tier 3:** if still empty *and a `size` was set* → retry without size or price. Size is relaxed last because a wrong-size item won't physically fit.
   - **Give up:** if every set filter has been removed and there are still no results (or there were no filters to loosen), set `session["error"]` and **return early — tools 2 and 3 are not called.**
   - When a retry succeeds, a note (e.g. *"No matches under $30 in size M — showing items at all prices."*) is stored in `session["search_note"]` and surfaced to the user.

2. **Select** — store `search_results[0]` as `session["selected_item"]`.

3. **Suggest outfit** — call `suggest_outfit(selected_item, wardrobe)`. The tool itself branches on whether the wardrobe has items (specific outfit vs. general advice). Result → `session["outfit_suggestion"]`.

4. **Fit card** — call `create_fit_card(outfit_suggestion, selected_item)` → `session["fit_card"]`.

5. **Return** the session dict.

The key branch points: *did the search find anything (after loosening)?* decides whether the loop continues or stops, and *does the wardrobe have items?* decides what kind of outfit advice is produced.

---

## State Management

All state for one interaction lives in a single **session dict** created by `_new_session()` at the start of every query. It is the single source of truth — tools never pass data to each other directly; each writes to its own field and reads from earlier ones.

| Field | Set by | Read by | Initial |
|-------|--------|---------|---------|
| `query` | `_new_session()` | parser | raw input |
| `parsed` | parser | `search_listings` | `{}` |
| `search_results` | search step | item selection | `[]` |
| `selected_item` | selection (`results[0]`) | `suggest_outfit`, `create_fit_card` | `None` |
| `wardrobe` | `_new_session()` | `suggest_outfit` | passed from UI |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` | `None` |
| `fit_card` | `create_fit_card` | final output | `None` |
| `search_note` | search retry | `handle_query()` (UI) | `None` |
| `error` | any failing step | `handle_query()` (UI) | `None` |

Because the found item is stored in `session["selected_item"]`, it flows into `suggest_outfit` and then `create_fit_card` automatically — the user never re-enters it. `app.py`'s `handle_query()` reads the finished session and maps `selected_item`, `outfit_suggestion`, and `fit_card` to the three UI panels (prepending `search_note` if present), or shows `error` alone if the run stopped early.

---

## Error Handling Strategy

Every tool owns its failure mode and returns a usable value instead of crashing.

| Tool | Failure mode | Response |
|------|-------------|----------|
| `search_listings` | No results match | Returns `[]` (no exception). The planning loop then **retries with loosened filters** (price, then size). Only if everything is loosened and still empty does it set `session["error"]` and stop. |
| `suggest_outfit` | Empty wardrobe | Not treated as an error — switches to a general-styling-advice prompt and returns useful text. |
| `suggest_outfit` | Groq API error | Caught internally; returns `"Couldn't generate outfit suggestions right now. Please try again later."` |
| `create_fit_card` | Empty/whitespace outfit | Returns `"Couldn't generate a fit card — no outfit suggestion was provided."` (no exception). |
| `create_fit_card` | Groq API error | Caught internally; returns `"Couldn't generate a fit card right now. Please try again later."` |

**Concrete example from testing.** Running the query `"vintage graphic tee under $1"` (an impossible price) — Tier 1 returns `[]`, so the loop dropped the price ceiling and re-ran the search. It returned the *Y2K Baby Tee — Butterfly Print*, set `session["search_note"]` to *"No matches under $1 — showing items at all prices."*, and still produced a full outfit and fit card. By contrast, `"designer ballgown size XXS under $5"` exhausted every tier, so `session["error"]` was set to *"No listings matched even after removing your size and price filters. Try different keywords."* and `outfit_suggestion`/`fit_card` stayed `None` — the agent did not call the downstream tools with empty input.

---

## Spec Reflection

**One way the spec helped.** Writing each tool's exact signature and the planning loop's *conditional* logic in `planning.md` before coding meant implementation was mostly wiring — the session-dict fields, the empty-result branch, and the tool interfaces all matched what was already written, so there was very little back-and-forth.

**One way implementation diverged.** The original spec/diagram had `search_listings` give up immediately on an empty result. During implementation I diverged by adding the **retry-with-fallback** loop (a stretch feature): the planning loop now re-calls the search tool with progressively looser constraints before stopping. The reason was UX — an exact-match-or-nothing search felt brittle, and having the loop *react* to an empty result (rather than terminate) is also a stronger demonstration of an actual planning loop. `planning.md` and the architecture diagram were updated to match.

---

## AI Usage

**1. Implementing the tools from the spec.** I gave Claude Code each tool's block from `planning.md` (inputs, return value, failure mode) and asked it to implement the function in `tools.py` using `load_listings()` and the Groq client. I reviewed each result against the spec before running it — e.g. I confirmed `search_listings` filtered on all three parameters and returned `[]` (rather than raising) on no match, and that `create_fit_card` guarded against an empty `outfit` string. I kept the case-insensitive size matching (`_size_matches`) but verified the keyword-scoring logic myself against a few queries.

**2. Designing and building the retry-with-fallback stretch feature.** I described the goal to Claude Code and had it propose a loosening strategy. Its first suggestion dropped the *size* filter first; I overrode that, because size is a physical constraint and price is a soft preference — so the final logic relaxes **price first, then size**, and only relaxes filters that were actually set. I also had it keep all retry logic inside the planning loop (`_search_with_fallback` in `agent.py`) rather than modifying `search_listings`, so the tool stayed a clean, single-responsibility function. I then verified the branches with `tests/test_agent.py` and live runs before committing.
