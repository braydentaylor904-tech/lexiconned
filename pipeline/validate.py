"""Check a generated batch against FAKES.md. Usage: python validate.py 000 [001 ...]  (or "all")."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def check(n):
    src = json.loads((ROOT / "data" / "batches" / f"in_{n}.json").read_text())
    out = json.loads((ROOT / "pipeline" / "generated" / f"out_{n}.json").read_text())
    errs = []
    # A batch may stop early (the build stops at the first unwritten word), but it must follow input order.
    if [r["w"] for r in src[:len(out)]] != [r["w"] for r in out]:
        return [f"batch {n}: words/order differ from input"]
    for s, o in zip(src, out):
        w = s["w"]
        if not o.get("ok", True):
            continue
        f = o.get("f", [])
        if len(f) != 3 or len({norm(x) for x in f}) != 3:
            errs.append(f"{w}: need 3 distinct fakes")
            continue
        real_len = len(s["d"].split())
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
            if norm(x) == norm(s["d"]):
                errs.append(f"{w}: fake equals the real definition")
        r = o.get("r", "")
        if not 8 <= len(r) <= 130:
            errs.append(f"{w}: roots length {len(r)}")
        sent = o.get("s", "")
        if w[:4].lower() not in sent.lower():
            errs.append(f"{w}: sentence lacks the word")
        if norm(sent) not in norm(s["s"].replace("/", ",")):
            errs.append(f"{w}: sentence is not an excerpt of the source")
        if not 25 <= len(sent) <= 200:
            errs.append(f"{w}: sentence length {len(sent)}")
    return errs


if __name__ == "__main__":
    names = sys.argv[1:]
    if names == ["all"]:
        names = sorted(p.stem[4:] for p in (ROOT / "pipeline" / "generated").glob("out_*.json"))
    bad = 0
    for n in names:
        e = check(n)
        bad += len(e)
        print(f"batch {n}: {'OK' if not e else str(len(e)) + ' problems'}")
        for x in e:
            print("   ", x)
    sys.exit(1 if bad else 0)
