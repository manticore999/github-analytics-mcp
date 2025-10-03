import opik
from fastmcp import FastMCP
from servers.prompts import GITHUB_ANALYTICS_PROMPT
import utils.opik_utils as opik_utils

opik_utils.configure()
agent_scope_mcp = FastMCP("agent_scope_prompts")


@agent_scope_mcp.prompt(
    name="github_analytics_prompt",
    description="Prompt for analyzing GitHub repositories across multiple dimensions"
)
@opik.track(name="github_analytics_prompt", type="general")
def github_analytics_prompt(arguments: dict):
    """
    Format the GITHUB_ANALYTICS_PROMPT using the provided arguments dict.
    All keys in arguments will be passed as keyword arguments to format().
    
    Args:
        arguments: Dictionary with context information for the analysis
                  Expected key: 'context' (str) - Current analysis context
    """
    return GITHUB_ANALYTICS_PROMPT.get().format(**arguments)



if __name__ == "__main__":
    agent_scope_mcp.run()
