"""Validation infrastructure for Odoo module quality checks."""

from odoo_gen_utils.validation.pylint_runner import parse_pylint_output  # noqa: F401
from odoo_gen_utils.validation.pylint_runner import run_pylint_odoo  # noqa: F401
from odoo_gen_utils.validation.report import format_report_json  # noqa: F401
from odoo_gen_utils.validation.report import format_report_markdown  # noqa: F401
from odoo_gen_utils.validation.types import InstallResult  # noqa: F401
from odoo_gen_utils.validation.types import TestResult  # noqa: F401
from odoo_gen_utils.validation.types import ValidationReport  # noqa: F401
from odoo_gen_utils.validation.types import Violation  # noqa: F401

__all__ = [
    "InstallResult",
    "TestResult",
    "ValidationReport",
    "Violation",
    "format_report_json",
    "format_report_markdown",
    "parse_pylint_output",
    "run_pylint_odoo",
]
