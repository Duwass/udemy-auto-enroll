"""
Configuration for Udemy Auto-Enroll Tool
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BROWSER_DATA_DIR = DATA_DIR / "browser_data"
FB_BROWSER_DATA_DIR = DATA_DIR / "fb_browser_data"
DB_PATH = DATA_DIR / "history.db"
QUEUE_FILE = DATA_DIR / "queue.json"
REPORTS_DIR = DATA_DIR / "reports"

# Create directories if not exist
DATA_DIR.mkdir(exist_ok=True)
BROWSER_DATA_DIR.mkdir(exist_ok=True)
FB_BROWSER_DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Udemy settings
UDEMY_BASE_URL = "https://www.udemy.com"
ENROLL_TIMEOUT = 30000  # 30 seconds

# Browser settings
HEADLESS = False  # Set to True to run browser in background
SLOW_MO = 100  # Slow down actions by 100ms for stability
