import logging
from fastmcp import FastMCP
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from clients.github_client import GitHubClient
from config import settings

logger = logging.getLogger("issue_server")
logging.basicConfig(level=logging.INFO)

# Initialize the MCP server
issue_mcp = FastMCP("issue_management")

# Initialize GitHub client
github_client = GitHubClient(token=settings.GITHUB_TOKEN)


@issue_mcp.tool(
    description="List issues for a repository with optional filtering by state and labels",
    tags={"github", "issues", "list"},
    annotations={"title": "List Issues", "readOnlyHint": True, "openWorldHint": True},
)
async def list_issues(owner: str, repo: str, state: str = "open", labels: str = "", limit: int = 30) -> Dict[str, Any]:
    """
    List issues for a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state - 'open', 'closed', or 'all' (default: 'open')
        labels: Comma-separated list of labels to filter by
        limit: Number of issues to retrieve (max 100)
        
    Returns:
        List of issues with title, number, state, labels, and dates
    """
    logger.info(f"Listing {state} issues for {owner}/{repo}")
    
    issues_data = github_client.get_issues(
        owner, repo, 
        state=state, 
        labels=labels if labels else None,
        per_page=min(limit, 100)
    )
    
    if isinstance(issues_data, dict) and "error" in issues_data:
        return {"error": issues_data["error"]}
    
    # Filter out pull requests (GitHub API includes PRs in issues endpoint)
    issues = [issue for issue in issues_data if "pull_request" not in issue]
    
    # Extract relevant information
    issue_list = []
    for issue in issues:
        issue_list.append({
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "labels": [label.get("name") for label in issue.get("labels", [])],
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "closed_at": issue.get("closed_at"),
            "author": issue.get("user", {}).get("login"),
            "comments": issue.get("comments"),
            "url": issue.get("html_url"),
        })
    
    return {
        "issues": issue_list,
        "count": len(issue_list),
        "state": state
    }


@issue_mcp.tool(
    description="Get detailed information about a specific issue including comments",
    tags={"github", "issues", "details"},
    annotations={"title": "Get Issue Details", "readOnlyHint": True, "openWorldHint": True},
)
async def get_issue_details(owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific issue.
    
    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number
        
    Returns:
        Detailed issue information including body, labels, assignees, and metadata
    """
    logger.info(f"Fetching issue #{issue_number} for {owner}/{repo}")
    
    issue_data = github_client.get_issue(owner, repo, issue_number)
    
    if "error" in issue_data:
        return {"error": issue_data["error"]}
    
    return {
        "number": issue_data.get("number"),
        "title": issue_data.get("title"),
        "body": issue_data.get("body"),
        "state": issue_data.get("state"),
        "labels": [label.get("name") for label in issue_data.get("labels", [])],
        "assignees": [assignee.get("login") for assignee in issue_data.get("assignees", [])],
        "created_at": issue_data.get("created_at"),
        "updated_at": issue_data.get("updated_at"),
        "closed_at": issue_data.get("closed_at"),
        "author": issue_data.get("user", {}).get("login"),
        "comments_count": issue_data.get("comments"),
        "url": issue_data.get("html_url"),
        "milestone": issue_data.get("milestone", {}).get("title") if issue_data.get("milestone") else None,
    }


@issue_mcp.tool(
    description="Analyze issues by labels to see distribution and categorization",
    tags={"github", "issues", "analytics"},
    annotations={"title": "Analyze Issue Labels", "readOnlyHint": True, "openWorldHint": True},
)
async def analyze_issue_labels(owner: str, repo: str, state: str = "all") -> Dict[str, Any]:
    """
    Analyze issues by their labels.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state to analyze - 'open', 'closed', or 'all'
        
    Returns:
        Breakdown of issues by label with counts
    """
    logger.info(f"Analyzing issue labels for {owner}/{repo}")
    
    issues_data = github_client.get_issues(owner, repo, state=state, per_page=100)
    
    if isinstance(issues_data, dict) and "error" in issues_data:
        return {"error": issues_data["error"]}
    
    # Filter out pull requests
    issues = [issue for issue in issues_data if "pull_request" not in issue]
    
    # Count issues by label
    label_counts = {}
    for issue in issues:
        for label in issue.get("labels", []):
            label_name = label.get("name")
            if label_name:
                label_counts[label_name] = label_counts.get(label_name, 0) + 1
    
    # Sort by count
    sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "label_breakdown": {label: count for label, count in sorted_labels},
        "total_issues": len(issues),
        "unique_labels": len(label_counts),
        "top_labels": dict(sorted_labels[:10])  # Top 10 labels
    }


@issue_mcp.tool(
    description="Find stale issues with no activity for a specified number of days",
    tags={"github", "issues", "stale"},
    annotations={"title": "Get Stale Issues", "readOnlyHint": True, "openWorldHint": True},
)
async def get_stale_issues(owner: str, repo: str, days: int = 30) -> Dict[str, Any]:
    """
    Find issues with no activity for a specified period.
    
    Args:
        owner: Repository owner
        repo: Repository name
        days: Number of days of inactivity to consider stale (default: 30)
        
    Returns:
        List of stale issues
    """
    logger.info(f"Finding stale issues (>{days} days) for {owner}/{repo}")
    
    issues_data = github_client.get_issues(owner, repo, state="open", per_page=100)
    
    if isinstance(issues_data, dict) and "error" in issues_data:
        return {"error": issues_data["error"]}
    
    # Filter out pull requests
    issues = [issue for issue in issues_data if "pull_request" not in issue]
    
    # Find stale issues
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    stale_issues = []
    
    for issue in issues:
        updated_at = datetime.fromisoformat(issue.get("updated_at", "").replace("Z", "+00:00"))
        if updated_at < cutoff_date:
            days_stale = (datetime.now(timezone.utc) - updated_at).days
            stale_issues.append({
                "number": issue.get("number"),
                "title": issue.get("title"),
                "days_stale": days_stale,
                "last_updated": issue.get("updated_at"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
                "url": issue.get("html_url"),
            })
    
    # Sort by staleness
    stale_issues.sort(key=lambda x: x["days_stale"], reverse=True)
    
    return {
        "stale_issues": stale_issues,
        "count": len(stale_issues),
        "threshold_days": days,
        "most_stale": stale_issues[0] if stale_issues else None
    }


@issue_mcp.tool(
    description="Calculate average time to close issues for a repository",
    tags={"github", "issues", "metrics"},
    annotations={"title": "Calculate Issue Resolution Time", "readOnlyHint": True, "openWorldHint": True},
)
async def calculate_avg_resolution_time(owner: str, repo: str) -> Dict[str, Any]:
    """
    Calculate average time to close issues.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Average resolution time in days and other statistics
    """
    logger.info(f"Calculating average issue resolution time for {owner}/{repo}")
    
    # Get closed issues
    closed_issues = github_client.get_issues(owner, repo, state="closed", per_page=100)
    
    if isinstance(closed_issues, dict) and "error" in closed_issues:
        return {"error": closed_issues["error"]}
    
    # Filter out pull requests
    issues = [issue for issue in closed_issues if "pull_request" not in issue]
    
    if not issues:
        return {
            "average_days": 0,
            "message": "No closed issues found"
        }
    
    # Calculate resolution times
    resolution_times = []
    for issue in issues:
        created_at = datetime.fromisoformat(issue.get("created_at", "").replace("Z", "+00:00"))
        closed_at = datetime.fromisoformat(issue.get("closed_at", "").replace("Z", "+00:00"))
        resolution_time = (closed_at - created_at).total_seconds() / 86400  # Convert to days
        resolution_times.append(resolution_time)
    
    avg_time = sum(resolution_times) / len(resolution_times)
    min_time = min(resolution_times)
    max_time = max(resolution_times)
    
    return {
        "average_days": round(avg_time, 2),
        "min_days": round(min_time, 2),
        "max_days": round(max_time, 2),
        "issues_analyzed": len(issues),
        "median_days": round(sorted(resolution_times)[len(resolution_times)//2], 2)
    }
