from __future__ import annotations

import pytest

from portfolio.content.rendering import render_markdown


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        ("<script>alert(1)</script>", "<script"),
        ("[bad](javascript:alert(1))", "javascript:"),
        ('<img src=x onerror="alert(1)">', "onerror"),
    ],
)
def test_render_markdown_removes_active_content(source, forbidden):
    assert forbidden not in render_markdown(source).lower()


def test_render_markdown_adds_safe_link_rel():
    html = render_markdown("[site](https://example.com)")

    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html
