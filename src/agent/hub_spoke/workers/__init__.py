"""Workers module for hub-spoke architecture.

This module exports all worker classes and provides a factory function
to create a complete set of workers for the executor.
"""
from src.agent.hub_spoke.workers.planner import PlannerWorker, PlannerResult
from src.agent.hub_spoke.workers.miner import MinerWorker, MinerResult
from src.agent.hub_spoke.workers.web import WebWorker, WebResult
from src.agent.hub_spoke.workers.orchestrator import OrchestratorWorker, OrchestratorResult
from src.agent.hub_spoke.workers.writer import WriterWorker, WriterResult
from src.agent.hub_spoke.workers.critic import CriticWorker, CriticResult

__all__ = [
    # Workers
    "PlannerWorker",
    "MinerWorker",
    "WebWorker",
    "OrchestratorWorker",
    "WriterWorker",
    "CriticWorker",
    # Results
    "PlannerResult",
    "MinerResult",
    "WebResult",
    "OrchestratorResult",
    "WriterResult",
    "CriticResult",
    # Factory
    "create_workers",
]


def create_workers() -> dict:
    """Create all workers for hub-spoke architecture.

    Returns:
        Dictionary mapping worker names to worker instances:
        {
            "planner": PlannerWorker(),
            "miner": MinerWorker(),
            "web": WebWorker(),
            "orchestrator": OrchestratorWorker(),
            "writer": WriterWorker(),
            "critic": CriticWorker(),
        }
    """
    return {
        "planner": PlannerWorker(),
        "miner": MinerWorker(),
        "web": WebWorker(),
        "orchestrator": OrchestratorWorker(),
        "writer": WriterWorker(),
        "critic": CriticWorker(),
    }
