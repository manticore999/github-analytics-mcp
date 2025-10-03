import sys
from pathlib import Path
from contextlib import AsyncExitStack
from typing import Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
import utils.opik_utils as opik_utils

# Import opik if available
if opik_utils.is_enabled():
    import opik


class ConnectionManager:
    """Manages the MCP client connection and tool operations."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._tools: list[dict] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize connection to the MCP server via HTTP.
        
        Connects to the MCP server, discovers available tools and prompts.
        """
        if self._initialized:
            logger.warning("ConnectionManager already initialized")
            return
        
        try:
            logger.info(f"Connecting to MCP server at {settings.mcp_server_url}")
            
            read_stream, write_stream, get_session_id = await self.exit_stack.enter_async_context(
                streamablehttp_client(url=settings.mcp_server_url)
            )
            
            logger.info("Streams established, creating session...")
            
            # Create ClientSession from streams
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            logger.info("MCP session created")
            
            # Initialize the session
            await self.session.initialize()
            logger.info("MCP session initialized")
            
            # Discover available tools and prompts
            await self._discover_tools()
            await self._discover_prompts()
            
            self._initialized = True
            logger.success(f"ConnectionManager initialized with {len(self._tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConnectionManager: {e}")
            raise
    
    async def _discover_prompts(self) -> None:
        """
        Discover and log all available prompts from the MCP server.
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            # List all available prompts
            result = await self.session.list_prompts()
            
            logger.info(f"Discovered {len(result.prompts)} prompts:")
            for prompt in result.prompts:
                logger.info(f"  - {prompt.name}: {prompt.description or 'No description'}")
        
        except Exception as e:
            logger.warning(f"Failed to discover prompts: {e}")
    
    async def _discover_tools(self) -> None:
        """
        Discover and cache all available tools from the MCP server.
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            # List all available tools
            result = await self.session.list_tools()
            self._tools = [tool.model_dump() for tool in result.tools]
            
            logger.info(f"Discovered {len(self._tools)} tools:")
            for tool in self._tools:
                logger.debug(f"  - {tool['name']}: {tool.get('description', 'No description')}")
        
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            raise
    
    def get_tools(self) -> list[dict]:
        """
        Get all available tools.
        
        Returns:
            List of tool definitions with name, description, and input schema.
        """
        if not self._initialized:
            raise RuntimeError("ConnectionManager not initialized. Call initialize() first.")
        
        return self._tools
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        # Track with Opik if enabled
        if opik_utils.is_enabled():
            return await self._call_tool_with_tracking(tool_name, arguments)
        else:
            return await self._call_tool_internal(tool_name, arguments)
    
    async def _call_tool_internal(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Internal method to call tool without tracking."""
        try:
            logger.info(f"Calling tool: {tool_name} with args: {arguments}")
            
            result = await self.session.call_tool(tool_name, arguments)
            
            logger.success(f"Tool {tool_name} executed successfully")
            return result
        
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    @opik.track(name="call-tool", type="tool") if opik_utils.is_enabled() else lambda f: f
    async def _call_tool_with_tracking(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call tool with Opik tracking."""
        return await self._call_tool_internal(tool_name, arguments)
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """
        Get a prompt from the MCP server.
        
        Args:
            prompt_name: Name of the prompt to fetch
            arguments: Optional arguments for the prompt
            
        Returns:
            Prompt content
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            logger.info(f"Fetching prompt: {prompt_name}")
            
            result = await self.session.get_prompt(prompt_name, arguments or {})
            
            logger.success(f"Prompt {prompt_name} fetched successfully")
            return result
        
        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_name}: {e}")
            raise
    
    async def cleanup(self) -> None:
        """
        Cleanup and close the MCP connection.
        """
        try:
            logger.info("Cleaning up ConnectionManager")
            await self.exit_stack.aclose()
            self._initialized = False
            logger.success("ConnectionManager cleaned up")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
