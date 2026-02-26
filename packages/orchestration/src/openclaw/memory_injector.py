import logging
from pathlib import Path

from openclaw.memory_client import AgentType, MemoryClient

logger = logging.getLogger(__name__)

async def generate_memory_context(
    project_id: str,
    agent_type: AgentType,
    task_description: str,
    workspace_path: Path,
    memu_url: str
) -> None:
    """
    Retrieves context via MemoryClient and writes to workspace/MEMORY.md
    """
    memories = []
    try:
        async with MemoryClient(memu_url, project_id, agent_type) as client:
            retrieved = await client.retrieve(task_description)
            memories = retrieved
    except Exception as e:
        logger.error(f"Failed to retrieve memory context: {e}")

    memory_file = workspace_path / "MEMORY.md"
    
    if not memories:
        memory_file.write_text("# Memory Context\n\nNo relevant prior context found.")
        return

    content = ["# Memory Context\n"]
    for m in memories:
        text = m.get("content", "")
        if text:
            content.append(f"- {text}")
            
    memory_file.write_text("\n".join(content))
