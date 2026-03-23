"""Helpers for running package-backed scripts directly from the repo root."""

from pathlib import Path
import sys


def bootstrap_project_root() -> None:
    """Add the project root to sys.path for `python scripts/<name>.py` runs."""
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
