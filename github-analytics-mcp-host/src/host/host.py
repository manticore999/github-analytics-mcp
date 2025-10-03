"""
MCPHost: Orchestrates the agentic loop with Groq LLM.

This class handles:
- Converting MCP tools to OpenAI/Groq format
- Managing conversation with the LLM
- Executing tool calls via ConnectionManager
- Implementing the agentic loop (max iterations)
"""

import sys
from pathlib import Path
from typing import Any, Optional
from openai import OpenAI
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from host.connection_manager import ConnectionManager
from config import settings
import utils.opik_utils as opik_utils

# Import opik if available
if opik_utils.is_enabled():
    import opik


class MCPHost:
    """Orchestrator that connects MCP tools with Groq LLM."""
    
    def __init__(self):
        """Initialize the MCP host."""
        self.connection_manager = ConnectionManager()
        self.groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key
        )
        self.system_prompt: Optional[str] = None
        self.tools_for_llm: list[dict] = []
    
    async def initialize(self) -> None:
        """
        Initialize the host:
        1. Connect to MCP server
        2. Fetch system prompt
        3. Convert tools to OpenAI format
        """
        logger.info("Initializing MCPHost...")
        
        # Connect to MCP server
        await self.connection_manager.initialize()
        
        # Fetch system prompt from MCP server with required arguments
        # The prompt function expects: arguments: dict with 'context' inside
        # MCP protocol wraps it as: {"arguments": json_string}
        import json
        prompt_result = await self.connection_manager.get_prompt(
            settings.system_prompt_name,
            arguments={"arguments": json.dumps({"context": ""})}  # Empty context initially
        )
        self.system_prompt = prompt_result.messages[0].content.text
        logger.info("System prompt loaded")
        
        # Convert MCP tools to OpenAI format
        mcp_tools = self.connection_manager.get_tools()
        self.tools_for_llm = [self._convert_tool(tool) for tool in mcp_tools]
        logger.success(f"MCPHost initialized with {len(self.tools_for_llm)} tools")
    
    def _convert_tool(self, mcp_tool: dict) -> dict:
        """
        Convert MCP tool format to OpenAI/Groq format.
        
        Args:
            mcp_tool: Tool in MCP format
            
        Returns:
            Tool in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool["description"],
                "parameters": mcp_tool["inputSchema"]
            }
        }
    
    async def process_query(self, user_query: str) -> str:
        """
        Process a user query using the agentic loop.
        
        Args:
            user_query: The user's question
            
        Returns:
            Final answer from the LLM
        """
        # Track with Opik if enabled
        if opik_utils.is_enabled():
            return await self._process_query_with_tracking(user_query)
        else:
            return await self._process_query_internal(user_query)
    
    @opik.track(name="process-query", type="general") if opik_utils.is_enabled() else lambda f: f
    async def _process_query_with_tracking(self, user_query: str) -> str:
        """Process query with Opik tracking."""
        return await self._process_query_internal(user_query)
    
    async def _process_query_internal(self, user_query: str) -> str:
        """Internal query processing logic."""
        logger.info(f"Processing query: {user_query}")
        
        # Initialize conversation with system prompt and user query
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        for iteration in range(settings.max_iterations):
            logger.info(f"🔄 Iteration {iteration + 1}/{settings.max_iterations}")
            
            # Call LLM
            response = self.groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                tools=self.tools_for_llm,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Log what LLM decided
            if assistant_message.tool_calls:
                tool_names = [tc.function.name for tc in assistant_message.tool_calls]
                logger.info(f"🤖 LLM Decision: Call {len(tool_names)} tools: {', '.join(tool_names)}")
            else:
                logger.info(f"🤖 LLM Decision: Provide final answer")
            
            # Add assistant response to conversation
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": assistant_message.tool_calls
            })
            
            # If no tool calls, LLM has final answer
            if not assistant_message.tool_calls:
                logger.success("✨ Query completed - LLM provided final answer")
                return assistant_message.content
            
            # Execute tool calls
            logger.info(f"🔧 Executing {len(assistant_message.tool_calls)} tool call(s)")
            
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = eval(tool_call.function.arguments)  # Parse JSON string
                
                logger.info(f"📞 Calling: {tool_name}")
                logger.debug(f"   Args: {tool_args}")
                
                # Execute tool via MCP
                result = await self.connection_manager.call_tool(tool_name, tool_args)
                
                # Extract text content from result
                result_text = self._extract_result_text(result)
                
                logger.info(f"✅ Result: {result_text[:100]}...")  # Show first 100 chars
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text
                })
                
                logger.success(f"Tool {tool_name} completed")
        
        # Max iterations reached
        logger.warning("Max iterations reached")
        return "I apologize, but I've reached my maximum number of analysis steps. Please try rephrasing your question or breaking it into smaller parts."
    
    def _extract_result_text(self, result: Any) -> str:
        """
        Extract text content from MCP tool result.
        
        Args:
            result: Tool execution result
            
        Returns:
            Text representation of the result
        """
        # MCP results have a 'content' list with text/image/resource items
        if hasattr(result, 'content') and result.content:
            # Get first text item
            for item in result.content:
                if hasattr(item, 'text'):
                    return item.text
        
        # Fallback: convert to string
        return str(result)
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.connection_manager.cleanup()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
