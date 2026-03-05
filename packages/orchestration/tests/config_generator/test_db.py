import os
import json
import pytest
import sqlite3
from openclaw.config_generator.db import ConfigDatabase, create_default_config

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_config.db")

@pytest.fixture
def db(temp_db_path):
    database = ConfigDatabase(temp_db_path)
    database.connect()
    yield database
    database.close()

def test_create_tables(db):
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {"providers", "models", "channels", "agents", "gateway_settings", "plugins"}
    assert expected_tables.issubset(tables)

def test_add_provider(db):
    db.add_provider("test_prov", "Test Provider", "openai")
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM providers WHERE id='test_prov'")
    row = cursor.fetchone()
    assert row is not None
    assert row["name"] == "Test Provider"
    assert row["type"] == "openai"
    assert row["enabled"] == 1

def test_add_model(db):
    db.add_provider("test_prov", "Test Provider", "openai")
    db.add_model("gpt-4", "test_prov", "GPT-4")
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM models WHERE id='gpt-4'")
    row = cursor.fetchone()
    assert row["provider_id"] == "test_prov"
    assert row["type"] == "chat"

def test_add_agent(db):
    db.add_agent("agent_1", "Agent One", level=1, config={"test": True})
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE id='agent_1'")
    row = cursor.fetchone()
    assert row["name"] == "Agent One"
    assert row["level"] == 1
    assert json.loads(row["config"]) == {"test": True}

def test_generate_openclaw_json(db, tmp_path):
    db.add_agent("main", "Central Core", level=1)
    db.set_gateway("port", 12345)
    db.add_channel("telegram", "Telegram", "telegram", config={"botToken": "test_token"})
    
    output_path = tmp_path / "openclaw.json"
    result = db.generate_openclaw_json(str(output_path))
    
    assert "agents" in result
    assert result["agents"]["list"][0]["id"] == "main"
    assert result["gateway"]["port"] == 12345
    assert result["channels"]["telegram"]["botToken"] == "test_token"
    
    assert output_path.exists()
    with open(output_path, "r") as f:
        data = json.load(f)
        assert data["gateway"]["port"] == 12345

def test_create_default_config(temp_db_path):
    db = create_default_config(temp_db_path)
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM gateway_settings WHERE key='port'")
    assert cursor.fetchone()["value"] == "18789"
    
    cursor.execute("SELECT * FROM agents WHERE id='main'")
    assert cursor.fetchone()["name"] == "Central Core"
    
    db.close()
