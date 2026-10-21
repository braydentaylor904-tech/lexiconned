"""Step 6: assemble the frozen sequence and write words/YYYY-MM.json plus words/manifest.json.

Day N (counted from the launch date in config.json) uses sequence entries 3N..3N+2.
The sequence is: hand-written entries, then generated WordNet entries in curation order, then generated
Wiktionary entries in wk_in_NNN order, skipping rejected ones and stopping at the first word that hasn't
been generated yet.

words/lock.json holds "locked_days": every day below it is already live and must never change.
Each build raises it automatically to cover every day that has started anywhere on Earth (players see
the day for their local date, and UTC+14 is a day ahead of UTC), and refuses to write if any locked day
would come out different.
"""
import datetime as dt
import json
from pathlib import Path

from sequence import sequence

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words"


def cap(t):
    return t[0].upper() + t[1:] if t else t


def build_sequence():
    hand, wn = sequence()
    gen = {}
    for f in sorted((ROOT / "pipeline" / "generated").glob("out_*.json")):
        for o in json.loads(f.read_text()):
            gen[o["w"]] = o
    dropped = json.loads((ROOT / "pipeline" / "curation.json").read_text()).get("dropped", {})
    seq = [dict(e) for e in hand]
    for r in wn:
        if r["w"] in dropped:
            continue
        o = gen.get(r["w"])
        if o is None:
            return seq
        if not o.get("ok", True):
            continue
        seq.append({"w": r["w"], "p": r["p"], "pos": r["pos"], "d": r["d"],
                    "f": [cap(x) for x in o["f"]], "r": cap(o["r"]), "s": o["s"]})
    for f in sorted((ROOT / "data" / "batches").glob("wk_in_*.json")):
        out = ROOT / "pipeline" / "generated" / f"wk_out_{f.stem[6:]}.json"
        done = json.loads(out.read_text()) if out.exists() else []
        for r, o in zip(json.loads(f.read_text()), done):
            if r["w"] in dropped or not o.get("ok", True):
                continue
            seq.append({"w": r["w"], "p": r["p"] or o["p"], "pos": r["pos"], "d": cap(o["d"]),
                        "f": [cap(x) for x in o["f"]], "r": cap(o["r"]), "s": o["s"]})
        if len(done) < len(json.loads(f.read_text())):
            break
    return seq


def main():
    cfg = json.loads((ROOT / "pipeline" / "config.json").read_text())
    launch = dt.date.fromisoformat(cfg["launch"])
    seq = build_sequence()
    days = len(seq) // 3
    lock_file = WORDS / "lock.json"
    stored = json.loads(lock_file.read_text())["locked_days"] if lock_file.exists() else 0
    started = (dt.datetime.now(dt.timezone.utc).date() - launch).days + 2   # through tomorrow (UTC), inclusive
    locked = max(stored, min(started, days))
    # Hint-proof fakes from `batch_generate.py --rewrite` replace the originals on every day that isn't locked.
    rw_file = ROOT / "pipeline" / "rewrites.json"
    rewrites = json.loads(rw_file.read_text()) if rw_file.exists() else {}
    applied = 0
    for n, e in enumerate(seq):
        if n >= 3 * locked and e["w"] in rewrites:
            e["f"] = [cap(x) for x in rewrites[e["w"]]["f"]]
            applied += 1
    seen = {}
    for e in seq:
        if e["d"] in seen:
            raise SystemExit(f"{e['w']} and {seen[e['d']]} share a definition; add one to curation.json \"dropped\"")
        seen[e["d"]] = e["w"]
    months = {}
    for n in range(days):
        key = (launch + dt.timedelta(days=n)).strftime("%Y-%m")
        m = months.setdefault(key, {"month": key, "first_day": n, "days": []})
        m["days"].append(seq[3 * n: 3 * n + 3])

    WORDS.mkdir(exist_ok=True)
    for key, m in months.items():
        path = WORDS / f"{key}.json"
        if path.exists() and m["first_day"] < locked:
            old = json.loads(path.read_text())
            for i, day in enumerate(old["days"]):
                n = old["first_day"] + i
                if n < locked and (i >= len(m["days"]) or m["days"][i] != day):
                    raise SystemExit(f"day {n} is locked but would change; refusing to build")
    if days < locked:
        raise SystemExit(f"only {days} days built but {locked} are locked")

    for p in WORDS.glob("20*.json"):
        if p.stem not in months:
            p.unlink()
    for key, m in months.items():
        (WORDS / f"{key}.json").write_text(json.dumps(m, ensure_ascii=False, separators=(",", ":")))
    manifest = {"launch": cfg["launch"], "days": days, "months": sorted(months)}
    (WORDS / "manifest.json").write_text(json.dumps(manifest, indent=1))
    lock_file.write_text(json.dumps({"locked_days": locked}, indent=1) + "\n")
    last = launch + dt.timedelta(days=days - 1)
    print(f"{len(seq)} entries -> {days} days ({cfg['launch']} to {last}), {len(months)} month files; "
          f"days 1-{locked} locked; {applied} rewritten fake sets applied")


if __name__ == "__main__":
    main()
