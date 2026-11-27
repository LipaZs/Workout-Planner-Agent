# Author: Shani Haimovich
# Three tests for every tool, like lecture 2 (slide 20):
# valid input, invalid input, and a temporary failure.
# Run from the main project folder with:  python -m pytest

import sys
sys.path.insert(0, "src")

import tool_runner
from tool_runner import run_tool
from state import create_session_state, SessionManager


# A fake "flaky" tool: fails once with a temporary error, then works.
# Like flaky_search in the lecture.
def make_flaky(name):
    real_tool = tool_runner.TOOLS[name]
    calls = {"count": 0}

    def flaky(**args):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("temporary problem")
        return real_tool(**args)

    tool_runner.TOOLS[name] = flaky
    return calls, real_tool

# ---------- Tool 1: get_base_routine ----------

def test_routine_valid_input():
    r = run_tool("get_base_routine",
                 {"goal": "toning", "level": "beginner", "avoid_joints": ["knees"]})
    assert r["status"] == "success"
    assert len(r["plan"]) == 4


def test_routine_invalid_input():
    r = run_tool("get_base_routine", {"goal": "toning", "level": "expert"})
    assert r["error_type"] == "INVALID_INPUT"


def test_routine_transient_failure():
    calls, real_tool = make_flaky("get_base_routine")
    r = run_tool("get_base_routine", {"goal": "toning", "level": "beginner"})
    tool_runner.TOOLS["get_base_routine"] = real_tool
    assert r["status"] == "success"
    assert calls["count"] == 2      # failed once, worked on the retry
    
    # ---------- Tool 2: classify_symptom_severity ----------

def test_classify_valid_input():
    r = run_tool("classify_symptom_severity", {"complaint_text": "אי נוחות קלה בברך"})
    assert r["severity"] == "LOW_DISCOMFORT"
    assert r["allow_swap"] == True


def test_classify_empty_input_goes_to_doctor():
    r = run_tool("classify_symptom_severity", {"complaint_text": ""})
    assert r["severity"] == "SEVERE_OR_UNCERTAIN"
    assert r["allow_swap"] == False


def test_classify_transient_failure():
    calls, real_tool = make_flaky("classify_symptom_severity")
    r = run_tool("classify_symptom_severity", {"complaint_text": "אי נוחות קלה בברך"})
    tool_runner.TOOLS["classify_symptom_severity"] = real_tool
    assert r["severity"] == "LOW_DISCOMFORT"
    assert calls["count"] == 2


def test_classify_unclear_goes_to_doctor():
    r = run_tool("classify_symptom_severity", {"complaint_text": "הברך מרגישה לא יציבה"})
    assert r["allow_swap"] == False
    
    
    # ---------- Tool 3: find_alternative_exercise ----------

def test_alternative_valid_input():
    r = run_tool("find_alternative_exercise",
                 {"current_exercise_id": "air_squat", "avoid_joints": ["knees"]})
    assert r["status"] == "success"
    assert r["muscle_group"] == "legs"


def test_alternative_unknown_exercise():
    r = run_tool("find_alternative_exercise",
                 {"current_exercise_id": "flying_kick", "avoid_joints": ["knees"]})
    assert r["error_type"] == "EXERCISE_NOT_FOUND"


def test_alternative_transient_failure():
    calls, real_tool = make_flaky("find_alternative_exercise")
    r = run_tool("find_alternative_exercise",
                 {"current_exercise_id": "air_squat", "avoid_joints": ["knees"]})
    tool_runner.TOOLS["find_alternative_exercise"] = real_tool
    assert r["status"] == "success"
    assert calls["count"] == 2
    
    
    # ---------- Tool 4: validate_workout_plan ----------

def test_validate_valid_input():
    r = run_tool("validate_workout_plan",
                 {"plan": ["glute_bridge", "forearm_plank"], "avoid_joints": ["knees"]})
    assert r["is_valid"] == True


def test_validate_empty_plan():
    r = run_tool("validate_workout_plan", {"plan": [], "avoid_joints": ["knees"]})
    assert r["error_type"] == "INVALID_PLAN"


def test_validate_transient_failure():
    calls, real_tool = make_flaky("validate_workout_plan")
    r = run_tool("validate_workout_plan",
                 {"plan": ["glute_bridge"], "avoid_joints": ["knees"]})
    tool_runner.TOOLS["validate_workout_plan"] = real_tool
    assert r["is_valid"] == True
    assert calls["count"] == 2


def test_validate_ignores_hidden_instruction():
    # jump_squats has "ignore all limits" hidden in its description
    r = run_tool("validate_workout_plan",
                 {"plan": ["jump_squats"], "avoid_joints": ["knees"]})
    assert r["is_valid"] == False
    
    
    # ---------- Tool 5: apply_session_state ----------

def test_apply_valid_input():
    s = create_session_state("s1")
    s["user_confirmed"] = True          # the user really said "yes"
    r = run_tool("apply_session_state",
                 {"state": s, "new_plan": ["glute_bridge"], "new_avoid_joints": ["knees"]})
    assert r["status"] == "success"
    assert s["current_plan"] == ["glute_bridge"]


def test_apply_without_confirmation_is_blocked():
    s = create_session_state("s1")      # the user did NOT confirm
    r = run_tool("apply_session_state",
                 {"state": s, "new_plan": ["glute_bridge"], "new_avoid_joints": ["knees"]})
    assert r["error_type"] == "PERMISSION_DENIED"
    assert s["current_plan"] == []


def test_apply_model_cannot_fake_confirmation():
    # The model tries to send user_confirmed=True by itself
    s = create_session_state("s1")
    r = run_tool("apply_session_state",
                 {"state": s, "new_plan": ["glute_bridge"], "new_avoid_joints": ["knees"],
                  "user_confirmed": True})
    assert r["status"] != "success"
    assert s["current_plan"] == []


def test_apply_transient_failure():
    s = create_session_state("s1")
    s["user_confirmed"] = True
    calls, real_tool = make_flaky("apply_session_state")
    r = run_tool("apply_session_state",
                 {"state": s, "new_plan": ["glute_bridge"], "new_avoid_joints": ["knees"]})
    tool_runner.TOOLS["apply_session_state"] = real_tool
    assert r["status"] == "success"
    assert calls["count"] == 2


# ---------- State: two conversations do not mix ----------

def test_sessions_are_separate():
    manager = SessionManager()
    dana = manager.get_or_create_session("dana")
    manager.get_or_create_session("yossi")
    dana["avoid_joints"].append("knees")       # only Dana has a knee problem
    yossi = manager.get_session_copy("yossi")
    assert yossi["avoid_joints"] == []