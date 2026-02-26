"""Mock LLM server for E2E testing with deterministic responses."""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load responses from environment-specified directory
RESPONSES_DIR = Path(os.environ.get("RESPONSES_DIR", "/app/responses"))


def load_responses() -> Dict[str, Any]:
    """Load all JSON response files from the responses directory."""
    responses = {}
    if RESPONSES_DIR.exists():
        for response_file in RESPONSES_DIR.glob("*.json"):
            try:
                with open(response_file) as f:
                    responses[response_file.stem] = json.load(f)
            except json.JSONDecodeError:
                app.logger.warning(f"Failed to parse {response_file}")
    return responses


def match_request_to_response(prompt: str, responses: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Match the incoming prompt to a predefined response.
    
    Uses keyword matching to determine which response file to return.
    """
    prompt_lower = prompt.lower()
    
    # Check for planning-related prompts
    if "plan" in prompt_lower and "steps" in prompt_lower:
        if "plan" in responses:
            return responses["plan"]
        # Default plan response
        return {
            "steps": [
                {"id": "1", "action": "Analyze requirements", "expected_outcome": "Clear scope"},
                {"id": "2", "action": "Execute task", "expected_outcome": "Task completed"}
            ]
        }
    
    # Check for tool analysis prompts
    if "tool" in prompt_lower and "categor" in prompt_lower:
        if "tools" in responses:
            return responses["tools"]
        return ["file_read", "file_write"]
    
    # Check for execution prompts
    if "execute" in prompt_lower or "step" in prompt_lower:
        if "execute" in responses:
            return responses["execute"]
        return "Step executed successfully"
    
    # Check for reflection/course correction prompts
    if "recovery" in prompt_lower or "course correction" in prompt_lower:
        if "recovery" in responses:
            return responses["recovery"]
        return {"steps": [{"id": "r1", "action": "Fix and retry", "expected_outcome": "Issue resolved"}]}
    
    # Default response
    return {"content": "Mock LLM response", "status": "success"}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "responses_loaded": len(load_responses())})


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint.
    
    Returns deterministic responses based on the prompt content.
    """
    data = request.get_json() or {}
    messages = data.get("messages", [])
    
    # Extract the latest user message
    prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            prompt = msg.get("content", "")
            break
    
    responses = load_responses()
    response_content = match_request_to_response(prompt, responses)
    
    # Format as OpenAI-compatible response
    return jsonify({
        "id": "mock-completion",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "mock-llm",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(response_content) if isinstance(response_content, dict) else str(response_content)
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 50,
            "total_tokens": len(prompt.split()) + 50
        }
    })


@app.route("/responses", methods=["GET"])
def list_responses():
    """List available response files."""
    responses = load_responses()
    return jsonify({
        "available_responses": list(responses.keys()),
        "responses_dir": str(RESPONSES_DIR)
    })


@app.route("/responses/<name>", methods=["POST"])
def add_response(name: str):
    """Add or update a response file dynamically."""
    data = request.get_json()
    response_file = RESPONSES_DIR / f"{name}.json"
    
    with open(response_file, "w") as f:
        json.dump(data, f, indent=2)
    
    return jsonify({"status": "created", "name": name})


def create_app(responses: Dict[str, Any] = None) -> Flask:
    """Factory function for creating the Flask app with pre-loaded responses."""
    if responses:
        # Pre-populate responses directory
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in responses.items():
            response_file = RESPONSES_DIR / f"{name}.json"
            with open(response_file, "w") as f:
                json.dump(content, f, indent=2)
    
    return app


if __name__ == "__main__":
    # Ensure responses directory exists
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
