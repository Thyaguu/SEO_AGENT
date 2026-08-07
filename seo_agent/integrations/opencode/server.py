"""OpenCode server manager.

Handles checking whether the OpenCode server is running and starting it
automatically if needed before starting the workflow.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def check_opencode_health(base_url: str, timeout: float = 2.0) -> bool:
    """Check if the OpenCode server is reachable and responsive at base_url.

    Args:
        base_url: The base URL of the OpenCode server (e.g. http://127.0.0.1:4096).
        timeout: HTTP request timeout in seconds.

    Returns:
        True if the server responds with a non-5xx status code, False otherwise.
    """
    clean_url = base_url.rstrip("/")
    target_url = f"{clean_url}/session"
    try:
        req = urllib.request.Request(target_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def start_opencode_server(base_url: str) -> subprocess.Popen[Any] | None:
    """Attempt to start the OpenCode server locally using opencode serve.

    Args:
        base_url: Configured OpenCode base URL to extract port/host.

    Returns:
        Popen object if process launched, None if binary is missing or launch fails.
    """
    from seo_agent.integrations.opencode.client import OpenCodeClient

    opencode_bin = OpenCodeClient._resolve_opencode_binary()

    bin_exists = (
        os.path.isfile(opencode_bin)
        if os.path.isabs(opencode_bin)
        else shutil.which(opencode_bin) is not None
    )
    if not bin_exists:
        logger.warning(f"OpenCode CLI binary not found at '{opencode_bin}'")
        return None

    parsed = urllib.parse.urlparse(base_url)
    port = parsed.port if parsed.port else 4096
    hostname = parsed.hostname or "127.0.0.1"

    cmd = [opencode_bin, "serve", "--port", str(port)]
    if hostname not in ("127.0.0.1", "localhost", "0.0.0.0"):
        cmd.extend(["--hostname", hostname])

    logger.info(f"Starting OpenCode server: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc
    except Exception as e:
        logger.error(f"Failed to launch OpenCode server process: {e}")
        return None


def ensure_opencode_server(
    base_url: str | None = None,
    startup_timeout: float | None = None,
    check_interval: float = 1.0,
) -> bool:
    """Ensure OpenCode server is running and healthy.

    If not running, attempts to start it automatically and waits up to
    startup_timeout seconds for it to become healthy.

    Args:
        base_url: Optional OpenCode endpoint URL. If None, reads from settings.
        startup_timeout: Maximum time in seconds to wait for server startup.
            If None, reads settings.opencode.server_startup_timeout (default 30).
        check_interval: Time in seconds between health check retries.

    Returns:
        True if server is running and healthy, False otherwise.
    """
    from config import settings

    if not base_url:
        base_url = str(settings.opencode.base_url)

    if startup_timeout is None:
        startup_timeout = float(getattr(settings.opencode, "server_startup_timeout", 30))

    clean_base_url = base_url.rstrip("/")

    print("Checking OpenCode server...", flush=True)

    if check_opencode_health(clean_base_url):
        print("✓ OpenCode server detected.", flush=True)
        return True

    print("Starting OpenCode server...", flush=True)
    proc = start_opencode_server(clean_base_url)

    print("Waiting for OpenCode...", flush=True)

    start_time = time.time()
    while time.time() - start_time < startup_timeout:
        time.sleep(check_interval)
        if check_opencode_health(clean_base_url):
            print("OpenCode is ready.", flush=True)
            return True

        if proc and proc.poll() is not None:
            logger.warning(f"OpenCode server subprocess exited with code {proc.returncode}")
            break

    parsed = urllib.parse.urlparse(clean_base_url)
    port = parsed.port if parsed.port else 4096

    print("\nOpenCode server is not running.", flush=True)
    print("\nPlease start it using:", flush=True)
    print(f"\nopencode serve --port {port}", flush=True)
    print("\nor configure OPENCODE_BASE_URL correctly.", flush=True)
    print("\nWorkflow aborted.", flush=True)

    return False
