"""Prevent pytest from collecting Odoo module fixture files.

The fixtures/docker_test_module/ directory contains a real Odoo module
that requires the Odoo runtime to import. These files are NOT pytest
test modules — they are test fixtures for Docker integration tests.
"""

collect_ignore_glob = ["docker_test_module/**/*.py"]
