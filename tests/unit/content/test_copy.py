from __future__ import annotations

import pytest

from portfolio.content.copy_apply import CopyError, parse_copy_file

SAMPLE = """---
type: project
match: pollywog
summary: Short.
stack: Access, CSV
---
## The Problem

Text.
"""


def test_parse_front_matter_and_body():
    doc = parse_copy_file(SAMPLE)

    assert doc.kind == "project" and doc.match == "pollywog"
    assert doc.fields == {"summary": "Short.", "stack": "Access, CSV"}
    assert doc.body.startswith("## The Problem")


def test_missing_front_matter_is_an_error():
    with pytest.raises(CopyError, match="front matter"):
        parse_copy_file("no front matter")


def test_unknown_field_is_an_error():
    with pytest.raises(CopyError, match="unknown field"):
        parse_copy_file("---\ntype: project\nmatch: x\nbogus: 1\n---\nbody")


def test_slug_state_and_published_at_cannot_be_set():
    for key in ("slug", "state", "published_at"):
        with pytest.raises(CopyError, match="unknown field"):
            parse_copy_file(f"---\ntype: project\nmatch: x\n{key}: y\n---\nbody")


def test_type_must_be_known():
    with pytest.raises(CopyError, match="type"):
        parse_copy_file("---\ntype: page\nmatch: x\n---\nbody")


def test_summary_longer_than_320_is_an_error():
    with pytest.raises(CopyError, match="320"):
        parse_copy_file("---\ntype: project\nmatch: x\nsummary: " + "a" * 321 + "\n---\nbody")


def test_trailing_comment_is_stripped_but_hash_in_value_is_kept():
    doc = parse_copy_file(
        "---\ntype: project\nmatch: x  # the slug\ntitle: C# Developer\n"
        "role: Dev  # comment\n---\nbody"
    )

    assert doc.match == "x"
    assert doc.fields == {"title": "C# Developer", "role": "Dev"}


def _doc(extra, kind="project"):
    return f"---\ntype: {kind}\nmatch: x\n{extra}\n---\nbody"


def test_empty_title_and_project_summary_are_rejected():
    with pytest.raises(CopyError, match="title must not be empty"):
        parse_copy_file(_doc("title:"))
    with pytest.raises(CopyError, match="summary must not be empty"):
        parse_copy_file(_doc("summary:"))


def test_empty_experience_summary_is_allowed():
    doc = parse_copy_file(_doc("summary:", kind="experience"))

    assert doc.fields == {"summary": ""}


@pytest.mark.parametrize(
    ("kind", "field_name", "limit"),
    [
        ("project", "title", 160),
        ("blog", "title", 180),
        ("project", "summary", 320),
        ("project", "role", 120),
        ("project", "stack", 240),
        ("project", "year", 20),
        ("project", "result_headline", 240),
        ("project", "seo_title", 180),
        ("project", "seo_description", 320),
    ],
)
def test_over_length_values_name_the_field(kind, field_name, limit):
    parse_copy_file(_doc(f"{field_name}: " + "a" * limit, kind))

    with pytest.raises(CopyError, match=f"{field_name}.*{limit}"):
        parse_copy_file(_doc(f"{field_name}: " + "a" * (limit + 1), kind))


def test_crlf_text_parses():
    doc = parse_copy_file("---\r\ntype: project\r\nmatch: x\r\nsummary: S\r\n---\r\nBody\r\n")

    assert doc.fields == {"summary": "S"} and doc.body == "Body\n"
