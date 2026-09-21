"""reading.py — furigana + romaji base pass.
Tries fugashi (mecab) if installed; else naive fallback flagged [?].
Agent (LLM) fixes Kansai/slang and confirms. Output JSON for template fill.
Usage: python tools/reading.py --text "私は香川が好きです" [--json]
"""
import argparse, json, re

def naive_tokens(text):
    # split into rough words/chars, all low-confidence
    parts = re.findall(r'[一-龯々〆ヵヶ]+|[ぁ-んァ-ンーa-zA-Z0-9]+|[。、！？「」『』…―]', text)
    return [{"w": p, "yomi": "", "low_conf": True} for p in parts if p.strip()]

def with_fugashi(text):
    try:
        from fugashi import Tagger
        tagger = Tagger()
        out = []
        for w in tagger(text):
            surf = w.surface
            reading = ""
            try:
                reading = w.feature.kana or ""
            except Exception:
                reading = ""
            # kana->hira rough
            hira = "".join(chr(ord(c)-0x60) if "ァ" <= c <= "ヶ" else c for c in reading) if reading else ""
            is_kanji = bool(re.search(r'[一-龯]', surf))
            out.append({"w": surf, "yomi": hira if is_kanji else "", "low_conf": False})
        return out
    except Exception as e:
        toks = naive_tokens(text)
        for t in toks: t["error"] = str(e)[:120]
        return toks

def to_romaji_stub(tokens):
    # stub: agent fills real romaji; tool leaves placeholder = w
    return [{"w": t["w"], "r": t["w"], "low_conf": t.get("low_conf", True)} for t in tokens]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    args = ap.parse_args()
    toks = with_fugashi(args.text)
    roma = to_romaji_stub(toks)
    print(json.dumps({"tokens": toks, "romaji": roma}, ensure_ascii=False, indent=2))
