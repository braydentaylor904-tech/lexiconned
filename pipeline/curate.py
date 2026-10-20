"""Record one batch of hand-review decisions: python curate.py START END i1,i2,... (pool indices kept)."""
import json, sys
p = json.load(open("../data/pool.json")); cur = json.load(open("curation.json"))
start, end = int(sys.argv[1]), int(sys.argv[2])
kept = {p[int(i)]["w"] for i in sys.argv[3].split(",") if i}
assert all(start <= int(i) < end for i in sys.argv[3].split(",") if i)
cur["reviewed"] = sorted(set(cur["reviewed"]) | {r["w"] for r in p[start:end]})
cur["keep"] = sorted(set(cur["keep"]) | kept)
json.dump(cur, open("curation.json", "w"), indent=0)
print(f"+{len(kept)} kept of {end-start}; total kept {len(cur['keep'])} of {len(cur['reviewed'])} reviewed")
