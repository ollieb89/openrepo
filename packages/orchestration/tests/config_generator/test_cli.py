import pytest
import os
from unittest.mock import patch
from openclaw.config_generator.cli import main

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_cli_config.db")

def test_cli_init_and_generate(temp_db_path, tmp_path):
    output_json = str(tmp_path / "test_openclaw.json")
    
    # Run init
    test_args = ["openclaw-config-gen", "--db", temp_db_path, "init"]
    with patch("sys.argv", test_args):
        main()
    
    assert os.path.exists(temp_db_path)
    
    # Run generate
    test_args = ["openclaw-config-gen", "--db", temp_db_path, "generate", "--output", output_json]
    with patch("sys.argv", test_args):
        main()
        
    assert os.path.exists(output_json)

def test_cli_list_commands(temp_db_path, capsys):
    # Init first to have default data
    test_args = ["openclaw-config-gen", "--db", temp_db_path, "init"]
    with patch("sys.argv", test_args):
        main()
        
    # Test listing agents
    test_args = ["openclaw-config-gen", "--db", temp_db_path, "agents"]
    with patch("sys.argv", test_args):
        main()
        
    captured = capsys.readouterr()
    assert "main" in captured.out
    assert "Central Core" in captured.out
