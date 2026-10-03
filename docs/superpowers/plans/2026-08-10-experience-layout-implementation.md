# Experience Layout Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove duplicated experience entries from the homepage and make `/experience` the single public location for experience content, using the preferred compact `mini-timeline` card layout there.

**Architecture:** Keep the public data flow unchanged by reusing `build_home_view()` and only changing template structure plus shared site CSS. Move the preferred `mini-timeline` presentation from the homepage preview into the dedicated experience page, and update the public integration tests so the canonical rendering location is `/experience`.

**Tech Stack:** Flask, Jinja templates, shared site CSS, pytest integration tests, uv

## Global Constraints

- Remove homepage experience cards from `src/portfolio/templates/public/home.html`.
- Keep the homepage `About` section as copy-only content.
- Replace the current `/experience` page entry markup with the `mini-timeline` card structure.
- Reuse the existing approved timeline header pattern on `/experience`: date, role, organization, optional right-aligned logo at `100px` height.
- Update CSS so the `mini-timeline` component works cleanly on the dedicated experience page in a single-column stack.
- Update integration tests to reflect the moved content and new canonical rendering location.
- No content model changes.
- No changes to admin experience editing.
- No changes to project, education, or credential layouts.
- No new homepage replacement section beyond removing the experience cards.

---

### Task 1: Move the Canonical Experience Rendering Surface Into `/experience`

**Files:**
- Modify: `tests/integration/public/test_public_pages.py`
- Modify: `src/portfolio/templates/public/home.html`
- Modify: `src/portfolio/templates/public/experience.html`
- Modify: `src/portfolio/static/assets/site.css`
- Test: `tests/integration/public/test_public_pages.py`

**Interfaces:**
- Consumes: `public_bp.get("/")`, `public_bp.get("/experience")`, `build_home_view() -> HomeView`
- Produces: homepage HTML with no `mini-timeline-header` markup, and experience-page HTML where each entry renders as `article.mini-timeline > header.mini-timeline-header` with optional `img.mini-timeline-logo[height="100"]`

- [ ] **Step 1: Write the failing tests**

```python
def test_homepage_about_section_does_not_render_experience_cards(client, db_session):
    db_session.add(SiteProfile())
    logo = MediaAsset(
        original_filename="dudefish.png",
        storage_key="test/dudefish.png",
        mime_type="image/png",
        byte_size=1,
        alt_text="Dudefish Printing logo",
        private=False,
    )
    db_session.add(logo)
    db_session.flush()
    db_session.add(
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            start_date="November 2024",
            end_date="Present",
            sort_position=1,
            logo_media_id=logo.id,
        )
    )
    db_session.commit()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="mini-timeline-header"' not in html
    assert "Owner Operator" not in html
    assert "Dudefish Printing" not in html


def test_experience_page_uses_mini_timeline_layout_with_100px_logo(client, db_session):
    db_session.add(SiteProfile())
    logo = MediaAsset(
        original_filename="dudefish.png",
        storage_key="test/dudefish.png",
        mime_type="image/png",
        byte_size=1,
        alt_text="Dudefish Printing logo",
        private=False,
    )
    db_session.add(logo)
    db_session.flush()
    db_session.add(
        Experience(
            organization="Dudefish Printing",
            role="Owner Operator",
            start_date="November 2024",
            end_date="Present",
            sort_position=1,
            logo_media_id=logo.id,
            summary="Managed business operations and custom software.",
        )
    )
    db_session.commit()

    response = client.get("/experience")
    html = response.get_data(as_text=True)
    header = re.search(r'<header class="mini-timeline-header">(.*?)</header>', html, re.DOTALL)

    assert response.status_code == 200
    assert header is not None
    assert "November 2024 - Present" in header.group(1)
    assert "Owner Operator" in header.group(1)
    assert "Dudefish Printing" in header.group(1)
    assert 'class="mini-timeline-logo"' in header.group(1)
    assert 'height="100"' in header.group(1)
```

- [ ] **Step 2: Run the targeted tests to verify they fail for the expected reason**

Run: `/bin/bash -lc 'UV_CACHE_DIR=/tmp/jeremyguill-uv-cache uv run pytest -q tests/integration/public/test_public_pages.py -k "homepage_about_section_does_not_render_experience_cards or experience_page_uses_mini_timeline_layout_with_100px_logo"'`

Expected: FAIL because the homepage still renders experience cards and `/experience` still uses the old `timeline-item` markup instead of `mini-timeline-header`.

- [ ] **Step 3: Write the minimal implementation**

```html
<!-- src/portfolio/templates/public/home.html -->
<section id="about" class="about-band bg-gray">
  <div class="container about-grid about-grid--single">
    <div class="about-intro reveal">
      <h2>Hi there, I'm Jeremy.</h2>
      <p>...</p>
    </div>
  </div>
</section>
```

```html
<!-- src/portfolio/templates/public/experience.html -->
<section class="page-section">
  <h1>Experience and technical background</h1>
  <div class="experience-list">
    {% for item in view.experience %}
      <article class="mini-timeline">
        <header class="mini-timeline-header">
          <div class="mini-timeline-copy">
            <p class="time">{{ item.start_date or "Current" }}{% if item.end_date %} - {{ item.end_date }}{% endif %}</p>
            <h3>{{ item.role }}</h3>
            <p>{{ item.organization }}</p>
          </div>
          {% if item.logo_media_id %}
            <img class="mini-timeline-logo" src="/media/public/{{ item.logo_media_id }}/profile.webp" alt="{{ item.organization }} logo" loading="lazy" height="100">
          {% endif %}
        </header>
        {% if item.summary %}
          <p>{{ item.summary }}</p>
        {% endif %}
        {% if item.rendered_html %}
          <div class="mini-timeline-markdown">
            {{ item.rendered_html|safe }}
          </div>
        {% endif %}
      </article>
    {% endfor %}
  </div>
</section>
```

```css
/* src/portfolio/static/assets/site.css */
.about-grid--single {
  grid-template-columns: 1fr;
}

.experience-list {
  display: grid;
  gap: 2.35rem;
  margin-top: 2rem;
}

.experience-list .mini-timeline + .mini-timeline {
  margin-top: 0;
}
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `/bin/bash -lc 'UV_CACHE_DIR=/tmp/jeremyguill-uv-cache uv run pytest -q tests/integration/public/test_public_pages.py -k "homepage_about_section_does_not_render_experience_cards or experience_page_uses_mini_timeline_layout_with_100px_logo"'`

Expected: PASS

- [ ] **Step 5: Run the full public page regression file**

Run: `/bin/bash -lc 'UV_CACHE_DIR=/tmp/jeremyguill-uv-cache uv run pytest -q tests/integration/public/test_public_pages.py'`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/integration/public/test_public_pages.py src/portfolio/templates/public/home.html src/portfolio/templates/public/experience.html src/portfolio/static/assets/site.css docs/superpowers/specs/2026-08-10-experience-layout-design.md docs/superpowers/plans/2026-08-10-experience-layout-implementation.md
git commit -m "feat: consolidate public experience layout"
```
