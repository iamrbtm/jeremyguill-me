from __future__ import annotations

from pathlib import Path


def test_editor_component_wires_source_textarea_to_browser_adapter():
    template = Path("src/portfolio/templates/admin/components/editor.html").read_text()

    assert "data-portfolio-editor" in template
    assert "data-editor-source" in template
    assert "data-editor-root" in template
    assert 'name="{{ name }}"' in template


def test_editor_adapter_exposes_narrow_roundtrip_contract():
    source = Path("src/portfolio/static_src/ts/editor.ts").read_text()

    assert "export class PortfolioEditor" in source
    assert "getMarkdown(): string" in source
    assert "setMarkdown(source: string): void" in source
    assert "changeMode" in source
    assert "portfolio:editor-ready" in source
    assert "sourceField.value = adapter.getMarkdown()" in source
