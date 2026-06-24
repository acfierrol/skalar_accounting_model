"""Read-only SQL guard: permit only a single ``SELECT``/``WITH`` statement.

This is defense-in-depth on top of the read-only IAM grant. It uses ``sqlparse``
(not regex) so it is not defeated by block comments, multiple statements, or a
leading CTE that hides DML.
"""

from __future__ import annotations

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import DDL, DML, Keyword, Punctuation

from .errors import WriteAttemptError

# Statement-initial keywords that are read-only.
_ALLOWED_FIRST = frozenset({"SELECT", "WITH"})

# Keywords that imply a write/DDL/side-effect anywhere in the statement.
_FORBIDDEN = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
        "REPLACE",
        "CREATE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "RENAME",
        "GRANT",
        "REVOKE",
        "CALL",
        "EXECUTE",
        "EXPORT",
        "LOAD",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "DECLARE",
        "INTO",  # `SELECT ... INTO` materialises a table
    }
)


def _is_meaningful(statement: Statement) -> bool:
    """True unless the statement is only whitespace/comments/punctuation (e.g. a bare ``;``)."""
    first = statement.token_first(skip_cm=True)
    return first is not None and first.ttype is not Punctuation


def assert_read_only(sql: str) -> None:
    """Raise :class:`WriteAttemptError` unless ``sql`` is one read-only statement."""
    if not sql or not sql.strip():
        raise WriteAttemptError("empty SQL is not allowed")

    stripped = sqlparse.format(sql, strip_comments=True).strip()
    parsed = [s for s in sqlparse.parse(stripped) if _is_meaningful(s)]

    if len(parsed) != 1:
        raise WriteAttemptError(f"exactly one statement is allowed; found {len(parsed)}")

    statement = parsed[0]
    first = statement.token_first(skip_cm=True)
    keyword = (first.normalized or "").upper() if first is not None else ""
    if keyword not in _ALLOWED_FIRST:
        raise WriteAttemptError(f"only SELECT/WITH statements are permitted; got {keyword!r}")

    for token in statement.flatten():
        if token.ttype in (DML, DDL, Keyword):
            word = (token.normalized or "").upper()
            if word in _FORBIDDEN:
                raise WriteAttemptError(f"forbidden keyword in read-only query: {word!r}")
