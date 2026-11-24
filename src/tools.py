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


# ---------------------------------------------------------------------------
# Tool 1: get_base_routine
# ---------------------------------------------------------------------------
def get_base_routine(
    goal: str = "toning",
    level: str = "beginner",
    avoid_joints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Dynamically queries the exercise database and selects one exercise per muscle group
    matching the requested difficulty level and avoiding any restricted joints.
    """
    if level not in ("beginner", "intermediate"):
        return {
            "status": "permanent_error",
            "error_type": "INVALID_INPUT",
            "message": "Level must be 'beginner' or 'intermediate'.",
        }

    restricted = set(avoid_joints or [])
    db = _load_exercises_db()

    selected_ids: List[str] = []
    for group in REQUIRED_MUSCLE_GROUPS:
        match_found = None
        for ex_id, ex_data in db.items():
            if ex_data.get("muscle_group") != group:
                continue
            if ex_data.get("level") != level:
                continue
            # Check structured 'strains' field only (never trust free-text description)
            if restricted.intersection(set(ex_data.get("strains", []))):
                continue
            match_found = ex_id
            break

        if not match_found:
            return {
                "status": "permanent_error",
                "error_type": "NO_MATCHING_EXERCISE",
                "message": f"No safe exercise found for muscle group '{group}' at level '{level}'.",
            }
        selected_ids.append(match_found)

    return {
        "status": "success",
        "goal": goal,
        "level": level,
        "plan": selected_ids,
    }