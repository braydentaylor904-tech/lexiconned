"""Step 2: pull etymology, IPA and example sentences from the Wiktionary (kaikki.org) English extract
for every WordNet candidate. Reads the .jsonl.gz as a stream, never unpacked to disk.

Writes data/wikt.json: {word: [{pos, ety, ipa: [...], senses: [{gloss, examples: [{text, type}]}]}]}
"""
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "kaikki" / "english.jsonl.gz"
WORD_RE = re.compile(r'"word": "([^"]+)"')


def main():
    wanted = {r["w"] for r in json.loads((ROOT / "data" / "candidates.json").read_text())}
    wanted |= set(json.loads((ROOT / "pipeline" / "hand_words.json").read_text()))
    out = {}
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            m = WORD_RE.search(line)
            if not m or m.group(1) not in wanted:
                continue
            e = json.loads(line)
            if e.get("lang_code") != "en" or e.get("word") not in wanted:
                continue
            ipa = []
            for s in e.get("sounds", []):
                if "ipa" in s:
                    ipa.append({"ipa": s["ipa"], "tags": s.get("tags", [])})
            senses = []
            for s in e.get("senses", []):
                if "glosses" not in s:
                    continue
                senses.append({
                    "gloss": s["glosses"][-1],
                    "tags": s.get("tags", []),
                    "examples": [{"text": x.get("text", ""), "type": x.get("type", ""), "ref": bool(x.get("ref"))}
                                 for x in s.get("examples", []) if x.get("text")],
                })
            out.setdefault(e["word"], []).append({
                "pos": e.get("pos"),
                "ety": e.get("etymology_text", ""),
                "ipa": ipa,
                "senses": senses,
            })
    (ROOT / "data" / "wikt.json").write_text(json.dumps(out, ensure_ascii=False))
    print(len(out), "of", len(wanted), "words found in Wiktionary")


if __name__ == "__main__":
    main()
