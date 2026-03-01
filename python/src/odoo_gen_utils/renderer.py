"""Jinja2 rendering engine with Odoo-specific filters for module scaffolding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _model_ref(name: str) -> str:
    """Convert Odoo dot-notation model name to external ID format.

    Example: "inventory.item" -> "model_inventory_item"
    """
    return f"model_{name.replace('.', '_')}"


def _to_class(name: str) -> str:
    """Convert Odoo dot-notation model name to Python class name.

    Example: "inventory.item" -> "InventoryItem"
    """
    return "".join(word.capitalize() for word in name.replace(".", "_").split("_"))


def _to_python_var(name: str) -> str:
    """Convert Odoo dot-notation model name to Python variable name.

    Example: "inventory.item" -> "inventory_item"
    """
    return name.replace(".", "_")


def _to_xml_id(name: str) -> str:
    """Convert Odoo dot-notation model name to XML id attribute format.

    Example: "inventory.item" -> "inventory_item"
    """
    return name.replace(".", "_")


def create_renderer(template_dir: Path) -> Environment:
    """Create a Jinja2 Environment configured for Odoo module rendering.

    Uses StrictUndefined to fail loudly on missing template variables (Pitfall 1 prevention).
    Registers custom filters for Odoo-specific name conversions.

    Args:
        template_dir: Path to the directory containing .j2 template files.

    Returns:
        Configured Jinja2 Environment.
    """
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    env.filters["model_ref"] = _model_ref
    env.filters["to_class"] = _to_class
    env.filters["to_python_var"] = _to_python_var
    env.filters["to_xml_id"] = _to_xml_id

    return env


def render_template(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> Path:
    """Render a single Jinja2 template to a file.

    Creates parent directories as needed.

    Args:
        env: Jinja2 Environment with loaded templates.
        template_name: Name of the template file (e.g., "manifest.py.j2").
        output_path: Destination file path for the rendered output.
        context: Dictionary of template variables.

    Returns:
        The output_path where the rendered file was written.
    """
    template = env.get_template(template_name)
    content = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def get_template_dir() -> Path:
    """Return the path to the bundled templates directory.

    The templates are shipped alongside this module in the templates/ subdirectory.

    Returns:
        Absolute path to the templates directory.
    """
    return Path(__file__).parent / "templates"


def _build_model_context(spec: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Build the template context for a single model from the module spec.

    Args:
        spec: Full module specification dictionary.
        model: Single model dictionary from spec["models"].

    Returns:
        Context dictionary suitable for rendering model-related templates.
    """
    model_var = _to_python_var(model["name"])
    model_xml_id = _to_xml_id(model["name"])

    required_fields = [f for f in model.get("fields", []) if f.get("required")]
    has_constraints = any(
        f.get("constraints") for f in model.get("fields", [])
    ) or bool(model.get("sql_constraints"))

    return {
        "module_name": spec["module_name"],
        "module_title": spec.get("module_title", spec["module_name"].replace("_", " ").title()),
        "summary": spec.get("summary", ""),
        "author": spec.get("author", ""),
        "website": spec.get("website", ""),
        "license": spec.get("license", "LGPL-3"),
        "category": spec.get("category", "Uncategorized"),
        "odoo_version": spec.get("odoo_version", "17.0"),
        "depends": spec.get("depends", ["base"]),
        "application": spec.get("application", True),
        "models": spec.get("models", []),
        "model_name": model["name"],
        "model_description": model.get("description", model["name"]),
        "model_var": model_var,
        "model_xml_id": model_xml_id,
        "fields": model.get("fields", []),
        "required_fields": required_fields,
        "has_constraints": has_constraints,
        "sql_constraints": model.get("sql_constraints", []),
        "inherit": model.get("inherit"),
    }


def _compute_view_files(spec: dict[str, Any]) -> list[str]:
    """Compute the list of view file paths for the manifest data section.

    Args:
        spec: Full module specification dictionary.

    Returns:
        List of view file relative paths (e.g., ["views/item_views.xml", ...]).
    """
    view_files = []
    for model in spec.get("models", []):
        model_var = _to_python_var(model["name"])
        view_files.append(f"{model_var}_views.xml")
        view_files.append(f"{model_var}_action.xml")
    view_files.append("menu.xml")
    return view_files


def render_module(spec: dict[str, Any], template_dir: Path, output_dir: Path) -> list[Path]:
    """Render a complete Odoo module from a specification dictionary.

    Produces the full OCA directory structure:
        __manifest__.py, __init__.py, models/, views/, security/,
        tests/, demo/, static/description/, README.rst

    Args:
        spec: Module specification dictionary with module_name, models, etc.
        template_dir: Path to Jinja2 template files.
        output_dir: Root directory where the module will be created.

    Returns:
        List of all created file paths.
    """
    env = create_renderer(template_dir)
    module_name = spec["module_name"]
    module_dir = output_dir / module_name
    created_files: list[Path] = []

    models = spec.get("models", [])
    view_files = _compute_view_files(spec)

    # -- Shared context for module-level templates --
    module_context = {
        "module_name": module_name,
        "module_title": spec.get("module_title", module_name.replace("_", " ").title()),
        "module_technical_name": module_name,
        "summary": spec.get("summary", ""),
        "author": spec.get("author", ""),
        "website": spec.get("website", ""),
        "license": spec.get("license", "LGPL-3"),
        "category": spec.get("category", "Uncategorized"),
        "odoo_version": spec.get("odoo_version", "17.0"),
        "depends": spec.get("depends", ["base"]),
        "application": spec.get("application", True),
        "models": models,
        "view_files": view_files,
    }

    # 1. __manifest__.py
    created_files.append(
        render_template(env, "manifest.py.j2", module_dir / "__manifest__.py", module_context)
    )

    # 2. Root __init__.py
    created_files.append(
        render_template(env, "init_root.py.j2", module_dir / "__init__.py", module_context)
    )

    # 3. models/__init__.py
    created_files.append(
        render_template(env, "init_models.py.j2", module_dir / "models" / "__init__.py", module_context)
    )

    # 4. Per-model files
    for model in models:
        model_ctx = _build_model_context(spec, model)
        model_var = _to_python_var(model["name"])

        # models/<model_var>.py
        created_files.append(
            render_template(env, "model.py.j2", module_dir / "models" / f"{model_var}.py", model_ctx)
        )

        # views/<model_var>_views.xml (form + tree + search combined)
        created_files.append(
            render_template(env, "view_form.xml.j2", module_dir / "views" / f"{model_var}_views.xml", model_ctx)
        )

        # views/<model_var>_action.xml
        created_files.append(
            render_template(env, "action.xml.j2", module_dir / "views" / f"{model_var}_action.xml", model_ctx)
        )

    # 5. views/menu.xml (single menu file for all models)
    created_files.append(
        render_template(env, "menu.xml.j2", module_dir / "views" / "menu.xml", module_context)
    )

    # 6. security/security.xml
    created_files.append(
        render_template(env, "security_group.xml.j2", module_dir / "security" / "security.xml", module_context)
    )

    # 7. security/ir.model.access.csv
    created_files.append(
        render_template(env, "access_csv.j2", module_dir / "security" / "ir.model.access.csv", module_context)
    )

    # 8. tests/__init__.py
    created_files.append(
        render_template(env, "init_tests.py.j2", module_dir / "tests" / "__init__.py", module_context)
    )

    # 9. Per-model test files
    for model in models:
        model_ctx = _build_model_context(spec, model)
        model_var = _to_python_var(model["name"])
        created_files.append(
            render_template(
                env, "test_model.py.j2", module_dir / "tests" / f"test_{model_var}.py", model_ctx
            )
        )

    # 10. demo/demo_data.xml
    created_files.append(
        render_template(env, "demo_data.xml.j2", module_dir / "demo" / "demo_data.xml", module_context)
    )

    # 11. static/description/index.html
    static_dir = module_dir / "static" / "description"
    static_dir.mkdir(parents=True, exist_ok=True)
    index_html = static_dir / "index.html"
    index_html.write_text(
        '<!DOCTYPE html>\n<html>\n<head><title>Module Description</title></head>\n'
        '<body><p>See README.rst for module documentation.</p></body>\n</html>\n',
        encoding="utf-8",
    )
    created_files.append(index_html)

    # 12. README.rst
    created_files.append(
        render_template(env, "readme.rst.j2", module_dir / "README.rst", module_context)
    )

    return created_files
