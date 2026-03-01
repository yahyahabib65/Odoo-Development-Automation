"""Click CLI for odoo-gen-utils: render templates and scaffold Odoo modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from odoo_gen_utils import __version__
from odoo_gen_utils.renderer import (
    create_renderer,
    get_template_dir,
    render_module,
    render_template,
)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """odoo-gen-utils: Python utilities for the odoo-gen GSD extension."""


@main.command()
@click.option("--template", required=True, help="Template file name (e.g., manifest.py.j2)")
@click.option("--output", required=True, type=click.Path(), help="Output file path")
@click.option("--var", multiple=True, help="Variable in key=value format (repeatable)")
@click.option("--var-file", type=click.Path(exists=True), help="JSON file with template variables")
def render(template: str, output: str, var: tuple[str, ...], var_file: str | None) -> None:
    """Render a single Jinja2 template to a file."""
    context: dict = {}

    if var_file:
        try:
            context = json.loads(Path(var_file).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error reading var-file: {exc}", err=True)
            sys.exit(1)

    for v in var:
        if "=" not in v:
            click.echo(f"Invalid --var format (expected key=value): {v}", err=True)
            sys.exit(1)
        key, value = v.split("=", 1)
        # Attempt to parse JSON values for non-string types
        try:
            context[key] = json.loads(value)
        except json.JSONDecodeError:
            context[key] = value

    template_dir = get_template_dir()
    env = create_renderer(template_dir)

    try:
        output_path = render_template(env, template, Path(output), context)
        click.echo(str(output_path))
    except Exception as exc:
        click.echo(f"Error rendering template: {exc}", err=True)
        sys.exit(1)


@main.command("list-templates")
def list_templates() -> None:
    """List all available Jinja2 templates."""
    template_dir = get_template_dir()

    if not template_dir.is_dir():
        click.echo(f"Templates directory not found: {template_dir}", err=True)
        sys.exit(1)

    templates = sorted(template_dir.glob("*.j2"))

    if not templates:
        click.echo("No templates found.", err=True)
        sys.exit(1)

    for tmpl in templates:
        # Extract description from first Jinja2 comment if present
        description = _extract_template_description(tmpl)
        if description:
            click.echo(f"{tmpl.name:30s} {description}")
        else:
            click.echo(tmpl.name)


def _extract_template_description(template_path: Path) -> str:
    """Extract the description from a Jinja2 template's first comment.

    Looks for pattern: {# template_name.j2 -- description #}

    Args:
        template_path: Path to the .j2 template file.

    Returns:
        The description string, or empty string if not found.
    """
    try:
        first_line = template_path.read_text(encoding="utf-8").split("\n", maxsplit=1)[0]
        if first_line.startswith("{#") and first_line.endswith("#}"):
            # Strip comment markers and extract after the dash separator
            content = first_line[2:-2].strip()
            parts = content.split(" -- ", maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()
            # Try single dash separator
            parts = content.split(" - ", maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()
    except OSError:
        pass
    return ""


@main.command("render-module")
@click.option("--spec-file", required=True, type=click.Path(exists=True), help="JSON file with module specification")
@click.option("--output-dir", required=True, type=click.Path(), help="Directory to create module in")
def render_module_cmd(spec_file: str, output_dir: str) -> None:
    """Render a complete Odoo module from a JSON specification file."""
    try:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error reading spec file: {exc}", err=True)
        sys.exit(1)

    # Validate required spec fields
    required_fields = ["module_name"]
    missing = [f for f in required_fields if f not in spec]
    if missing:
        click.echo(f"Missing required fields in spec: {', '.join(missing)}", err=True)
        sys.exit(1)

    template_dir = get_template_dir()
    output_path = Path(output_dir)

    try:
        created_files = render_module(spec, template_dir, output_path)
        for f in created_files:
            click.echo(str(f))
    except Exception as exc:
        click.echo(f"Error rendering module: {exc}", err=True)
        sys.exit(1)
