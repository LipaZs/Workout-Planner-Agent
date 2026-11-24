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


# ---------------------------------------------------------------------------
# Tool 2: classify_symptom_severity
# ---------------------------------------------------------------------------
def classify_symptom_severity(complaint_text: str) -> Dict[str, Any]:
    """
    Classifies user symptom feedback into a closed Enum level.
    Enforces strict medical safety boundaries before allowing any exercise swap.
    """
    if not complaint_text or not isinstance(complaint_text, str):
        return {
            "status": "permanent_error",
            "error_type": "INVALID_INPUT",
            "message": "Complaint text must be a non-empty string.",
        }

    text = complaint_text.lower()

    # Severe or red-flag keywords -> immediate medical escalation
    severe_keywords = [
        "sharp", "swelling", "numbness", "dizziness", "chest", "unable to bear weight",
        "חד", "נפיחות", "נימול", "סחרחורת", "חזה", "לא יכולה לדרוך", "חזק מאוד",
    ]
    if any(word in text for word in severe_keywords):
        return {
            "status": "success",
            "severity": SymptomSeverity.SEVERE_OR_UNCERTAIN.value,
            "allow_swap": False,
            "action": "STOP_AND_REFER_TO_DOCTOR",
        }

    # Moderate pain keywords -> stop workout and refer to a professional
    moderate_keywords = [
        "moderate", "pain", "hurts", "ache",
        "כואב", "כאב", "בינוני", "דקירה",
    ]
    if any(word in text for word in moderate_keywords):
        return {
            "status": "success",
            "severity": SymptomSeverity.MODERATE_PAIN.value,
            "allow_swap": False,
            "action": "STOP_AND_REFER_TO_DOCTOR",
        }

    # Mild / low discomfort -> safe to propose a joint-friendly alternative
    mild_keywords = [
        "mild", "slight", "discomfort", "tight", "sensitivity",
        "אי-נוחות", "אי נוחות", "קלה", "קל", "עומס", "רגישות",
    ]
    if any(word in text for word in mild_keywords):
        return {
            "status": "success",
            "severity": SymptomSeverity.LOW_DISCOMFORT.value,
            "allow_swap": True,
            "action": "PROPOSE_ALTERNATIVE",
        }

    # Default to SEVERE_OR_UNCERTAIN when ambiguous (fail-safe)
    return {
        "status": "success",
        "severity": SymptomSeverity.SEVERE_OR_UNCERTAIN.value,
        "allow_swap": False,
        "action": "STOP_AND_REFER_TO_DOCTOR",
    }


# ---------------------------------------------------------------------------
# Tool 3: find_alternative_exercise
# ---------------------------------------------------------------------------
def find_alternative_exercise(
    current_exercise_id: str,
    avoid_joints: List[str],
) -> Dict[str, Any]:
    """
    Finds a safe replacement exercise targeting the same muscle group
    while avoiding all restricted joints in 'avoid_joints'.
    """
    db = _load_exercises_db()
    if current_exercise_id not in db:
        return {
            "status": "permanent_error",
            "error_type": "EXERCISE_NOT_FOUND",
            "message": f"Exercise '{current_exercise_id}' does not exist in the database.",
        }

    current_ex = db[current_exercise_id]
    target_group = current_ex["muscle_group"]
    restricted = set(avoid_joints)

    # First check the predefined safe_alternative if it meets all joint constraints
    preferred_alt_id = current_ex.get("safe_alternative")
    if preferred_alt_id and preferred_alt_id in db:
        alt_data = db[preferred_alt_id]
        if (
            alt_data["muscle_group"] == target_group
            and not restricted.intersection(set(alt_data.get("strains", [])))
        ):
            return {
                "status": "success",
                "original_exercise": current_exercise_id,
                "alternative_exercise": preferred_alt_id,
                "muscle_group": target_group,
            }

    # Otherwise scan the database for any safe exercise in the same muscle group
    for candidate_id, candidate_data in db.items():
        if candidate_id == current_exercise_id:
            continue
        if candidate_data["muscle_group"] != target_group:
            continue
        if restricted.intersection(set(candidate_data.get("strains", []))):
            continue
        return {
            "status": "success",
            "original_exercise": current_exercise_id,
            "alternative_exercise": candidate_id,
            "muscle_group": target_group,
        }

    return {
        "status": "permanent_error",
        "error_type": "NO_SAFE_ALTERNATIVE",
        "message": f"No safe alternative found for '{current_exercise_id}' avoiding {avoid_joints}.",
    }


# ---------------------------------------------------------------------------
# Tool 4: validate_workout_plan
# ---------------------------------------------------------------------------
def validate_workout_plan(
    plan: List[str],
    avoid_joints: List[str],
) -> Dict[str, Any]:
    """
    Validates every exercise in the proposed plan against the database.
    Strictly checks structured 'strains' tags and ignores free-text descriptions
    (preventing prompt injection attacks embedded in exercise descriptions).
    """
    if not isinstance(plan, list) or not plan:
        return {
            "status": "permanent_error",
            "error_type": "INVALID_PLAN",
            "message": "Workout plan must be a non-empty list of exercise IDs.",
        }

    db = _load_exercises_db()
    restricted = set(avoid_joints)
    violations: List[Dict[str, Any]] = []

    for ex_id in plan:
        if ex_id not in db:
            return {
                "status": "permanent_error",
                "error_type": "UNKNOWN_EXERCISE",
                "message": f"Exercise '{ex_id}' is not in the approved database.",
            }

        ex_strains = set(db[ex_id].get("strains", []))
        conflicting = restricted.intersection(ex_strains)
        if conflicting:
            violations.append({
                "exercise_id": ex_id,
                "conflicting_joints": sorted(list(conflicting)),
            })

    if violations:
        return {
            "status": "success",
            "is_valid": False,
            "violations": violations,
        }

    return {
        "status": "success",
        "is_valid": True,
        "violations": [],
    }