"""
E2E test configuration and fixtures for OpenClaw autonomy tests.

This module provides pytest fixtures for containerized E2E testing
of the autonomy framework using testcontainers and Docker Compose.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
import pytest_asyncio
import requests


# Mark all tests in this directory as E2E
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "e2e: end-to-end tests using Docker containers")
    config.addinivalue_line("markers", "slow: tests that take >30 seconds to run")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    # Navigate from tests/e2e/ to project root
    return Path(__file__).parent.parent.parent.resolve()


@pytest.fixture(scope="session")
def e2e_dir(project_root: Path) -> Path:
    """Return the E2E tests directory."""
    return project_root / "tests" / "e2e"


@pytest.fixture(scope="session")
def compose_file(e2e_dir: Path) -> Path:
    """Return the Docker Compose file path."""
    return e2e_dir / "fixtures" / "docker-compose.yml"


@pytest.fixture
def mock_llm_url() -> str:
    """Return the mock LLM server URL."""
    return os.getenv("MOCK_LLM_URL", "http://localhost:8080")


@pytest.fixture
def orchestrator_url() -> str:
    """Return the orchestrator API URL."""
    return os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


class DockerComposeStack:
    """Manages a Docker Compose stack for E2E tests."""
    
    def __init__(self, compose_file: Path, project_name: str = "openclaw-e2e"):
        self.compose_file = compose_file
        self.project_name = project_name
        self._services: Dict[str, str] = {}
    
    def start(self, services: Optional[List[str]] = None) -> None:
        """Start the Docker Compose stack."""
        cmd = [
            "docker", "compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "up", "-d", "--build"
        ]
        if services:
            cmd.extend(services)
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Wait for services to be healthy
        self._wait_for_healthy()
    
    def stop(self) -> None:
        """Stop the Docker Compose stack."""
        subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), "-p", self.project_name, "down", "-v"],
            check=True,
            capture_output=True
        )
    
    def logs(self, service: str) -> str:
        """Get logs from a service."""
        result = subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), "-p", self.project_name, "logs", service],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    
    def exec(self, service: str, command: List[str]) -> str:
        """Execute a command in a service container."""
        result = subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), "-p", self.project_name, "exec", service] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    
    def _wait_for_healthy(self, timeout: int = 60) -> None:
        """Wait for services to be healthy."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Check mock LLM health
                resp = requests.get("http://localhost:8080/health", timeout=2)
                if resp.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise TimeoutError(f"Services not healthy after {timeout}s")


@pytest.fixture
def compose_stack(compose_file: Path) -> DockerComposeStack:
    """Provide a Docker Compose stack manager."""
    stack = DockerComposeStack(compose_file)
    try:
        stack.start()
        yield stack
    finally:
        stack.stop()


class MockLLMClient:
    """Client for interacting with the mock LLM server."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
    
    def is_healthy(self) -> bool:
        """Check if mock LLM is healthy."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2)
            return resp.status_code == 200
        except requests.RequestException:
            return False
    
    def configure_response(self, pattern: str, response: Dict[str, Any]) -> None:
        """Configure a mock response pattern."""
        resp = requests.post(
            f"{self.base_url}/configure",
            json={"pattern": pattern, "response": response},
            timeout=5
        )
        resp.raise_for_status()
    
    def reset(self) -> None:
        """Reset all mock responses."""
        resp = requests.post(f"{self.base_url}/reset", timeout=5)
        resp.raise_for_status()
    
    def get_calls(self) -> List[Dict[str, Any]]:
        """Get recorded API calls."""
        resp = requests.get(f"{self.base_url}/calls", timeout=5)
        resp.raise_for_status()
        return resp.json()


@pytest.fixture
def mock_llm(mock_llm_url: str) -> MockLLMClient:
    """Provide a mock LLM client."""
    client = MockLLMClient(mock_llm_url)
    client.reset()
    yield client
    client.reset()


class EventCapture:
    """Captures autonomy events for verification."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
    
    def add(self, event: Dict[str, Any]) -> None:
        """Add an event to the capture."""
        self.events.append(event)
    
    def find(self, event_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Find an event by type and optional field values."""
        for event in self.events:
            if event.get("event_type") == event_type:
                if all(
                    event.get("payload", {}).get(k) == v or event.get(k) == v
                    for k, v in kwargs.items()
                ):
                    return event
        return None
    
    def find_all(self, event_type: str) -> List[Dict[str, Any]]:
        """Find all events of a specific type."""
        return [e for e in self.events if e.get("event_type") == event_type]
    
    def clear(self) -> None:
        """Clear all captured events."""
        self.events.clear()


@pytest.fixture
def event_capture() -> EventCapture:
    """Provide an event capture utility."""
    return EventCapture()


class AutonomyStack:
    """Combined stack for autonomy E2E tests."""
    
    def __init__(self, compose_stack: DockerComposeStack, mock_llm: MockLLMClient):
        self.compose = compose_stack
        self.mock_llm = mock_llm
        self.events = EventCapture()
    
    def get_orchestrator_logs(self) -> str:
        """Get orchestrator container logs."""
        return self.compose.logs("orchestrator")
    
    def get_mock_llm_logs(self) -> str:
        """Get mock LLM container logs."""
        return self.compose.logs("mock-llm")
    
    def exec_in_orchestrator(self, command: List[str]) -> str:
        """Execute command in orchestrator container."""
        return self.compose.exec("orchestrator", command)
    
    def get_sentinel_files(self) -> List[str]:
        """List sentinel files in workspace."""
        try:
            output = self.exec_in_orchestrator(["ls", "-la", "/workspace/.openclaw/sentinel/"])
            return [line.split()[-1] for line in output.split("\n") if line.strip() and not line.startswith("total")]
        except Exception:
            return []
    
    def get_jarvis_state(self) -> Optional[Dict[str, Any]]:
        """Read JarvisState from sentinel file."""
        try:
            output = self.exec_in_orchestrator([
                "cat", "/workspace/.openclaw/sentinel/jarvis_state.json"
            ])
            return json.loads(output)
        except Exception:
            return None
    
    def set_jarvis_state(self, state: str) -> None:
        """Update JarvisState via sentinel file."""
        self.exec_in_orchestrator([
            "sh", "-c",
            f'echo \'{{"state": "{state}", "updated_at": "{time.time()}"}}\' > /workspace/.openclaw/sentinel/jarvis_state.json'
        ])


@pytest_asyncio.fixture
async def autonomy_stack(compose_stack: DockerComposeStack, mock_llm: MockLLMClient) -> AsyncGenerator[AutonomyStack, None]:
    """
    Provide a complete autonomy stack for E2E tests.
    
    This fixture spins up the full Docker Compose environment including:
    - Mock LLM server for deterministic responses
    - Orchestrator with autonomy enabled
    
    Example:
        async def test_something(autonomy_stack):
            autonomy_stack.mock_llm.configure_response("plan", {...})
            # Run test...
    """
    stack = AutonomyStack(compose_stack, mock_llm)
    
    # Verify stack is ready
    assert stack.mock_llm.is_healthy(), "Mock LLM not healthy"
    
    yield stack


# Shared test utilities

def wait_for_condition(condition_func, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Wait for a condition to become true."""
    start = time.time()
    while time.time() - start < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


@pytest.fixture
def wait_for():
    """Provide the wait_for_condition utility."""
    return wait_for_condition
