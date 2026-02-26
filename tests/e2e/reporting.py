"""
Test reporting and artifact capture for E2E tests.

Provides utilities for capturing diagnostic information when
tests fail, including logs, events, state, and configuration.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactCollector:
    """Collects diagnostic artifacts from E2E test failures."""
    
    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        Initialize the artifact collector.
        
        Args:
            artifacts_dir: Directory to save artifacts (default: tests/e2e/artifacts)
        """
        if artifacts_dir is None:
            self.artifacts_dir = Path(__file__).parent / "artifacts"
        else:
            self.artifacts_dir = Path(artifacts_dir)
        
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_failure_artifacts(
        self,
        test_name: str,
        compose_stack: Any,
        event_capture: Any,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Capture comprehensive artifacts on test failure.
        
        Args:
            test_name: Name of the test that failed
            compose_stack: DockerComposeStack instance for container access
            event_capture: EventCapture instance with recorded events
            additional_data: Optional additional data to include
            
        Returns:
            Path to the artifact directory for this failure
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        failure_dir = self.artifacts_dir / f"{test_name}_{timestamp}"
        failure_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts = {
            "test_name": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "orchestrator_logs": self._get_container_logs(compose_stack, "orchestrator"),
            "mock_llm_logs": self._get_container_logs(compose_stack, "mock-llm"),
            "events": self._format_events(event_capture.events if event_capture else []),
            "container_status": self._get_container_status(compose_stack),
        }
        
        # Add optional data
        if additional_data:
            artifacts.update(additional_data)
        
        # Save main artifact file
        artifact_file = failure_dir / "artifacts.json"
        with open(artifact_file, "w") as f:
            json.dump(artifacts, f, indent=2, default=str)
        
        # Save individual log files for easy viewing
        if artifacts["orchestrator_logs"]:
            (failure_dir / "orchestrator.log").write_text(artifacts["orchestrator_logs"])
        if artifacts["mock_llm_logs"]:
            (failure_dir / "mock_llm.log").write_text(artifacts["mock_llm_logs"])
        
        # Save events as JSONL for easy parsing
        if artifacts["events"]:
            events_file = failure_dir / "events.jsonl"
            with open(events_file, "w") as f:
                for event in artifacts["events"]:
                    f.write(json.dumps(event, default=str) + "\n")
        
        return failure_dir
    
    def _get_container_logs(self, compose_stack: Any, service: str) -> str:
        """Get logs from a Docker Compose service."""
        try:
            return compose_stack.logs(service)
        except Exception as e:
            return f"Error retrieving logs: {e}"
    
    def _get_container_status(self, compose_stack: Any) -> Dict[str, Any]:
        """Get status of containers in the compose stack."""
        try:
            # This would need implementation based on compose_stack capabilities
            return {"status": "unknown", "note": "Implement via compose_stack if needed"}
        except Exception as e:
            return {"error": str(e)}
    
    def _format_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format events for serialization."""
        formatted = []
        for event in events:
            formatted_event = {
                "event_type": event.get("event_type"),
                "task_id": event.get("task_id"),
                "timestamp": event.get("timestamp"),
                "payload": event.get("payload"),
            }
            formatted.append(formatted_event)
        return formatted


def capture_failure_artifacts(
    test_name: str,
    autonomy_stack: Any,
    event_capture: Any = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Convenience function to capture failure artifacts.
    
    Usage in tests:
        try:
            # test code
        except AssertionError:
            artifacts_dir = capture_failure_artifacts(
                "test_name",
                autonomy_stack,
                event_capture
            )
            raise
    """
    collector = ArtifactCollector()
    return collector.capture_failure_artifacts(
        test_name=test_name,
        compose_stack=autonomy_stack.compose,
        event_capture=event_capture,
        additional_data=additional_data
    )


def list_sentinel_files(compose_stack: Any) -> List[str]:
    """List sentinel files in the orchestrator container."""
    try:
        output = compose_stack.exec("orchestrator", ["ls", "-la", "/workspace/.openclaw/sentinel/"])
        files = []
        for line in output.split("\n"):
            if line.strip() and not line.startswith("total"):
                parts = line.split()
                if len(parts) >= 9:
                    files.append(parts[-1])
        return files
    except Exception as e:
        return [f"Error: {e}"]


def get_event_bus_history(autonomy_stack: Any) -> List[Dict[str, Any]]:
    """
    Get event history from the event bus.
    
    Note: This would require the event bus to expose history.
    Currently a placeholder for future implementation.
    """
    return []


def load_jarvis_state(compose_stack: Any) -> Optional[Dict[str, Any]]:
    """Load JarvisState from sentinel file in container."""
    try:
        output = compose_stack.exec(
            "orchestrator",
            ["cat", "/workspace/.openclaw/sentinel/jarvis_state.json"]
        )
        return json.loads(output)
    except Exception:
        return None


def save_artifacts(test_name: str, artifacts: Dict[str, Any]) -> Path:
    """
    Save artifacts dictionary to file.
    
    Args:
        test_name: Name of test
        artifacts: Dictionary of artifact data
        
    Returns:
        Path to saved artifact file
    """
    artifacts_dir = Path(__file__).parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_{timestamp}.json"
    filepath = artifacts_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(artifacts, f, indent=2, default=str)
    
    return filepath


def get_container_logs(compose_stack: Any, service: str, tail: int = 100) -> str:
    """
    Get container logs with optional tail limit.
    
    Args:
        compose_stack: DockerComposeStack instance
        service: Service name
        tail: Number of lines to get from end (default: 100)
        
    Returns:
        Log content as string
    """
    try:
        logs = compose_stack.logs(service)
        lines = logs.split("\n")
        if len(lines) > tail:
            lines = lines[-tail:]
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting logs: {e}"


def format_artifact_summary(artifacts_dir: Path) -> str:
    """
    Format a human-readable summary of captured artifacts.
    
    Args:
        artifacts_dir: Path to artifact directory
        
    Returns:
        Formatted summary string
    """
    if not artifacts_dir.exists():
        return f"Artifacts directory not found: {artifacts_dir}"
    
    summary = [f"Artifact Summary: {artifacts_dir.name}", "=" * 50, ""]
    
    # List files
    files = list(artifacts_dir.iterdir())
    summary.append(f"Files captured: {len(files)}")
    summary.append("")
    
    for f in sorted(files):
        size = f.stat().st_size
        summary.append(f"  - {f.name} ({size} bytes)")
    
    # Load and summarize events if available
    events_file = artifacts_dir / "events.jsonl"
    if events_file.exists():
        with open(events_file) as f:
            events = [json.loads(line) for line in f if line.strip()]
        
        event_types = {}
        for e in events:
            et = e.get("event_type", "unknown")
            event_types[et] = event_types.get(et, 0) + 1
        
        summary.append("")
        summary.append("Events captured:")
        for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
            summary.append(f"  - {et}: {count}")
    
    # Load main artifact file for summary
    artifact_file = artifacts_dir / "artifacts.json"
    if artifact_file.exists():
        with open(artifact_file) as f:
            data = json.load(f)
        
        summary.append("")
        summary.append(f"Test: {data.get('test_name', 'unknown')}")
        summary.append(f"Timestamp: {data.get('timestamp', 'unknown')}")
    
    return "\n".join(summary)


# Pytest fixture for automatic artifact capture on failure
import pytest


@pytest.fixture
def artifact_collector():
    """Provide an ArtifactCollector instance."""
    return ArtifactCollector()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture artifacts on test failure.
    
    This requires the test to have `autonomy_stack` and optionally
    `event_capture` fixtures available.
    """
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Check if we have the required fixtures
        if hasattr(item, "funcargs"):
            funcargs = item.funcargs
            if "autonomy_stack" in funcargs:
                try:
                    autonomy_stack = funcargs["autonomy_stack"]
                    event_capture = funcargs.get("event_capture")
                    
                    collector = ArtifactCollector()
                    artifacts_dir = collector.capture_failure_artifacts(
                        test_name=item.name,
                        compose_stack=autonomy_stack.compose,
                        event_capture=event_capture
                    )
                    
                    # Add artifact location to report
                    report.artifacts_dir = str(artifacts_dir)
                    
                    # Print summary
                    print(f"\nArtifacts captured: {artifacts_dir}")
                    print(format_artifact_summary(artifacts_dir))
                    
                except Exception as e:
                    print(f"Failed to capture artifacts: {e}")
