#!/usr/bin/env python3
"""pick_local.py — random local source picker. LLM must not roll its own.
Uses secrets.SystemRandom (OS entropy). Optional --seed for repro.

Sources layout (in sources/):
  - tinystories_jap.dedup.jsonl[.gz] — one story per line {"text": "..."}
    -> return WHOLE story.
  - aozorabunko-text-modern.jsonl[.gz] OR chunk-*.jsonl.gz — long texts
    -> return 3-5 sentence snippet from random window.

Usage:
  python tools/pick_local.py pick [--kind tiny|aozora|any] [--seed N] [--sources sources]
  python tools/pick_local.py list [--sources sources]
"""
import argparse, gzip, json, os, re, secrets, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def rng_for(seed):
    if seed is not None:
        import random
        return random.Random(seed)
    return secrets.SystemRandom()

def resolve_sources(sources_dir):
    """Return {'tiny': [paths], 'aozora': [paths]} preferring raw .jsonl if present, else .gz."""
    tiny_raw = os.path.join(sources_dir, "tinystories_jap.dedup.jsonl")
    tiny_gz = tiny_raw + ".gz"
    tiny = []
    if os.path.exists(tiny_raw):
        tiny = [tiny_raw]
    elif os.path.exists(tiny_gz):
        tiny = [tiny_gz]

    # aozora: single file or 5 chunks
    aozora = []
    single_raw = os.path.join(sources_dir, "aozorabunko-text-modern.jsonl")
    single_gz = single_raw + ".gz"
    chunks = sorted(
        os.path.join(sources_dir, f)
        for f in os.listdir(sources_dir)
        if re.fullmatch(r"aozorabunko-text-modern\.chunk-\d+\.jsonl(\.gz)?", f)
    ) if os.path.isdir(sources_dir) else []
    # prefer chunks if present (what's pushed), else single raw/gz
    if chunks:
        # prefer gzipped chunks if both exist? keep whatever exists, prefer .gz to match remote
        aozora = chunks
    elif os.path.exists(single_raw):
        aozora = [single_raw]
    elif os.path.exists(single_gz):
        aozora = [single_gz]
    return {"tiny": tiny, "aozora": aozora}

def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8")

def count_lines(path):
    n = 0
    with open_text(path) as f:
        for _ in f:
            n += 1
    return n

def read_line(path, idx):
    with open_text(path) as f:
        for i, line in enumerate(f):
            if i == idx:
                return line
    raise IndexError(f"line {idx} out of range in {path}")

def parse_text(line):
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return line.strip()
    if isinstance(obj, dict) and isinstance(obj.get("text"), str):
        return obj["text"]
    return line.strip()

def split_sentences_ja(text):
    # Normalize newlines, split on Japanese sentence enders + newlines, keep ender.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # split while keeping delimiters
    parts = re.split(r"(?<=[。！？…」』])\s*|\n+", text)
    sents = [p.strip(" \t\n　") for p in parts]
    return [s for s in sents if s]

def pick_snippet(text, rng, min_sents=3, max_sents=5, min_chars=150, max_chars=600):
    sents = split_sentences_ja(text)
    if len(sents) <= max_sents:
        return text.strip(), {"sentences": len(sents), "window": [0, len(sents)]}
    # try random windows until length fits, else fall back to first fitting window
    for _ in range(20):
        n = rng.randint(min_sents, max_sents)
        start = rng.randint(0, len(sents) - n)
        cand = "".join(sents[start:start + n])
        if min_chars <= len(cand) <= max_chars:
            return cand, {"sentences": n, "window": [start, start + n]}
    # fallback: first window with min_sents, trimmed to max_chars
    n = min_sents
    start = rng.randint(0, len(sents) - n)
    cand = "".join(sents[start:start + n])
    if len(cand) > max_chars:
        cand = cand[:max_chars]
    return cand, {"sentences": n, "window": [start, start + n], "fallback_trim": True}

def last_local_sources(n=10):
    """Read recent file:line ids from memory/global.md + lesson notes."""
    ids = []
    g = os.path.join(ROOT, "memory", "global.md")
    try:
        txt = open(g, encoding="utf-8").read()
        ids += re.findall(r"sources/[^\s,\)\]]+", txt)
    except FileNotFoundError:
        pass
    mem = os.path.join(ROOT, "memory")
    if os.path.isdir(mem):
        files = sorted(f for f in os.listdir(mem) if f.startswith("lesson-"))
        for fn in files[-3:]:
            try:
                ids += re.findall(r"sources/[^\s,\)\]]+", open(os.path.join(mem, fn), encoding="utf-8").read())
            except Exception:
                pass
    return ids[-n:] if n else []

def pick(kind, rng, sources_dir, avoid_n=10):
    groups = resolve_sources(sources_dir)
    if not groups["tiny"] and not groups["aozora"]:
        raise SystemExit(f"no local sources in {sources_dir} (expected *.jsonl or *.jsonl.gz)")
    if kind == "any":
        # dataset-level 50/50 if both exist, else whatever exists
        avail = [k for k in ("tiny", "aozora") if groups[k]]
        kind = rng.choice(avail) if len(avail) == 1 else ("tiny" if rng.random() < 0.5 else "aozora")
    files = groups.get(kind, [])
    if not files:
        raise SystemExit(f"no files for kind={kind} in {sources_dir}")
    avoid = set(last_local_sources(avoid_n))
    # try up to 10 draws to avoid exact file:line repeats
    for _ in range(10):
        # uniform file pick (chunks have ~equal lines via split -n l/5)
        path = rng.choice(files)
        total = count_lines(path)
        if total == 0:
            continue
        idx = rng.randrange(total)
        rel = os.path.relpath(path, ROOT)
        fid = f"{rel}:{idx}"
        if fid in avoid:
            continue
        line = read_line(path, idx)
        full = parse_text(line)
        if not full:
            continue
        if kind == "tiny":
            return {
                "kind": "tiny",
                "file": rel,
                "line_index": idx,
                "line_count": total,
                "source_id": fid,
                "text": full,
                "snippet": full,
                "note": "tiny: whole story",
            }
        else:
            snippet, meta = pick_snippet(full, rng)
            return {
                "kind": "aozora",
                "file": rel,
                "line_index": idx,
                "line_count": total,
                "source_id": fid,
                "text": full,
                "snippet": snippet,
                "snippet_meta": meta,
                "note": "aozora: 3-5 sentence snippet",
            }
    raise SystemExit("could not pick non-avoided line after 10 tries")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick")
    p.add_argument("--kind", choices=["tiny", "aozora", "any"], default="any")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--sources", default=os.path.join(ROOT, "sources"))
    p.add_argument("--avoid-n", type=int, default=10)
    l = sub.add_parser("list")
    l.add_argument("--sources", default=os.path.join(ROOT, "sources"))
    args = ap.parse_args()
    if args.cmd == "list":
        groups = resolve_sources(args.sources)
        out = {}
        for k, files in groups.items():
            out[k] = [{"file": os.path.relpath(f, ROOT), "lines": count_lines(f)} for f in files]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    rng = rng_for(args.seed)
    res = pick(args.kind, rng, args.sources, args.avoid_n)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
