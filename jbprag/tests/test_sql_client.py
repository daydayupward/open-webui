import pytest
from unittest.mock import MagicMock, patch
from src.sql.sql_client import execute_read_query, clean_db_url

@pytest.mark.anyio
async def test_clean_db_url():
    assert clean_db_url("postgresql+psycopg://user:pass@host:5432/db") == "postgresql://user:pass@host:5432/db"
    assert clean_db_url("postgresql+psycopg2://user:pass@host/db") == "postgresql://user:pass@host/db"
    assert clean_db_url("postgresql://user:pass@host/db") == "postgresql://user:pass@host/db"

@patch("psycopg.connect")
@pytest.mark.anyio
async def test_execute_read_query_success(mock_connect):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    
    # Mock cursor description and fetchall
    mock_cur.description = [("id", None), ("metric_name", None), ("value", None)]
    mock_cur.fetchall.return_value = [
        (1, "latency", 12.5),
        (2, "power", 95.0)
    ]
    
    results = execute_read_query("SELECT * FROM project_metrics", timeout=3.5)
    
    # Verify psycopg.connect called with cleaned database URL
    mock_connect.assert_called_once()
    
    # Verify statement_timeout is set
    mock_cur.execute.assert_any_call("SET statement_timeout = 3500;")
    mock_cur.execute.assert_any_call("SELECT * FROM project_metrics", None)
    
    # Verify output mapping
    assert results == [
        {"id": 1, "metric_name": "latency", "value": 12.5},
        {"id": 2, "metric_name": "power", "value": 95.0}
    ]

@patch("psycopg.connect")
@pytest.mark.anyio
async def test_execute_read_query_exception(mock_connect):
    mock_connect.side_effect = Exception("Connection failed")
    with pytest.raises(Exception, match="Connection failed"):
        with patch("src.sql.sql_client.settings") as mock_settings:
            mock_settings.DATABASE_URL = "postgresql://test:test@localhost/test"
            execute_read_query("SELECT * FROM project_metrics")
