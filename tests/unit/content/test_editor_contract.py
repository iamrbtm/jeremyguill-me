from __future__ import annotations

import pytest

from portfolio.content.editor_contract import validate_editor_source
from portfolio.content.enums import PublicationState
from portfolio.content.models import Project
from portfolio.content.schemas import ContentCommand
from portfolio.content.services import ContentValidationError, save_draft
from portfolio.extensions import db


def test_editor_contract_accepts_supported_markdown():
    source = "# Heading\n\n- one\n- two\n\n```python\nprint('safe')\n```"

    assert validate_editor_source(source).valid is True


def test_editor_contract_rejects_raw_html():
    result = validate_editor_source("<iframe src='https://evil.example'></iframe>")

    assert result.valid is False
    assert "Raw HTML is not supported." in result.errors


def test_editor_contract_rejects_oversized_source():
    result = validate_editor_source("a" * 500_001)

    assert result.valid is False
    assert "Content exceeds 500 KB." in result.errors


@pytest.mark.parametrize(
    "source",
    [
        "![x](javascript:alert(1))",
        "![x](https://evil.example/tracker.png)",
    ],
)
def test_editor_contract_rejects_unapproved_image_targets(source: str):
    result = validate_editor_source(source)

    assert result.valid is False
    assert "Images must use approved media paths." in result.errors


def test_save_draft_uses_editor_contract(db_session):
    project = Project(title="Old", slug="old", summary="Old", state=PublicationState.DRAFT)
    db.session.add(project)
    db.session.commit()

    with pytest.raises(ContentValidationError, match="Raw HTML"):
        save_draft(
            project,
            ContentCommand(title="Unsafe", summary="Unsafe", source_markdown="<script></script>"),
        )
    db.session.refresh(project)
    assert project.title == "Old"
