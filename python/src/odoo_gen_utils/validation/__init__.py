"""Validation infrastructure for Odoo module quality checks."""

from odoo_gen_utils.validation.docker_runner import (
    check_docker_available,
    docker_install_module,
    docker_run_tests,
    get_compose_file,
)
from odoo_gen_utils.validation.log_parser import (
    extract_traceback,
    parse_install_log,
    parse_test_log,
)
from odoo_gen_utils.validation.types import (
    InstallResult,
    TestResult,
    ValidationReport,
    Violation,
)

__all__ = [
    "InstallResult",
    "TestResult",
    "ValidationReport",
    "Violation",
    "check_docker_available",
    "docker_install_module",
    "docker_run_tests",
    "extract_traceback",
    "get_compose_file",
    "parse_install_log",
    "parse_test_log",
]
