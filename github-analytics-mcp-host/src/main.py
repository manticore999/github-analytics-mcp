

import sys
from pathlib import Path
import asyncio
from loguru import logger


sys.path.insert(0, str(Path(__file__).parent))

from host.host import MCPHost
from config import settings
import utils.opik_utils as opik_utils


async def interactive_mode():
    """Run interactive CLI mode."""
    logger.info("Starting GitHub Analytics MCP Host")
    logger.info(f"Using model: {settings.groq_model}")
    logger.info(f"Connected to MCP server: {settings.mcp_server_url}")
    
    async with MCPHost() as host:
        logger.success("Host initialized! Ready for queries.\n")
        
        print("=" * 70)
        print("🚀 GitHub Analytics - Interactive Mode")
        print("=" * 70)
        print("\nAsk questions about GitHub repositories!")
        print("Examples:")
        print("  - How many stars does facebook/react have?")
        print("  - Compare React and Vue")
        print("  - Full health check for kubernetes/kubernetes")
        print("\nType 'exit' or 'quit' to stop.\n")
        print("=" * 70 + "\n")
        
        while True:
            try:
                # Get user input
                user_query = input("📝 Your question: ").strip()
                
                # Check for exit commands
                if user_query.lower() in ["exit", "quit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                
                # Skip empty queries
                if not user_query:
                    continue
                
                print("\n🤔 Analyzing...\n")
                
                # Process the query
                answer = await host.process_query(user_query)
                
                # Display the answer
                print("=" * 70)
                print("📊 ANSWER:")
                print("=" * 70)
                print(answer)
                print("=" * 70 + "\n")
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                print(f"\n❌ Error: {e}\n")


async def single_query_mode(query: str):
    """Run a single query and exit."""
    async with MCPHost() as host:
        logger.info(f"Processing query: {query}")
        answer = await host.process_query(query)
        print(answer)


def main():
    """Main entry point."""
    import sys
    
    # Configure Opik tracking
    opik_utils.configure()
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # Check if query provided as command line argument
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        asyncio.run(single_query_mode(query))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
