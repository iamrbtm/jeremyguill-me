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
    home_projects: list[Project]
    has_more_projects: bool
    experience: list[Experience]
    education: list[Education]
    credentials: list[Credential]
    show_blog: bool
    blog_posts: list[BlogPost]


def published_projects() -> list[Project]:
    return list(
        db.session.execute(
            select(Project)
            .where(Project.state == PublicationState.PUBLISHED)
            .order_by(Project.sort_position, Project.title)
        ).scalars()
    )


def get_profile() -> SiteProfile:
    profile = db.session.execute(select(SiteProfile).limit(1)).scalar_one_or_none()
    if profile is None:
        return SiteProfile()
    return profile


def build_home_view() -> HomeView:
    all_projects = published_projects()
    home_projects = all_projects[:3]
    experience = (
        db.session.execute(
            select(Experience)
            .where(Experience.visible.is_(True))
            .order_by(Experience.sort_position)
        )
        .scalars()
        .all()
    )
    education = (
        db.session.execute(
            select(Education).where(Education.visible.is_(True)).order_by(Education.sort_position)
        )
        .scalars()
        .all()
    )
    credentials = (
        db.session.execute(
            select(Credential)
            .where(Credential.visible.is_(True))
            .order_by(Credential.sort_position)
        )
        .scalars()
        .all()
    )
    show_blog = (
        db.session.execute(
            select(BlogPost.id).where(BlogPost.state == PublicationState.PUBLISHED)
        ).first()
        is not None
    )
    blog_posts: list[BlogPost] = []
    if show_blog:
        blog_posts = list(
            db.session.execute(
                select(BlogPost)
                .where(BlogPost.state == PublicationState.PUBLISHED)
                .order_by(BlogPost.published_at.desc(), BlogPost.title)
                .limit(3)
            ).scalars()
        )
    return HomeView(
        profile=get_profile(),
        capabilities=[
            CapabilityView(
                "Workflow-aware software",
                "Custom tools and automations shaped around real operational steps, constraints, and users.",
            ),
            CapabilityView(
                "Database-backed operations",
                "Structured records, reporting needs, and repeatable processes made easier to run and review.",
            ),
            CapabilityView(
                "Implementation mindset",
                "Requirements, practical rollouts, user training, troubleshooting, and iteration after launch.",
            ),
        ],
        home_projects=list(home_projects),
        has_more_projects=len(all_projects) > len(home_projects),
        experience=list(experience),
        education=list(education),
        credentials=list(credentials),
        show_blog=show_blog,
        blog_posts=blog_posts,
    )
