"""Repository-wide pytest setup."""

from pathlib import Path


def pytest_configure() -> None:
    # pytest's --basetemp (see pyproject) does not create missing parent directories.
    Path(".tmp").mkdir(exist_ok=True)
