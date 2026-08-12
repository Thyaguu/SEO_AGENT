"""OpenCode CLI client.

This module provides a subprocess-based client for communicating with OpenCode.
It handles request construction, CLI invocation, event stream parsing, and
error handling.

The client follows the single responsibility principle by focusing only
on CLI communication with OpenCode.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

from seo_agent.core.exceptions import IntegrationError
from seo_agent.core.result import Result, Success, Failure

if TYPE_CHECKING:
    from seo_agent.integrations.opencode.models import (
        OpenCodeRequest,
        OpenCodeResponse,
        OpenCodeStatus,
        OpenCodeActionResult,
        OpenCodeFileChange,
    )

logger = logging.getLogger(__name__)


class OpenCodeClientError(IntegrationError):
    """Raised when OpenCode CLI communication fails."""

    pass


class OpenCodeClient:
    """CLI client for OpenCode.

    This client handles all communication with OpenCode via the CLI,
    including command construction, subprocess execution, and event
    stream parsing.

    Attributes:
        base_url: Attach URL for the OpenCode server.
        api_key: API key for authentication (retained for interface compatibility).
        timeout: Request timeout in seconds.
        default_model: Default model to use if not specified.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 15,
        default_model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        """Initialize the OpenCode client.

        Args:
            base_url: Attach URL for the OpenCode server (e.g. http://127.0.0.1:4096).
            api_key: API key for authentication (retained for compatibility).
            timeout: Request timeout in seconds.
            default_model: Default model to use.

        Raises:
            OpenCodeClientError: If configuration is invalid.
        """
        if not base_url:
            raise OpenCodeClientError("OpenCode base URL is required")
        if not api_key:
            raise OpenCodeClientError("OpenCode API key is required")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._default_model = default_model
        self._opencode_bin = self._resolve_opencode_binary()
        self._session_id: str | None = None
        self._session_workspace_path: str | None = None
        logger.debug(
            f"Initialized OpenCode client with attach URL: {base_url}, "
            f"binary: {self._opencode_bin}"
        )

    @staticmethod
    def _resolve_opencode_binary() -> str:
        """Resolve the absolute path to the opencode CLI binary.

        Checks shutil.which first, then falls back to common installation
        paths (Homebrew, Go, local bin).

        Returns:
            Absolute path to the opencode binary, or 'opencode' if not found.
        """
        found = shutil.which("opencode")
        if found:
            return found

        import os

        candidates = [
            "/opt/homebrew/bin/opencode",
            "/usr/local/bin/opencode",
            os.path.expanduser("~/go/bin/opencode"),
            os.path.expanduser("~/.local/bin/opencode"),
        ]
        for path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return "opencode"

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url

    def _serialize_request(self, request: OpenCodeRequest) -> bytes:
        """Serialize an OpenCode request to JSON.

        Retained for backward compatibility and potential future use.

        Args:
            request: The request to serialize.

        Returns:
            JSON-encoded request body.

        Raises:
            OpenCodeClientError: If serialization fails.
        """
        try:
            data = asdict(request)
            # Remove internal fields not expected by OpenCode API schema
            data.pop("created_at", None)
            # Convert enums to values
            data["model"] = request.model.value if hasattr(request.model, "value") else request.model
            data["actions"] = [
                {
                    "action": a.action.value if hasattr(a.action, "value") else a.action,
                    "file_path": a.file_path,
                    "content": a.content,
                    "old_content": a.old_content,
                    "search_query": (
                        asdict(a.search_query) if a.search_query else None
                    ),
                    "max_results": a.max_results,
                }
                for a in request.actions
            ]
            return json.dumps(data).encode("utf-8")
        except Exception as e:
            raise OpenCodeClientError(f"Failed to serialize request: {e}")

    def _parse_event_stream(
        self,
        stdout: str,
        request_id: str,
        started_at: datetime,
    ) -> OpenCodeResponse:
        """Parse the NDJSON event stream from OpenCode CLI into an OpenCodeResponse.

        Each line of stdout is a JSON object with a 'type' field.
        Recognized types: step_start, tool_use, text, step_finish, error.

        For tool_use events, file changes are extracted from:
            part.tool         -> tool name ("write", "edit", etc.)
            part.state.input  -> {"filePath": "...", "content": "...", "diff": "..."}
            part.state.output -> output string
            part.state.status -> "completed" or other

        Args:
            stdout: Raw stdout from the opencode CLI process.
            request_id: The request ID for correlation.
            started_at: When execution started.

        Returns:
            Parsed OpenCodeResponse.

        Raises:
            OpenCodeClientError: If parsing fails critically.
        """
        from seo_agent.integrations.opencode.models import (
            OpenCodeResponse,
            OpenCodeActionResult,
            OpenCodeFileChange,
            OpenCodeStatus,
            OpenCodeAction,
        )

        file_changes: list[OpenCodeFileChange] = []
        text_parts: list[str] = []
        error_message: str | None = None
        status = OpenCodeStatus.COMPLETED
        iteration_count = 0

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"Skipping non-JSON line: {line[:120]}")
                continue

            event_type = event.get("type")

            if event_type == "step_start":
                iteration_count += 1

            elif event_type == "tool_use":
                part = event.get("part", {})
                tool_name = part.get("tool", "").lower()
                state = part.get("state", {})
                tool_input = state.get("input", {})
                tool_status = state.get("status", "")

                is_file_tool = any(
                    k in tool_name
                    for k in ("write", "edit", "replace", "create", "modify")
                )
                if is_file_tool:
                    file_path = (
                        tool_input.get("filePath")
                        or tool_input.get("file_path")
                        or tool_input.get("TargetFile")
                        or tool_input.get("path")
                        or tool_input.get("file")
                        or ""
                    )
                    content = (
                        tool_input.get("content")
                        or tool_input.get("CodeContent")
                        or tool_input.get("ReplacementContent")
                    )
                    diff = tool_input.get("diff")

                    if file_path:
                        change_type = (
                            "created"
                            if any(k in tool_name for k in ("write", "create"))
                            else "modified"
                        )
                        file_changes.append(
                            OpenCodeFileChange(
                                file_path=file_path,
                                change_type=change_type,
                                diff=diff,
                                content=content,
                            )
                        )
                        logger.debug(
                            f"Parsed file change: {tool_name} -> {file_path} "
                            f"(status={tool_status})"
                        )

            elif event_type == "text":
                part = event.get("part", {})
                text = part.get("text", "")
                if text:
                    text_parts.append(text)

            elif event_type == "error":
                part = event.get("part", {})
                error_message = (
                    part.get("error")
                    or part.get("text")
                    or part.get("message")
                    or str(part)
                )
                status = OpenCodeStatus.FAILED
                logger.error(f"OpenCode error event: {error_message}")

            elif event_type == "step_finish":
                # step_finish confirms completion; status stays COMPLETED
                # unless an error was already encountered.
                pass

        # Build action results from collected file changes
        results: list[OpenCodeActionResult] = []

        if file_changes:
            # Group file changes by tool type for correct action mapping
            write_changes = [fc for fc in file_changes if fc.change_type == "created"]
            edit_changes = [fc for fc in file_changes if fc.change_type == "modified"]

            if write_changes:
                results.append(
                    OpenCodeActionResult(
                        action=OpenCodeAction.WRITE_FILE,
                        success=True,
                        output={"text": "Files written successfully."},
                        file_changes=tuple(write_changes),
                    )
                )

            if edit_changes:
                results.append(
                    OpenCodeActionResult(
                        action=OpenCodeAction.EDIT_FILE,
                        success=True,
                        output={"text": "Files edited successfully."},
                        file_changes=tuple(edit_changes),
                    )
                )

        # Add text output as a result if present and no file changes produced
        if text_parts and not results:
            aggregated_text = "".join(text_parts)
            results.append(
                OpenCodeActionResult(
                    action=OpenCodeAction.EXECUTE_COMMAND,
                    success=True,
                    output={"text": aggregated_text},
                )
            )

        completed_at = datetime.utcnow()

        return OpenCodeResponse(
            request_id=request_id,
            status=status,
            results=tuple(results),
            total_iterations=iteration_count,
            model=None,
            error=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _is_session_valid(self, session_id: str) -> bool:
        """Check if a session ID exists and is active on the OpenCode server."""
        import urllib.request
        try:
            url = f"{self._base_url}/session/{session_id}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def delete_session(self, session_id: str | None = None) -> bool:
        """Delete an OpenCode session on the server to release resources.

        Args:
            session_id: Session ID to delete. If None, deletes cached session.

        Returns:
            True if deletion succeeded or session did not exist, False otherwise.
        """
        import urllib.request

        target_id = session_id or self._session_id
        if not target_id:
            return True

        logger.info(f"[OpenCode] Deleting session: {target_id}")
        try:
            url = f"{self._base_url}/session/{target_id}"
            req = urllib.request.Request(url, method="DELETE")
            with urllib.request.urlopen(req, timeout=5) as resp:
                success = resp.status in (200, 204)
                if success and target_id == self._session_id:
                    self._session_id = None
                    self._session_workspace_path = None
                return success
        except Exception as e:
            logger.warning(f"[OpenCode] Failed to delete session {target_id}: {e}")
            if target_id == self._session_id:
                self._session_id = None
                self._session_workspace_path = None
            return False

    def _create_session(self, workspace_path: str | None = None) -> str:
        """Create a new OpenCode session on the server."""
        import urllib.request
        import json

        logger.info("[OpenCode]\nCreating session...")
        url = f"{self._base_url}/session"
        payload: dict[str, Any] = {}
        if workspace_path:
            payload["directory"] = workspace_path

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                session_id = result.get("id")
                if not session_id:
                    raise OpenCodeClientError(
                        "Failed to obtain session ID from OpenCode server response"
                    )
                logger.info(f"[OpenCode] Created new session: {session_id}")
                return session_id
        except Exception as e:
            logger.error(f"[OpenCode] Failed to create session on server: {e}")
            raise OpenCodeClientError(f"Failed to create OpenCode session: {e}")

    def get_or_create_session(self, workspace_path: str | None = None) -> str:
        """Get an existing valid active session or create a new session.

        Ensures:
        - Automatically creates a new session if repo path changes.
        - Validates session state before reuse.
        - Caches only valid sessions.
        """
        if (
            self._session_id
            and self._session_workspace_path == workspace_path
            and self._is_session_valid(self._session_id)
        ):
            logger.info("[OpenCode]\nReusing existing session...")
            return self._session_id

        if self._session_id and not self._is_session_valid(self._session_id):
            logger.info("[OpenCode]\nSession expired. Creating a new session...")

        self._session_id = self._create_session(workspace_path)
        self._session_workspace_path = workspace_path
        return self._session_id

    def _run_cli_command(
        self,
        cmd: list[str],
        cwd: str | None,
        timeout: float,
    ) -> tuple[int, str, str]:
        """Execute CLI subprocess with process group isolation and proper cleanup.

        Args:
            cmd: Command list to execute.
            cwd: Working directory.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (returncode, stdout, stderr).
        """
        import os
        import sys

        kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "cwd": cwd,
        }
        if sys.platform != "win32":
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **kwargs)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return proc.returncode, stdout or "", stderr or ""
        except subprocess.TimeoutExpired as exc:
            self._terminate_process(proc)
            proc.communicate()
            raise exc
        except Exception as exc:
            self._terminate_process(proc)
            proc.communicate()
            raise exc

    @staticmethod
    def _terminate_process(proc: subprocess.Popen[Any]) -> None:
        """Terminate a subprocess and its process group safely."""
        import os
        import signal
        import sys
        import time

        try:
            if sys.platform != "win32":
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                proc.terminate()

            t0 = time.time()
            while time.time() - t0 < 0.5:
                if proc.poll() is not None:
                    return
                time.sleep(0.05)

            if sys.platform != "win32":
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            proc.wait(timeout=1.0)
        except Exception as e:
            logger.debug(f"Error terminating process {proc.pid}: {e}")

    def execute(self, request: OpenCodeRequest) -> Result[OpenCodeResponse, str]:
        """Execute an OpenCode request via CLI subprocess in an isolated session.

        Each request uses a dedicated OpenCode session to prevent context bloat,
        state pollution, and hangs. The session is cleaned up after execution.

        Args:
            request: The OpenCode request to execute.

        Returns:
            Result containing the response or error message.
        """
        logger.info(f"Executing OpenCode request: {request.request_id}")

        session_id = self._create_session(request.workspace_path)
        cwd = request.workspace_path or None
        started_at = datetime.utcnow()

        try:
            cmd = [
                self._opencode_bin,
                "run",
                "--attach", self._base_url,
                "--session", session_id,
                "--format", "json",
                request.instructions,
            ]

            logger.debug(f"OpenCode command: {' '.join(cmd)}")
            if cwd:
                logger.debug(f"OpenCode working directory: {cwd}")

            returncode, stdout, stderr = self._run_cli_command(
                cmd=cmd,
                cwd=cwd,
                timeout=self._timeout,
            )

            # Detect session not found error and recover automatically with fresh session
            combined_output = f"{stderr}\n{stdout}"
            if returncode != 0 and "session not found" in combined_output.lower():
                logger.warning("[OpenCode]\nSession expired. Creating a new session...")
                logger.info("[OpenCode]\nRetrying execution with fresh session...")
                self.delete_session(session_id)
                session_id = self._create_session(request.workspace_path)

                cmd = [
                    self._opencode_bin,
                    "run",
                    "--attach", self._base_url,
                    "--session", session_id,
                    "--format", "json",
                    request.instructions,
                ]
                returncode, stdout, stderr = self._run_cli_command(
                    cmd=cmd,
                    cwd=cwd,
                    timeout=self._timeout,
                )

            logger.debug(
                f"OpenCode Completed: request_id={request.request_id}, "
                f"exit_code={returncode}"
            )

            if returncode != 0 and not stdout.strip():
                error_msg = (
                    f"OpenCode CLI exited with code {returncode}: "
                    f"{stderr.strip() or 'no output'}"
                )
                logger.error(error_msg)
                return Failure(error_msg)

            result = self._parse_event_stream(
                stdout=stdout,
                request_id=request.request_id,
                started_at=started_at,
            )

            logger.info(
                f"OpenCode request {request.request_id} completed "
                f"with status: {result.status.value}"
            )
            return Success(result)

        except FileNotFoundError:
            error_msg = (
                f"OpenCode CLI not found at '{self._opencode_bin}'. "
                "Ensure opencode is installed and on the PATH."
            )
            logger.error(error_msg)
            return Failure(error_msg)

        except subprocess.TimeoutExpired as exc:
            def _decode(data):
                if data is None:
                    return None
                if isinstance(data, bytes):
                    return data.decode("utf-8", errors="replace")
                return data

            logger.error(
                f"OpenCode Timeout: request_id={request.request_id}, "
                f"timeout={self._timeout}s, cmd={exc.cmd}, cwd={cwd}"
            )

            error_msg = (
                f"OpenCode request {request.request_id} timed out "
                f"after {self._timeout}s"
            )
            logger.error(error_msg)
            return Failure(error_msg)

        except OpenCodeClientError as e:
            logger.error(f"OpenCode client error: {e}")
            return Failure(str(e))

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            return Failure(error_msg)

        finally:
            self.delete_session(session_id)

    def execute_simple(
        self,
        instructions: str,
        workspace_path: str | None = None,
        model: str | None = None,
    ) -> Result[OpenCodeResponse, str]:
        """Execute a simple OpenCode request with just instructions.

        This is a convenience method for simple single-instruction requests.

        Args:
            instructions: Natural language instructions.
            workspace_path: Optional workspace path.
            model: Optional model override.

        Returns:
            Result containing the response or error message.
        """
        from seo_agent.integrations.opencode.models import (
            OpenCodeRequest,
            OpenCodeModel,
        )

        request = OpenCodeRequest(
            request_id=f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            instructions=instructions,
            workspace_path=workspace_path,
            model=OpenCodeModel(model) if model else OpenCodeModel(self._default_model),
        )

        return self.execute(request)

    def health_check(self) -> Result[bool, str]:
        """Check if the OpenCode server is reachable and the execution path works.

        Verifies both that the opencode CLI binary exists and that the
        server at the attach URL is responsive by running a minimal
        no-op prompt.

        Returns:
            Result indicating health status.
        """
        logger.debug("Checking OpenCode health")

        # Step 1: Verify the CLI binary exists
        import os
        bin_exists = (
            os.path.isfile(self._opencode_bin)
            if os.path.isabs(self._opencode_bin)
            else shutil.which(self._opencode_bin) is not None
        )
        if not bin_exists:
            return Failure(
                f"OpenCode CLI not found at '{self._opencode_bin}'. "
                "Ensure opencode is installed and on the PATH."
            )

        # Step 2: Verify the server is reachable by running a minimal prompt
        cmd = [
            self._opencode_bin,
            "run",
            "--attach", self._base_url,
            "--format", "json",
            "Respond with exactly: health_ok",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if proc.returncode == 0:
                logger.debug("OpenCode health check passed")
                return Success(True)
            else:
                error_detail = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
                return Failure(
                    f"OpenCode health check failed (exit {proc.returncode}): "
                    f"{error_detail[:200]}"
                )

        except FileNotFoundError:
            return Failure(
                f"OpenCode CLI not found at '{self._opencode_bin}'."
            )

        except subprocess.TimeoutExpired:
            return Failure(
                "OpenCode health check timed out after 30s. "
                f"Is the server running at {self._base_url}?"
            )

        except Exception as e:
            error_msg = f"Health check failed: {e}"
            logger.warning(error_msg)
            return Failure(error_msg)