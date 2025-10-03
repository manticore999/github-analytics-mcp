import logging
from fastmcp import FastMCP
from typing import Dict, Any
from datetime import datetime, timedelta
from clients.github_client import GitHubClient
from config import settings

logger = logging.getLogger("pr_analytics_server")
logging.basicConfig(level=logging.INFO)

# Initialize the MCP server
pr_analytics_mcp = FastMCP("pr_analytics")

# Initialize GitHub client
github_client = GitHubClient(token=settings.GITHUB_TOKEN)


@pr_analytics_mcp.tool(
    description="List pull requests for a repository with optional state filtering",
    tags={"github", "pull_requests", "list"},
    annotations={"title": "List Pull Requests", "readOnlyHint": True, "openWorldHint": True},
)
async def list_pull_requests(owner: str, repo: str, state: str = "open", limit: int = 30) -> Dict[str, Any]:
    """
    List pull requests for a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: PR state - 'open', 'closed', or 'all' (default: 'open')
        limit: Number of PRs to retrieve (max 100)
        
    Returns:
        List of pull requests with title, number, state, and dates
    """
    logger.info(f"Listing {state} pull requests for {owner}/{repo}")
    
    prs_data = github_client.get_pull_requests(owner, repo, state=state, per_page=min(limit, 100))
    
    if isinstance(prs_data, dict) and "error" in prs_data:
        return {"error": prs_data["error"]}
    
    # Extract relevant information
    pr_list = []
    for pr in prs_data:
        pr_list.append({
            "number": pr.get("number"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "closed_at": pr.get("closed_at"),
            "merged_at": pr.get("merged_at"),
            "author": pr.get("user", {}).get("login"),
            "draft": pr.get("draft"),
            "mergeable_state": pr.get("mergeable_state"),
            "url": pr.get("html_url"),
        })
    
    return {
        "pull_requests": pr_list,
        "count": len(pr_list),
        "state": state
    }


@pr_analytics_mcp.tool(
    description="Get detailed information about a specific pull request",
    tags={"github", "pull_requests", "details"},
    annotations={"title": "Get Pull Request Details", "readOnlyHint": True, "openWorldHint": True},
)
async def get_pr_details(owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific pull request.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        
    Returns:
        Detailed PR information including body, commits, changes, and review status
    """
    logger.info(f"Fetching PR #{pr_number} for {owner}/{repo}")
    
    pr_data = github_client.get_pull_request(owner, repo, pr_number)
    
    if "error" in pr_data:
        return {"error": pr_data["error"]}
    
    return {
        "number": pr_data.get("number"),
        "title": pr_data.get("title"),
        "body": pr_data.get("body"),
        "state": pr_data.get("state"),
        "created_at": pr_data.get("created_at"),
        "updated_at": pr_data.get("updated_at"),
        "closed_at": pr_data.get("closed_at"),
        "merged_at": pr_data.get("merged_at"),
        "merged": pr_data.get("merged"),
        "author": pr_data.get("user", {}).get("login"),
        "draft": pr_data.get("draft"),
        "commits": pr_data.get("commits"),
        "additions": pr_data.get("additions"),
        "deletions": pr_data.get("deletions"),
        "changed_files": pr_data.get("changed_files"),
        "mergeable": pr_data.get("mergeable"),
        "mergeable_state": pr_data.get("mergeable_state"),
        "labels": [label.get("name") for label in pr_data.get("labels", [])],
        "url": pr_data.get("html_url"),
        "head_branch": pr_data.get("head", {}).get("ref"),
        "base_branch": pr_data.get("base", {}).get("ref"),
    }


@pr_analytics_mcp.tool(
    description="Calculate average time to merge pull requests",
    tags={"github", "pull_requests", "metrics"},
    annotations={"title": "Calculate Average Merge Time", "readOnlyHint": True, "openWorldHint": True},
)
async def calculate_avg_merge_time(owner: str, repo: str) -> Dict[str, Any]:
    """
    Calculate average time to merge pull requests.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Average merge time in days and other statistics
    """
    logger.info(f"Calculating average merge time for {owner}/{repo}")
    
    # Get closed PRs (includes merged)
    prs_data = github_client.get_pull_requests(owner, repo, state="closed", per_page=100)
    
    if isinstance(prs_data, dict) and "error" in prs_data:
        return {"error": prs_data["error"]}
    
    # Filter only merged PRs
    merged_prs = [pr for pr in prs_data if pr.get("merged_at")]
    
    if not merged_prs:
        return {
            "average_days": 0,
            "message": "No merged PRs found"
        }
    
    # Calculate merge times
    merge_times = []
    for pr in merged_prs:
        created_at = datetime.fromisoformat(pr.get("created_at", "").replace("Z", "+00:00"))
        merged_at = datetime.fromisoformat(pr.get("merged_at", "").replace("Z", "+00:00"))
        merge_time = (merged_at - created_at).total_seconds() / 86400  # Convert to days
        merge_times.append(merge_time)
    
    avg_time = sum(merge_times) / len(merge_times)
    min_time = min(merge_times)
    max_time = max(merge_times)
    
    return {
        "average_days": round(avg_time, 2),
        "min_days": round(min_time, 2),
        "max_days": round(max_time, 2),
        "prs_analyzed": len(merged_prs),
        "median_days": round(sorted(merge_times)[len(merge_times)//2], 2)
    }


@pr_analytics_mcp.tool(
    description="Find stale pull requests with no activity for a specified number of days",
    tags={"github", "pull_requests", "stale"},
    annotations={"title": "Get Stale Pull Requests", "readOnlyHint": True, "openWorldHint": True},
)
async def get_stale_prs(owner: str, repo: str, days: int = 30) -> Dict[str, Any]:
    """
    Find pull requests with no activity for a specified period.
    
    Args:
        owner: Repository owner
        repo: Repository name
        days: Number of days of inactivity to consider stale (default: 30)
        
    Returns:
        List of stale pull requests
    """
    logger.info(f"Finding stale PRs (>{days} days) for {owner}/{repo}")
    
    prs_data = github_client.get_pull_requests(owner, repo, state="open", per_page=100)
    
    if isinstance(prs_data, dict) and "error" in prs_data:
        return {"error": prs_data["error"]}
    
    # Find stale PRs
    cutoff_date = datetime.now() - timedelta(days=days)
    stale_prs = []
    
    for pr in prs_data:
        updated_at = datetime.fromisoformat(pr.get("updated_at", "").replace("Z", "+00:00"))
        if updated_at < cutoff_date:
            days_stale = (datetime.now(updated_at.tzinfo) - updated_at).days
            stale_prs.append({
                "number": pr.get("number"),
                "title": pr.get("title"),
                "days_stale": days_stale,
                "last_updated": pr.get("updated_at"),
                "author": pr.get("user", {}).get("login"),
                "draft": pr.get("draft"),
                "url": pr.get("html_url"),
            })
    
    # Sort by staleness
    stale_prs.sort(key=lambda x: x["days_stale"], reverse=True)
    
    return {
        "stale_prs": stale_prs,
        "count": len(stale_prs),
        "threshold_days": days,
        "most_stale": stale_prs[0] if stale_prs else None
    }


@pr_analytics_mcp.tool(
    description="Analyze PR velocity - how many PRs are opened vs merged over time",
    tags={"github", "pull_requests", "velocity"},
    annotations={"title": "Analyze PR Velocity", "readOnlyHint": True, "openWorldHint": True},
)
async def analyze_pr_velocity(owner: str, repo: str) -> Dict[str, Any]:
    """
    Analyze PR velocity - the rate at which PRs are opened and merged.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        PR velocity metrics including open/closed/merged counts
    """
    logger.info(f"Analyzing PR velocity for {owner}/{repo}")
    
    # Get open, closed PRs
    open_prs = github_client.get_pull_requests(owner, repo, state="open", per_page=100)
    closed_prs = github_client.get_pull_requests(owner, repo, state="closed", per_page=100)
    
    if isinstance(open_prs, dict) and "error" in open_prs:
        return {"error": open_prs["error"]}
    if isinstance(closed_prs, dict) and "error" in closed_prs:
        return {"error": closed_prs["error"]}
    
    # Count merged vs closed without merge
    merged_count = sum(1 for pr in closed_prs if pr.get("merged_at"))
    closed_without_merge = len(closed_prs) - merged_count
    
    # Calculate velocity ratio
    open_count = len(open_prs)
    total_closed = len(closed_prs)
    
    return {
        "open_prs": open_count,
        "closed_prs": total_closed,
        "merged_prs": merged_count,
        "closed_without_merge": closed_without_merge,
        "merge_rate": round((merged_count / total_closed * 100), 2) if total_closed > 0 else 0,
        "velocity_status": "healthy" if merged_count > open_count else "needs attention" if open_count > merged_count * 2 else "normal"
    }
