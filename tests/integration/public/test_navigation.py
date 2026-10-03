from __future__ import annotations

import re
from pathlib import Path


def _nav(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'<header class="site-header">.*?</header>', html, re.DOTALL).group(0)


def test_work_link_is_current_on_work_pages(client):
    nav = _nav(client, "/work")

    assert re.search(r'<a href="/work"[^>]*aria-current="page"', nav)
    assert nav.count('aria-current="page"') == 1


def test_current_page_not_marked_on_home_for_other_links(client):
    assert 'aria-current="page"' not in _nav(client, "/")


def test_nav_has_toggle_button_wired_to_nav(client):
    nav = _nav(client, "/")

    assert 'class="nav-toggle"' in nav and 'aria-expanded="false"' in nav
    assert 'aria-controls="primary-nav"' in nav and 'id="primary-nav"' in nav
    assert "hidden" in re.search(r'<button class="nav-toggle"[^>]*>', nav).group(0)


def test_contact_is_styled_as_call_to_action(client):
    assert 'class="nav-cta"' in _nav(client, "/")


def test_capabilities_anchor_is_gone_from_nav(client):
    assert "#capabilities" not in _nav(client, "/")


def test_script_wires_menu_toggle_and_escape():
    js = Path("src/portfolio/static/assets/site.js").read_text()

    assert "nav-toggle" in js and "aria-expanded" in js and "Escape" in js
