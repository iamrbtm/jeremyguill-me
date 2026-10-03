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
