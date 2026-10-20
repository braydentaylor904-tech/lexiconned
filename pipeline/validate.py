"""Check a generated batch against FAKES.md.

Usage: python validate.py 000 [001 ...]   year-one WordNet batches (in_NNN / out_NNN)
       python validate.py wk_000 ...       Wiktionary batches (wk_in_NNN / wk_out_NNN)
       python validate.py all
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESPELL = re.compile(r"^[A-Za-z']+(-[A-Za-z']+)*$")


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def check_entry(s, o):
    """Problems with one generated entry `o` for input row `s`. Wiktionary rows carry "senses"."""
    w = s["w"]
    if o.get("w") != w:
        return [f"{w}: output is for {o.get('w')!r}"]
    if not o.get("ok", True):
        return []
    errs = []
    wk = "senses" in s
    real = s["d"] if not wk else o.get("d", "")
    if wk:
        if not real or not any(norm(real) in norm(g) for g in s["senses"]):
            errs.append(f"{w}: definition is not an excerpt of a Wiktionary sense: {real!r}")
        if len(real.split()) < 2:
            errs.append(f"{w}: definition too short: {real!r}")
        if s["pos"] == "verb" and re.match(r"(?i)^to ", real):
            errs.append(f"{w}: verb definition starts with 'to'")
        if real.endswith("."):
            errs.append(f"{w}: definition ends with a period")
        p = o.get("p", "")
        if s.get("p") and p:
            errs.append(f"{w}: respelling given although the input has one")
        if not s.get("p") and not (p and RESPELL.match(p)):
            errs.append(f"{w}: needs a respelling like neh-KRAH-puh-lus, got {p!r}")
    f = o.get("f", [])
    if len(f) != 3 or len({norm(x) for x in f}) != 3:
        return errs + [f"{w}: need 3 distinct fakes"]
    real_len = len(real.split())
    stem = w[: max(4, len(w) - 3)].lower()
    for x in f:
        n_words = len(x.split())
        lo, hi = max(2, round(real_len * 0.6)), round(real_len * 1.45) + 1
        if not lo <= n_words <= hi:
            errs.append(f"{w}: fake length {n_words} vs real {real_len}: {x!r}")
        if stem in x.lower():
            errs.append(f"{w}: fake contains the word: {x!r}")
        if x.endswith(".") and not x.endswith("etc."):
            errs.append(f"{w}: fake ends with a period: {x!r}")
        if s["pos"] == "verb" and re.match(r"(?i)^to ", x):
            errs.append(f"{w}: verb fake starts with 'to': {x!r}")
        if norm(x) == norm(real):
            errs.append(f"{w}: fake equals the real definition")
    r = o.get("r", "")
    if not 8 <= len(r) <= 130:
        errs.append(f"{w}: roots length {len(r)}")
    sent = o.get("s", "")
    if w[:4].lower() not in sent.lower():
        errs.append(f"{w}: sentence lacks the word")
    sources = s["examples"] if wk else [s["s"]]
    if sources and not any(norm(sent) in norm(x.replace("/", ",")) for x in sources):
        if not wk:
            errs.append(f"{w}: sentence is not an excerpt of the source")
        elif not o.get("s_new"):
            errs.append(f"{w}: sentence is not an excerpt of an example (set s_new if it is original)")
    if not 25 <= len(sent) <= 200:
        errs.append(f"{w}: sentence length {len(sent)}")
    return errs


def paths(n):
    if n.startswith("wk_"):
        return ROOT / "data" / "batches" / f"wk_in_{n[3:]}.json", ROOT / "pipeline" / "generated" / f"wk_out_{n[3:]}.json"
    return ROOT / "data" / "batches" / f"in_{n}.json", ROOT / "pipeline" / "generated" / f"out_{n}.json"


def check(n):
    src_path, out_path = paths(n)
    src = json.loads(src_path.read_text())
    out = json.loads(out_path.read_text())
    # A batch may stop early (the build stops at the first unwritten word), but it must follow input order.
    if [r["w"] for r in src[:len(out)]] != [r["w"] for r in out]:
        return [f"batch {n}: words/order differ from input"]
    return [e for s, o in zip(src, out) for e in check_entry(s, o)]


if __name__ == "__main__":
    names = sys.argv[1:]
    if names == ["all"]:
        gen = ROOT / "pipeline" / "generated"
        names = sorted(p.stem[4:] for p in gen.glob("out_*.json")) + sorted("wk_" + p.stem[7:] for p in gen.glob("wk_out_*.json"))
    bad = 0
    for n in names:
        e = check(n)
        bad += len(e)
        print(f"batch {n}: {'OK' if not e else str(len(e)) + ' problems'}")
        for x in e:
            print("   ", x)
    sys.exit(1 if bad else 0)
