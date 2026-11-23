"""Check that every user page of the documentation exists in all five languages.

    python scripts/check_docs_i18n.py

User pages are `docs/index.md` and `docs/user-guide/*.md`; translations are siblings named
`<page>.<lang>.md`. A translation must have the same heading levels as its English source, which
catches sections that were added or dropped on one side. Developer pages are English only.

Exits with 1 and prints every problem found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LANGUAGES = ("it", "de", "fr", "es")
# Languages whose translations are still being written; emptied when the last one lands.
PENDING: frozenset[str] = frozenset()

_TRANSLATION = re.compile(r"^(?P<stem>.+)\.(?P<lang>[a-z]{2})\.md$")


def user_pages(root: Path) -> list[Path]:
    """English user pages, relative to `docs/`."""
    docs = root / "docs"
    pages = [Path("index.md")] if (docs / "index.md").exists() else []
    guide = docs / "user-guide"
    if guide.is_dir():
        pages += [
            page.relative_to(docs)
            for page in sorted(guide.glob("*.md"))
            if not _TRANSLATION.match(page.name)
        ]
    return pages


def heading_levels(text: str) -> list[int]:
    levels: list[int] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and (match := re.match(r"(#{1,2}) ", line)):
            levels.append(len(match.group(1)))
    return levels


def translated(page: Path, lang: str) -> Path:
    return page.with_name(f"{page.stem}.{lang}.md")


def problems(
    root: Path,
    languages: tuple[str, ...] = LANGUAGES,
    pending: frozenset[str] = PENDING,
) -> list[str]:
    docs = root / "docs"
    found: list[str] = []
    pages = user_pages(root)
    for page in pages:
        source = heading_levels((docs / page).read_text("utf-8"))
        for lang in languages:
            target = translated(page, lang)
            if not (docs / target).exists():
                if lang not in pending:
                    found.append(f"{target.as_posix()} is missing")
                continue
            levels = heading_levels((docs / target).read_text("utf-8"))
            if levels != source:
                found.append(
                    f"{target.as_posix()} has headings {levels} but {page.as_posix()} has {source}"
                )
    known = set(pages)
    candidates = list(docs.glob("*.md")) + list((docs / "user-guide").glob("*.md"))
    for path in sorted(candidates):
        match = _TRANSLATION.match(path.name)
        if not match or match.group("lang") not in languages:
            continue
        relative = path.relative_to(docs)
        source_page = relative.with_name(f"{match.group('stem')}.md")
        if source_page not in known:
            found.append(f"{relative.as_posix()} has no English source {source_page.as_posix()}")
    return found


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    found = problems(root)
    for line in found:
        print(f"check_docs_i18n: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
