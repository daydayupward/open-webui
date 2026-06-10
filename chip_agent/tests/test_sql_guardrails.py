import pytest
from src.sql.sql_guardrails import validate_sql_query

def test_validate_sql_query_valid():
    # Valid queries
    assert validate_sql_query("SELECT * FROM project_metrics") is True
    assert validate_sql_query("select name, value from project_metrics where value > 10") is True
    assert validate_sql_query("SELECT * FROM public.project_metrics;") is True
    assert validate_sql_query("SELECT * FROM project_metrics -- comment here") is True

def test_validate_sql_query_not_select():
    # Does not start with SELECT
    assert validate_sql_query("WITH cte AS (SELECT * FROM project_metrics) SELECT * FROM cte") is False
    assert validate_sql_query("INSERT INTO project_metrics (name) VALUES ('test')") is False

def test_validate_sql_query_blocked_commands():
    # Contains blocked commands
    assert validate_sql_query("SELECT * FROM project_metrics; DELETE FROM project_metrics") is False
    assert validate_sql_query("SELECT * FROM project_metrics WHERE name = 'DELETE'") is True  # literal string 'DELETE' is allowed
    assert validate_sql_query("SELECT delete_col FROM project_metrics") is True  # column prefix containing delete is allowed
    assert validate_sql_query("SELECT * FROM project_metrics; DROP TABLE project_metrics") is False

def test_validate_sql_query_disallowed_tables():
    # Disallowed tables
    assert validate_sql_query("SELECT * FROM other_table") is False
    assert validate_sql_query("SELECT * FROM project_metrics JOIN users ON project_metrics.user_id = users.id") is False
    assert validate_sql_query("SELECT * FROM project_metrics, other_table") is False

def test_validate_sql_query_multiple_statements():
    # Multiple statements
    assert validate_sql_query("SELECT * FROM project_metrics; SELECT * FROM project_metrics") is False
