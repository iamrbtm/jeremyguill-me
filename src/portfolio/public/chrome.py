from __future__ import annotations

from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import BlogPost, SiteProfile
from portfolio.extensions import db


class SiteChrome:
    """Per-request data every public page needs. Every property fails soft."""

    @cached_property
    def show_blog(self) -> bool:
        try:
            return (
                db.session.execute(
                    select(BlogPost.id).where(BlogPost.state == PublicationState.PUBLISHED).limit(1)
                ).first()
                is not None
            )
        except Exception:
            db.session.rollback()
            return False

    @cached_property
    def profile(self) -> SiteProfile:
        try:
            found = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
        except Exception:
            db.session.rollback()
            found = None
        return found or SiteProfile(display_name="Jeremy Guill")

    @cached_property
    def has_resume(self) -> bool:
        return (Path(current_app.static_folder or "") / "resume" / "Resume2026.pdf").is_file()

    @cached_property
    def has_portrait(self) -> bool:
        return (
            Path(current_app.static_folder or "") / "assets" / "img" / "jeremyguill_profile.webp"
        ).is_file()

    @cached_property
    def analytics(self) -> dict[str, str] | None:
        url = (current_app.config.get("ANALYTICS_SCRIPT_URL") or "").strip()
        site_id = (current_app.config.get("ANALYTICS_WEBSITE_ID") or "").strip()
        if not site_id:
            return None
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        return {"script_url": url, "website_id": site_id}

    @cached_property
    def year(self) -> int:
        return datetime.now(UTC).year
