"""CLI entry point for SEO Agent.

Provides command-line interface to execute the complete SEO workflow on a target
HTML repository using WorkflowOrchestrator.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from seo_agent.api.dependencies import get_container, register_services
from seo_agent.core.logging import configure_logging
from seo_agent.integrations.opencode import ensure_opencode_server
from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.orchestrator import WorkflowOrchestrator


def main() -> None:
    """Run SEO Agent workflow from CLI."""
    configure_logging()

    parser = argparse.ArgumentParser(description="SEO Agent CLI")
    parser.add_argument(
        "--Path_html",
        "--path_html",
        dest="path_html",
        required=True,
        help="Absolute path to target HTML repository",
    )
    args = parser.parse_args()

    repo_path = Path(args.path_html).resolve()
    if not repo_path.exists():
        print(f"Error: Path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)
    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}", file=sys.stderr)
        sys.exit(1)

    html_files = list(repo_path.glob("*.html")) + list(repo_path.glob("*/*.html"))
    if not html_files:
        print(f"Error: Directory contains no HTML files: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Check and start OpenCode server if needed before starting workflow
    if not ensure_opencode_server():
        sys.exit(1)

    print("Starting SEO workflow...\n", flush=True)

    # Initialize dependencies & container
    register_services()
    container = get_container()
    orchestrator = container.resolve(WorkflowOrchestrator)

    # Build workflow context
    context = WorkflowContext(repository_path=repo_path)
    context.config["skip_git"] = True

    # Execute workflow orchestrator
    result = asyncio.run(orchestrator.run(context))
    if result.is_success():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
