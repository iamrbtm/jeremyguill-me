from __future__ import annotations

from portfolio.content.toc import enhance_case_study_html, reading_minutes


def test_adds_unique_ids_and_builds_toc():
    html, items = enhance_case_study_html(
        "<h2>The Problem</h2><p>x</p><h2>The Problem</h2><h2>What I Built &amp; Why</h2>"
    )

    assert [i.id for i in items] == ["the-problem", "the-problem-2", "what-i-built-why"]
    assert '<h2 id="the-problem">' in html and '<h2 id="the-problem-2">' in html
    assert items[2].text == "What I Built & Why"


def test_no_headings_gives_empty_toc_and_untouched_html():
    html, items = enhance_case_study_html("<p>Just text.</p>")

    assert items == [] and html == "<p>Just text.</p>"


def test_tables_are_wrapped_for_horizontal_scroll():
    html, _ = enhance_case_study_html("<table><tr><td>a</td></tr></table>")

    assert html == '<div class="table-scroll"><table><tr><td>a</td></tr></table></div>'


def test_heading_with_only_symbols_gets_fallback_id():
    _, items = enhance_case_study_html("<h2>???</h2>")

    assert items[0].id == "section"


def test_reading_minutes_has_floor_of_one():
    assert reading_minutes("<p>short</p>") == 1
    assert reading_minutes("<p>" + "word " * 650 + "</p>") == 3
