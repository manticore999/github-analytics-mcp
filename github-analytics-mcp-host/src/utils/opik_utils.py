"""Opik utilities for tracking and monitoring."""
import os
from loguru import logger

try:
    import opik
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    logger.warning("Opik not available - tracking disabled")


def configure():
    """Configure Opik tracking if enabled."""
    from config import settings
    
    if not OPIK_AVAILABLE:
        logger.info("Opik not available, skipping configuration")
        return
    
    if not settings.enable_opik_tracking:
        logger.info("Opik tracking disabled in configuration")
        return
    
    if not settings.opik_api_key:
        logger.warning("OPIK_API_KEY not set - tracking disabled")
        return
    
    try:
        # Configure Opik
        opik.configure(
            api_key=settings.opik_api_key,
            workspace=settings.opik_workspace
        )
        logger.info(f"✅ Opik tracking enabled for project: {settings.opik_project_name}")
    except Exception as e:
        logger.error(f"Failed to configure Opik: {e}")


def is_enabled() -> bool:
    """Check if Opik tracking is enabled."""
    from config import settings
    return OPIK_AVAILABLE and settings.enable_opik_tracking and bool(settings.opik_api_key)
