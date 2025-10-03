"""Configuration settings for GitHub Analytics MCP Host."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Groq API Configuration
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # MCP Server Configuration
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
    registry_port: int = int(os.getenv("REGISTRY_PORT", "8000"))
    
    # Opik Configuration (Optional)
    opik_api_key: str = os.getenv("OPIK_API_KEY", "")
    opik_project_name: str = os.getenv("OPIK_PROJECT_NAME", "github-analytics-host")
    opik_workspace: str = os.getenv("OPIK_WORKSPACE", "default")
    
    # Host Configuration
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "5"))
    enable_opik_tracking: bool = os.getenv("ENABLE_OPIK_TRACKING", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # System Prompt Configuration
    system_prompt_name: str = "scope_github_analytics_prompt"  # Prefixed with 'scope' from registry
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Validation
if not settings.groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable is required")
