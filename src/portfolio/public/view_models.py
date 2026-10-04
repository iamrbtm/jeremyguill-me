from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select

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
from portfolio.media.models import MediaAsset


@dataclass(frozen=True)
class CapabilityView:
    title: str
    body: str


@dataclass(frozen=True)
class ProjectCardView:
    slug: str
    title: str
    summary: str
    year: str | None
    stack: list[str]
    result_headline: str | None
    hero_media_id: uuid.UUID | None
    hero_alt: str


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
    home_project_cards: list[ProjectCardView] = field(default_factory=list)
    show_blog_section: bool = False


def build_project_cards(projects: list[Project]) -> list[ProjectCardView]:
    ids = [p.hero_media_id for p in projects if p.hero_media_id]
    alts: dict[uuid.UUID, str] = {}
    if ids:
        rows = db.session.execute(
            select(MediaAsset.id, MediaAsset.alt_text).where(MediaAsset.id.in_(ids))
        ).all()
        alts = {row.id: row.alt_text for row in rows}
    return [
        ProjectCardView(
            slug=p.slug,
            title=p.title,
            summary=p.summary,
            year=p.year,
            stack=p.stack_list,
            result_headline=p.result_headline,
            hero_media_id=p.hero_media_id,
            hero_alt=(alts.get(p.hero_media_id) if p.hero_media_id else None)
            or f"{p.title} project preview",
        )
        for p in projects
    ]


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


def default_capabilities() -> list[CapabilityView]:
    return [
        CapabilityView(
            "Workflow-aware software",
            "Custom tools and automations shaped around real operational steps, "
            "constraints, and users.",
        ),
        CapabilityView(
            "Database-backed operations",
            "Structured records, reporting needs, and repeatable processes made easier "
            "to run and review.",
        ),
        CapabilityView(
            "Implementation mindset",
            "Requirements, practical rollouts, user training, troubleshooting, and "
            "iteration after launch.",
        ),
    ]


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
    published_posts = (
        db.session.scalar(
            select(func.count())
            .select_from(BlogPost)
            .where(BlogPost.state == PublicationState.PUBLISHED)
        )
        or 0
    )
    return HomeView(
        profile=get_profile(),
        capabilities=default_capabilities(),
        home_projects=list(home_projects),
        has_more_projects=len(all_projects) > len(home_projects),
        experience=list(experience),
        education=list(education),
        credentials=list(credentials),
        show_blog=show_blog,
        blog_posts=blog_posts,
        home_project_cards=build_project_cards(list(home_projects)),
        show_blog_section=published_posts >= 3,
    )
