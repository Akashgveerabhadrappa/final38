import os
import logging
import traceback
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Paths ---
# We'll use the 'instance' folder for writable files (logs, cache)
# It's automatically created by Flask and is in our .gitignore
INSTANCE_DIR = "instance"
GEO_CACHE_FILE = os.path.join(INSTANCE_DIR, "geo_cache.json")
LOG_FILE = os.path.join(INSTANCE_DIR, "app.log")

# --- Ensure Dirs Exist ---
os.makedirs(INSTANCE_DIR, exist_ok=True)

# --- Logging ---
def setup_logging():
    """Configures logging to file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()  # Also print to console
        ]
    )

def log(msg):
    logging.info(msg)

def log_exception(msg, e):
    logging.error(f"{msg}: {e}")
    logging.error(traceback.format_exc())

# --- Web Session ---
def setup_session() -> requests.Session:
    """Sets up a requests session with retries for API calls."""
    session = requests.Session()
    retry = Retry(
        total=5, 
        backoff_factor=1, 
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# --- Initialize logging on import ---
setup_logging()