import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

EXERCISES_DIR = ROOT / "exercises"
GENERATED_DIR = ROOT / "generated"
TASKS_DIR = ROOT / "tasks"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sqlcoach:sqlcoach@localhost:5432/sqlcoach",
)
STUDENT_DATABASE_URL = os.getenv(
    "STUDENT_DATABASE_URL",
    "postgresql://student:student@localhost:5432/sqlcoach",
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
ROW_LIMIT = 200
