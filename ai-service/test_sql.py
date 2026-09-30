import pytest
import os
import sys

# Add current directory to path so we can import main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import extract_sql, validate_sql

def test_extract_sql_from_markdown():
    text = "```sql\nSELECT * FROM users;\n```"
    result = extract_sql(text)
    assert result == "SELECT * FROM users;"

def test_extract_sql_from_plain_text():
    text = "The query is SELECT COUNT(*) FROM parking_sessions;"
    result = extract_sql(text)
    assert result == "SELECT COUNT(*) FROM parking_sessions;"

def test_extract_sql_no_sql_found():
    text = "I cannot answer that question."
    result = extract_sql(text)
    assert result is None

def test_validate_safe_select_query():
    sql = "SELECT * FROM parking_sessions"
    assert validate_sql(sql) is True

def test_validate_cte_query():
    sql = "WITH cte AS (SELECT * FROM users) SELECT * FROM cte"
    assert validate_sql(sql) is True

def test_reject_dangerous_drop_table():
    sql = "DROP TABLE parking_sessions"
    assert validate_sql(sql) is False

def test_reject_dangerous_delete():
    sql = "DELETE FROM users WHERE id = 1"
    assert validate_sql(sql) is False

def test_reject_insert_disguised_in_text():
    sql = "INSERT INTO users VALUES ('admin', 'pass')"
    assert validate_sql(sql) is False
