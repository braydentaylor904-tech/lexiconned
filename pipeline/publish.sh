#!/bin/sh
# Rebuild, then publish only the game (index.html, words/, plus CNAME for the custom domain) to the gh-pages branch that GitHub Pages serves.
# pipeline/ (including review.html, which shows every answer) and data/ are never published.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python pipeline/build.py
git diff --quiet words || { git add words && git commit -q -m "Rebuild word files"; }
git push -q origin main
tmp=$(mktemp -d)
git worktree add -q --detach "$tmp"
(
  cd "$tmp"
  git checkout -q --orphan gh-pages-new
  git rm -q -r --cached . >/dev/null
  find . -mindepth 1 -maxdepth 1 ! -name .git ! -name index.html ! -name words ! -name .nojekyll ! -name CNAME -exec rm -rf {} +
  git add index.html .nojekyll CNAME words
  git commit -q -m "Publish $(date -u +%Y-%m-%d)"
  git push -q -f origin HEAD:gh-pages
)
git worktree remove --force "$tmp"
git branch -q -D gh-pages-new
echo "Published. Site: https://playlexiconned.com/"
