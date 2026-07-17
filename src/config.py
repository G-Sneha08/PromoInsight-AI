import os
from pathlib import Path
from dotenv import load_dotenv

# Load env files
load_dotenv()

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Config variables
DATABASE_PATH = os.environ.get("DATABASE_PATH", "database/promoinsight.db")
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = str(PROJECT_ROOT / DATABASE_PATH)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Verify if database exists
def is_db_ready() -> bool:
    return os.path.exists(DATABASE_PATH)
