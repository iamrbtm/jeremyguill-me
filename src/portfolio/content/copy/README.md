# Owner-reviewed copy files

Every file here is reviewed by the owner before it is applied. Always run with
`--dry-run` first:

    flask --app portfolio content apply-copy --dry-run
    flask --app portfolio content apply-copy

With no paths, every `*.md` in this directory except `README.md` is applied. The run is
all-or-nothing: any error rolls back every file. Applying an unchanged file is a no-op.

## Format

    ---
    type: project            # project | blog | experience
    match: pollywog-scheduling-automation   # project/blog: slug; experience: "Organization | Role"
    title: Pollywog scheduling automation   # optional (project/blog)
    summary: One sentence, 320 characters or fewer   # optional
    role: Developer          # optional, project only
    stack: Microsoft Access, TripLink CSV   # optional, project only
    year: 2012–2014          # optional, project only
    result_headline: Prep time 4 h → 30 min # optional, project only
    seo_title: ...           # optional (project/blog)
    seo_description: ...     # optional (project/blog)
    ---
    Markdown body (becomes source_markdown and is rendered to HTML).

Trailing comments start with two spaces then `#`. Unknown fields are rejected; `slug`,
`state` and `published_at` can never be set from a copy file.

## Empty values and limits

- `title` and `summary` cannot be empty for projects and blog posts.
- For the optional project fields (`role`, `stack`, `year`, `result_headline`, `seo_title`,
  `seo_description`) and blog `seo_*` fields, an empty value clears the field (stored as NULL).
- Experience `summary` may be empty.
- Values longer than the column limit are rejected, naming the field and limit.
- Files may use CRLF line endings and a UTF-8 BOM; errors are prefixed with the file name.
