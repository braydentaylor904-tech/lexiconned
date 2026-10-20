# Writing a batch

Input: `data/batches/in_NNN.json` (word, part of speech, real WordNet definition, Wiktionary etymology, Wiktionary/WordNet sentence).
Output: `pipeline/generated/out_NNN.json`, one object per input word, same order:

```json
{"w": "imbroglio", "f": ["…", "…", "…"], "r": "Italian imbroglio “tangle, muddle”", "s": "…", "ok": true}
```

`python pipeline/validate.py NNN` must pass before a batch counts as done.

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

Use the given sentence, or a trimmed excerpt of it that contains the word: a contiguous stretch of the original, with only the first letter re-capitalised and a final period added when the excerpt ends mid-sentence. Poetry slashes may be replaced with commas. Aim for 40–160 characters.

## Rejecting a word (`ok: false`)

Set `ok` to false (and leave `f` empty) when the sentence can't be trimmed into something readable, the sentence uses a different sense than the definition, the etymology is too thin to make a useful hint, or the real definition is misleading. The build step skips it and the next spare word takes its place.
