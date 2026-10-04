from __future__ import annotations

from sqlalchemy import select

from portfolio.content import copy_apply
from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Experience, Project

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


def test_empty_year_clears_to_none_and_is_unchanged_on_rerun(app, db_session, tmp_path):
    project = _project()
    project.year = "2012"
    db_session.add(project)
    db_session.commit()
    path = _write(tmp_path, "---\ntype: project\nmatch: pollywog\nyear:\n---\n")

    first = _run(app, path)
    db_session.refresh(project)
    second = _run(app, path)
    db_session.refresh(project)

    assert first.exit_code == 0 and project.year is None
    assert "unchanged" in second.output and project.version == 2


def test_empty_title_is_rejected_and_names_the_file(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()

    result = _run(app, _write(tmp_path, "---\ntype: project\nmatch: pollywog\ntitle:\n---\n"))

    assert result.exit_code != 0
    assert "p.md: title must not be empty" in result.output


def test_over_length_field_is_rejected_by_the_cli(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    doc = "---\ntype: project\nmatch: pollywog\nrole: " + "a" * 121 + "\n---\n"

    result = _run(app, _write(tmp_path, doc))

    assert result.exit_code != 0 and "role" in result.output and "120" in result.output


def test_crlf_file_applies(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    path = tmp_path / "crlf.md"
    path.write_bytes(DOC.replace("\n", "\r\n").encode())

    result = _run(app, str(path))

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code == 0, result.output
    assert project.summary == "New summary."


def test_bom_file_applies(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    path = tmp_path / "bom.md"
    path.write_bytes(b"\xef\xbb\xbf" + DOC.encode())

    assert _run(app, str(path)).exit_code == 0


def test_non_utf8_file_fails_naming_the_file(app, db_session, tmp_path):
    path = tmp_path / "bad.md"
    path.write_bytes(b"---\ntype: project\nmatch: x\n---\n\xff\xfe")

    result = _run(app, str(path))

    assert result.exit_code != 0 and "bad.md" in result.output


def test_default_discovery_skips_readme_and_empty_dir_is_ok(app, db_session, tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("# not a copy file")
    monkeypatch.setattr(copy_apply, "COPY_DIR", tmp_path)

    result = _run(app)

    assert result.exit_code == 0 and "no copy files found" in result.output


def test_default_discovery_applies_other_files(app, db_session, tmp_path, monkeypatch):
    db_session.add(_project())
    db_session.commit()
    (tmp_path / "README.md").write_text("# not a copy file")
    _write(tmp_path, DOC, "pollywog.md")
    monkeypatch.setattr(copy_apply, "COPY_DIR", tmp_path)

    result = _run(app)

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code == 0 and project.summary == "New summary."


def test_empty_body_keeps_existing_markdown(app, db_session, tmp_path):
    project = _project()
    project.source_markdown = "## Keep"
    project.rendered_html = "<h2>Keep</h2>"
    db_session.add(project)
    db_session.commit()

    doc = "---\ntype: project\nmatch: pollywog\nrole: Dev\n---\n"

    result = _run(app, _write(tmp_path, doc))

    db_session.refresh(project)
    assert result.exit_code == 0
    assert project.role == "Dev"
    assert project.source_markdown == "## Keep" and project.rendered_html == "<h2>Keep</h2>"


def test_blog_doc_renders_markdown(app, db_session, tmp_path):
    db_session.add(
        BlogPost(title="Post", slug="post", summary="old", state=PublicationState.PUBLISHED)
    )
    db_session.commit()
    doc = "---\ntype: blog\nmatch: post\nsummary: New.\n---\n## Heading\n"

    result = _run(app, _write(tmp_path, doc, "b.md"))

    post = db_session.scalar(select(BlogPost))
    db_session.refresh(post)
    assert result.exit_code == 0, result.output
    assert "<h2>Heading</h2>" in post.rendered_html and post.summary == "New."


def _revisions(db_session):
    from portfolio.content.models import ContentRevision

    return list(db_session.scalars(select(ContentRevision)))


def test_changed_apply_creates_one_revision_of_the_old_state(app, db_session, tmp_path):
    project = _project()
    project.source_markdown = "old body"
    db_session.add(project)
    db_session.commit()
    path = _write(tmp_path, DOC)

    assert _run(app, path).exit_code == 0
    revisions = _revisions(db_session)
    assert len(revisions) == 1
    assert revisions[0].reason == "apply-copy" and revisions[0].source_markdown == "old body"

    assert _run(app, path).exit_code == 0
    assert len(_revisions(db_session)) == 1


def test_dry_run_creates_no_revision(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()

    assert _run(app, "--dry-run", _write(tmp_path, DOC)).exit_code == 0

    assert _revisions(db_session) == []


def test_external_image_body_is_rejected_even_in_dry_run(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    doc = "---\ntype: project\nmatch: pollywog\nsummary: X.\n---\n![a](https://evil.example/x.png)\n"

    for args in (("--dry-run",), ()):
        result = _run(app, *args, _write(tmp_path, doc))
        assert result.exit_code != 0 and "approved media" in result.output

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert project.summary == "old" and _revisions(db_session) == []


def test_oversized_body_is_rejected_and_nothing_written(app, db_session, tmp_path):
    db_session.add(_project())
    db_session.commit()
    doc = "---\ntype: project\nmatch: pollywog\nsummary: X.\n---\n" + "a" * 500_001 + "\n"

    result = _run(app, _write(tmp_path, doc))

    project = db_session.scalar(select(Project))
    db_session.refresh(project)
    assert result.exit_code != 0 and "500 KB" in result.output
    assert project.summary == "old" and _revisions(db_session) == []
