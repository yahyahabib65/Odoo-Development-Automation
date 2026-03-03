"""Stub index module — will be implemented in GREEN phase."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "odoo-gen" / "chromadb"


def get_github_token() -> str | None:
    raise NotImplementedError


def _parse_manifest_safe(content: str) -> dict | None:
    raise NotImplementedError


def _build_document_text(manifest: dict, module_name: str) -> str:
    raise NotImplementedError


def build_oca_index(
    token: str,
    db_path: str,
    incremental: bool = False,
    progress_callback: Callable | None = None,
) -> int:
    raise NotImplementedError


def get_index_status(db_path: str | None = None) -> "IndexStatus":
    raise NotImplementedError
