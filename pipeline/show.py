"""Print a batch compactly for writing: python show.py 000"""
import json, sys
for i, r in enumerate(json.load(open(f"../data/batches/in_{sys.argv[1]}.json"))):
    print(f"## {r['w']} ({r['pos']}) — {r['d']}\n   E: {r['ety'][:260]}\n   S: {r['s']}")
