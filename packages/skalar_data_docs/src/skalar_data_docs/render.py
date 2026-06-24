"""Render a :class:`TableProfile` (+ optional null fractions) into markdown."""

from __future__ import annotations

from skalar_data_access import TableProfile


def render_table_doc(
    profile: TableProfile,
    *,
    null_fractions: dict[str, float] | None = None,
    grain: str = "",
    role: str = "",
) -> str:
    """Return a markdown doc for one table: title, grain/role, size, column table."""
    nulls = null_fractions or {}
    lines: list[str] = [f"# `{profile.table_id}`", ""]
    if grain:
        lines += [f"**Grain.** {grain}", ""]
    if role:
        lines += [f"**Role in the pipeline.** {role}", ""]
    lines += [
        f"**Size.** {profile.num_rows:,} rows / {profile.num_bytes:,} bytes "
        f"(~{profile.num_bytes / 1024**3:.2f} GiB).",
        "",
        "| Column | Type | Nullable | Null % | Description |",
        "|---|---|---|---:|---|",
    ]
    for col in profile.columns:
        null_pct = nulls.get(col.name)
        null_cell = f"{null_pct * 100:.2f}%" if null_pct is not None else "—"
        nullable = "yes" if col.is_nullable else "no"
        lines.append(
            f"| `{col.name}` | {col.field_type} | {nullable} | {null_cell} | {col.description} |"
        )
    lines.append("")
    return "\n".join(lines)
