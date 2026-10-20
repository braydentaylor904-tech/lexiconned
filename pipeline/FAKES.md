# Writing a batch

Year one: input `data/batches/in_NNN.json` (word, part of speech, real WordNet definition, Wiktionary etymology, Wiktionary/WordNet sentence); output `pipeline/generated/out_NNN.json`.
Years 2–10: input `data/batches/wk_in_NNN.json` (word, part of speech, up to five Wiktionary senses, etymology, up to three Wiktionary example sentences, respelling when Wiktionary has an IPA); output `pipeline/generated/wk_out_NNN.json`. `pipeline/batch_generate.py` writes these through the Message Batches API, one request per word, with this file as the system prompt.

One object per input word, same order:

```json
{"w": "imbroglio", "d": "…", "f": ["…", "…", "…"], "r": "Italian imbroglio “tangle, muddle”", "s": "…", "p": "", "ok": true}
```

`d` and `p` are only used for Wiktionary words. `python pipeline/validate.py NNN` (or `wk_NNN`) must pass before a batch counts as done.

## Choosing the word (Wiktionary words only)

The player should be an educated adult who has *probably* met the word but couldn't define it: obscure-but-real literary, historical or everyday-rare vocabulary (lacuna, cosset, sonorous, portico). Reject (`ok: false`) when the word is:

- too easy (most adults know it: litterbug, orangeade, teleprompter, salve);
- technical, scientific or medical jargon, a taxon or species, a chemical, or a term of art only specialists use;
- regional or foreign (a word mainly used in one country, a loanword not naturalised in English, an untranslated food or garment);
- a trivial derivative whose meaning is obvious from a commoner word (ceilinged, calypsonian, analogize, brambly);
- offensive, sexual, slang, a brand, or a proper noun in disguise;
- a word whose definitions below don't include one clear, self-contained sense suitable as the answer.

## The real definition (`d`, Wiktionary words only)

Pick the single best sense (the one most players would recognise as *the* meaning, and the one the sentence uses). Copy it as a contiguous excerpt of that gloss: drop a leading "To " on verbs, may stop before a trailing "; …" or ", especially …" clause, no final period. Never reword it; if no sense works without rewording, reject the word.

## Fake definitions (`f`)

1. **Same shape as the real one.** Same part of speech and the same WordNet grammar: verb definitions start with a bare verb ("pledge without delivery…", never "to…"), noun definitions name a thing or person, adjective definitions describe. Match the real definition's register and punctuation habits.
2. **Same length.** Each fake is within roughly ±35% of the real definition's word count. If the real one has a parenthetical or a semicolon, at least one fake does too.
3. **Plausible from the word itself.** Lean on what the word looks or sounds like: false roots, near-homophones, the wrong half of a compound, a related-looking word's meaning (anodyne → "relating to anodes"). A good fake makes the player hesitate.
4. **Actually false.** Not true of the word in any sense Wiktionary or WordNet lists, not a synonym or paraphrase of the real definition, and not the real meaning of a lookalike that is *also* a sense of this word.
5. **Three different ideas.** No two fakes in the same semantic field as each other, and at most one in the real definition's field.
6. **Clean.** Don't use the word or its stem, nothing offensive or sexual, no proper nouns unless the real definition has one, sentence case without a final period (the build step capitalises).

## Roots (`r`)

One line, at most ~110 characters, condensed **only** from the given etymology text; never add facts it doesn't contain. Prefer the most informative step (usually the classical or Old French source) over the full chain. Format glosses in curly quotes: `Latin pusillus “very small” + animus “spirit”`. Drop Proto-Indo-European, cognate lists, and "see also" notes.

## Sentence (`s`)

Use the given sentence (for Wiktionary words, the one example that best fits the chosen sense), or a trimmed excerpt of it that contains the word: a contiguous stretch of the original, with only the first letter re-capitalised and a final period added when the excerpt ends mid-sentence. Poetry slashes may be replaced with commas. Aim for 40–160 characters.

When a Wiktionary word has no example sentences (or none uses the chosen sense), write one original sentence of 40–140 characters that uses the word naturally in the chosen sense and gives a fair contextual clue without restating the definition.

## Pronunciation (`p`, Wiktionary words only)

Leave `p` empty when the input has a respelling. Otherwise give the standard American pronunciation as a respelling in the same style: syllables joined by hyphens, the stressed syllable in capitals, plain-English spellings (`uh`, `ee`, `ay`, `oh`, `oo`, `ow`, `y`, `zh`, `th`), e.g. `neh-KRAH-puh-lus`, `kun-JEEL`, `swyr`. Reject the word if you are not confident how it is pronounced.

## Rejecting a word (`ok: false`)

Set `ok` to false (and leave every other field empty) when the word fails "Choosing the word", or when the sentence can't be trimmed into something readable, the sentence uses a different sense than the definition, the etymology is too thin to make a useful hint, or the real definition is misleading. The build step skips it and the next spare word takes its place.
