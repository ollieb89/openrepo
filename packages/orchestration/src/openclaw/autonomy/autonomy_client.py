"""
L3 container integration client for autonomy system.

This module provides a client that runs inside L3 containers to communicate
with the orchestrator's autonomy system. It reports state updates, requests
escalations, and maintains sentinel files as a local backup.

The client degrades gracefully if the autonomy endpoint is unavailable,
fallback to sentinel files for state recovery.

Example:
    from openclaw.autonomy.autonomy_client import AutonomyClient
    
    client = AutonomyClient("task-123", "http://host.docker.internal:8080")
    client.report_state_update("executing", 0.85)
"""

import json
import logging
import time
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("openclaw.autonomy.client")

# Sentinel file constants
SENTINEL_DIR = "/tmp/openclaw/autonomy"
SENTINEL_VERSION = "1.0"

# HTTP retry constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_TIMEOUT = 5.0  # seconds


@dataclass
class AutonomyClientConfig:
    """Configuration for the autonomy client."""
    task_id: str
    base_url: str
    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    timeout: float = DEFAULT_TIMEOUT
    sentinel_dir: str = SENTINEL_DIR


class AutonomyClient:
    """
    HTTP client for L3 containers to report autonomy state to orchestrator.
    
    This client runs inside L3 containers and communicates with the
    orchestrator's autonomy HTTP endpoint. It implements retry logic
    with exponential backoff and maintains sentinel files as backup.
    
    The client gracefully degrades if the endpoint is unavailable - 
    state updates are written to sentinel files and can be recovered later.
    
    Attributes:
        task_id: The task identifier
        base_url: Base URL of the orchestrator autonomy endpoint
        max_retries: Maximum retry attempts for HTTP calls
        base_delay: Initial delay between retries (doubles each attempt)
        timeout: HTTP request timeout in seconds
    
    Example:
        client = AutonomyClient("task-123", "http://host.docker.internal:8080")
        
        # Report state update
        client.report_state_update("executing", 0.85)
        
        # Request escalation
        client.request_escalation("Confidence below threshold")
    """
    
    def __init__(
        self,
        task_id: str,
        base_url: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.config = AutonomyClientConfig(
            task_id=task_id,
            base_url=base_url.rstrip("/"),
            max_retries=max_retries,
            base_delay=base_delay,
            timeout=timeout,
        )
        self._session = None
        self._ensure_sentinel_dir()
    
    def _ensure_sentinel_dir(self) -> None:
        """Create sentinel directory if it doesn't exist."""
        Path(self.config.sentinel_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_sentinel_path(self) -> str:
        """Get the sentinel file path for this task."""
        return os.path.join(self.config.sentinel_dir, f"{self.config.task_id}.json")
    
    def _write_sentinel(self, data: Dict[str, Any]) -> None:
        """
        Write state to sentinel file as backup.
        
        Args:
            data: State data to persist
        """
        sentinel_path = self._get_sentinel_path()
        sentinel_data = {
            "version": SENTINEL_VERSION,
            "task_id": self.config.task_id,
            "timestamp": time.time(),
            "data": data,
        }
        try:
            with open(sentinel_path, "w") as f:
                json.dump(sentinel_data, f, indent=2)
            logger.debug(f"Wrote sentinel file: {sentinel_path}")
        except Exception as e:
            logger.warning(f"Failed to write sentinel file: {e}")
    
    def _read_sentinel(self) -> Optional[Dict[str, Any]]:
        """
        Read state from sentinel file.
        
        Returns:
            State data if file exists and is valid, None otherwise
        """
        sentinel_path = self._get_sentinel_path()
        try:
            with open(sentinel_path, "r") as f:
                sentinel_data = json.load(f)
            
            # Validate version
            if sentinel_data.get("version") != SENTINEL_VERSION:
                logger.warning(f"Sentinel version mismatch: {sentinel_data.get('version')}")
                return None
            
            return sentinel_data.get("data")
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"Failed to read sentinel file: {e}")
            return None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic and exponential backoff.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response data if successful, None if all retries failed
        """
        import urllib.request
        import urllib.error
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        # Prepare request
        if data:
            body = json.dumps(data).encode("utf-8")
        else:
            body = None
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )
                
                with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                    response_data = response.read().decode("utf-8")
                    if response_data:
                        return json.loads(response_data)
                    return {"status": "ok"}
                    
            except urllib.error.HTTPError as e:
                last_error = e
                # Don't retry 4xx errors (client errors)
                if 400 <= e.code < 500:
                    logger.warning(f"HTTP {e.code} error, not retrying: {e}")
                    return None
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
            
            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                delay = self.config.base_delay * (2 ** attempt)
                logger.debug(f"Retrying in {delay}s...")
                time.sleep(delay)
        
        logger.error(f"All {self.config.max_retries} retries failed: {last_error}")
        return None
    
    def report_state_update(
        self,
        state: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Report a state update to the orchestrator.
        
        Writes to sentinel file regardless of HTTP success. Returns True
        if HTTP request succeeded, False if only sentinel was written.
        
        Args:
            state: New autonomy state (e.g., "executing", "blocked")
            confidence: Current confidence score (0.0-1.0)
            metadata: Optional additional data
            
        Returns:
            True if HTTP request succeeded, False otherwise
            
        Example:
            success = client.report_state_update("executing", 0.85, {
                "progress_percent": 50,
                "current_step": "Implementing core logic",
            })
        """
        data = {
            "task_id": self.config.task_id,
            "state": state,
            "confidence": confidence,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        
        # Always write sentinel file first (backup)
        self._write_sentinel(data)
        
        # Attempt HTTP request
        response = self._make_request(
            "POST",
            "/api/v1/autonomy/state",
            data,
        )
        
        if response is not None:
            logger.info(f"Reported state update: {state} (confidence: {confidence})")
            return True
        else:
            logger.warning(f"State update via HTTP failed, sentinel file written")
            return False
    
    def request_escalation(self, reason: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Request human escalation for the task.
        
        Args:
            reason: Why escalation is needed
            context: Additional context for the human reviewer
            
        Returns:
            True if HTTP request succeeded, False otherwise
            
        Example:
            client.request_escalation(
                "Confidence below threshold",
                {"current_confidence": 0.45, "uncertainty_areas": ["requirements"]}
            )
        """
        data = {
            "task_id": self.config.task_id,
            "reason": reason,
            "context": context or {},
            "timestamp": time.time(),
        }
        
        # Write escalation request to sentinel
        sentinel_data = {
            "type": "escalation_request",
            **data,
        }
        self._write_sentinel(sentinel_data)
        
        # Attempt HTTP request
        response = self._make_request(
            "POST",
            "/api/v1/autonomy/escalate",
            data,
        )
        
        if response is not None:
            logger.info(f"Requested escalation: {reason}")
            return True
        else:
            logger.warning(f"Escalation request via HTTP failed, sentinel file written")
            return False
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the current autonomy state from the orchestrator.
        
        Falls back to sentinel file if HTTP request fails.
        
        Returns:
            Current state data, or None if unavailable
            
        Example:
            state = client.get_current_state()
            if state:
                print(f"Current state: {state['state']}")
        """
        # Try HTTP first
        response = self._make_request(
            "GET",
            f"/api/v1/autonomy/state/{self.config.task_id}",
        )
        
        if response is not None:
            return response
        
        # Fall back to sentinel file
        logger.debug("Falling back to sentinel file for state")
        return self._read_sentinel()
    
    def clear_sentinel(self) -> bool:
        """
        Remove the sentinel file for this task.
        
        Returns:
            True if file was removed or didn't exist, False on error
            
        Example:
            # Clean up after task completion
            client.clear_sentinel()
        """
        sentinel_path = self._get_sentinel_path()
        try:
            if os.path.exists(sentinel_path):
                os.remove(sentinel_path)
                logger.debug(f"Removed sentinel file: {sentinel_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove sentinel file: {e}")
            return False


def create_client_from_env() -> Optional[AutonomyClient]:
    """
    Create an AutonomyClient from environment variables.
    
    Environment variables:
    - OPENCLAW_TASK_ID: Task identifier (required)
    - OPENCLAW_ORCHESTRATOR_URL: Orchestrator URL (default: http://host.docker.internal:8080)
    - OPENCLAW_AUTONOMY_RETRIES: Max retries (default: 3)
    
    Returns:
        AutonomyClient if OPENCLAW_TASK_ID is set, None otherwise
        
    Example:
        client = create_client_from_env()
        if client:
            client.report_state_update("executing", 0.9)
    """
    task_id = os.environ.get("OPENCLAW_TASK_ID")
    if not task_id:
        logger.debug("OPENCLAW_TASK_ID not set, skipping autonomy client creation")
        return None
    
    base_url = os.environ.get(
        "OPENCLAW_ORCHESTRATOR_URL",
        "http://host.docker.internal:8080"
    )
    
    max_retries = int(os.environ.get("OPENCLAW_AUTONOMY_RETRIES", DEFAULT_MAX_RETRIES))
    
    return AutonomyClient(
        task_id=task_id,
        base_url=base_url,
        max_retries=max_retries,
    )


__all__ = [
    "AutonomyClient",
    "AutonomyClientConfig",
    "create_client_from_env",
    "SENTINEL_VERSION",
    "SENTINEL_DIR",
]
