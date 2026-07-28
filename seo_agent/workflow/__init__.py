"""Workflow orchestration package.

This package provides the workflow orchestration components for the SEO agent.

Modules:
    stages: Workflow stage definitions and transition helpers.
    context: Workflow execution context for shared state.
    orchestrator: Main workflow orchestrator.

Example:
    >>> from seo_agent.workflow import (
    ...     WorkflowOrchestrator,
    ...     WorkflowContext,
    ...     WorkflowStage,
    ...     OrchestratorConfig,
    ...     create_orchestrator,
    ... )
"""

from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.orchestrator import (
    OrchestratorConfig,
    WorkflowOrchestrator,
    create_orchestrator,
)
from seo_agent.workflow.stages import (
    STAGE_INFO,
    STAGE_TRANSITIONS,
    StageInfo,
    StageTransition,
    WorkflowStage,
    can_transition,
    create_transition,
    get_execution_stages,
    get_next_stage,
    get_stage_info,
    get_stage_order,
)

__all__ = [
    # Context
    "WorkflowContext",
    # Orchestrator
    "WorkflowOrchestrator",
    "OrchestratorConfig",
    "create_orchestrator",
    # Stages
    "WorkflowStage",
    "StageInfo",
    "StageTransition",
    "STAGE_INFO",
    "STAGE_TRANSITIONS",
    "can_transition",
    "create_transition",
    "get_execution_stages",
    "get_next_stage",
    "get_stage_info",
    "get_stage_order",
]