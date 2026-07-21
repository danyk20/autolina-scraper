"""Shared HTML-parsing primitives for autolina.ch's server-rendered pages.

autolina.ch embeds an internal JSON cache (``window.SS_Requests``) on some
responses, but — confirmed empirically — only when the request's User-Agent
looks like a real browser. This project identifies itself honestly (see
:mod:`autolina_scraper.http`), so it never receives that shortcut, and parses
the same server-rendered HTML a real browser gets instead. The rendered DOM
itself does not vary by User-Agent (verified: identical listing-card counts
either way), so this is the reliable, primary data path — not a fallback.

autolina.ch's detail page renders most specs as ``<label>Name</label><span>
value</span>`` pairs, sometimes with the value further broken into
icon-tagged sub-values (e.g. doors + seats share one row, each preceded by its
own ``<i class="icon-...">``). :func:`label_value_pairs` extracts these
generically — keyed by the label text itself — rather than hardcoding every
field name, so a new row autolina.ch adds later shows up automatically
instead of being silently dropped.
"""

from __future__ import annotations

import re
from typing import Final

from selectolax.parser import HTMLParser, Node

_WHITESPACE_RE = re.compile(r"\s+")
_UMLAUT_TRANSLATION: Final = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
)
_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]+")


def parse(html: str) -> HTMLParser:
    return HTMLParser(html)


def clean_text(node: Node | None) -> str:
    """A node's full text content, whitespace-collapsed and stripped."""
    if node is None:
        return ""
    return _WHITESPACE_RE.sub(" ", node.text(deep=True, separator=" ")).strip()


def slugify_label(label: str) -> str:
    """A German UI label -> a safe, lowercase, underscore-separated column name.

    E.g. ``"Farbe (aussen & innen)"`` -> ``"farbe_aussen_innen"``.
    """
    ascii_label = label.translate(_UMLAUT_TRANSLATION)
    return _NON_ALNUM_RE.sub("_", ascii_label).strip("_").lower()


def label_value_pairs(row_container: Node) -> dict[str, str]:
    """Extract every ``<label>...</label><span>...</span>`` pair under
    *row_container* (typically a ``.details-row``, ``.sub-details-grid``, or
    ``.energy-data-row .row-container``), keyed by the label text.

    A value span containing more than one ``<i class="icon-...">`` is a
    multi-value row (e.g. doors + seats) — each icon's class suffix is
    appended to the label to keep the sub-values distinct.
    """
    pairs: dict[str, str] = {}
    for label_node in row_container.css("label"):
        label_text = clean_text(label_node)
        if not label_text:
            continue
        value_node = label_node.next
        if value_node is None:
            continue

        icons = [child for child in value_node.iter() if child.tag == "i"]
        if len(icons) <= 1:
            value_text = clean_text(value_node)
            if value_text:
                pairs[label_text] = value_text
            continue

        current_suffix: str | None = None
        for child in value_node.iter():
            if child.tag == "i":
                icon_class = (child.attributes.get("class") or "").split()[0]
                current_suffix = icon_class.removeprefix("icon-") or None
            elif current_suffix is not None:
                value_text = clean_text(child)
                if value_text:
                    pairs[f"{label_text} {current_suffix}"] = value_text
                current_suffix = None
    return pairs


def equipment_sections(tree: HTMLParser) -> dict[str, list[str]]:
    """``{section_title: [item, ...]}`` for every ``.equipment-row`` block.

    Each block renders its items twice — once split across two ``.equipment-large``
    columns (desktop layout) and once as a single ``.equipment-small`` list (mobile
    layout) — so only the single-column variant is read, to avoid double-counting.
    """
    sections: dict[str, list[str]] = {}
    for row in tree.css(".equipment-row"):
        title = clean_text(row.css_first(".title"))
        if not title:
            continue
        items = [clean_text(item) for item in row.css(".equipment-small .parent-eq")]
        sections[title] = [item for item in items if item]
    return sections
