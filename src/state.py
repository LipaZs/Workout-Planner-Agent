from copy import deepcopy
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. Explicit State Schema creation for a single workout session
# ---------------------------------------------------------------------------
def create_session_state(
    session_id: str,
    profile_id: str = "synthetic_user_01",
    goal: str = "toning",
    level: str = "beginner",
    initial_avoid_joints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Creates an explicit, isolated initial state dictionary for a single session.
    The 'user_confirmed' flag always defaults to False to prevent unapproved plan updates.
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id must be a non-empty string.")
    if level not in ("beginner", "intermediate"):
        raise ValueError("level must be 'beginner' or 'intermediate'.")

    return {
        "session_id": session_id,
        "profile_id": profile_id,  # Synthetic test profile ID only (no personal data)
        "goal": goal,
        "level": level,
        "current_plan": [],        # List of active exercise IDs in the current routine
        "avoid_joints": list(initial_avoid_joints) if initial_avoid_joints else [],
        "user_confirmed": False,   # Permission flag: updated only after explicit user approval
        "step_count": 0,           # Loop step counter to enforce stopping budget (MAX_STEPS = 8)
        "swap_count": 0,           # Counter for exercise replacements performed in this session
        "history": [],             # Conversation and tool observation history for this session
    }


# ---------------------------------------------------------------------------
# 2. Session Manager - guarantees strict isolation between different sessions
# ---------------------------------------------------------------------------
class SessionManager:
    """
    Manages multiple workout sessions concurrently using a dictionary keyed by session_id.
    Guarantees that updates in Session A never affect or leak into Session B.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(
        self,
        session_id: str,
        profile_id: str = "synthetic_user_01",
        goal: str = "toning",
        level: str = "beginner",
        initial_avoid_joints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieves an existing session by ID, or creates a new isolated session if absent."""
        if session_id not in self._sessions:
            self._sessions[session_id] = create_session_state(
                session_id=session_id,
                profile_id=profile_id,
                goal=goal,
                level=level,
                initial_avoid_joints=initial_avoid_joints,
            )
        return self._sessions[session_id]

    def get_session_copy(self, session_id: str) -> Dict[str, Any]:
        """Returns a deep copy of the session state to prevent accidental external mutation."""
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' does not exist.")
        return deepcopy(self._sessions[session_id])


# ---------------------------------------------------------------------------
# 3. History management and Context Builder (Full vs. Compact comparison)
# ---------------------------------------------------------------------------
def append_message(state: Dict[str, Any], role: str, content: str) -> None:
    """Appends a single turn message ('user', 'assistant', or 'tool') to the session history."""
    state["history"].append({"role": role, "content": content})


def build_context(state: Dict[str, Any], mode: str = "full") -> List[Dict[str, str]]:
    """
    Builds the message list (context) passed to the model:
    - 'full' mode: sends the current state summary + complete conversation and tool history.
    - 'compact' mode: sends only the current state summary + the latest message.
    """
    if mode not in ("full", "compact"):
        raise ValueError("Context mode must be 'full' or 'compact'.")

    # System message summarizing the up-to-date structured session state
    summary_message = {
        "role": "system",
        "content": (
            f"Goal: {state['goal']} | Level: {state['level']} | "
            f"Current Plan: {state['current_plan']} | "
            f"Avoid Joints: {state['avoid_joints']} | "
            f"User Confirmed: {state['user_confirmed']}"
        ),
    }

    if mode == "full":
        return [summary_message] + list(state["history"])

    # In compact mode, retain only the most recent message from history
    latest_messages = state["history"][-1:] if state["history"] else []
    return [summary_message] + latest_messages