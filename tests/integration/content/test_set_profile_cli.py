from __future__ import annotations

from sqlalchemy import select

from portfolio.content.models import SiteProfile


def test_set_profile_updates_only_given_fields(app, db_session):
    db_session.add(SiteProfile(email="a@example.test"))
    db_session.commit()

    result = app.test_cli_runner().invoke(
        args=[
            "content",
            "set-profile",
            "--linkedin",
            "https://www.linkedin.com/in/x",
            "--availability",
            "Open to roles",
        ]
    )

    assert result.exit_code == 0, result.output
    profile = db_session.scalar(select(SiteProfile))
    db_session.refresh(profile)
    assert profile.linkedin_url == "https://www.linkedin.com/in/x"
    assert profile.availability_text == "Open to roles"
    assert profile.github_url is None
    assert profile.email == "a@example.test"


def test_set_profile_rejects_non_https_links(app, db_session):
    db_session.add(SiteProfile())
    db_session.commit()

    result = app.test_cli_runner().invoke(
        args=["content", "set-profile", "--github", "javascript:alert(1)"]
    )

    assert result.exit_code != 0


def test_set_profile_empty_string_clears_field(app, db_session):
    db_session.add(SiteProfile(github_url="https://github.com/x"))
    db_session.commit()

    result = app.test_cli_runner().invoke(args=["content", "set-profile", "--github", ""])

    assert result.exit_code == 0, result.output
    profile = db_session.scalar(select(SiteProfile))
    db_session.refresh(profile)
    assert profile.github_url is None
