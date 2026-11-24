import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# Path to the synthetic 30-exercise database
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "exercises_db.json"

# Standard balanced muscle groups for a complete toning routine
REQUIRED_MUSCLE_GROUPS = ["legs", "glutes", "core", "upper_body"]


# ---------------------------------------------------------------------------
# 1. Closed Enum for Symptom Severity Classification (Medical Boundary)
# ---------------------------------------------------------------------------
class SymptomSeverity(str, Enum):
    LOW_DISCOMFORT = "LOW_DISCOMFORT"
    MODERATE_PAIN = "MODERATE_PAIN"
    SEVERE_OR_UNCERTAIN = "SEVERE_OR_UNCERTAIN"


def _load_exercises_db() -> Dict[str, Any]:
    """Loads the local JSON exercise database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Exercise database not found at {DB_PATH}")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f) 