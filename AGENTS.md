# reading-real-content — Real Japanese Lesson Builder

Consumer lock: small HTML lessons (~10 min) from real public Japanese. Tokyo-heavy 60/20/20. Raw, no filter. Agent memory drives recall to N3.

## Commands
- `give me a lesson` → build + serve lesson (agent runs `python tools/server.py --new` or manual flow below).
- `reset memory` → archive `memory/` to `memory/archive-YYYYMMDD/` + fresh `global.md`.
- `show memory` → print `global.md` + last 3 lesson notes (only on request; else hidden).

## Build flow (every lesson)
1. Read `memory/global.md` + latest 2-3 `memory/lesson-*.md` (if exist). Note top weak item (max 1 resurface/lesson).
2. Roll hat with tool: `python tools/randomize.py pick-source` (weighted 60/20/20, auto-avoids last-10). Never hand-pick or LLM-pick. Record returned `hat` + `entry.url`.
3. Fetch live (NHK/Aozora/PR Times etc.). Trim to 3-5 sentences. Keep source title + URL + retrieved date.
   Fallback: other URL → other category → LLM-generated flagged `synthetic-fallback: true` (last resort).
4. Generate readings: `python tools/reading.py --text "snippet"` → furigana segments + romaji tokens. LLM fixes Kansai/slang, marks low-conf `[?]`.
5. Build `lessons/lesson-YYYY-MM-DD-N.html` from `template.html`: snippet ruby + romaji dots + quiz (4 MCQ max: 3 gist + 1 vocab, NO try-it/writing; shuffle every MCQ via `randomize.py shuffle --correct 0`; each Q has clickable options with hint/reinforcement + per-item Romaji/English toggles) + trivia (English) + difficulty notes ([N3]/[N2+] tags, English) + dialect notes (English) + FINISH (auto data + comments box only, no sentence box).
6. Serve: `python tools/server.py` → give user `http://localhost:8000/lessons/lesson-....html`. Page POSTs to `/api/save` → writes `memory/lesson-...md` + patches `global.md`. Show `saved ✓`.
7. Never filter typos/slang/memes/profanity. Short quotes only + attribution. Public data only.

## Memory format
- `memory/lesson-YYYY-MM-DD-N.md`: frontmatter (date, source, url, hat, score, missed, peeks, furigana, seconds) + comments + weak+. No sentence field (writing removed 2026-09-21).
- `memory/global.md`: cumulative weak-top-5 / strong / N3 counts (rough, steering only) / last-10 sources.

## Language + furigana rules (fixed 2026-09-21)
- Japanese WITH furigana (ruby, global ON/OFF applies to whole page): title (`{{TITLE_RUBY}}`), snippet (`{{SNIPPET_RUBY}}`), quiz questions + options (`{{QUIZ_HTML}}` — every kanji gets `<ruby>Kanji<rt>(reading)</rt></ruby>` with readings IN PARENS so boundaries are visible).
- English ONLY (no furigana, never Japanese exercise text): trivia (`{{TRIVIA}}` + `{{TRIVIA_MORE}}`), dialect notes (`{{DIALECT}}`), quiz hints/reinforcement/feedback, section UI/labels/buttons (keep English).
- Quiz interaction (no SHOW ANSWER, no try-it, NO reveal-on-wrong): each Q is a segregated card with `Qn · tap one` header. Options are radio-style buttons; wrong pick marks ONLY that option red + English hint, keeps correct hidden, allows retry; correct pick marks green + English reinforcement and locks card. Track `attempts` per Q. Each stem + option keeps [Romaji] [English] toggles.
- Difficulty notes: English explanations; Japanese terms cited with ruby.
- `tools/reading.py` must run for title, snippet, AND each quiz Japanese string before building HTML. No bare kanji in exercise zones.

## Template contract
- Title: `<h1>{{TITLE_RUBY}}</h1>` (ruby required). Keep `<title>` plain-text fallback.
- Furigana: `<ruby>漢字<rt>(かんじ)</rt></ruby>` — parens REQUIRED inside every `rt` so single-kanji boundaries read clearly, global toggle hides ALL `rt` on page (title+snippet+quiz).
- Romaji INLINE (no separate section): each snippet word is `<span class="w" data-jp data-ro><ruby>Kanji<rt>(reading)</rt></ruby><span class="ro">romaji</span></span>` — romaji under the word, hidden by default, global ROMAJI toggle + tap word to peek. Quiz Romaji/English: per-item toggles under each stem/option (hidden divs), never overlay.
- Quiz: 4 MCQ max, options are radio-style `.opt` buttons in segregated `.quiz` cards; FINISH POSTs JSON `{lesson, picked{}, attempts{}, score, comments, peeks[], furigana, seconds}` (no sentence).
- Track: tap on snippet word logs peek; toggle logs furigana/romaji state; timer logs seconds.

## Randomness (mandatory — never let the LLM roll)
- All source picks and MCQ shuffles MUST use `tools/randomize.py` (OS entropy via `secrets`). LLM guessing, "pick one", or hardcoding first entry is banned.
- Source: `python tools/randomize.py pick-source` (weighted 60/20/20, auto-avoids last-10 from `memory/`). `--seed` only for repro/debugging. `--hat` only to retry a failed fetch, never to bias.
- MCQ: build options with correct at index 0, then `python tools/randomize.py shuffle --options '<json>' --correct 0` and use returned `shuffled` + `new_correct`. Re-shuffle per lesson.
- Hat-only roll (no pick): `python tools/randomize.py hat`.
