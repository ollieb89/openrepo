import asyncio
import os

from dotenv import load_dotenv
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

# Load environment variables from .env file
load_dotenv()


async def get_user_input() -> tuple[str | None, bool]:
    """Get input from the user."""
    try:
        user_input = input("\nYou: ").strip()
    except EOFError:
        return None, True

    if not user_input:
        return None, False

    if user_input.lower() in ("quit", "exit"):
        return None, True

    return user_input, False


async def process_response(client: ClaudeSDKClient) -> list[str]:
    """Process the assistant response and return collected text parts."""
    assistant_text_parts: list[str] = []

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
                    assistant_text_parts.append(block.text)

    return assistant_text_parts


async def run_conversation_loop(client: ClaudeSDKClient) -> None:
    """Run the main conversation loop."""
    print("Claude Autorun (Simple - No Memory)")
    print("Type 'quit' or 'exit' to end the session.")
    print("-" * 40)

    while True:
        user_input, should_break = await get_user_input()

        if should_break:
            break
        if user_input is None:
            continue

        await client.query(user_input)
        await process_response(client)


async def main():
    options = ClaudeAgentOptions()

    async with ClaudeSDKClient(options=options) as client:
        await run_conversation_loop(client)

    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
