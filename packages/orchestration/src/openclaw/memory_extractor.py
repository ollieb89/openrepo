import logging
from typing import Any, Dict

from openclaw.memory_client import AgentType, MemoryClient

logger = logging.getLogger(__name__)

async def extract_and_memorize(
    project_id: str,
    agent_type: AgentType,
    task_result: Dict[str, Any],
    status: str,
    memu_url: str
) -> None:
    """
    Extracts learnings from task result and memorizes them.
    """
    if status not in ("completed", "failed", "rejected"):
        return
        
    description = task_result.get("description", "")
    summary = task_result.get("summary", "")
    
    if not description and not summary:
        return
        
    # Format the payload based on agent type
    agent_context = ""
    if agent_type == AgentType.L2_PM:
        agent_context = "Project Management / Architecture Decision"
    elif agent_type == AgentType.L3_CODE:
        agent_context = "Implementation / Code Pattern"
    elif agent_type == AgentType.L3_TEST:
        agent_context = "Testing / Edge Case"
        
    payload = f"[{agent_context}] Task {status.upper()}:\n"
    if description:
        payload += f"Description: {description}\n"
    if summary:
        payload += f"Outcome/Learnings: {summary}\n"
        
    try:
        async with MemoryClient(memu_url, project_id, agent_type) as client:
            await client.memorize(payload)
    except Exception as e:
        logger.error(f"Failed to extract and memorize: {e}")
