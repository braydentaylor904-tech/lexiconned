# Lexiconned

A daily vocabulary game: three hard words a day, four definitions each, one real.

- `index.html`: the whole game (static; no build step).
- `words/`: one JSON file per month plus `manifest.json`. Day N (from the launch date) uses sequence entries 3N–3N+2.
- `words/lock.json`: `locked_days`. Days below this number are live, and the build refuses to change them. `build.py` raises it automatically to cover every day that has started anywhere.
- `pipeline/`: scripts that select words, generate fakes, validate, and build the month files. See `pipeline/FAKES.md` for the writing rules.
- `data/batches/`: frozen generation inputs (`in_NNN` WordNet, year one; `wk_in_NNN` Wiktionary, years 2–10). Never edit or reorder a published batch.
- `pipeline/batch_generate.py`: writes `pipeline/generated/` through the Message Batches API (`prepare`, `estimate`, `submit --count N`, `status`, `collect`). Needs `ANTHROPIC_API_KEY`; run `estimate` first.
- `pipeline/review.html`: spot-check page (serve the repo locally, then open `/pipeline/review.html`).

Preview any day locally with `?day=N`.

Deployment: `pipeline/publish.sh` rebuilds, pushes `main`, and force-updates the `gh-pages` branch with only `index.html`, `.nojekyll`, `CNAME` (playlexiconned.com) and `words/`. GitHub Pages serves `gh-pages`, so nothing in `pipeline/` or `data/` is published.

```bash
python3 -m http.server 8417
```

Definitions from WordNet 3.0 (Princeton University). Origins, pronunciations and example sentences adapted from Wiktionary, CC BY-SA 4.0.
