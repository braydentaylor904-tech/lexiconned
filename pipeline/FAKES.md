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

1. **Plausible first.** Every fake must read like a believable dictionary definition of a real English word: a meaning a lexicographer could have written. No puns on the English sense of a root (mendacious, from "lying", is not "lying flat"; lachrymose, from "tear", is not "tearing along"), nothing absurd or jokey (miscreant is not "a person who misbelieves the clock"), and no oddly specific scenes ("before a test", "at country weddings"). This rule beats every rule below: if a root-based fake can't be made plausible, use rule 6.
2. **Consistent with the roots.** Every fake must be a believable meaning for a word built from the roots shown in `r`. Use the root's literal sense and take it somewhere false: for defenestrate (Latin *fenestra* "window"), every fake involves windows ("to board up the windows of a building", "to fit a house with new windows"). For jejune ("fasting, barren", French *jeune* "young"): "bleak and joyless; also gloomy from long fasting", "young and passionate; also bold and full of feeling". For anfractuous ("a bending, a winding"): "bending steeply downhill; sharply sloping", "winding through thick forest; deeply shaded". Name the root idea you used for each fake in `hooks`. When the roots are English parts of the word (backslide + -er), build on those parts' meanings.
3. **Same part of speech, subject area and format as the real definition.** Same grammar and opening: if the real verb definition starts with "To", every fake does; if it starts with a bare verb, none do. Nouns name the same kind of thing (a person, an object, a quality, a state); adjectives describe the same kind of thing. Stay in the real definition's general field (feelings, speech, buildings, behaviour, law…) so the field gives nothing away. Copy its shape: if it is "X or Y", "X; Y" or has a parenthetical, the fakes look the same; no "e.g." clause unless the real definition has one. Each fake is within roughly ±35% of the real definition's word count, in the same register.
4. **Fits the example sentence.** Each fake, substituted for the word in `s`, must still produce a sentence that makes sense. If the sentence is about nobles throwing envoys out of a window, a fake about decorating windows fails; one about shouting at someone through a window works.
5. **Clearly wrong.** The fake must not overlap with the real meaning: not true of the word in any sense Wiktionary or WordNet lists, not a synonym, near-synonym or narrower case of the real definition, and not the real meaning of a lookalike that is *also* a sense of this word. A player who knows the word must be able to rule it out at once (hubris is "overbearing pride", so "insolent mockery of rivals" is too close). What separates fakes from the real definition is meaning, never clues.
6. **Thin roots.** When the roots can't support three plausible, clearly wrong fakes (a root whose gloss *is* the meaning, like mendax "lying" or hubris "insolence"; a bare name; no gloss at all), a fake may instead rest only on the subject area and the sentence: a believable meaning in the real definition's field that fits `s`. Use root-based fakes where they work and field-based ones for the rest; set that fake's hook to `(field)`.
7. **Three different ideas.** No two fakes say nearly the same thing.
8. **Clean.** Don't use the word itself or its stem, nothing offensive or sexual, no proper nouns unless the real definition has one, sentence case without a final period (the build step capitalises).

## Hooks (`hooks`)

Three strings, one per fake, in the same order: the root idea that fake builds on, copied as it appears in `r` (a gloss such as `window` or `tear`, or an English part of the word such as `backslide`), or `(field)` for a fake that rests only on the subject area and sentence (rule 6). The validator checks that each hook appears in the roots line and in its fake (a different form of the same word is fine; if the hook is the word's own stem, it only has to appear in `r`).

## Roots (`r`)

Write this before the fakes; they are built on it. One line, at most ~110 characters, condensed **only** from the given etymology text; never add facts it doesn't contain. Prefer the most informative step (usually the classical or Old French source) over the full chain. Include the English gloss of the key root whenever the etymology gives one, since the fakes hang on it. Format glosses in curly quotes: `Latin pusillus “very small” + animus “spirit”`. Drop Proto-Indo-European, cognate lists, and "see also" notes.

## Sentence (`s`)

Use the given sentence (for Wiktionary words, the one example that best fits the chosen sense), or a trimmed excerpt of it that contains the word: a contiguous stretch of the original, with only the first letter re-capitalised and a final period added when the excerpt ends mid-sentence. Poetry slashes may be replaced with commas. Aim for 40–160 characters.

When a Wiktionary word has no example sentences (or none uses the chosen sense), write one original sentence of 40–140 characters that uses the word naturally in the chosen sense and gives a fair contextual clue without restating the definition.

## Pronunciation (`p`, Wiktionary words only)

Leave `p` empty when the input has a respelling. Otherwise give the standard American pronunciation as a respelling in the same style: syllables joined by hyphens, the stressed syllable in capitals, plain-English spellings (`uh`, `ee`, `ay`, `oh`, `oo`, `ow`, `y`, `zh`, `th`), e.g. `neh-KRAH-puh-lus`, `kun-JEEL`, `swyr`. Reject the word if you are not confident how it is pronounced.

## Rejecting a word (`ok: false`)

Set `ok` to false (and leave every other field empty) when the word fails "Choosing the word", or when the sentence can't be trimmed into something readable, the sentence uses a different sense than the definition, the etymology is too thin to make a useful hint, or the real definition is misleading. The build step skips it and the next spare word takes its place.
