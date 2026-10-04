# Experience Layout Consolidation Design

## Goal

Remove the duplicated experience listing from the homepage `About` section and make the dedicated `/experience` page the single place where experience entries are displayed. Restyle the `/experience` page so each entry uses the same compact `mini-timeline` presentation pattern currently used on the homepage.

## Scope

- Remove homepage experience cards from `src/portfolio/templates/public/home.html`.
- Keep the homepage `About` section as copy-only content.
- Replace the current `/experience` page entry markup with the `mini-timeline` card structure.
- Reuse the existing approved timeline header pattern on `/experience`:
  - date
  - role
  - organization
  - optional right-aligned logo at `100px` height
- Update CSS so the `mini-timeline` component works cleanly on the dedicated experience page in a single-column stack.
- Update integration tests to reflect the moved content and new canonical rendering location.

## Non-Goals

- No content model changes.
- No changes to admin experience editing.
- No changes to project, education, or credential layouts.
- No new homepage replacement section beyond removing the experience cards.

## Template Changes

### Homepage

The homepage `About` band currently combines intro copy with two timeline columns. That duplication will be removed entirely. The section will render only the introductory copy block so the page keeps the existing voice and spacing without repeating experience content already available on `/experience`.

### Experience Page

Each experience entry on `/experience` will adopt the `mini-timeline` card structure already preferred by the user:

- outer `article.mini-timeline`
- `header.mini-timeline-header`
- `div.mini-timeline-copy` containing date, role, and organization
- optional `img.mini-timeline-logo` with `height="100"`
- existing summary and rendered markdown below the header

This keeps a single canonical presentation for experience items while preserving the richer detail already shown on the dedicated page.

## Styling Changes

The current `/experience` page uses the older `timeline-item`, `timeline-header`, and `timeline-logo` styles. The page will instead use the `mini-timeline` styles already present in `site.css`.

Additional CSS will be limited to page-level layout for the dedicated experience list:

- a single-column stack for entries
- consistent spacing between `mini-timeline` cards
- no duplicate visual rules when the shared `mini-timeline` classes already solve the problem

The existing small-screen behavior for `mini-timeline-header` will remain in place so the logo drops below or beside the text naturally on narrow widths.

## Testing

The regression surface is public HTML rendering.

- Update the homepage integration tests so they no longer expect experience timeline markup on `/`.
- Add or update an experience-page integration test that proves the preferred `mini-timeline` structure renders on `/experience`, including the `100px` logo height and the presence of date, role, and organization in the header block.

## Risks and Mitigation

### Risk: Homepage spacing looks sparse after removing experience cards

Mitigation: keep the `About` intro intact and only make the smallest layout adjustment necessary if the section collapses awkwardly.

### Risk: Two different timeline style systems remain in CSS

Mitigation: move `/experience` onto the `mini-timeline` system and avoid expanding the legacy timeline rules further.

## Acceptance Criteria

- The homepage no longer renders experience entries in the `About` section.
- The `/experience` page becomes the only public page showing the experience list.
- `/experience` uses the compact `mini-timeline` card layout rather than the old timeline layout.
- Experience logos on `/experience` render at `100px` height with automatic width.
- Public integration tests cover the moved rendering location and pass.
