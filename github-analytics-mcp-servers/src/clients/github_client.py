import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class GitHubClient:
    """A client for interacting with GitHub's REST API v3."""

    def __init__(self, token: Optional[str] = None):
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _make_request(
        self, 
        endpoint: str, 
        method: str = "GET", 
        params: Optional[Dict] = None
    ) -> Any:
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method, 
                url, 
                headers=self.headers, 
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"GitHub API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return {"error": str(e)}

  
    
    def get_repository(self, owner: str, repo: str) -> Dict:
        
        return self._make_request(f"/repos/{owner}/{repo}")

    def get_repository_languages(self, owner: str, repo: str) -> Dict:
        """
        Get programming languages used in the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dictionary of languages with byte counts
        """
        return self._make_request(f"/repos/{owner}/{repo}/languages")

    def get_commits(
        self, 
        owner: str, 
        repo: str, 
        per_page: int = 30,
        since: Optional[str] = None,
        author: Optional[str] = None
    ) -> List[Dict]:
        """
        Get commit history for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of commits per page (max 100)
            since: Only commits after this date (ISO 8601 format)
            author: GitHub username to filter commits by
            
        Returns:
            List of commit objects
        """
        params = {"per_page": per_page}
        if since:
            params["since"] = since
        if author:
            params["author"] = author
        return self._make_request(f"/repos/{owner}/{repo}/commits", params=params)

    # ===== Issue Methods =====
    
    def get_issues(
        self, 
        owner: str, 
        repo: str, 
        state: str = "open",
        labels: Optional[str] = None,
        per_page: int = 30
    ) -> List[Dict]:
        """
        Get issues for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state - 'open', 'closed', or 'all'
            labels: Comma-separated list of label names
            per_page: Number of issues per page (max 100)
            
        Returns:
            List of issue objects
        """
        params = {
            "state": state,
            "per_page": per_page
        }
        if labels:
            params["labels"] = labels
        return self._make_request(f"/repos/{owner}/{repo}/issues", params=params)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict:
        """
        Get a specific issue by number.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            
        Returns:
            Issue object with details
        """
        return self._make_request(f"/repos/{owner}/{repo}/issues/{issue_number}")

    # ===== Pull Request Methods =====
    
    def get_pull_requests(
        self, 
        owner: str, 
        repo: str, 
        state: str = "open",
        per_page: int = 30
    ) -> List[Dict]:
        """
        Get pull requests for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state - 'open', 'closed', or 'all'
            per_page: Number of PRs per page (max 100)
            
        Returns:
            List of pull request objects
        """
        params = {
            "state": state,
            "per_page": per_page
        }
        return self._make_request(f"/repos/{owner}/{repo}/pulls", params=params)

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict:
        """
        Get a specific pull request by number.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Pull request object with details
        """
        return self._make_request(f"/repos/{owner}/{repo}/pulls/{pr_number}")

    # ===== Contributor Methods =====
    
    def get_contributors(
        self, 
        owner: str, 
        repo: str, 
        per_page: int = 30
    ) -> List[Dict]:
        """
        Get contributors for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of contributors per page (max 100)
            
        Returns:
            List of contributor objects with commit counts
        """
        params = {"per_page": per_page}
        return self._make_request(f"/repos/{owner}/{repo}/contributors", params=params)

    # ===== Rate Limit Methods =====
    
    def get_rate_limit(self) -> Dict:
        """
        Get current rate limit status.
        
        Returns:
            Rate limit information
        """
        return self._make_request("/rate_limit")
