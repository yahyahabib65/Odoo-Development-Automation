"""Tests for Phase 15 Odoo dev instance infrastructure.

Unit tests validate config files and scripts without Docker.
Integration tests (docker-marked) validate the full stack when Docker is available.
"""

from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import pytest

# Project root: two parents up from tests/ dir
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Unit tests: Config file validation (no Docker needed)
# ---------------------------------------------------------------------------


class TestDevInstanceConfig:
    """Validate Docker Compose config, Odoo conf, and .env defaults."""

    def test_compose_file_exists(self) -> None:
        """docker/dev/docker-compose.yml must exist."""
        compose_path = PROJECT_ROOT / "docker" / "dev" / "docker-compose.yml"
        assert compose_path.is_file(), f"Compose file not found at {compose_path}"

    def test_compose_uses_named_volumes(self) -> None:
        """Compose must use named volumes (odoo-dev-db, odoo-dev-data), not tmpfs."""
        compose_path = PROJECT_ROOT / "docker" / "dev" / "docker-compose.yml"
        content = compose_path.read_text()

        assert "odoo-dev-db" in content, "Missing named volume 'odoo-dev-db'"
        assert "odoo-dev-data" in content, "Missing named volume 'odoo-dev-data'"
        assert "tmpfs" not in content, "Dev compose must not use tmpfs (persistent volumes required)"

    def test_compose_separate_from_validation(self) -> None:
        """Dev compose must have name: odoo-dev; validation compose must NOT."""
        dev_compose = PROJECT_ROOT / "docker" / "dev" / "docker-compose.yml"
        val_compose = PROJECT_ROOT / "docker" / "docker-compose.yml"

        dev_content = dev_compose.read_text()
        assert "name: odoo-dev" in dev_content, "Dev compose must declare 'name: odoo-dev'"

        if val_compose.is_file():
            val_content = val_compose.read_text()
            assert "name: odoo-dev" not in val_content, (
                "Validation compose must NOT contain 'name: odoo-dev'"
            )

    def test_compose_healthcheck_uses_python(self) -> None:
        """Healthcheck must use python3 (not curl), since curl may not be in Odoo image."""
        compose_path = PROJECT_ROOT / "docker" / "dev" / "docker-compose.yml"
        content = compose_path.read_text()

        assert "python3 -c" in content, "Healthcheck must use 'python3 -c' (not curl)"
        # Ensure curl is not used in healthcheck section
        lines = content.splitlines()
        in_healthcheck = False
        for line in lines:
            stripped = line.strip()
            if "healthcheck:" in stripped:
                in_healthcheck = True
            elif in_healthcheck and not stripped.startswith(("-", "test:", "interval:", "timeout:", "retries:", "start_period:", '"')):
                in_healthcheck = False
            if in_healthcheck and "curl" in stripped:
                pytest.fail("Healthcheck must not use curl")

    def test_odoo_conf_settings(self) -> None:
        """Odoo conf must have correct db_name, list_db, and admin_passwd settings."""
        conf_path = PROJECT_ROOT / "docker" / "dev" / "odoo.conf"
        content = conf_path.read_text()

        assert "db_name = odoo_dev" in content, "odoo.conf must set db_name = odoo_dev"
        assert "list_db = False" in content, "odoo.conf must set list_db = False"
        assert "admin_passwd = admin" in content, "odoo.conf must set admin_passwd = admin"

    def test_env_file_defaults(self) -> None:
        """docker/dev/.env must contain ODOO_DEV_PORT=8069."""
        env_path = PROJECT_ROOT / "docker" / "dev" / ".env"
        content = env_path.read_text()

        assert "ODOO_DEV_PORT=8069" in content, ".env must set ODOO_DEV_PORT=8069"


# ---------------------------------------------------------------------------
# Unit tests: Management script validation (no Docker needed)
# ---------------------------------------------------------------------------


class TestManagementScript:
    """Validate the management script content and permissions."""

    def test_script_executable(self) -> None:
        """scripts/odoo-dev.sh must have executable permission."""
        script_path = PROJECT_ROOT / "scripts" / "odoo-dev.sh"
        assert script_path.is_file(), f"Script not found at {script_path}"
        assert os.access(script_path, os.X_OK), "odoo-dev.sh must be executable"

    def test_script_uses_run_for_init(self) -> None:
        """_init_modules must use 'run --rm' (not exec) to avoid serialization failures.

        See CLAUDE.md mistake #4: Two Odoo processes on the same DB cause
        psycopg2.errors.SerializationFailure.
        """
        script_path = PROJECT_ROOT / "scripts" / "odoo-dev.sh"
        content = script_path.read_text()

        # Find the _init_modules function body
        lines = content.splitlines()
        in_init = False
        init_body: list[str] = []
        for line in lines:
            if "_init_modules()" in line or "_init_modules ()" in line:
                in_init = True
                continue
            if in_init:
                if line.startswith("}"):
                    break
                init_body.append(line)

        init_text = "\n".join(init_body)
        assert "run --rm" in init_text, (
            "_init_modules must use 'run --rm', not 'exec' (avoids serialization failures)"
        )

    def test_script_has_all_commands(self) -> None:
        """Management script must support start, stop, status, reset, and logs."""
        script_path = PROJECT_ROOT / "scripts" / "odoo-dev.sh"
        content = script_path.read_text()

        required_commands = ["start", "stop", "status", "reset", "logs"]
        for cmd in required_commands:
            assert cmd in content, f"Script missing command: {cmd}"

    def test_script_bash_syntax_valid(self) -> None:
        """scripts/odoo-dev.sh must pass bash -n syntax check."""
        script_path = PROJECT_ROOT / "scripts" / "odoo-dev.sh"
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"Bash syntax error in odoo-dev.sh:\n{result.stderr.decode()}"
        )

    def test_verify_script_parseable(self) -> None:
        """scripts/verify-odoo-dev.py must be valid Python (parses without SyntaxError)."""
        verify_path = PROJECT_ROOT / "scripts" / "verify-odoo-dev.py"
        source = verify_path.read_text()
        try:
            ast.parse(source, filename=str(verify_path))
        except SyntaxError as exc:
            pytest.fail(f"verify-odoo-dev.py has syntax error: {exc}")

    def test_verify_script_checks_required_modules(self) -> None:
        """Verify script must reference all 6 required modules."""
        verify_path = PROJECT_ROOT / "scripts" / "verify-odoo-dev.py"
        content = verify_path.read_text()

        required_modules = ["base", "mail", "sale", "purchase", "hr", "account"]
        for mod in required_modules:
            assert mod in content, (
                f"verify-odoo-dev.py missing reference to required module: {mod}"
            )
