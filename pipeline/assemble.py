"""Step 3: join WordNet candidates with Wiktionary, apply stricter filters, and freeze the shuffled order.

Writes data/pool.json: the shuffled candidate walk. Curation (step 4) walks this list in order,
so accepted words keep their relative order and new words only ever extend the end.
"""
import json
import random
import re
from pathlib import Path

from wordfreq import zipf_frequency

from respell import respell

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261019

KAIKKI_POS = {"adjective": "adj", "noun": "noun", "verb": "verb", "adverb": "adv"}
FORM_OF = re.compile(r"^(alternative|obsolete|archaic|dated|rare|nonstandard|misspelling|eye dialect|plural|"
                     r"present participle|past tense|past participle|simple past|comparative|superlative|"
                     r"third-person|abbreviation|initialism|acronym|clipping|synonym of)\b", re.I)
TECH_SUFFIX = ("osis", "itis", "ectomy", "otomy", "plegia", "emia", "aemia", "cele", "azole", "mycin", "cillin",
               "ase", "ide", "scope", "metry", "graph", "gram", "phyte", "phage", "cyte", "ogen", "oma", "algia",
               "pathy", "uria", "ene", "ane", "ol", "ium", "iasis", "plasty")
PREFIXES = ("un", "re", "semi", "inter", "over", "under", "non", "counter", "super", "out", "after", "self",
            "fore", "mis", "pre", "sub", "anti", "multi", "hyper", "mid", "post", "co", "dis", "in", "im")
ETY_USELESS = re.compile(r"^(unknown|uncertain|origin unknown|of unknown|of uncertain|see |compare )", re.I)
BAD_EXAMPLE = re.compile(r"[ſ\[\]{}<>|=_*#]|vv|\bthee\b|\bthou\b|\bhath\b|\bdoth\b|\bwhich\b.*\bwhich\b")


def is_compound(w):
    for p in PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 4 and zipf_frequency(w[len(p):], "en") >= 3.0:
            return True
    for i in range(4, len(w) - 3):
        a, b = w[:i], w[i:]
        if zipf_frequency(a, "en") >= 3.6 and zipf_frequency(b, "en") >= 3.6:
            return True
    return False


def pick_ipa(entries):
    for want in (("US",), ("General-American",), ()):
        for e in entries:
            for i in e["ipa"]:
                if (not want or set(want) & set(i["tags"])) and i["ipa"].startswith("/"):
                    return i["ipa"]
    return None


def overlap(a, b):
    ta = set(re.findall(r"[a-z]{4,}", a.lower()))
    tb = set(re.findall(r"[a-z]{4,}", b.lower()))
    return len(ta & tb) / (len(ta) or 1)


def clean(t):
    return re.sub(r"\s+", " ", t).strip()


def pick_sentence(word, wn_gloss, entries, wn_ex):
    form = re.compile(r"\b" + re.escape(word[: max(4, len(word) - 2)]) + r"\w*", re.I)
    best = None
    for e in entries:
        for s in e["senses"]:
            match = overlap(wn_gloss, s["gloss"])
            for x in s["examples"]:
                t = clean(x["text"])
                if not (30 <= len(t) <= 200) or not form.search(t) or BAD_EXAMPLE.search(t):
                    continue
                if t[0].islower() or t.count('"') % 2:
                    continue
                score = match * 2 + (1.0 if x["type"] == "example" else 0) - len(t) / 400
                if best is None or score > best[0]:
                    best = (score, t, "wiktionary")
    if best:
        return best[1], best[2]
    for t in wn_ex:
        if len(t.split()) >= 5:
            t = t[0].upper() + t[1:]
            return (t if t.endswith((".", "!", "?")) else t + "."), "wordnet"
    return None, None


def main():
    cands = json.loads((ROOT / "data" / "candidates.json").read_text())
    wikt = json.loads((ROOT / "data" / "wikt.json").read_text())
    stats = {}
    pool = []

    def drop(reason):
        stats[reason] = stats.get(reason, 0) + 1

    for c in cands:
        w = c["w"]
        if c["lex"].startswith("noun") and w.endswith(TECH_SUFFIX):
            drop("technical suffix"); continue
        if w.endswith(("ing", "ed")) and c["pos"] != "adjective":
            drop("inflected form"); continue
        if is_compound(w):
            drop("compound"); continue
        entries = [e for e in wikt.get(w, []) if e["pos"] == KAIKKI_POS[c["pos"]]]
        if not entries:
            drop("not in wiktionary for this part of speech"); continue
        glosses = [s["gloss"] for e in entries for s in e["senses"]]
        if not glosses or all(FORM_OF.search(g) for g in glosses):
            drop("only a variant spelling or inflection"); continue
        ety = next((clean(e["ety"]) for e in entries if e["ety"]), "")
        if len(ety) < 15 or ETY_USELESS.search(ety):
            drop("no usable etymology"); continue
        ipa = pick_ipa(entries)
        if not ipa:
            drop("no pronunciation"); continue
        sentence, s_src = pick_sentence(w, c["d"], entries, c["wn_ex"])
        if not sentence:
            drop("no usable sentence"); continue
        pool.append({
            "w": w, "pos": c["pos"], "d": c["d"], "ipa": ipa, "p": respell(ipa),
            "ety": ety[:2500], "s": sentence, "s_src": s_src, "zipf": c["zipf"], "lex": c["lex"],
        })

    random.Random(SEED).shuffle(pool)
    (ROOT / "data" / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=0))
    print(len(pool), "in shuffled pool")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  dropped {v:>5}  {k}")
    print("sentence sources:", {s: sum(p["s_src"] == s for p in pool) for s in ("wiktionary", "wordnet")})


if __name__ == "__main__":
    main()
