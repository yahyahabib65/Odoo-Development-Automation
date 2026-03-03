"""Public API for the OCA module search package."""

from odoo_gen_utils.search.index import (  # noqa: F401
    build_oca_index,
    get_github_token,
    get_index_status,
)
from odoo_gen_utils.search.query import (  # noqa: F401
    SearchResult,
    format_results_json,
    format_results_text,
    search_modules,
)
from odoo_gen_utils.search.types import IndexEntry, IndexStatus  # noqa: F401

__all__ = [
    "build_oca_index",
    "get_github_token",
    "get_index_status",
    "IndexEntry",
    "IndexStatus",
    "SearchResult",
    "format_results_json",
    "format_results_text",
    "search_modules",
]
