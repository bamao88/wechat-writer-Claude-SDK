"""Router module for hub-spoke architecture.

Determines next step based on current state machine position:
planner → miner/web/orchestrator → writer → critic
"""
from typing import Optional
from .state import State


def determine_next_step(state: State, agent_output: Optional[str]) -> str:
    """Determine the next step based on current state.

    State machine transitions:
    - planner → miner/web/orchestrator (based on use_private/use_web flags)
    - miner → web/orchestrator (based on use_web flag)
    - web → orchestrator
    - orchestrator → writer
    - writer → critic

    Note: critic routing is handled directly in Executor._execute_critic.

    Raises:
        ValueError: If current next_step is unknown
    """
    current_step = state.next_step

    if current_step == "planner":
        # Planner routes based on use_private/use_web flags
        if state.use_private:
            return "miner"
        elif state.use_web:
            return "web"
        else:
            return "orchestrator"

    elif current_step == "miner":
        # Miner routes to web if needed, otherwise orchestrator
        if state.use_web:
            return "web"
        else:
            return "orchestrator"

    elif current_step == "web":
        # Web always routes to orchestrator
        return "orchestrator"

    elif current_step == "orchestrator":
        # Orchestrator always routes to writer
        return "writer"

    elif current_step == "writer":
        # Writer always routes to critic
        return "critic"

    else:
        raise ValueError(f"Unknown next_step: {current_step}")
