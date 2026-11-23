"""Every user page exists in all five languages with the same heading structure."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_docs_i18n", ROOT / "scripts/check_docs_i18n.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load()
LANGS = ("it", "de")


def _write(root: Path, name: str, text: str) -> None:
    path = root / "docs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


def test_the_repository_docs_are_consistent() -> None:
    assert check.problems(ROOT) == []


def test_complete_translations_pass(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", "# Home\n\n## One\n")
    _write(tmp_path, "index.it.md", "# Casa\n\n## Uno\n")
    _write(tmp_path, "index.de.md", "# Start\n\n## Eins\n")
    assert check.problems(tmp_path, LANGS, pending=frozenset()) == []


def test_a_missing_translation_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "user-guide/pro.md", "# Pro\n")
    _write(tmp_path, "user-guide/pro.it.md", "# Pro\n")
    found = check.problems(tmp_path, LANGS, pending=frozenset())
    assert found == ["user-guide/pro.de.md is missing"]


def test_a_pending_language_may_be_missing(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", "# Home\n")
    _write(tmp_path, "index.it.md", "# Casa\n")
    assert check.problems(tmp_path, LANGS, pending=frozenset({"de"})) == []


def test_a_translation_without_a_source_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "user-guide/old.it.md", "# Vecchio\n")
    found = check.problems(tmp_path, LANGS, pending=frozenset({"de"}))
    assert found == ["user-guide/old.it.md has no English source user-guide/old.md"]


def test_a_different_heading_structure_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", "# Home\n\n## One\n\n## Two\n")
    _write(tmp_path, "index.it.md", "# Casa\n\n## Uno\n")
    found = check.problems(tmp_path, LANGS, pending=frozenset({"de"}))
    assert found == ["index.it.md has headings [1, 2] but index.md has [1, 2, 2]"]


def test_headings_inside_code_fences_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", "# Home\n\n```\n# not a heading\n```\n")
    _write(tmp_path, "index.it.md", "# Casa\n")
    assert check.problems(tmp_path, ("it",), pending=frozenset()) == []


def test_developer_pages_need_no_translation(tmp_path: Path) -> None:
    _write(tmp_path, "developers/adapters.md", "# Adapters\n")
    _write(tmp_path, "architecture/api.md", "# API\n")
    assert check.problems(tmp_path, LANGS, pending=frozenset()) == []
