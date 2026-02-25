import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from openclaw.memory_injector import generate_memory_context
from openclaw.memory_client import AgentType

@pytest.mark.asyncio
async def test_generate_memory_context(tmp_path):
    project_id = "test_project"
    agent_type = AgentType.L2_PM
    task_desc = "Design the database schema"
    memu_url = "http://localhost:18791"
    
    # Mock MemoryClient
    mock_client = AsyncMock()
    mock_client.retrieve.return_value = [
        {"content": "Use PostgreSQL with pgvector for embeddings."},
        {"content": "All tables must have created_at and updated_at."}
    ]
    
    with patch("openclaw.memory_injector.MemoryClient", return_value=mock_client) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        await generate_memory_context(
            project_id=project_id,
            agent_type=agent_type,
            task_description=task_desc,
            workspace_path=tmp_path,
            memu_url=memu_url
        )
        
    memory_file = tmp_path / "MEMORY.md"
    assert memory_file.exists()
    content = memory_file.read_text()
    
    assert "Use PostgreSQL with pgvector for embeddings." in content
    assert "All tables must have created_at and updated_at." in content
    mock_client.retrieve.assert_called_once_with(task_desc)
