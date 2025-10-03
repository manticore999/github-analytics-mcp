import logging
from fastmcp import FastMCP
from typing import Dict, Any
from clients.github_client import GitHubClient
from config import settings

logger = logging.getLogger("repo_stats_server")
logging.basicConfig(level=logging.INFO)

# Initialize the MCP server
repo_stats_mcp = FastMCP("repository_stats")

# Initialize GitHub client
github_client = GitHubClient(token=settings.GITHUB_TOKEN)


@repo_stats_mcp.tool(
    description="Get comprehensive repository information including stars, forks, issues, and metadata",
    tags={"github", "repository", "stats"},
)
async def get_repo_info(owner: str, repo: str) -> Dict[str, Any]:
    """
    Fetch detailed information about a repository.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        
    Returns:
        Repository metadata including stars, forks, language, description, etc.
    """
    logger.info(f"Fetching repository info for {owner}/{repo}")
    
    repo_data = github_client.get_repository(owner, repo)
    
    if "error" in repo_data:
        return {"error": repo_data["error"]}
    
    # Extract key metrics
    return {
        "name": repo_data.get("name"),
        "full_name": repo_data.get("full_name"),
        "description": repo_data.get("description"),
        "owner": repo_data.get("owner", {}).get("login"),
        "stars": repo_data.get("stargazers_count"),
        "forks": repo_data.get("forks_count"),
        "watchers": repo_data.get("watchers_count"),
        "open_issues": repo_data.get("open_issues_count"),
        "language": repo_data.get("language"),
        "created_at": repo_data.get("created_at"),
        "updated_at": repo_data.get("updated_at"),
        "size": repo_data.get("size"),
        "default_branch": repo_data.get("default_branch"),
        "is_private": repo_data.get("private"),
        "has_wiki": repo_data.get("has_wiki"),
        "has_pages": repo_data.get("has_pages"),
        "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
        "url": repo_data.get("html_url"),
    }


@repo_stats_mcp.tool(
    description="Get programming languages used in the repository with their percentage breakdown",
    tags={"github", "repository", "languages"},
)
async def get_repo_languages(owner: str, repo: str) -> Dict[str, Any]:
    """
    Fetch programming languages used in a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Dictionary of languages with byte counts and percentages
    """
    logger.info(f"Fetching languages for {owner}/{repo}")
    
    languages_data = github_client.get_repository_languages(owner, repo)
    
    if "error" in languages_data:
        return {"error": languages_data["error"]}
    
    # Calculate percentages
    total_bytes = sum(languages_data.values())
    languages_with_percentages = {
        lang: {
            "bytes": bytes_count,
            "percentage": round((bytes_count / total_bytes) * 100, 2) if total_bytes > 0 else 0
        }
        for lang, bytes_count in languages_data.items()
    }
    
    return {
        "languages": languages_with_percentages,
        "total_bytes": total_bytes,
        "primary_language": max(languages_data, key=languages_data.get) if languages_data else None
    }


@repo_stats_mcp.tool(
    description="Get recent commit history for a repository",
    tags={"github", "repository", "commits"},
)
async def get_recent_commits(owner: str, repo: str, limit: int = 10) -> Dict[str, Any]:
    """
    Fetch recent commits from a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        limit: Number of commits to fetch (default: 10, max: 100)
        
    Returns:
        List of recent commits with author, message, and date
    """
    logger.info(f"Fetching {limit} recent commits for {owner}/{repo}")
    
    # Ensure limit is within bounds
    limit = min(limit, 100)
    
    commits_data = github_client.get_commits(owner, repo, per_page=limit)
    
    if isinstance(commits_data, dict) and "error" in commits_data:
        return {"error": commits_data["error"]}
    
    # Extract relevant commit information
    commits = []
    for commit in commits_data:
        commit_info = commit.get("commit", {})
        commits.append({
            "sha": commit.get("sha"),
            "message": commit_info.get("message"),
            "author": commit_info.get("author", {}).get("name"),
            "date": commit_info.get("author", {}).get("date"),
            "url": commit.get("html_url"),
        })
    
    return {
        "commits": commits,
        "count": len(commits)
    }


@repo_stats_mcp.tool(
    description="Compare two repositories side by side",
    tags={"github", "repository", "compare"},
)
async def compare_repos(owner1: str, repo1: str, owner2: str, repo2: str) -> Dict[str, Any]:
    """
    Compare two repositories and their key metrics.
    
    Args:
        owner1: First repository owner
        repo1: First repository name
        owner2: Second repository owner
        repo2: Second repository name
        
    Returns:
        Comparison of stars, forks, issues, and other metrics
    """
    logger.info(f"Comparing {owner1}/{repo1} with {owner2}/{repo2}")
    
    # Fetch both repositories
    repo1_data = github_client.get_repository(owner1, repo1)
    repo2_data = github_client.get_repository(owner2, repo2)
    
    if "error" in repo1_data:
        return {"error": f"Error fetching {owner1}/{repo1}: {repo1_data['error']}"}
    if "error" in repo2_data:
        return {"error": f"Error fetching {owner2}/{repo2}: {repo2_data['error']}"}
    
    return {
        "repository_1": {
            "name": repo1_data.get("full_name"),
            "stars": repo1_data.get("stargazers_count"),
            "forks": repo1_data.get("forks_count"),
            "open_issues": repo1_data.get("open_issues_count"),
            "language": repo1_data.get("language"),
            "created_at": repo1_data.get("created_at"),
        },
        "repository_2": {
            "name": repo2_data.get("full_name"),
            "stars": repo2_data.get("stargazers_count"),
            "forks": repo2_data.get("forks_count"),
            "open_issues": repo2_data.get("open_issues_count"),
            "language": repo2_data.get("language"),
            "created_at": repo2_data.get("created_at"),
        },
        "comparison": {
            "stars_diff": repo1_data.get("stargazers_count", 0) - repo2_data.get("stargazers_count", 0),
            "forks_diff": repo1_data.get("forks_count", 0) - repo2_data.get("forks_count", 0),
            "more_popular": repo1_data.get("full_name") if repo1_data.get("stargazers_count", 0) > repo2_data.get("stargazers_count", 0) else repo2_data.get("full_name"),
        }
    }
