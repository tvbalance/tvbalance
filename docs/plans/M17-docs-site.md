# M17: Documentation site and user guide in five languages

Status: done.

## Goal
Spec: a multilingual user guide, per-brand guides, troubleshooting, FAQ and an adapter contributor guide, published
as a site. The site is built in CI on every push; publishing to GitHub Pages happens only at release or by hand,
because the repository is still private.

## Decisions
- MkDocs Material 9.x with `mkdocs-static-i18n` (suffix layout: `page.md`, `page.it.md`, ...), English as the
  default and fallback, a language switcher and per-language search.
- Pinned in a root `docs` dependency group. Nothing from the site is shipped in the Engine, Add-on or client.
- Internal folders (`plans/`, `discovery/`, `product/`, `operations/`) are excluded from the build. `architecture/`
  is published under "Developers", English only.
- User pages (home and `user-guide/`) are translated into it, de, fr and es. Developer pages stay English.
- `scripts/check_docs_i18n.py` fails when a user page lacks a translation, when a translation has no English
  source, or when the heading structure differs from the source.
- Facts (ports, image name, options, SDK names) are taken from the code, and UI wording from the `web/` locales.

## Steps
1. This plan.
2. Toolchain: `docs` group, `mkdocs.yml`, home page; `mkdocs build --strict` passes.
3. `check_docs_i18n` test first, then the script; `docs.yml` builds on push and pull request.
4. Install and getting-started pages.
5. Troubleshooting and FAQ.
6. Adapter contributor guide and API reference (the hook copies `engine/openapi.json` into the site).
7. to 10. Translations, one language per commit (it, de, fr, es).
11. Pages deploy job (manual and tags), release checklist, links from README and Add-on docs, mark done.

## Out of scope
A help link inside the web UI, a custom domain, versioned docs, screenshots.

## Verification
- `check_docs_i18n` and its test pass, the full test suite stays green, `ruff` is clean.
- `mkdocs build --strict` has no warnings, all five languages switch, internal folders are absent from `site/`.
- CI and the Docs workflow are green; the deploy job does not run on push.
