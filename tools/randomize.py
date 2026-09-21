#!/usr/bin/env python3
"""randomize.py — single source of randomness. LLM must not roll its own.
Uses secrets.SystemRandom (OS entropy). Optional --seed for repro.

Usage:
  pick source (weighted 60/20/20, avoid last-10):
    python tools/randomize.py pick-source [--seed 123] [--sources sources.json]
  shuffle MCQ options (returns new order + index map):
    python tools/randomize.py shuffle --options '["A","B","C","D"]' [--seed 123] [--correct 0]
  roll hat only:
    python tools/randomize.py hat [--seed 123]
"""
import argparse, json, os, re, secrets, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = [("tokyo_life", 60), ("kansai_forum", 20), ("fun", 20)]

def rng_for(seed):
    if seed is not None:
        import random
        return random.Random(seed)
    return secrets.SystemRandom()

def load_sources(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def last_sources(n=10):
    """Read last-N source urls from memory/global.md + lesson notes."""
    urls = []
    g = os.path.join(ROOT, "memory", "global.md")
    try:
        txt = open(g, encoding="utf-8").read()
        urls += re.findall(r"https?://\S+", txt)
    except FileNotFoundError:
        pass
    mem = os.path.join(ROOT, "memory")
    if os.path.isdir(mem):
        files = sorted(f for f in os.listdir(mem) if f.startswith("lesson-"))
        for fn in files[-3:]:
            try:
                urls += re.findall(r"https?://\S+", open(os.path.join(mem, fn), encoding="utf-8").read())
            except Exception:
                pass
    # most-recent last
    return urls[-n:] if n else []

def weighted_hat(rng):
    total = sum(w for _, w in WEIGHTS)
    r = rng.uniform(0, total)
    acc = 0
    for hat, w in WEIGHTS:
        acc += w
        if r < acc:
            return hat
    return WEIGHTS[0][0]

def pick_source(sources, rng, avoid):
    avoidset = set(avoid)
    # try hats in random order fallback if hat pool exhausted
    hats = [weighted_hat(rng)] + [h for h, _ in WEIGHTS]
    seen = set()
    for hat in hats:
        if hat in seen:
            continue
        seen.add(hat)
        pool = [e for e in sources.get(hat, []) if e.get("url") not in avoidset]
        if pool:
            return hat, rng.choice(pool)
    # all avoided: relax, pick from full pool
    hats_all = [e for h, _ in WEIGHTS for e in sources.get(h, [])]
    if not hats_all:
        raise SystemExit("sources.json empty")
    e = rng.choice(hats_all)
    return "fallback-any", e

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick-source")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--sources", default=os.path.join(ROOT, "sources.json"))
    p.add_argument("--avoid-n", type=int, default=10)
    p.add_argument("--hat", default=None, help="force hat")
    s = sub.add_parser("shuffle")
    s.add_argument("--options", required=True, help='JSON list, e.g. \'["a","b","c"]\'')
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--correct", type=int, default=None, help="original correct index")
    h = sub.add_parser("hat")
    h.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    rng = rng_for(getattr(args, "seed", None))

    if args.cmd == "hat":
        print(json.dumps({"hat": weighted_hat(rng)}, ensure_ascii=False))
    elif args.cmd == "pick-source":
        sources = load_sources(args.sources)
        avoid = last_sources(args.avoid_n)
        if args.hat:
            pool = [e for e in sources.get(args.hat, []) if e.get("url") not in set(avoid)]
            if not pool:
                pool = sources.get(args.hat, [])
            hat, entry = args.hat, rng.choice(pool)
        else:
            hat, entry = pick_source(sources, rng, avoid)
        print(json.dumps({"hat": hat, "entry": entry, "avoided": avoid}, ensure_ascii=False, indent=2))
    elif args.cmd == "shuffle":
        opts = json.loads(args.options)
        idx = list(range(len(opts)))
        rng.shuffle(idx)
        out = {"order": idx, "shuffled": [opts[i] for i in idx]}
        if args.correct is not None:
            out["new_correct"] = idx.index(args.correct)
        print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
