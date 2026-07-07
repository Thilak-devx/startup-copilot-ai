"""Shared report path, naming, and cache helpers."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

REPORT_BASENAME_SUFFIX = "_report"
REPORT_SUFFIXES = frozenset({".md", ".pdf"})


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    configured = os.environ.get("STARTUP_COPILOT_DB")
    return Path(configured).expanduser() if configured else project_root() / "startup_copilot.db"


def get_outputs_dir() -> Path:
    configured = os.environ.get("STARTUP_COPILOT_OUTPUTS_DIR")
    return Path(configured).expanduser() if configured else project_root() / "outputs"


def report_slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_").lower()
    return slug or "startup"


def report_filename(startup_name: str, suffix: str = ".md") -> str:
    if suffix not in REPORT_SUFFIXES:
        raise ValueError(f"Unsupported report suffix: {suffix}")
    return f"{report_slug(startup_name)}{REPORT_BASENAME_SUFFIX}{suffix}"


def startup_slug_from_report_filename(filename: str) -> str:
    stem = Path(filename).stem
    if stem.endswith(REPORT_BASENAME_SUFFIX):
        stem = stem[: -len(REPORT_BASENAME_SUFFIX)]
    return report_slug(stem)


def safe_report_path(
    outputs_dir: Path,
    filename: str,
    allowed_suffixes: frozenset[str] = REPORT_SUFFIXES,
) -> Path:
    safe_name = Path(filename).name
    candidate = (outputs_dir / safe_name).resolve()
    outputs_root = outputs_dir.resolve()

    if candidate.suffix not in allowed_suffixes:
        raise ValueError(f"Unsupported report suffix: {candidate.suffix}")
    try:
        candidate.relative_to(outputs_root)
    except ValueError as exc:
        raise ValueError("Report path resolves outside the outputs directory.") from exc

    return candidate


def resolve_markdown_path(markdown_path: str | Path, outputs_dir: Path) -> Path:
    candidate = Path(markdown_path)
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return safe_report_path(outputs_dir, candidate.name, frozenset({".md"}))


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def is_pdf_current(markdown_path: Path, pdf_path: Path) -> bool:
    return (
        pdf_path.exists()
        and markdown_path.exists()
        and pdf_path.stat().st_mtime_ns >= markdown_path.stat().st_mtime_ns
    )
