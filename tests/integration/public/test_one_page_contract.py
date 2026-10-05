"""Contract: the real /api/site-content.json export must feed the one-page generator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from portfolio.content.enums import PublicationState
from portfolio.content.models import Experience, Project

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_one_page.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_one_page_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_one_page_contract"] = module
    spec.loader.exec_module(module)
    return module


def test_real_export_builds_a_page(app, client, db_session):
    origin = app.config["PUBLIC_ORIGIN"].rstrip("/")
    db_session.add_all(
        [
            Project(
                title="Contract Project",
                slug="contract-project",
                summary="Sum",
                role="Dev",
                stack="Flask, SQL",
                year="2024",
                result_headline="Saved hours",
                rendered_html="<h2>Problem</h2><p>Body</p>",
                state=PublicationState.PUBLISHED,
            ),
            Experience(
                organization="Acme", role="Engineer", summary="Did things", visible=True
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/site-content.json")
    assert response.status_code == 200
    page = _load().build_page(response.get_json(), origin=origin)

    assert "Contract Project" in page
    assert f'href="{origin}/work/contract-project"' in page
    assert "Acme" in page
