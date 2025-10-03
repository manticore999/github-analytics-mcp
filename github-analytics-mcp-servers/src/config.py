import os
from pathlib import Path
from dotenv import load_dotenv


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    
    DEFAULT_REPO_OWNER: str = os.getenv("DEFAULT_REPO_OWNER", "")
    DEFAULT_REPO_NAME: str = os.getenv("DEFAULT_REPO_NAME", "")
    
   
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    
    
    REGISTRY_PORT: int = int(os.getenv("REGISTRY_PORT", "8000"))
    
    
    OPIK_API_KEY: str = os.getenv("OPIK_API_KEY", "")
    OPIK_PROJECT: str = os.getenv("OPIK_PROJECT", "github_analytics_servers")
    
    def __init__(self):
        """Log configuration on initialization for debugging."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Config loaded: OPIK_PROJECT={self.OPIK_PROJECT}")
    
    @property
    def github_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {self.GITHUB_TOKEN}"
        return headers



settings = Settings()
