import logging
from fastmcp import FastMCP
from typing import Dict, Any
from datetime import datetime, timedelta
from clients.github_client import GitHubClient
from config import settings

logger = logging.getLogger("contributor_server")
logging.basicConfig(level=logging.INFO)

# Initialize the MCP server
contributor_mcp = FastMCP("contributor_insights")

# Initialize GitHub client
github_client = GitHubClient(token=settings.GITHUB_TOKEN)


@contributor_mcp.tool(
    description="List all contributors to a repository with their contribution counts",
    tags={"github", "contributors", "list"},
    annotations={"title": "List Contributors", "readOnlyHint": True, "openWorldHint": True},
)
async def list_contributors(owner: str, repo: str, limit: int = 30) -> Dict[str, Any]:
    """
    List all contributors to a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        limit: Number of contributors to retrieve (max 100)
        
    Returns:
        List of contributors with their contribution counts
    """
    logger.info(f"Listing contributors for {owner}/{repo}")
    
    contributors_data = github_client.get_contributors(owner, repo, per_page=min(limit, 100))
    
    if isinstance(contributors_data, dict) and "error" in contributors_data:
        return {"error": contributors_data["error"]}
    
    # Extract relevant information
    contributor_list = []
    for contributor in contributors_data:
        contributor_list.append({
            "username": contributor.get("login"),
            "contributions": contributor.get("contributions"),
            "type": contributor.get("type"),
            "profile_url": contributor.get("html_url"),
            "avatar_url": contributor.get("avatar_url"),
        })
    
    return {
        "contributors": contributor_list,
        "count": len(contributor_list),
        "total_contributions": sum(c["contributions"] for c in contributor_list)
    }


@contributor_mcp.tool(
    description="Get the top contributors to a repository ranked by contribution count",
    tags={"github", "contributors", "top"},
    annotations={"title": "Get Top Contributors", "readOnlyHint": True, "openWorldHint": True},
)
async def get_top_contributors(owner: str, repo: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get top contributors to a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        limit: Number of top contributors to retrieve (default: 10)
        
    Returns:
        Top contributors ranked by contribution count
    """
    logger.info(f"Fetching top {limit} contributors for {owner}/{repo}")
    
    contributors_data = github_client.get_contributors(owner, repo, per_page=100)
    
    if isinstance(contributors_data, dict) and "error" in contributors_data:
        return {"error": contributors_data["error"]}
    
    # Get top N contributors (already sorted by GitHub API)
    top_contributors = contributors_data[:limit]
    
    contributor_list = []
    for i, contributor in enumerate(top_contributors, 1):
        contributor_list.append({
            "rank": i,
            "username": contributor.get("login"),
            "contributions": contributor.get("contributions"),
            "profile_url": contributor.get("html_url"),
        })
    
    total_contributions = sum(c.get("contributions", 0) for c in contributors_data)
    top_contributions = sum(c["contributions"] for c in contributor_list)
    
    return {
        "top_contributors": contributor_list,
        "count": len(contributor_list),
        "top_contributor_percentage": round((top_contributions / total_contributions * 100), 2) if total_contributions > 0 else 0,
        "total_contributors": len(contributors_data)
    }


@contributor_mcp.tool(
    description="Analyze contributor activity patterns over time",
    tags={"github", "contributors", "activity"},
    annotations={"title": "Analyze Contributor Activity", "readOnlyHint": True, "openWorldHint": True},
)
async def analyze_contributor_activity(owner: str, repo: str, days: int = 30) -> Dict[str, Any]:
    """
    Analyze contributor activity over a time period.
    
    Args:
        owner: Repository owner
        repo: Repository name
        days: Time period in days to analyze (default: 30)
        
    Returns:
        Activity analysis including active contributors and commit patterns
    """
    logger.info(f"Analyzing contributor activity for last {days} days in {owner}/{repo}")
    
    # Get recent commits to analyze activity
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    commits_data = github_client.get_commits(owner, repo, per_page=100, since=since_date)
    
    if isinstance(commits_data, dict) and "error" in commits_data:
        return {"error": commits_data["error"]}
    
    # Count commits per contributor
    contributor_commits = {}
    for commit in commits_data:
        author = commit.get("commit", {}).get("author", {}).get("name")
        if author:
            contributor_commits[author] = contributor_commits.get(author, 0) + 1
    
    # Sort by commit count
    sorted_contributors = sorted(contributor_commits.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "time_period_days": days,
        "active_contributors": len(contributor_commits),
        "total_commits": len(commits_data),
        "top_active_contributors": dict(sorted_contributors[:10]),
        "average_commits_per_contributor": round(len(commits_data) / len(contributor_commits), 2) if contributor_commits else 0,
    }


@contributor_mcp.tool(
    description="Get detailed statistics for a specific contributor",
    tags={"github", "contributors", "stats"},
    annotations={"title": "Get Contributor Stats", "readOnlyHint": True, "openWorldHint": True},
)
async def get_contributor_stats(owner: str, repo: str, username: str) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific contributor.
    
    Args:
        owner: Repository owner
        repo: Repository name
        username: Contributor's GitHub username
        
    Returns:
        Detailed contributor statistics
    """
    logger.info(f"Fetching stats for contributor {username} in {owner}/{repo}")
    
    # Get all contributors to find the specific one
    contributors_data = github_client.get_contributors(owner, repo, per_page=100)
    
    if isinstance(contributors_data, dict) and "error" in contributors_data:
        return {"error": contributors_data["error"]}
    
    # Find the specific contributor
    contributor = next((c for c in contributors_data if c.get("login") == username), None)
    
    if not contributor:
        return {"error": f"Contributor '{username}' not found in {owner}/{repo}"}
    
    # Get their rank
    rank = next((i+1 for i, c in enumerate(contributors_data) if c.get("login") == username), None)
    
    # Calculate percentage of total contributions
    total_contributions = sum(c.get("contributions", 0) for c in contributors_data)
    contributor_contributions = contributor.get("contributions", 0)
    contribution_percentage = round((contributor_contributions / total_contributions * 100), 2) if total_contributions > 0 else 0
    
    return {
        "username": contributor.get("login"),
        "contributions": contributor_contributions,
        "rank": rank,
        "contribution_percentage": contribution_percentage,
        "total_contributors": len(contributors_data),
        "profile_url": contributor.get("html_url"),
        "type": contributor.get("type"),
    }


@contributor_mcp.tool(
    description="Analyze commit frequency patterns for a repository",
    tags={"github", "contributors", "commits"},
    annotations={"title": "Analyze Commit Frequency", "readOnlyHint": True, "openWorldHint": True},
)
async def analyze_commit_frequency(owner: str, repo: str, days: int = 30) -> Dict[str, Any]:
    """
    Analyze commit frequency patterns.
    
    Args:
        owner: Repository owner
        repo: Repository name
        days: Time period in days to analyze (default: 30)
        
    Returns:
        Commit frequency analysis with daily/weekly patterns
    """
    logger.info(f"Analyzing commit frequency for last {days} days in {owner}/{repo}")
    
    # Get recent commits
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    commits_data = github_client.get_commits(owner, repo, per_page=100, since=since_date)
    
    if isinstance(commits_data, dict) and "error" in commits_data:
        return {"error": commits_data["error"]}
    
    if not commits_data:
        return {
            "average_commits_per_day": 0,
            "total_commits": 0,
            "message": "No commits found in the specified period"
        }
    
    # Count commits per day
    daily_commits = {}
    for commit in commits_data:
        commit_date = commit.get("commit", {}).get("author", {}).get("date", "")
        if commit_date:
            date_obj = datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
            date_key = date_obj.strftime("%Y-%m-%d")
            daily_commits[date_key] = daily_commits.get(date_key, 0) + 1
    
    total_commits = len(commits_data)
    avg_commits_per_day = round(total_commits / days, 2)
    
    # Find most active day
    most_active_day = max(daily_commits.items(), key=lambda x: x[1]) if daily_commits else None
    
    return {
        "time_period_days": days,
        "total_commits": total_commits,
        "average_commits_per_day": avg_commits_per_day,
        "most_active_day": {
            "date": most_active_day[0],
            "commits": most_active_day[1]
        } if most_active_day else None,
        "days_with_commits": len(daily_commits),
        "activity_rate": round((len(daily_commits) / days * 100), 2)
    }
