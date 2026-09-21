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
5. Build `lessons/lesson-YYYY-MM-DD-N.html` from `template.html`: snippet ruby + romaji dots + quiz (5 max: 3 gist + 1 vocab + 1 try-it; shuffle every MCQ via `randomize.py shuffle --correct 0`) + trivia + difficulty notes ([N3]/[N2+] tags) + dialect notes (Standard ⇄ Kansai always) + FINISH (score auto + sentence box + comments box).
6. Serve: `python tools/server.py` → give user `http://localhost:8000/lessons/lesson-....html`. Page POSTs to `/api/save` → writes `memory/lesson-...md` + patches `global.md`. Show `saved ✓`.
7. Never filter typos/slang/memes/profanity. Short quotes only + attribution. Public data only.

## Memory format
- `memory/lesson-YYYY-MM-DD-N.md`: frontmatter (date, source, url, hat, score, missed, peeks, furigana, seconds) + sentence + comments + weak+.
- `memory/global.md`: cumulative weak-top-5 / strong / N3 counts (rough, steering only) / last-10 sources.

## Template contract
- Furigana: `<ruby>漢字<rt>かんじ</rt></ruby>`, global toggle hides `rt`.
- Romaji: token spans `data-r="watashi"`, hidden as `▪` until tap; SHOW ALL/HIDE ALL.
- Quiz: each Q has [SHOW ANSWER]; try-it is free text; FINISH POSTs JSON `{lesson, score, missed[], sentence, comments, peeks[], furigana, seconds}`.
- Track: click on romaji token logs peek; toggle logs furigana state; timer logs seconds.

## Randomness (mandatory — never let the LLM roll)
- All source picks and MCQ shuffles MUST use `tools/randomize.py` (OS entropy via `secrets`). LLM guessing, "pick one", or hardcoding first entry is banned.
- Source: `python tools/randomize.py pick-source` (weighted 60/20/20, auto-avoids last-10 from `memory/`). `--seed` only for repro/debugging. `--hat` only to retry a failed fetch, never to bias.
- MCQ: build options with correct at index 0, then `python tools/randomize.py shuffle --options '<json>' --correct 0` and use returned `shuffled` + `new_correct`. Re-shuffle per lesson.
- Hat-only roll (no pick): `python tools/randomize.py hat`.
