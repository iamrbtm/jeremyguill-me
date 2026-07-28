from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from portfolio.content.enums import PublicationState
from portfolio.content.models import (
    BlogPost,
    Credential,
    Education,
    Experience,
    Project,
    SiteProfile,
)
from portfolio.extensions import db


@dataclass(frozen=True)
class CapabilityView:
    title: str
    body: str


@dataclass(frozen=True)
class HomeView:
    profile: SiteProfile
    capabilities: list[CapabilityView]
    featured_projects: list[Project]
    experience: list[Experience]
    education: list[Education]
    credentials: list[Credential]
    show_blog: bool


def get_profile() -> SiteProfile:
    profile = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
    if profile is None:
        return SiteProfile()
    return profile


def build_home_view() -> HomeView:
    featured_projects = db.session.execute(
        select(Project)
        .where(Project.state == PublicationState.PUBLISHED, Project.featured.is_(True))
        .order_by(Project.sort_position, Project.title)
    ).scalars().all()
    experience = db.session.execute(
        select(Experience).where(Experience.visible.is_(True)).order_by(Experience.sort_position)
    ).scalars().all()
    education = db.session.execute(
        select(Education).where(Education.visible.is_(True)).order_by(Education.sort_position)
    ).scalars().all()
    credentials = db.session.execute(
        select(Credential).where(Credential.visible.is_(True)).order_by(Credential.sort_position)
    ).scalars().all()
    show_blog = (
        db.session.execute(select(BlogPost.id).where(BlogPost.state == PublicationState.PUBLISHED))
        .first()
        is not None
    )
    return HomeView(
        profile=get_profile(),
        capabilities=[
            CapabilityView(
                "Software that fits the workflow",
                "Custom tools, databases, and automations shaped around real operational steps.",
            ),
            CapabilityView(
                "Database-backed operations",
                "Structured records, reporting needs, and repeatable business processes "
                "made easier to run.",
            ),
            CapabilityView(
                "Implementation and support",
                "Clear requirements, practical rollouts, user training, troubleshooting, "
                "and iteration.",
            ),
        ],
        featured_projects=list(featured_projects),
        experience=list(experience),
        education=list(education),
        credentials=list(credentials),
        show_blog=show_blog,
    )
