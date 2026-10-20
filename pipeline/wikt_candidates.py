"""Years 2-10, step 1: pull candidate words straight from the Wiktionary (kaikki.org) English extract.

Year one came from WordNet; WordNet runs out after ~1,400 good words, so later years take their real
definitions from Wiktionary glosses instead. Every WordNet candidate (kept or rejected) is excluded, so
nothing from year one comes back and nothing rejected there is retried.

Writes data/wk_pool.json: the shuffled walk. Like data/pool.json it is frozen once generation starts;
new words only ever go on the end. Claude makes the final keep/reject call per word during generation.
"""
import gzip
import json
import random
import re
from pathlib import Path

from wordfreq import zipf_frequency

from assemble import ETY_USELESS, TECH_SUFFIX, clean, is_compound, pick_ipa
from respell import respell

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "kaikki" / "english.jsonl.gz"
SEED = 20261020

POS = {"adj": "adjective", "noun": "noun", "verb": "verb", "adv": "adverb"}
WORD = re.compile(r"^[a-z]{5,16}$")
SKIP_TAGS = {"obsolete", "archaic", "rare", "slang", "vulgar", "offensive", "derogatory", "ethnic", "slur",
             "form-of", "alt-of", "misspelling", "nonstandard", "abbreviation", "initialism", "acronym",
             "plural", "plural-only", "participle", "past", "comparative", "superlative", "dialectal",
             "proscribed", "pejorative", "euphemistic", "internet", "nonce-word"}
SKIP_TOPICS = {"medicine", "pathology", "chemistry", "biology", "anatomy", "physics", "mathematics", "computing",
               "geology", "botany", "zoology", "genetics", "biochemistry", "pharmacology", "electronics",
               "statistics", "physiology", "law", "finance", "economics", "engineering", "astronomy",
               "mineralogy", "linguistics", "grammar", "phonetics", "logic", "military", "nautical", "sports",
               "religion", "sexuality", "lgbt", "taxonomy", "organic-chemistry", "biochemistry", "medical"}
TECH_GLOSS = re.compile(r"\b(genus|species|family [A-Z]|taxonomic|chemical|compound|acid|enzyme|protein|cell|"
                        r"tissue|disease|syndrome|molecule|mineral|alloy|isotope|surname|given name|placename|"
                        r"place name|city|town|river|county|country|demonym|language|trademark|brand)\b")
# Glosses that only point at a related word ("Relating to insurrection.") make for a trivial puzzle.
DERIVED_GLOSS = re.compile(r"^(of,? (or )?(pertaining|relating) to|(pertaining|relating) to|that \w+s?\.?$|the (state|quality|"
                           r"condition|act|fact) of being \w+\.?$|one who \w+s\.?$|in an? \w+ (manner|way)\.?$|any of (the|various))", re.I)
BAD_EXAMPLE = re.compile(r"[ſ\[\]{}<>|=_*#]|vv|\bthee\b|\bthou\b|\bhath\b|\bdoth\b")
MAX_SENSES = 5


def usable_senses(e):
    out = []
    for s in e.get("senses", []):
        g = (s.get("glosses") or [""])[-1]
        tags = set(s.get("tags", []))
        topics = set(s.get("topics", []))
        if not g or tags & SKIP_TAGS or topics & SKIP_TOPICS or "form_of" in s or "alt_of" in s:
            continue
        if TECH_GLOSS.search(g) or DERIVED_GLOSS.search(g) or len(g) < 12 or len(g) > 220:
            continue
        ex = [clean(x["text"]) for x in s.get("examples", []) if x.get("text")]
        out.append({"gloss": clean(g), "examples": ex})
    return out


def good_example(word, t):
    stem = word[: max(4, len(word) - 2)]
    return 30 <= len(t) <= 220 and stem in t.lower() and not BAD_EXAMPLE.search(t) and t[0].isupper() \
        and t.count('"') % 2 == 0


def main():
    exclude = {r["w"] for r in json.loads((ROOT / "data" / "candidates.json").read_text())}
    exclude |= set(json.loads((ROOT / "pipeline" / "hand_words.json").read_text()))
    exclude |= {r["w"] for r in json.loads((ROOT / "data" / "pool.json").read_text())}
    words = {}
    stats = {}

    def drop(reason):
        stats[reason] = stats.get(reason, 0) + 1

    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            if '"lang_code": "en"' not in line:
                continue
            e = json.loads(line)
            w, pos = e.get("word", ""), POS.get(e.get("pos"))
            if not pos or not WORD.match(w) or w in exclude or w in words:
                continue
            z = zipf_frequency(w, "en")
            if not 1.0 <= z <= 3.0:
                continue
            if w.endswith(TECH_SUFFIX) and pos == "noun":
                drop("technical suffix"); continue
            if (w.endswith(("ing", "ed")) and pos != "adjective") or (pos == "adverb" and w.endswith("ly")) \
                    or w.endswith("ness"):
                drop("inflected or derived form"); continue
            senses = usable_senses(e)
            if not senses or len(senses) > MAX_SENSES:
                drop("no usable sense" if not senses else "too many senses"); continue
            ety = clean(e.get("etymology_text", ""))
            if len(ety) < 15 or ETY_USELESS.search(ety):
                drop("no usable etymology"); continue
            ipa = pick_ipa([{"ipa": [{"ipa": s["ipa"], "tags": s.get("tags", [])}
                                     for s in e.get("sounds", []) if "ipa" in s]}])
            examples = [t for s in senses for t in s["examples"] if good_example(w, t)][:3]
            if is_compound(w):
                drop("compound"); continue
            words[w] = {"w": w, "pos": pos, "senses": [s["gloss"] for s in senses], "ety": ety[:2500],
                        "ipa": ipa, "p": respell(ipa) if ipa else None, "examples": examples, "zipf": round(z, 2)}

    # Fully sourced words (Wiktionary pronunciation and example sentence) come first; words missing either
    # follow, and Claude supplies the respelling or writes the sentence for those.
    full = sorted((r for r in words.values() if r["p"] and r["examples"]), key=lambda r: r["w"])
    part = sorted((r for r in words.values() if not (r["p"] and r["examples"])), key=lambda r: r["w"])
    random.Random(SEED).shuffle(full)
    random.Random(SEED + 1).shuffle(part)
    pool = full + part
    (ROOT / "data" / "wk_pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=0))
    print(len(pool), f"Wiktionary candidates ({len(full)} fully sourced, {len(part)} missing a pronunciation or sentence)")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  dropped {v:>6}  {k}")


if __name__ == "__main__":
    main()
