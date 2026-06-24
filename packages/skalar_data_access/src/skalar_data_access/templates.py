"""Jinja-templated SQL rendering.

Templates render *structure only* (table references, optional column lists, the
date-grain expression). All **values** flow through bound ``@parameters`` — never
string interpolation. ``StrictUndefined`` makes a missing context variable fail
loudly instead of silently emitting empty SQL.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined

_SUFFIX = ".sql.jinja"

_ENV = Environment(
    loader=PackageLoader("skalar_data_access", "sql"),
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render_template(name: str, /, **context: object) -> str:
    """Render ``sql/<name>.sql.jinja`` with ``context`` and return the SQL string."""
    template_name = name if name.endswith(_SUFFIX) else f"{name}{_SUFFIX}"
    return _ENV.get_template(template_name).render(**context)


def list_templates() -> tuple[str, ...]:
    """Return the available template names (sorted)."""
    return tuple(sorted(_ENV.list_templates()))
