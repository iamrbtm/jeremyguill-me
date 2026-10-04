from __future__ import annotations

import pytest

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, Project


@pytest.fixture
def no_home_view(monkeypatch):
    def boom():
        raise AssertionError("build_home_view must not run for this route")

    monkeypatch.setattr("portfolio.public.view_models.build_home_view", boom)
    monkeypatch.setattr("portfolio.public.routes.build_home_view", boom)


def test_routes_that_do_not_read_the_home_view_do_not_build_it(client, db_session, no_home_view):
    db_session.add(
        Project(title="Alpha", slug="alpha", summary="S.", rendered_html="<p>x</p>",
                state=PublicationState.PUBLISHED, sort_position=1)
    )
    db_session.add(
        BlogPost(title="Post", slug="post", summary="S.", rendered_html="<p>b</p>",
                 state=PublicationState.PUBLISHED)
    )
    db_session.commit()

    assert b"Alpha" in client.get("/work").data
    assert client.get("/work/alpha").status_code == 200
    assert client.get("/contact").status_code == 200
    assert b"Post" in client.get("/blog").data
    assert client.get("/blog/post").status_code == 200
    invalid = client.post("/contact", data={})
    assert invalid.status_code == 422
