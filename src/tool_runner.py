# Author: Shani Haimovich
# run_tool: the safe way to call any tool (based on lecture 2, slide 19).
# It separates temporary failures (try again) from permanent failures (stop).

import json
import time

import tools

# The tools the agent is allowed to call
TOOLS = {
    "get_base_routine": tools.get_base_routine,
    "classify_symptom_severity": tools.classify_symptom_severity,
    "find_alternative_exercise": tools.find_alternative_exercise,
    "validate_workout_plan": tools.validate_workout_plan,
    "apply_session_state": tools.apply_session_state,
}

# Temporary problems: worth one more try
TRANSIENT_ERRORS = (TimeoutError, PermissionError, ConnectionError)

# Permanent problems: trying again will not help
PERMANENT_ERRORS = (FileNotFoundError, json.JSONDecodeError)

SEVERITY_VALUES = ["LOW_DISCOMFORT", "MODERATE_PAIN", "SEVERE_OR_UNCERTAIN"]


def error(error_type, message):
    return {"status": "error", "error_type": error_type, "message": message}


def run_tool(name, args, retries=1):
    # 1. Only known tools can run
    if name not in TOOLS:
        return error("UNKNOWN_TOOL", f"No tool named {name}")

    # 2. Try the tool, and try once more if the failure is temporary
    for attempt in range(retries + 1):
        try:
            result = TOOLS[name](**args)
            break
        except TRANSIENT_ERRORS:
            time.sleep(0.1)            # short wait before trying again
        except PERMANENT_ERRORS as e:
            result = error("DATABASE_UNAVAILABLE", str(e))
            break
        except TypeError as e:
            result = error("INVALID_ARGUMENTS", str(e))
            break
    else:
        result = error("TEMPORARY_FAILURE", "Tool failed after retrying")

    # 3. Medical safety: anything that is not a clear severity -> doctor
    if name == "classify_symptom_severity":
        if result.get("severity") not in SEVERITY_VALUES:
            result = {
                "status": "success",
                "severity": "SEVERE_OR_UNCERTAIN",
                "allow_swap": False,
                "action": "STOP_AND_REFER_TO_DOCTOR",
            }

    return result