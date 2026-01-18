#!/usr/bin/env python3
"""
Configuration for Instagram Reel Fetcher and AI Enhancer.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Base Directory (script location)
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()

# =============================================================================
# API Configuration
# =============================================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# =============================================================================
# Model Configuration
# =============================================================================

QUALITY_CHECK_MODEL = os.getenv("QUALITY_CHECK_MODEL", "gemini-2.5-flash-lite")
ENHANCEMENT_MODEL = os.getenv("ENHANCEMENT_MODEL", "gemini-2.5-flash")

# =============================================================================
# Processing Options
# =============================================================================

AUTO_ENHANCE = os.getenv("AUTO_ENHANCE", "true").lower() == "true"

# =============================================================================
# Paths - All configurable via .env, with sensible defaults
# =============================================================================

# Notes/markdown output directory
NOTES_DIR = Path(os.getenv("NOTES_DIR", str(SCRIPT_DIR / "data")))

# Video/attachments output directory
ATTACHMENTS_DIR = Path(os.getenv("ATTACHMENTS_DIR", str(SCRIPT_DIR / "video")))

# Temporary files directory (downloads, compression, tracking)
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(SCRIPT_DIR / "temp")))

# Queue file for watcher mode
QUEUE_FILE = Path(os.getenv("QUEUE_FILE", str(
    NOTES_DIR / "Instagram Queue.md")))


def validate_config() -> bool:
    """Validate that required configuration is present."""
    if not GOOGLE_API_KEY:
        print("❌ Error: GOOGLE_API_KEY is not set!")
        print("   Please set it in your .env file or environment variables.")
        return False
    return True


def ensure_directories():
    """Create all required directories if they don't exist."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
