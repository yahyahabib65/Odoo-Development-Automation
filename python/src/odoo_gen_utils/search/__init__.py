"""Public API for the OCA module search package."""

from odoo_gen_utils.search.index import (  # noqa: F401
    build_oca_index,
    get_github_token,
    get_index_status,
)
from odoo_gen_utils.search.types import IndexEntry, IndexStatus  # noqa: F401

__all__ = [
    "build_oca_index",
    "get_github_token",
    "get_index_status",
    "IndexEntry",
    "IndexStatus",
]
