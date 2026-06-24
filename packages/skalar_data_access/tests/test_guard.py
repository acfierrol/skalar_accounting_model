"""Read-only guard: SELECT/WITH allowed; everything else rejected."""

from __future__ import annotations

import pytest

from skalar_data_access import WriteAttemptError, assert_read_only

ALLOWED = [
    "SELECT 1",
    "select * from `p.d.t` where x = @x",
    "WITH a AS (SELECT 1 AS n) SELECT n FROM a",
    "SELECT 1 -- trailing line comment\n",
    "/* leading block comment */ SELECT 1",
    "SELECT 1;",  # single trailing semicolon
    "SELECT 1;;",  # doubled trailing semicolon -> bare ; is punctuation-only, not a statement
    "SELECT created_at, updated_at FROM `p.d.t`",  # identifiers containing keyword substrings
]

REJECTED = [
    "",
    "   ",
    "DELETE FROM t",
    "UPDATE t SET x = 1",
    "INSERT INTO t VALUES (1)",
    "DROP TABLE t",
    "ALTER TABLE t ADD COLUMN c INT64",
    "TRUNCATE TABLE t",
    "CREATE TABLE t AS SELECT 1",
    "CREATE OR REPLACE VIEW v AS SELECT 1",
    "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE",
    "GRANT `roles/viewer` ON TABLE t TO 'x'",
    "CALL my_proc()",
    "EXPORT DATA OPTIONS(uri='gs://b/f') AS SELECT 1",
    "SELECT * INTO t2 FROM t",
    "SELECT 1; DELETE FROM t",  # multi-statement
    "/* */ SELECT 1; DROP TABLE t",  # comment-hidden second statement
    "-- only a comment",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed(sql: str) -> None:
    assert_read_only(sql)  # must not raise


@pytest.mark.parametrize("sql", REJECTED)
def test_rejected(sql: str) -> None:
    with pytest.raises(WriteAttemptError):
        assert_read_only(sql)
