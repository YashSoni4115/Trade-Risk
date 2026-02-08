"""
TariffShock Configuration
========================
Centralized configuration values loaded from environment variables.
"""

import os

ENGINE_VERSION: str = os.getenv("ENGINE_VERSION", "1")
BACKBOARD_BASE_URL: str = os.getenv("BACKBOARD_BASE_URL", "").rstrip("/")
BACKBOARD_API_KEY: str = os.getenv("BACKBOARD_API_KEY", "")

DEFAULT_BACKBOARD_TIMEOUT: float = float(os.getenv("BACKBOARD_TIMEOUT", "5"))
DEFAULT_BACKBOARD_MAX_RETRIES: int = int(os.getenv("BACKBOARD_MAX_RETRIES", "2"))
