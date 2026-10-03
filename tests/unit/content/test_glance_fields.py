from __future__ import annotations

from portfolio.admin.forms import ProjectForm
from portfolio.content.models import Project


def test_stack_list_splits_and_trims():
    project = Project(stack=" Flask, PostgreSQL ,, Docker ")
    assert project.stack_list == ["Flask", "PostgreSQL", "Docker"]
    assert Project(stack=None).stack_list == []


def test_project_form_reads_glance_fields():
    form = ProjectForm.from_mapping(
        {
            "title": "T",
            "slug": "t",
            "version": "1",
            "role": "Creator & Developer",
            "stack": "Next.js, SQL",
            "year": "2025",
            "result_headline": "Resume creation became consistent",
        }
    )

    assert (form.role, form.stack, form.year) == ("Creator & Developer", "Next.js, SQL", "2025")
    assert form.result_headline == "Resume creation became consistent"
    assert form.validate()


def test_project_form_rejects_overlong_glance_fields():
    form = ProjectForm.from_mapping({"title": "T", "slug": "t", "version": "1", "role": "x" * 121})

    assert not form.validate()
    assert "role" in form.errors
