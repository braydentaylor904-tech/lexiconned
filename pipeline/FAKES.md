# Writing a batch

Rewriting year-one fakes: input is a published entry (word, definition, roots, sentence, old fakes); only `f` and `hooks` are written, against the existing `r` and `s`. See `batch_generate.py rewrite`.

Year one: input `data/batches/in_NNN.json` (word, part of speech, real WordNet definition, Wiktionary etymology, Wiktionary/WordNet sentence); output `pipeline/generated/out_NNN.json`.
Years 2–10: input `data/batches/wk_in_NNN.json` (word, part of speech, up to five Wiktionary senses, etymology, up to three Wiktionary example sentences, respelling when Wiktionary has an IPA); output `pipeline/generated/wk_out_NNN.json`. `pipeline/batch_generate.py` writes these through the Message Batches API, one request per word, with this file as the system prompt.

One object per input word, same order:

```json
{"w": "imbroglio", "d": "…", "f": ["…", "…", "…"], "hooks": ["tangle", "muddle", "tangle"], "r": "Italian imbroglio “tangle, muddle”", "s": "…", "p": "", "ok": true}
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

The game shows hints only after wrong guesses: first the roots line (`r`), then the example sentence (`s`). A fake that either hint rules out is a free answer, so every fake must survive both hints. Write the roots line and pick the sentence first, then write fakes against them.

1. **Consistent with the roots.** Every fake must be a believable meaning for a word built from the roots shown in `r`. Use the root's literal sense and push it somewhere false: for defenestrate (Latin *fenestra* "window"), every fake involves windows ("to board up the windows of a building", "to fit a house with new windows", "to spy on someone through a window"). For lachrymose (*lacrima* "tear"), every fake involves tears or weeping. Name the root idea you used for each fake in `hooks` (see below). When the roots are English parts of the word (backslide + -er), build on those parts' meanings.
2. **Same part of speech and subject area as the real definition.** Same grammar and opening as the real one: if the real verb definition starts with "To", every fake does; if it starts with a bare verb, none do. Nouns name the same kind of thing (a person, an object, a quality, an act); adjectives describe the same kind of thing. Stay in the real definition's general field (feelings, speech, buildings, behaviour, law…) so the field itself gives nothing away.
3. **Fits the example sentence.** Each fake, substituted for the word in `s`, must still produce a sentence that makes sense. If the sentence is about a man throwing envoys out of a window, a fake about decorating windows fails it; one about pushing envoys through a window to their deaths is too close to true; one about shouting at someone through a window works.
4. **Differs in meaning, not in clues.** The fakes and the real definition must look alike: same length (each fake within roughly ±35% of the real word count), same register, same punctuation habits (if the real one has a parenthetical or a semicolon, at least one fake does too), no tell-tale vagueness or over-specific detail. What separates them is only what the word actually means.
5. **Actually false.** Not true of the word in any sense Wiktionary or WordNet lists, not a synonym or paraphrase of the real definition, and not the real meaning of a lookalike that is *also* a sense of this word.
6. **Three different ideas.** Each fake takes the roots in a different direction; no two fakes say nearly the same thing.
7. **Clean.** Don't use the word itself or its stem, nothing offensive or sexual, no proper nouns unless the real definition has one, sentence case without a final period (the build step capitalises).

## Hooks (`hooks`)

Three strings, one per fake, in the same order: the root idea that fake builds on, copied as it appears in `r` (a gloss such as `window` or `tear`, or an English part of the word such as `backslide`). The validator checks that each hook appears in the roots line and in its fake (a different form of the same word is fine; if the hook is the word's own stem, it only has to appear in `r`).

## Roots (`r`)

Write this before the fakes; they are built on it. One line, at most ~110 characters, condensed **only** from the given etymology text; never add facts it doesn't contain. Prefer the most informative step (usually the classical or Old French source) over the full chain. Include the English gloss of the key root whenever the etymology gives one, since the fakes hang on it. Format glosses in curly quotes: `Latin pusillus “very small” + animus “spirit”`. Drop Proto-Indo-European, cognate lists, and "see also" notes.

## Sentence (`s`)

Use the given sentence (for Wiktionary words, the one example that best fits the chosen sense), or a trimmed excerpt of it that contains the word: a contiguous stretch of the original, with only the first letter re-capitalised and a final period added when the excerpt ends mid-sentence. Poetry slashes may be replaced with commas. Aim for 40–160 characters.

When a Wiktionary word has no example sentences (or none uses the chosen sense), write one original sentence of 40–140 characters that uses the word naturally in the chosen sense and gives a fair contextual clue without restating the definition.

## Pronunciation (`p`, Wiktionary words only)

Leave `p` empty when the input has a respelling. Otherwise give the standard American pronunciation as a respelling in the same style: syllables joined by hyphens, the stressed syllable in capitals, plain-English spellings (`uh`, `ee`, `ay`, `oh`, `oo`, `ow`, `y`, `zh`, `th`), e.g. `neh-KRAH-puh-lus`, `kun-JEEL`, `swyr`. Reject the word if you are not confident how it is pronounced.

## Rejecting a word (`ok: false`)

Set `ok` to false (and leave every other field empty) when the word fails "Choosing the word", or when the sentence can't be trimmed into something readable, the sentence uses a different sense than the definition, the etymology is too thin to make a useful hint, or the real definition is misleading. The build step skips it and the next spare word takes its place.
