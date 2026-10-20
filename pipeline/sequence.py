"""Step 5: lay out the frozen word sequence and cut generation batches.

The sequence is the 64 hand-written entries, then the hand-reviewed WordNet words in shuffled-pool order.
Day N uses sequence entries 3N..3N+2. Once a month file has been published, never reorder or remove
anything before its last entry; new words only ever go on the end.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = 40

KEEP_LABEL = re.compile(r"^\((of |used |usually |especially |often )", re.I)


def clean_gloss(g):
    parts = [p.strip() for p in g.split(";")]
    parts = [p for p in parts if p and not p.startswith("-")]
    g = "; ".join(parts)
    g = re.sub(r"\s+-+\s*[A-Z][\w.' ]*$", "", g)          # trailing "- Author"
    g = g.replace("`", "‘").replace("'", "’")
    while g.startswith("(") and not KEEP_LABEL.match(g) and ")" in g:
        g = g[g.index(")") + 1:].strip()
    g = g.rstrip(":;, ").strip()
    return g[0].upper() + g[1:]


ETY_START = re.compile(r"\b(From|Borrowed|Learned|Via|Coined|Originally|Probably|Possibly|Perhaps|Back-formation|Blend|"
                       r"Clipping|Named|Of uncertain|Ultimately|Calque|Shortening|Variant|Alteration|Imitative|Onomatopoeic|"
                       r"Unadapted|Partly|Apparently|The (?:noun|verb|adjective) is)\b")


def clean_ety(e):
    if e.startswith(("Etymology tree", "PIE word")):
        m = ETY_START.search(e, 15)
        e = e[m.start():] if m else ""
    return e


def sequence():
    hand = json.loads((ROOT / "pipeline" / "hand_entries.json").read_text())
    pool = json.loads((ROOT / "data" / "pool.json").read_text())
    keep = set(json.loads((ROOT / "pipeline" / "curation.json").read_text())["keep"])
    wn = [dict(r, d=clean_gloss(r["d"])) for r in pool if r["w"] in keep]
    return hand, wn


def main(days):
    # Batches cover every kept word in fixed positions, so writing more batches never shifts earlier ones.
    # Rejected words (ok: false) are skipped at build time and later words move up to fill the days.
    hand, wn = sequence()
    need = days * 3 - len(hand)
    todo = wn
    out = ROOT / "data" / "batches"
    out.mkdir(parents=True, exist_ok=True)
    for b in range(0, len(todo), BATCH):
        rows = [{"w": r["w"], "pos": r["pos"], "d": r["d"], "ety": clean_ety(r["ety"])[:400], "s": r["s"]}
                for r in todo[b:b + BATCH]]
        (out / f"in_{b // BATCH:03d}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(f"{len(todo)} kept words -> {-(-len(todo) // BATCH)} batches; {days} days need {need} accepted")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 365)
