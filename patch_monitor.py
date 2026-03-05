import sys

with open("packages/orchestration/src/openclaw/cli/monitor.py", "r") as f:
    content = f.read()

# Add new tail_events function before def main
tail_events_code = """
import asyncio
from openclaw.events.transport import event_bridge

async def tail_events(project_id: str = None):
    \"\"\"Stream events in real-time using UnixSocketTransport.\"\"\"
    print(f"{Colors.BLUE}Streaming live events...{Colors.RESET}")
    
    def render_event(event):
        if project_id and event.project_id != project_id:
            return
            
        color = Colors.BLUE
        if 'error' in event.type.value or 'failed' in event.type.value:
            color = Colors.RED
        elif 'completed' in event.type.value:
            color = Colors.GREEN
            
        task_str = f" [Task: {event.task_id}]" if event.task_id else ""
        print(f"[{event.timestamp:.2f}] {color}{event.type.value}{Colors.RESET}{task_str} Domain: {event.domain.value} Payload: {event.payload}")

    event_bridge.subscribe("openclaw.*", render_event)
    await event_bridge.start_server()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await event_bridge.stop_server()

def run_tail_events(project_id: str = None):
    asyncio.run(tail_events(project_id))

def main():"""

content = content.replace("def main():", tail_events_code)

# Add --events flag
arg_patch = """
    tail_parser.add_argument(
        '--events',
        action='store_true',
        help='Stream via cross-runtime event bridge instead of polling'
    )
    tail_parser.add_argument(
        '--state-file',"""

content = content.replace("    tail_parser.add_argument(\n        '--state-file',", arg_patch)

# Route to run_tail_events if flag set
route_patch = """
    if args.command == 'tail':
        if getattr(args, 'events', False):
            project_id = get_active_project_env()
            run_tail_events(project_id)
            return
        
        state_file = getattr(args, 'state_file', None)"""

content = content.replace("    if args.command == 'tail':\n        state_file = getattr(args, 'state_file', None)", route_patch)

with open("packages/orchestration/src/openclaw/cli/monitor.py", "w") as f:
    f.write(content)
