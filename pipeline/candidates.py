"""Step 1: pull obscure-but-real, non-technical, non-offensive words out of WordNet.

Writes data/candidates.json: one record per word with its primary WordNet sense.
"""
import json
import re
from pathlib import Path

import nltk
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent
nltk.data.path.insert(0, str(ROOT / "data" / "nltk_data"))
from nltk.corpus import wordnet as wn  # noqa: E402

# Lexicographer files that are mostly species, places, chemicals, body parts or taxonomy.
SKIP_LEXNAMES = {
    "noun.animal", "noun.plant", "noun.body", "noun.substance", "noun.location", "noun.Tops",
    "noun.quantity", "noun.object", "noun.time", "noun.group", "noun.food", "noun.process",
    "adj.pert", "adj.ppl",
}
# WordNet topic domains that make a word "too technical" for a general audience.
SKIP_TOPICS = {
    "medicine", "pathology", "chemistry", "biology", "anatomy", "physics", "mathematics",
    "computer_science", "geology", "botany", "zoology", "genetics", "biochemistry",
    "pharmacology", "electronics", "statistics", "physiology", "psychiatry", "surgery",
    "law", "finance", "economics", "accounting", "engineering", "electricity", "chemical_science",
    "immunology", "microbiology", "astronomy", "meteorology", "mineralogy", "petrology",
    "crystallography", "ophthalmology", "dentistry", "obstetrics", "neurology", "cardiology",
    "linguistics", "grammar", "phonetics", "logic", "telecommunication", "computing",
    "military", "nautical_science", "navigation", "sport", "baseball", "football", "cricket",
    "golf", "tennis", "basketball", "bridge", "chess",
}
SKIP_USAGE = {"vulgarism", "obscenity", "ethnic_slur", "disparagement", "trademark", "trade_name"}
TECH_WORDS = re.compile(
    r"\b(genus|genera|family|species|order|class|phylum|subfamily|chemical|compound|acid|enzyme|protein|"
    r"cell|cells|tissue|disease|inflammation|tumou?r|surgery|surgical|bacteria|bacterium|drug|syndrome|"
    r"gland|hormone|molecule|ion|alloy|mineral|vertebra|membrane|larva|fungus|alkaloid|isotope|"
    r"equation|algebra|theorem|polynomial|cardinal number|unit of|plural of|variant of)\b"
)
OFFENSIVE = re.compile(
    r"\b(sex|sexual|sexually|penis|vagina|genital|genitals|anus|anal|buttocks|breasts?|testicles?|"
    r"copulat\w*|intercourse|masturbat\w*|prostitut\w*|whore|rape|urine|urinat\w*|feces|faeces|excrement|"
    r"defecat\w*|vomit\w*|race|racial|negro|jew|jewish|homosexual\w*|lesbian|slur|offensive|"
    r"derogatory|contemptuous|obscene|vulgar|semen|menstru\w*|suicide|torture)\b"
)
BORING_DEF = re.compile(
    r"^(of or relating to|of or pertaining to|relating to|pertaining to|in a \w+ manner|in an \w+ manner|"
    r"the quality of being|the state of being|the act of|the condition of being|having the quality|"
    r"characteristic of|resembling a|resembling an|a \w+ish |of or like|any of)"
)
HAND_WORDS = set(json.loads((ROOT / "pipeline" / "hand_words.json").read_text()))


def stem_in_def(word, gloss):
    stem = word[: max(4, len(word) - 3)]
    return stem in gloss


def main():
    out = []
    seen = set()
    for word in wn.all_lemma_names():
        if word in seen or word in HAND_WORDS or not re.fullmatch(r"[a-z]{6,17}", word):
            continue
        seen.add(word)
        if word.endswith(("ness", "ly", "ism", "ist", "ology", "ologist")):
            continue
        synsets = wn.synsets(word)
        if not synsets or len(synsets) > 4:
            continue
        s = synsets[0]
        if s.lexname() in SKIP_LEXNAMES:
            continue
        if {d.name().split(".")[0] for d in s.topic_domains()} & SKIP_TOPICS:
            continue
        if {d.name().split(".")[0] for d in s.usage_domains()} & SKIP_USAGE:
            continue
        if any(l.name()[0].isupper() for l in s.lemmas() if l.name().lower() == word):
            continue
        gloss = s.definition().strip()
        n_words = len(gloss.split())
        if not 3 <= n_words <= 22:
            continue
        if TECH_WORDS.search(gloss) or OFFENSIVE.search(gloss) or OFFENSIVE.search(word):
            continue
        if BORING_DEF.search(gloss) or stem_in_def(word, gloss):
            continue
        zipf = zipf_frequency(word, "en")
        if not 0.9 <= zipf <= 3.0:
            continue
        examples = [e for e in s.examples() if word[:4] in e]
        out.append({
            "w": word,
            "pos": {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}[s.pos()],
            "lex": s.lexname(),
            "synset": s.name(),
            "d": gloss,
            "wn_ex": examples,
            "zipf": round(zipf, 2),
            "senses": len(synsets),
        })
    out.sort(key=lambda r: r["w"])
    (ROOT / "data" / "candidates.json").write_text(json.dumps(out, indent=0, ensure_ascii=False))
    from collections import Counter
    print(len(out), "candidates")
    print(Counter(r["lex"] for r in out).most_common())
    print(Counter(int(r["zipf"] * 2) / 2 for r in out).most_common())


if __name__ == "__main__":
    main()
