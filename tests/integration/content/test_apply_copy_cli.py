from __future__ import annotations

from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import Experience, Project

DOC = """---
type: project
match: pollywog
summary: New summary.
stack: Access, CSV
year: 2012
---
## The Problem

Nightly prep took hours.
"""


def _write(tmp_path, text, name="p.md"):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def _project(slug="pollywog", title="Pollywog"):
    return Project(title=title, slug=slug, summary="old", state=PublicationState.PUBLISHED)


def _run(app, *args):
    return app.test_cli_runner().invoke(args=["content", "apply-copy", *args])


def test_apply_updates_project_and_renders_html(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()

    result = _run(app, _write(tmp_path, DOC))

    assert result.exit_code == 0, result.output
    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert project.summary == "New summary."
    assert project.stack == "Access, CSV" and project.year == "2012"
    assert "<h2>The Problem</h2>" in project.rendered_html
    assert project.source_markdown.startswith("## The Problem")


def test_dry_run_changes_nothing(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()

    result = _run(app, "--dry-run", _write(tmp_path, DOC))

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code == 0 and project.summary == "old"
    assert "dry run" in result.output.lower()


def test_unknown_slug_fails_with_clear_message(app, db_session, tmp_path):
    result = _run(app, _write(tmp_path, DOC))

    assert result.exit_code != 0 and "no project with slug 'pollywog'" in result.output


def test_apply_is_idempotent_and_does_not_bump_version_twice(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    path = _write(tmp_path, DOC)

    first = _run(app, path)
    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    version_after_first = project.version
    second = _run(app, path)
    db_session.refresh(project)

    assert first.exit_code == 0 and second.exit_code == 0 and "unchanged" in second.output
    assert version_after_first == 2 and project.version == version_after_first


def test_bad_second_file_rolls_back_the_first(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    good = _write(tmp_path, DOC, "a.md")
    bad = _write(tmp_path, DOC.replace("match: pollywog", "match: missing"), "b.md")

    result = _run(app, good, bad)

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code != 0 and "no project with slug 'missing'" in result.output
    assert project.summary == "old" and project.version == 1


def test_experience_doc_matches_by_organization_and_role(app, db_session, tmp_path):
    db_session.add(
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            start_date="2024",
            sort_position=1,
        )
    )
    db_session.commit()
    doc = (
        "---\ntype: experience\nmatch: Dudefish Printing | Owner Operator\n"
        "summary: Ran the business.\n---\n- Built custom software\n- Managed finances\n"
    )

    result = _run(app, _write(tmp_path, doc, "e.md"))

    exp = db_session.scalar(select(Experience))
    db_session.refresh(exp)
    assert result.exit_code == 0, result.output
    assert exp.summary == "Ran the business."
    assert "<li>Built custom software</li>" in exp.rendered_html
