"""OpenCode agent integration."""

from seo_agent.integrations.opencode.models import (
    # Enums
    OpenCodeModel,
    OpenCodeAction,
    OpenCodeStatus,
    # Request models
    OpenCodeFileEdit,
    OpenCodeFileRead,
    OpenCodeSearchQuery,
    OpenCodeActionRequest,
    OpenCodeRequest,
    # Response models
    OpenCodeFileChange,
    OpenCodeActionResult,
    OpenCodeResponse,
    OpenCodeExecutionContext,
)
from seo_agent.integrations.opencode.client import OpenCodeClient, OpenCodeClientError
from seo_agent.integrations.opencode.adapter import (
    OpenCodeAdapter,
    FileEditResult,
    PageGenerationResult,
    OpenCodeExecutionResult,
)

__all__ = [
    # Enums
    "OpenCodeModel",
    "OpenCodeAction",
    "OpenCodeStatus",
    # Request models
    "OpenCodeFileEdit",
    "OpenCodeFileRead",
    "OpenCodeSearchQuery",
    "OpenCodeActionRequest",
    "OpenCodeRequest",
    # Response models
    "OpenCodeFileChange",
    "OpenCodeActionResult",
    "OpenCodeResponse",
    "OpenCodeExecutionContext",
    # Client
    "OpenCodeClient",
    "OpenCodeClientError",
    # Adapter
    "OpenCodeAdapter",
    "FileEditResult",
    "PageGenerationResult",
    "OpenCodeExecutionResult",
]