import pytest
from unittest.mock import AsyncMock, patch
from openclaw.memory_extractor import extract_and_memorize
from openclaw.memory_client import AgentType

@pytest.mark.asyncio
async def test_extract_and_memorize():
    project_id = "test_project"
    agent_type = AgentType.L3_CODE
    task_result = {
        "status": "completed",
        "description": "Implemented auth middleware",
        "summary": "Used FastAPI dependency injection for JWT validation."
    }
    status = "completed"
    memu_url = "http://localhost:18791"
    
    mock_client = AsyncMock()
    mock_client.memorize.return_value = {"accepted": True, "message": "success"}
    
    with patch("openclaw.memory_extractor.MemoryClient", return_value=mock_client) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        await extract_and_memorize(
            project_id=project_id,
            agent_type=agent_type,
            task_result=task_result,
            status=status,
            memu_url=memu_url
        )
        
    mock_client.memorize.assert_called_once()
    args, kwargs = mock_client.memorize.call_args
    assert "Implemented auth middleware" in args[0]
    assert "FastAPI dependency injection" in args[0]
