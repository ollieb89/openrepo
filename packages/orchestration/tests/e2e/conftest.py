"""E2E test fixtures for autonomy testing."""
import pytest
import asyncio
import time
import json
from pathlib import Path
from typing import Dict, Any, Generator

# Use local imports to avoid Docker dependencies in unit tests
try:
    from testcontainers.compose import DockerCompose
    from testcontainers.core.container import DockerContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


@pytest.fixture(scope="session")
def e2e_enabled() -> bool:
    """Check if E2E tests should run (skip in CI unless explicitly enabled)."""
    import os
    return os.environ.get("E2E_TESTS_ENABLED", "0") == "1"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to E2E fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def mock_llm_responses(fixtures_dir: Path) -> Dict[str, Any]:
    """Load mock LLM response files."""
    responses_dir = fixtures_dir / "responses"
    responses = {}
    
    if responses_dir.exists():
        for response_file in responses_dir.glob("*.json"):
            with open(response_file) as f:
                responses[response_file.stem] = json.load(f)
    
    return responses


@pytest.fixture
def mock_llm_server(mock_llm_responses: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """
    Start mock LLM server for testing.
    
    Returns server info including URL and loaded responses.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")
    
    from tests.e2e.mock_llm.server import create_app
    
    # For faster tests, use Flask test client instead of full container
    app = create_app(mock_llm_responses)
    
    server_info = {
        "url": "http://localhost:8080",
        "responses": mock_llm_responses,
        "app": app,
    }
    
    yield server_info


@pytest.fixture
def autonomy_context(tmp_path: Path) -> Dict[str, Any]:
    """Create isolated autonomy context for a test."""
    task_id = f"test-task-{int(time.time() * 1000)}"
    
    return {
        "task_id": task_id,
        "workspace_dir": tmp_path / "workspace",
        "state_file": tmp_path / "state.json",
        "sentinel_dir": tmp_path / "sentinel",
    }


@pytest.fixture
async def event_bus():
    """Create isolated event bus for testing."""
    from openclaw.autonomy.events import AutonomyEventBus
    
    # Create fresh event bus instance
    bus = AutonomyEventBus()
    events_captured = []
    
    def capture_event(event):
        events_captured.append(event)
    
    # Subscribe to all events
    bus.subscribe("*", capture_event)
    
    yield {
        "bus": bus,
        "events": events_captured,
    }


@pytest.fixture
def cli_runtime() -> str:
    """Return CLI runtime for testing."""
    return "echo"  # Use echo as mock CLI for tests


@pytest.fixture
def mock_plan_response() -> Dict[str, Any]:
    """Return a mock plan response for testing."""
    return {
        "steps": [
            {
                "id": "1",
                "action": "Analyze task requirements",
                "expected_outcome": "Clear understanding of what needs to be done"
            },
            {
                "id": "2",
                "action": "Create implementation plan",
                "expected_outcome": "Detailed plan with actionable steps"
            },
            {
                "id": "3",
                "action": "Execute plan",
                "expected_outcome": "Task completed successfully"
            }
        ]
    }


@pytest.fixture
def mock_execution_response() -> str:
    """Return a mock execution success response."""
    return "Step executed successfully. Output: Task completed."
