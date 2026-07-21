from __future__ import annotations

from autolina_scraper import htmlparse


def test_slugify_label_basic() -> None:
    assert htmlparse.slugify_label("Erstzulassung") == "erstzulassung"


def test_slugify_label_transliterates_umlauts() -> None:
    assert htmlparse.slugify_label("Serienmässige Ausstattung") == "serienmaessige_ausstattung"


def test_slugify_label_strips_punctuation() -> None:
    assert htmlparse.slugify_label("Fahrgestell-Nr.") == "fahrgestell_nr"
    assert htmlparse.slugify_label("Farbe (aussen & innen)") == "farbe_aussen_innen"


def test_clean_text_collapses_whitespace() -> None:
    tree = htmlparse.parse("<div>  hello   <span>world</span>  </div>")
    assert htmlparse.clean_text(tree.css_first("div")) == "hello world"


def test_clean_text_returns_empty_string_for_none() -> None:
    assert htmlparse.clean_text(None) == ""


def test_label_value_pairs_single_value_row() -> None:
    tree = htmlparse.parse(
        '<div class="details-row"><div><label>Treibstoff</label>'
        "<span>Benzin</span></div></div>"
    )
    row = tree.css_first(".details-row")
    assert htmlparse.label_value_pairs(row) == {"Treibstoff": "Benzin"}


def test_label_value_pairs_multi_value_row_pairs_icons_with_following_span() -> None:
    tree = htmlparse.parse(
        '<div class="details-row"><div><label>Türen & Sitze</label>'
        '<span><i class="icon-doors"></i><span>5</span>'
        '<i class="icon-seats"></i><span>5</span></span></div></div>'
    )
    row = tree.css_first(".details-row")
    pairs = htmlparse.label_value_pairs(row)
    assert pairs == {"Türen & Sitze doors": "5", "Türen & Sitze seats": "5"}


def test_label_value_pairs_ignores_rows_without_a_value() -> None:
    tree = htmlparse.parse('<div class="details-row"><div><label>Empty</label></div></div>')
    row = tree.css_first(".details-row")
    assert htmlparse.label_value_pairs(row) == {}


def test_label_value_pairs_skips_empty_label() -> None:
    tree = htmlparse.parse(
        '<div class="details-row"><div><label></label><span>value</span></div></div>'
    )
    row = tree.css_first(".details-row")
    assert htmlparse.label_value_pairs(row) == {}


def test_equipment_sections_reads_single_column_variant_only() -> None:
    html = """
    <div class="equipment-row">
      <div class="title">Optionale Ausstattung</div>
      <div class="equipment-large">
        <div class="parent-eq"><span>A</span></div>
      </div>
      <div class="equipment-small">
        <div class="parent-eq"><span>A</span></div>
        <div class="parent-eq"><span>B</span></div>
      </div>
    </div>
    """
    tree = htmlparse.parse(html)
    assert htmlparse.equipment_sections(tree) == {"Optionale Ausstattung": ["A", "B"]}


def test_equipment_sections_skips_rows_without_a_title() -> None:
    html = '<div class="equipment-row"><div class="equipment-small"></div></div>'
    tree = htmlparse.parse(html)
    assert htmlparse.equipment_sections(tree) == {}
