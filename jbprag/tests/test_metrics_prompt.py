"""Tests for metrics prompt templates."""
import pytest
from src.prompts.metrics_prompt import (
    TEXT_TO_SQL_SYSTEM_PROMPT,
    TEXT_TO_SQL_USER_TEMPLATE,
    RESULT_SUMMARY_SYSTEM_PROMPT,
    RESULT_SUMMARY_USER_TEMPLATE,
)


class TestTextToSqlPrompts:
    def test_system_prompt_contains_schema_placeholder(self):
        assert "{schema}" in TEXT_TO_SQL_SYSTEM_PROMPT

    def test_system_prompt_forbids_write_operations(self):
        upper = TEXT_TO_SQL_SYSTEM_PROMPT.upper()
        for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"):
            assert keyword in upper

    def test_system_prompt_mentions_select(self):
        assert "SELECT" in TEXT_TO_SQL_SYSTEM_PROMPT.upper()

    def test_user_template_contains_question_placeholder(self):
        assert "{question}" in TEXT_TO_SQL_USER_TEMPLATE

    def test_user_template_ends_with_sql_prompt(self):
        assert TEXT_TO_SQL_USER_TEMPLATE.strip().endswith("SQL Query:")

    def test_system_prompt_formats_with_schema(self):
        schema = "TABLE project_metrics (id INT, project_id VARCHAR)"
        rendered = TEXT_TO_SQL_SYSTEM_PROMPT.format(schema=schema)
        assert schema in rendered
        assert "{schema}" not in rendered


class TestResultSummaryPrompts:
    def test_system_prompt_contains_engineering_guidance(self):
        assert "ns" in RESULT_SUMMARY_SYSTEM_PROMPT
        assert "W" in RESULT_SUMMARY_SYSTEM_PROMPT
        assert "area" in RESULT_SUMMARY_SYSTEM_PROMPT

    def test_user_template_contains_question_placeholder(self):
        assert "{question}" in RESULT_SUMMARY_USER_TEMPLATE

    def test_user_template_contains_results_placeholder(self):
        assert "{results}" in RESULT_SUMMARY_USER_TEMPLATE

    def test_user_template_ends_with_summary_prompt(self):
        assert RESULT_SUMMARY_USER_TEMPLATE.strip().endswith("Summary:")

    def test_user_template_formats_correctly(self):
        rendered = RESULT_SUMMARY_USER_TEMPLATE.format(
            question="What is the WNS?",
            results="[(Proj_A, -0.12)]",
        )
        assert "What is the WNS?" in rendered
        assert "(Proj_A, -0.12)" in rendered
        assert "{question}" not in rendered
        assert "{results}" not in rendered
