---
name: Bug report
about: Something isn't working as expected
title: ""
labels: bug
assignees: ""
---

**Describe the bug**
A clear, concise description of what's wrong.

**To reproduce**

```python
from autolina_scraper import scrape
result = scrape("...", "...")  # minimal repro
```

Or the equivalent CLI command.

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened — include the full traceback if there is one.

**Environment**

- `autolina-scraper` version:
- Python version:
- OS:

**If this looks like autolina.ch changed its markup**
See [CONTRIBUTING.md](../../CONTRIBUTING.md#if-autolinach-changes-its-markup-and-a-test-starts-failing)
for the loop to diagnose and fix this — a fresh HTML fixture of the affected
page is the single most useful thing to attach here.
