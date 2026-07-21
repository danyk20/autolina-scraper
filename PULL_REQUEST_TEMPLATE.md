## What

Brief description of the change.

## Why

What problem this solves / what it enables.

## Checklist

- [ ] `ruff check .` passes
- [ ] `mypy src` passes
- [ ] `pytest` passes with the coverage gate (100% for new code, ideally)
- [ ] If this touches HTML parsing: fixtures under `tests/fixtures/` were
      refreshed from a live fetch, not hand-edited
- [ ] If this adds/changes a filter query parameter: live-diffing evidence
      (before/after result counts for a couple of query strings) is included
      below, not just the code
- [ ] `CHANGELOG.md` updated under `Unreleased` (if user-visible)

## Live-diffing evidence (if applicable)

<!-- e.g. `?bodyType=1003` narrows count from 1578 to 402, confirmed against `/vw/tiguan` -->
