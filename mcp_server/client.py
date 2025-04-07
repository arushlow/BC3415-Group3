from contextlib import AsyncExitStack
from typing import Optional
import asyncio
import threading
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None
        self.stdio = None
        self.write = None
        self.background_task = None
        self.lock = asyncio.Lock()
        self.server_config = None
        self.last_error = None
        self.connecting = False
        self._loop = None
        self._thread = None
        self._running = False

    def start_background_loop(self):
        if self._thread and self._thread.is_alive():
            print("Background loop already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_event_loop_in_thread, daemon=True
        )
        self._thread.start()

        time.sleep(0.5)
        print("Background event loop started in separate thread")

    def _run_event_loop_in_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            if self.server_config:
                self._loop.run_until_complete(
                    self.connect_to_server(self.server_config)
                )

            while self._running:
                self._loop.run_until_complete(asyncio.sleep(0.1))
        except Exception as e:
            print(f"Error in background event loop: {e}")
        finally:
            try:
                pending_tasks = asyncio.all_tasks(self._loop)
                for task in pending_tasks:
                    task.cancel()

                if pending_tasks:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending_tasks, return_exceptions=True)
                    )

                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                self._loop.close()
            except Exception as e:
                print(f"Error cleaning up event loop: {e}")

            print("Background event loop stopped")

    def stop_background_loop(self):
        if not self._thread or not self._thread.is_alive():
            return

        self._running = False

        if threading.current_thread() != self._thread:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                print("Warning: Background thread did not terminate properly")

    def run_in_background(self, coro):
        if not self._loop or self._loop.is_closed():
            raise RuntimeError("Background event loop not running")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    async def connect_to_server(self, server_config):
        self.server_config = server_config

        async with self.lock:
            if self.connecting:
                print("Already connecting, waiting...")
                while self.connecting:
                    await asyncio.sleep(0.1)
                if self.session:
                    return self.session

            self.connecting = True

            try:
                if self.session is not None:
                    await self.cleanup_session()

                # Create a new exit stack for each connection
                self.exit_stack = AsyncExitStack()

                server_params = StdioServerParameters(**server_config)
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                self.stdio, self.write = stdio_transport
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(self.stdio, self.write)
                )

                await self.session.initialize()

                # Create a background task to keep the connection alive
                if self.background_task and not self.background_task.done():
                    print("Cancelling existing background task")
                    self.background_task.cancel()
                    try:
                        await asyncio.wait_for(self.background_task, timeout=1.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass

                print("Starting keep-alive task...")
                self.background_task = asyncio.create_task(self._keep_alive())
                self.background_task.add_done_callback(self._on_task_done)

                print("Successfully connected to MCP server")
                self.last_error = None
                return self.session
            except Exception as e:
                self.last_error = str(e)
                print(f"Error in connect_to_server: {e}")
                await self.cleanup_session()
                raise
            finally:
                self.connecting = False

    async def ensure_connected(self):
        if not self.session or hasattr(self.stdio, "_closed") and self.stdio._closed:
            print("Connection closed, reconnecting...")
            if self.server_config:
                try:
                    await self.connect_to_server(self.server_config)
                except Exception as e:
                    print(f"Failed to reconnect: {e}")
                    raise
            else:
                raise RuntimeError("Cannot reconnect: server_config not available")
        return self.session

    async def _keep_alive(self):
        try:
            print("Keep-alive task started")
            while True:
                await asyncio.sleep(30)

                if not self.session:
                    print("Session lost, exiting keep_alive task")
                    break

                if hasattr(self.stdio, "_closed") and self.stdio._closed:
                    print("Connection lost, attempting to reconnect in keep_alive...")
                    try:
                        await self.ensure_connected()
                        print("Successfully reconnected in keep_alive")
                    except Exception as e:
                        print(f"Reconnection failed in keep_alive: {e}")
                        await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Keep-alive task cancelled")
            raise
        except Exception as e:
            print(f"Keep-alive task error: {e}")

        print("Keep-alive task exiting")

    def _on_task_done(self, task):
        try:
            task.result()
        except asyncio.CancelledError:
            print("Background task was cancelled")
        except Exception as e:
            print(f"Background task failed with exception: {e}")
            self.last_error = str(e)

    async def cleanup_session(self):
        try:
            if self.background_task and not self.background_task.done():
                print("Cancelling background task...")
                self.background_task.cancel()
                try:
                    await asyncio.wait_for(self.background_task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    print("Background task cancellation timed out or was cancelled")
                except Exception as e:
                    print(f"Error cancelling background task: {e}")
                self.background_task = None

            if self.exit_stack:
                print("Closing exit stack...")
                try:
                    await self.exit_stack.aclose()
                except Exception as e:
                    print(f"Error closing exit stack: {e}")

            print("Clearing session references...")
            self.exit_stack = None
            self.session = None
            self.stdio = None
            self.write = None
        except Exception as e:
            print(f"Error during session cleanup: {e}")
            self.last_error = str(e)

    async def cleanup(self):
        await self.cleanup_session()
        self.stop_background_loop()

    def list_tools(self):
        async def _list_tools():
            await self.ensure_connected()
            return await self.session.list_tools()

        if threading.current_thread() == self._thread:
            return asyncio.run_coroutine_threadsafe(_list_tools(), self._loop).result(
                timeout=30
            )
        else:
            return self.run_in_background(_list_tools())

    def call_tool(self, name, args):
        async def _call_tool():
            await self.ensure_connected()
            return await self.session.call_tool(name, args)

        if threading.current_thread() == self._thread:
            return asyncio.run_coroutine_threadsafe(_call_tool(), self._loop).result(
                timeout=30
            )
        else:
            return self.run_in_background(_call_tool())
