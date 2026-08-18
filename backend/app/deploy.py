from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

# Default runtime directory for pidfiles and deploy logs. Relative to the
# repo root so the helper works from any working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RUNTIME_DIR = _REPO_ROOT / "runtime"

# Default deploy command: run the stdlib health server with JSON-arg style.
DEFAULT_SERVER_CMD: Sequence[str] = [sys.executable, "-m", "app.health_server"]

# Seconds to wait for the server to accept its port after start.
START_TIMEOUT = 10.0
# Seconds to wait for a graceful shutdown before force-killing.
STOP_TIMEOUT = 5.0


class DeployError(Exception):
    """Raised when a deploy or pidfile operation fails."""


def default_runtime_dir() -> Path:
    return DEFAULT_RUNTIME_DIR


def default_pidfile_path() -> Path:
    return default_runtime_dir() / "health_server.pid"


def default_log_path() -> Path:
    return default_runtime_dir() / "health_server.log"


def read_pid(pidfile: Path) -> int | None:
    """Read a PID from a pidfile. Returns None when the file is missing or
    does not contain a valid integer PID."""
    try:
        text = pidfile.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def write_pid(pidfile: Path, pid: int) -> None:
    """Write a PID to a pidfile, creating parent directories as needed."""
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(f"{pid}\n", encoding="utf-8")


def pid_exists(pid: int) -> bool:
    """Check whether a process with the given PID is currently running.

    POSIX can use the signal(0) probe. Windows cannot: Python's os.kill
    emulates signals differently there, so use tasklist instead of risking a
    Ctrl-C style interrupt to the current process.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return False
        return f'"{pid}"' in completed.stdout or f",{pid}," in completed.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but belongs to another user.
        return True
    except (OSError, TypeError):
        return False
    return True


def pidfile_is_stale(pidfile: Path) -> bool:
    """Return True when a pidfile exists but no matching process is running.

    A missing pidfile is not stale (there is simply nothing to clean up).
    """
    pid = read_pid(pidfile)
    if pid is None:
        return False
    return not pid_exists(pid)


def cleanup_stale_pidfile(pidfile: Path) -> bool:
    """Remove a pidfile that is stale (no live process behind it).

    Returns True if a stale pidfile was removed, False otherwise (missing or
    still in use).
    """
    if not pidfile.exists():
        return False
    if not pidfile_is_stale(pidfile):
        return False
    try:
        pidfile.unlink()
    except OSError:
        return False
    return True


def stop_server(pidfile: Path, timeout: float = STOP_TIMEOUT) -> int | None:
    """Stop the server recorded in a pidfile.

    Sends SIGTERM (where available), waits up to `timeout` seconds for the
    process to exit, force-kills if it lingers, and finally removes the
    pidfile. Returns the stopped PID, or None when no pidfile was present.
    """
    pid = read_pid(pidfile)
    if pid is None:
        # No usable pidfile. Clean up any stale leftover and stop.
        cleanup_stale_pidfile(pidfile)
        return None

    if not pid_exists(pid):
        # Stale pidfile: process is gone, just remove the file.
        cleanup_stale_pidfile(pidfile)
        return pid

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    else:
        # Send SIGTERM if available on this platform.
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            # Process already exited between probe and signal.
            cleanup_stale_pidfile(pidfile)
            return pid

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if os.name != "nt":
            try:
                waited_pid, _status = os.waitpid(pid, os.WNOHANG)
                if waited_pid == pid:
                    break
            except ChildProcessError:
                pass
        if not pid_exists(pid):
            break
        time.sleep(0.1)
    else:
        # Force kill if it still lingers.
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

    cleanup_stale_pidfile(pidfile)
    return pid


def _port_reachable(host: str, port: int, timeout: float = START_TIMEOUT) -> bool:
    """Poll the host:port until a connection is accepted or timeout elapses."""
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def deploy_server(
    cmd: Sequence[str] = DEFAULT_SERVER_CMD,
    host: str = "127.0.0.1",
    port: int = 8765,
    runtime_dir: Path | None = None,
    cwd: str | None = None,
    wait: bool = True,
) -> int:
    """Start the local server in the background and record its PID.

    Creates the runtime directory, writes a pidfile, and (optionally) waits
    for the server port to become reachable. Returns the server PID.
    """
    runtime_dir = runtime_dir or default_runtime_dir()
    pidfile = runtime_dir / "health_server.pid"
    log_path = runtime_dir / "health_server.log"

    # Remove any stale pidfile before starting a fresh server.
    cleanup_stale_pidfile(pidfile)

    if pidfile.exists():
        raise DeployError(
            f"pidfile {pidfile} already in use by a live process; "
            "stop it first with stop_server"
        )

    runtime_dir.mkdir(parents=True, exist_ok=True)
    # Force unbuffered output so the log file reflects server output
    # promptly (mirrors the Dockerfile's PYTHONUNBUFFERED=1).
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    log_file = open(log_path, "wb")
    process = subprocess.Popen(
        list(cmd),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )
    pid = process.pid
    write_pid(pidfile, pid)
    log_file.close()

    if wait:
        reachable = _port_reachable(host, port)
        if not reachable:
            # Leave the process running but report failure clearly.
            raise DeployError(
                f"server on {host}:{port} did not become reachable within "
                f"{START_TIMEOUT:.0f}s (pid {pid})"
            )
    return pid


def is_deployed(pidfile: Path = default_pidfile_path()) -> bool:
    """Return True when a live process is recorded in the pidfile."""
    pid = read_pid(pidfile)
    return pid is not None and pid_exists(pid)


def deploy_status(pidfile: Path = default_pidfile_path()) -> dict[str, object]:
    """Return a JSON-serializable deploy status for the local server."""
    pid = read_pid(pidfile)
    alive = pid is not None and pid_exists(pid)
    stale = pid is not None and not alive
    return {
        "pid": pid,
        "running": alive,
        "stale": stale,
        "pidfile": str(pidfile),
    }


def post_merge_deploy(
    cmd: Sequence[str] = DEFAULT_SERVER_CMD,
    host: str = "127.0.0.1",
    port: int = 8765,
    runtime_dir: Path | None = None,
    cwd: str | None = None,
    wait: bool = True,
) -> dict[str, object]:
    """Post-merge local deployment helper.

    Cleans up any stale pidfile, deploys the server locally, and returns a
    status dict suitable for JSON output. This is the one-call entry point a
    developer (or automation) uses right after merging.
    """
    runtime_dir = runtime_dir or default_runtime_dir()
    pid = deploy_server(
        cmd=cmd,
        host=host,
        port=port,
        runtime_dir=runtime_dir,
        cwd=cwd,
        wait=wait,
    )
    status = deploy_status(runtime_dir / "health_server.pid")
    status["action"] = "deployed"
    status["host"] = host
    status["port"] = port
    status["pid"] = pid
    return status


def post_merge_undeploy(
    runtime_dir: Path | None = None,
) -> dict[str, object]:
    """Stop the locally deployed server and remove its pidfile."""
    pidfile = (runtime_dir or default_runtime_dir()) / "health_server.pid"
    stopped_pid = stop_server(pidfile)
    status = deploy_status(pidfile)
    status["action"] = "undeployed"
    status["stopped_pid"] = stopped_pid
    return status


def deploy_payload(status: dict[str, object]) -> str:
    """Render a deploy status dict as sorted, indented JSON."""
    return json.dumps(status, indent=2, sort_keys=True)
