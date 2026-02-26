"""
Mock LLM server for E2E testing.

Provides deterministic OpenAI-compatible API responses for testing
the autonomy framework without hitting real LLM APIs.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from flask import Flask, request, jsonify


app = Flask(__name__)


@dataclass
class MockResponse:
    """A configured mock response."""
    pattern: str
    response: Dict[str, Any]
    match_count: int = 0
    priority: int = 0


class MockLLMStore:
    """Stores and manages mock LLM responses."""
    
    def __init__(self):
        self.responses: List[MockResponse] = []
        self.calls: List[Dict[str, Any]] = []
    
    def add_response(self, pattern: str, response: Dict[str, Any], priority: int = 0) -> None:
        """Add a mock response for a pattern."""
        self.responses.append(MockResponse(
            pattern=pattern,
            response=response,
            priority=priority
        ))
        # Sort by priority (higher first)
        self.responses.sort(key=lambda r: r.priority, reverse=True)
    
    def find_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Find a matching response for the given content."""
        for mock_resp in self.responses:
            if mock_resp.pattern.lower() in content.lower():
                mock_resp.match_count += 1
                return mock_resp.response
        return None
    
    def record_call(self, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> None:
        """Record an API call."""
        self.calls.append({
            "request": request_data,
            "response": response_data,
        })
    
    def reset(self) -> None:
        """Clear all responses and calls."""
        self.responses.clear()
        self.calls.clear()
    
    def get_calls(self) -> List[Dict[str, Any]]:
        """Get all recorded calls."""
        return self.calls.copy()


# Global store instance
store = MockLLMStore()


# Default responses for common patterns
DEFAULT_RESPONSES = [
    # Plan generation response
    (
        "plan",
        {
            "content": json.dumps({
                "steps": [
                    {"step": 1, "action": "Analyze requirements", "tool": "none"},
                    {"step": 2, "action": "Execute task", "tool": "code_executor"},
                    {"step": 3, "action": "Verify result", "tool": "none"}
                ],
                "estimated_duration": "30s"
            })
        },
        10
    ),
    # Tool selection response
    (
        "tool",
        {
            "content": json.dumps({
                "selected_tools": ["code_executor", "file_reader"],
                "reasoning": "Task requires code execution and file access"
            })
        },
        5
    ),
    # Success execution response
    (
        "execute",
        {
            "content": "Task completed successfully. Output verified."
        },
        1
    ),
    # Step failure response (for retry testing)
    (
        "fail",
        {
            "content": None,
            "error": "Step execution failed: mock failure for testing"
        },
        100  # High priority to override
    ),
    # Recovery response
    (
        "recover",
        {
            "content": json.dumps({
                "recovery_steps": [
                    {"step": 1, "action": "Diagnose issue", "tool": "none"},
                    {"step": 2, "action": "Apply fix", "tool": "code_executor"}
                ]
            })
        },
        50
    ),
    # Escalation trigger (low confidence)
    (
        "escalate",
        {
            "content": "Unable to proceed with confidence. Escalation required."
        },
        90
    ),
]


def init_defaults():
    """Initialize default responses."""
    for pattern, response, priority in DEFAULT_RESPONSES:
        store.add_response(pattern, response, priority)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "responses_configured": len(store.responses)})


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint.
    
    Returns deterministic responses based on pattern matching
    against the request content.
    """
    data = request.get_json() or {}
    
    # Extract content from messages
    messages = data.get("messages", [])
    content = " ".join(
        msg.get("content", "") for msg in messages if msg.get("content")
    )
    
    # Find matching response
    response_data = store.find_response(content)
    
    if response_data is None:
        # Default fallback response
        response_data = {"content": "Default mock response"}
    
    # Build OpenAI-compatible response
    openai_response = {
        "id": f"mock-{len(store.calls)}",
        "object": "chat.completion",
        "created": 1234567890,
        "model": data.get("model", "gpt-4-mock"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_data.get("content")
                },
                "finish_reason": "stop" if response_data.get("content") else "error"
            }
        ],
        "usage": {
            "prompt_tokens": len(content.split()),
            "completion_tokens": len(str(response_data.get("content", "")).split()),
            "total_tokens": 0
        }
    }
    
    # Record the call
    store.record_call(data, response_data)
    
    return jsonify(openai_response)


@app.route("/configure", methods=["POST"])
def configure():
    """Configure a mock response pattern."""
    data = request.get_json() or {}
    pattern = data.get("pattern")
    response = data.get("response")
    priority = data.get("priority", 0)
    
    if not pattern or response is None:
        return jsonify({"error": "Missing pattern or response"}), 400
    
    store.add_response(pattern, response, priority)
    
    return jsonify({
        "status": "configured",
        "pattern": pattern,
        "total_responses": len(store.responses)
    })


@app.route("/reset", methods=["POST"])
def reset():
    """Reset all responses and recorded calls."""
    store.reset()
    init_defaults()
    return jsonify({"status": "reset", "responses_configured": len(store.responses)})


@app.route("/calls", methods=["GET"])
def get_calls():
    """Get recorded API calls."""
    return jsonify(store.get_calls())


@app.route("/responses", methods=["GET"])
def list_responses():
    """List configured response patterns."""
    return jsonify([
        {
            "pattern": r.pattern,
            "match_count": r.match_count,
            "priority": r.priority
        }
        for r in store.responses
    ])


def main():
    """Run the mock LLM server."""
    init_defaults()
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()
