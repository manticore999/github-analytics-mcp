import opik
import logging
from typing import Set

from fastmcp import FastMCP

from servers.repo_stats_server import repo_stats_mcp
from servers.issue_server import issue_mcp
from servers.pr_analytics_server import pr_analytics_mcp
from servers.contributor_server import contributor_mcp
from servers.agent_scope_server import agent_scope_mcp

log = logging.getLogger(__name__)


class McpServersRegistry:
    def __init__(self):
        self.registry = FastMCP("github_analytics_registry")
        self.all_tags: Set[str] = set()
        self._is_initialized = False

    @opik.track(name="tool-registry-initialize", type="general")
    async def initialize(self):
        if self._is_initialized:
            return

        log.info("Initializing McpServersRegistry...")
        await self.registry.import_server(repo_stats_mcp, prefix="repo")
        await self.registry.import_server(issue_mcp, prefix="issue")
        await self.registry.import_server(pr_analytics_mcp, prefix="pr")
        await self.registry.import_server(contributor_mcp, prefix="contributor")
        await self.registry.import_server(agent_scope_mcp, prefix="scope")

        all_tools = await self.registry.get_tools()
        for tool in all_tools.values():
            if tool.tags:
                self.all_tags.update(tool.tags)

        log.info(f"Registry initialization complete. Found tags: {self.all_tags}")
        self._is_initialized = True

    def get_registry(self) -> FastMCP:
        """returns the initialized tool registry."""
        return self.registry

    def get_all_tags(self) -> Set[str]:
        """returns the pre-calculated set of all tool tags."""
        return self.all_tags
