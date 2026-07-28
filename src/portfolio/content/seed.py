from __future__ import annotations

import click

from portfolio.content.enums import PublicationState
from portfolio.content.models import Credential, Education, Experience, Project, SiteProfile
from portfolio.content.rendering import render_markdown
from portfolio.extensions import db


@click.group("content")
def content_cli() -> None:
    """Content management commands."""


@content_cli.command("seed-initial")
def seed_initial_command() -> None:
    created = seed_initial_content()
    click.echo(f"seeded {created} records")


def seed_initial_content() -> int:
    if db.session.query(SiteProfile).first() is not None:
        return 0

    records: list[object] = [
        SiteProfile(
            display_name="Jeremy Guill",
            headline="I build practical software for real-world problems.",
            summary=(
                "Technology professional with experience across custom software, database "
                "workflows, technical support, business operations, and customer service."
            ),
            email="rbtm2006@me.com",
            location="Dallas, Oregon",
        ),
        Project(
            title="Pollywog scheduling automation",
            slug="pollywog-scheduling-automation",
            summary=(
                "A Microsoft Access scheduling tool that imported TripLink CSV data "
                "and generated driver schedules."
            ),
            source_markdown=(
                "Built a Microsoft Access scheduling tool to import TripLink CSV exports, "
                "structure trip data, and generate driver schedules for dispatcher review. "
                "The workflow reduced nightly scheduling preparation from about four hours "
                "to about thirty minutes and improved automated schedule-placement accuracy "
                "from about 75% to about 93% over three years."
            ),
            rendered_html=render_markdown(
                "Built a Microsoft Access scheduling tool to import TripLink CSV exports, "
                "structure trip data, and generate driver schedules for dispatcher review."
            ),
            state=PublicationState.PUBLISHED,
            featured=True,
            sort_position=1,
        ),
        Project(
            title="TRIO lending library system",
            slug="trio-lending-library-system",
            summary=(
                "A lending-library check-in and check-out software system for "
                "resource tracking."
            ),
            source_markdown=(
                "Developed and built a custom lending library check-in and check-out software "
                "system to streamline resource tracking for Western Oregon University TRIO."
            ),
            rendered_html=render_markdown(
                "Developed and built a custom lending library check-in and check-out "
                "software system."
            ),
            state=PublicationState.PUBLISHED,
            featured=True,
            sort_position=2,
        ),
        Project(
            title="FileMaker authorization workflow",
            slug="filemaker-authorization-workflow",
            summary=(
                "A FileMaker workflow that automated credit-card authorization list "
                "preparation and receipt matching."
            ),
            source_markdown=(
                "Developed a custom FileMaker program at Salem Communications that automated "
                "the credit card authorization workflow and reduced processing time by "
                "approximately ten minutes per authorization."
            ),
            rendered_html=render_markdown(
                "Developed a custom FileMaker program that automated the credit card "
                "authorization workflow."
            ),
            state=PublicationState.PUBLISHED,
            featured=True,
            sort_position=3,
        ),
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            summary=(
                "Managed end-to-end business operations and developed custom software "
                "to track market applications, company finances, and profits."
            ),
            start_date="November 2024",
            end_date="Present",
            sort_position=1,
        ),
        Experience(
            organization="Western Oregon University TRIO",
            role="Front Desk Student Worker",
            summary=(
                "Built lending library software, improved handover logs, and supported "
                "student-facing daily operations."
            ),
            start_date="October 2025",
            end_date="January 2026",
            sort_position=2,
        ),
        Experience(
            organization="Willamette Valley Transportation",
            role="Driver / Office Assistant",
            summary=(
                "Built and maintained Pollywog scheduling automation, trained staff, "
                "and improved route assignment workflows."
            ),
            start_date="October 2008",
            end_date="June 2014",
            sort_position=3,
        ),
        Education(
            institution="Western Oregon University",
            program="Bachelor's degree in Information Systems",
            details=(
                "Focused on systems, business logic, and database workflows. "
                "Expected June 2026."
            ),
            sort_position=1,
        ),
        Education(
            institution="Chemeketa Community College",
            program="Associate's Degree in Computer Information Systems",
            details="Coursework in computer systems and information technology. June 2024.",
            sort_position=2,
        ),
        Credential(name="iOS Certified", issuer="Apple Certification", sort_position=1),
    ]
    db.session.add_all(records)
    db.session.commit()
    return len(records)
