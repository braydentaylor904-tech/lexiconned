"""Rewrite year-one fakes by hand (in a Claude Code session) instead of through the API.

    python rewrite_local.py cut          freeze every unplayed year-one entry into data/batches/rw_in_NNN.json (40 each)
    python rewrite_local.py show NNN     print a batch compactly for writing
    python rewrite_local.py check NNN    validate pipeline/generated/rw_out_NNN.json against FAKES.md
    python rewrite_local.py merge        add every valid batch (and rewrite_examples.json) to pipeline/rewrites.json

Output format, one object per input row in the same order: {"w": ..., "f": [3 fakes], "hooks": [3 hooks]}.
build.py applies rewrites.json only to days that aren't locked, so a day that locks before publishing keeps its old fakes.
"""
import json
import sys
from pathlib import Path

import batch_generate as bg
from validate import check_fakes

ROOT = Path(__file__).resolve().parent.parent
BATCHES = ROOT / "data" / "batches"
GEN = ROOT / "pipeline" / "generated"
EXAMPLES = ROOT / "pipeline" / "rewrite_examples.json"
SIZE = 40


def cut():
    if list(BATCHES.glob("rw_in_*.json")):
        sys.exit("rewrite batches already cut")
    skip = set(json.loads(EXAMPLES.read_text()))
    rows = [r for _, r in bg.rewrite_items() if r["w"] not in skip]
    for b in range(0, len(rows), SIZE):
        (BATCHES / f"rw_in_{b // SIZE:03d}.json").write_text(json.dumps(rows[b:b + SIZE], ensure_ascii=False, indent=0))
    print(f"{len(rows)} entries -> {-(-len(rows) // SIZE)} batches")


def show(n):
    for r in json.loads((BATCHES / f"rw_in_{n}.json").read_text()):
        print(f"{r['w']} | {r['pos']} | {r['d']} | R: {r['r']} | S: {r['s']}")


def check(n):
    src = json.loads((BATCHES / f"rw_in_{n}.json").read_text())
    out = json.loads((GEN / f"rw_out_{n}.json").read_text())
    if [r["w"] for r in src] != [o["w"] for o in out]:
        return ["words/order differ from input"]
    return [e for r, o in zip(src, out) for e in check_fakes(r["w"], r["pos"], r["d"], r["r"], o["f"], o["hooks"])]


def merge():
    rw = bg.load_rewrites()
    for w, v in json.loads(EXAMPLES.read_text()).items():
        rw[w] = v
    done = 0
    for p in sorted(GEN.glob("rw_out_*.json")):
        n = p.stem[7:]
        errs = check(n)
        if errs:
            print(f"batch {n} skipped: {len(errs)} problems")
            continue
        for o in json.loads(p.read_text()):
            rw[o["w"]] = {"f": o["f"], "hooks": o["hooks"]}
        done += 1
    bg.REWRITES.write_text(json.dumps(rw, ensure_ascii=False, indent=1) + "\n")
    print(f"{done} batches merged; {len(rw)} words in rewrites.json")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "cut":
        cut()
    elif cmd == "show":
        show(sys.argv[2])
    elif cmd == "check":
        e = check(sys.argv[2])
        print("OK" if not e else f"{len(e)} problems")
        for x in e:
            print("   ", x)
        sys.exit(1 if e else 0)
    elif cmd == "merge":
        merge()
