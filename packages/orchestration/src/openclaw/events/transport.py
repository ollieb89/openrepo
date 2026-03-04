"Bidirectional event transport over Unix domain socket."

import asyncio
import atexit
import json
import logging
import os
import time
from typing import Callable, Dict, Optional, Set
from .protocol import OrchestratorEvent

logger = logging.getLogger("openclaw.events.transport")


def get_socket_path() -> str:
    """Return the Unix socket path for the event bridge.

    Resolution order:
    1. OPENCLAW_EVENTS_SOCK env var (explicit override for testing / custom installs)
    2. $OPENCLAW_ROOT/run/events.sock  (derived from OPENCLAW_ROOT via config)
    3. ~/.openclaw/run/events.sock     (default fallback)
    """
    env_override = os.environ.get("OPENCLAW_EVENTS_SOCK")
    if env_override:
        return env_override
    # Lazy import to avoid circular dependency at module level
    try:
        from openclaw.config import get_project_root
        return str(get_project_root() / "run" / "events.sock")
    except Exception:
        return str(os.path.join(os.path.expanduser("~"), ".openclaw", "run", "events.sock"))


class UnixSocketTransport:
    """Bidirectional event transport over Unix domain socket."""

    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._server = None
        self._clients: Set[asyncio.StreamWriter] = set()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval: int = 30

    @property
    def SOCKET_PATH(self) -> str:
        """Socket path derived from OPENCLAW_ROOT at runtime."""
        return get_socket_path()

    async def start_server(self) -> bool:
        """Start the Unix domain socket server.

        Returns:
            True if the server was started successfully, False if another
            process already owns the socket (stale-socket detection).
        """
        socket_path = get_socket_path()

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(socket_path), exist_ok=True)

        if os.path.exists(socket_path):
            # Stale-socket detection: try to connect with a short timeout.
            # If connection succeeds, another process owns the socket — skip.
            # If connection fails (ConnectionRefusedError), it is stale — remove.
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(socket_path), timeout=0.5
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                logger.info(f"Event socket already owned by another process: {socket_path}")
                return False
            except (ConnectionRefusedError, FileNotFoundError):
                # Stale socket file — remove and start fresh
                try:
                    os.remove(socket_path)
                except OSError:
                    pass
            except asyncio.TimeoutError:
                # No response in 0.5s — treat as stale
                try:
                    os.remove(socket_path)
                except OSError:
                    pass
            except Exception:
                # Any other error: remove and proceed
                try:
                    os.remove(socket_path)
                except OSError:
                    pass

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=socket_path
        )

        # Register atexit cleanup so socket file is removed on graceful exit
        atexit.register(self._cleanup_socket, socket_path)

        # Start heartbeat loop to keep connected clients alive
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

        logger.info(f"Event server started on {socket_path}")
        return True

    def _cleanup_socket(self, socket_path: str) -> None:
        """Remove the socket file on process exit (atexit callback)."""
        try:
            if os.path.exists(socket_path):
                os.remove(socket_path)
        except OSError:
            pass

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all connected clients."""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            heartbeat = json.dumps({"type": "heartbeat", "timestamp": time.time()}) + "\n"
            heartbeat_bytes = heartbeat.encode("utf-8")
            disconnected = set()
            for writer in list(self._clients):
                try:
                    writer.write(heartbeat_bytes)
                    await writer.drain()
                except ConnectionError:
                    disconnected.add(writer)
            for writer in disconnected:
                self._clients.discard(writer)
                writer.close()

    async def stop_server(self):
        """Stop the server and close all client connections."""
        # Cancel heartbeat before closing clients
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for writer in list(self._clients):
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        socket_path = get_socket_path()
        if os.path.exists(socket_path):
            try:
                os.remove(socket_path)
            except OSError:
                pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connections and messages from clients."""
        self._clients.add(writer)
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                try:
                    event_data = data.decode('utf-8').strip()
                    if event_data:
                        event = OrchestratorEvent.from_json(event_data)
                        await self._route_event(event)
                except Exception as e:
                    logger.error(f"Error handling client data: {e}")
        finally:
            self._clients.discard(writer)
            writer.close()

    async def _route_event(self, event: OrchestratorEvent):
        """Route an incoming event to registered subscribers."""
        logger.info(
            f"{event.type.value}",
            extra={
                "event_domain": event.domain.value,
                "project_id": event.project_id,
                "agent_id": event.agent_id,
                "task_id": event.task_id,
                "correlation_id": event.correlation_id,
            }
        )
        
        pattern = f"{event.domain.value}.{event.type.value}"
        handlers = self._subscribers.get(pattern, set()) | self._subscribers.get("*", set()) | self._subscribers.get(f"{event.domain.value}.*", set())
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in subscriber handler for {pattern}: {e}")

    async def publish(self, event: OrchestratorEvent):
        """Publish event to all connected subscribers and local handlers."""
        # Route locally first
        await self._route_event(event)
        
        # Then publish to all connected clients
        event_json = event.to_json() + "\n"
        event_bytes = event_json.encode('utf-8')
        
        disconnected = set()
        for writer in self._clients:
            try:
                writer.write(event_bytes)
                await writer.drain()
            except ConnectionError:
                disconnected.add(writer)
                
        for writer in disconnected:
            self._clients.discard(writer)
            writer.close()

    def subscribe(self, pattern: str, handler: Callable):
        """Subscribe to events matching pattern (e.g., 'openclaw.task.*')."""
        if pattern not in self._subscribers:
            self._subscribers[pattern] = set()
        self._subscribers[pattern].add(handler)

    def unsubscribe(self, pattern: str, handler: Callable):
        """Unsubscribe from events."""
        if pattern in self._subscribers:
            self._subscribers[pattern].discard(handler)
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]

# Singleton instance for easy importing
event_bridge = UnixSocketTransport()
