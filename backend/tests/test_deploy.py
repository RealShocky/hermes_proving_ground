from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from app.deploy import (
    DeployError,
    cleanup_stale_pidfile,
    deploy_server,
    deploy_status,
    is_deployed,
    post_merge_deploy,
    post_merge_undeploy,
    pid_exists,
    pidfile_is_stale,
    read_pid,
    stop_server,
    write_pid,
)


# -- read_pid / write_pid --


def test_read_pid_returns_none_when_missing(tmp_path: Path) -> None:
    assert read_pid(tmp_path / "nope.pid") is None


def test_read_pid_parses_integer(tmp_path: Path) -> None:
    pidfile = tmp_path / "server.pid"
    pidfile.write_text("12345\n", encoding="utf-8")
    assert read_pid(pidfile) == 12345


def test_read_pid_returns_none_for_garbage(tmp_path: Path) -> None:
    pidfile = tmp_path / "bad.pid"
    pidfile.write_text("not a pid\n", encoding="utf-8")
    assert read_pid(pidfile) is None


def test_write_pid_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dirs" / "server.pid"
    write_pid(target, 4321)
    assert target.exists()
    assert read_pid(target) == 4321


def test_write_pid_overwrites_existing(tmp_path: Path) -> None:
    pidfile = tmp_path / "server.pid"
    write_pid(pidfile, 100)
    write_pid(pidfile, 200)
    assert read_pid(pidfile) == 200


# -- pid_exists --


def test_pid_exists_false_for_nonpositive() -> None:
    assert pid_exists(0) is False
    assert pid_exists(-1) is False


def test_pid_exists_false_for_absent_pid() -> None:
    # Pick a pid that should not exist.
    pid = 2**31 - 1
    assert pid_exists(pid) is False


def test_pid_exists_true_for_self() -> None:
    # Our own pid must be reported as alive.
    assert pid_exists(os.getpid()) is True


# -- pidfile_is_stale / cleanup_stale_pidfile --


def test_pidfile_is_stale_false_when_missing(tmp_path: Path) -> None:
    assert pidfile_is_stale(tmp_path / "missing.pid") is False


def test_pidfile_is_stale_true_for_dead_pid(tmp_path: Path) -> None:
    pidfile = tmp_path / "dead.pid"
    write_pid(pidfile, 2**31 - 1)
    assert pidfile_is_stale(pidfile) is True


def test_pidfile_is_stale_false_for_live_pid(tmp_path: Path) -> None:
    pidfile = tmp_path / "live.pid"
    write_pid(pidfile, os.getpid())
    assert pidfile_is_stale(pidfile) is False


def test_cleanup_stale_removes_dead_pidfile(tmp_path: Path) -> None:
    pidfile = tmp_path / "dead.pid"
    write_pid(pidfile, 2**31 - 1)
    assert cleanup_stale_pidfile(pidfile) is True
    assert not pidfile.exists()


def test_cleanup_stale_leaves_live_pidfile(tmp_path: Path) -> None:
    pidfile = tmp_path / "live.pid"
    write_pid(pidfile, os.getpid())
    assert cleanup_stale_pidfile(pidfile) is False
    assert pidfile.exists()


def test_cleanup_stale_noop_when_missing(tmp_path: Path) -> None:
    assert cleanup_stale_pidfile(tmp_path / "missing.pid") is False


# -- stop_server --


def test_stop_server_missing_pidfile_returns_none(tmp_path: Path) -> None:
    result = stop_server(tmp_path / "missing.pid")
    assert result is None


def test_stop_server_removes_stale_pidfile(tmp_path: Path) -> None:
    pidfile = tmp_path / "stale.pid"
    write_pid(pidfile, 2**31 - 1)
    result = stop_server(pidfile)
    # Should report the recorded pid and remove the file.
    assert result == 2**31 - 1
    assert not pidfile.exists()


# -- deploy_status / is_deployed --


def test_deploy_status_reports_stale(tmp_path: Path) -> None:
    pidfile = tmp_path / "stale.pid"
    write_pid(pidfile, 2**31 - 1)
    status = deploy_status(pidfile)
    assert status["pid"] == 2**31 - 1
    assert status["running"] is False
    assert status["stale"] is True
    assert status["pidfile"] == str(pidfile)


def test_deploy_status_reports_missing(tmp_path: Path) -> None:
    status = deploy_status(tmp_path / "missing.pid")
    assert status["pid"] is None
    assert status["running"] is False
    assert status["stale"] is False


def test_is_deployed_false_when_missing(tmp_path: Path) -> None:
    assert is_deployed(tmp_path / "missing.pid") is False


def test_is_deployed_false_for_stale(tmp_path: Path) -> None:
    pidfile = tmp_path / "stale.pid"
    write_pid(pidfile, 2**31 - 1)
    assert is_deployed(pidfile) is False


def test_is_deployed_true_for_live_self(tmp_path: Path) -> None:
    pidfile = tmp_path / "self.pid"
    write_pid(pidfile, os.getpid())
    assert is_deployed(pidfile) is True


# -- deploy_server (real background process) --


def test_deploy_server_starts_process_and_writes_pidfile(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    try:
        pid = deploy_server(
            cmd=cmd,
            runtime_dir=runtime,
            wait=False,
        )
        assert pid == os.getpid() or pid > 0
        pidfile = runtime / "health_server.pid"
        assert read_pid(pidfile) == pid
        assert is_deployed(pidfile) is True
    finally:
        # Clean up the background sleeper.
        stop_server(runtime / "health_server.pid")
        assert not (runtime / "health_server.pid").exists()


def test_deploy_server_rejects_when_live_pidfile_present(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    pidfile = runtime / "health_server.pid"
    # Record our own (live) pid so deploy should refuse.
    write_pid(pidfile, os.getpid())
    with pytest.raises(DeployError):
        deploy_server(
            cmd=[sys.executable, "-c", "pass"],
            runtime_dir=runtime,
            wait=False,
        )


def test_deploy_server_removes_stale_pidfile_before_start(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    pidfile = runtime / "health_server.pid"
    write_pid(pidfile, 2**31 - 1)  # stale
    try:
        deploy_server(
            cmd=[sys.executable, "-c", "import time; time.sleep(60)"],
            runtime_dir=runtime,
            wait=False,
        )
        # The stale pidfile should have been replaced with a live pid.
        assert is_deployed(pidfile) is True
    finally:
        stop_server(pidfile)


def test_deploy_server_logs_output(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cmd = [sys.executable, "-c", "print('hello deploy'); import time; time.sleep(60)"]
    try:
        deploy_server(cmd=cmd, runtime_dir=runtime, wait=False)
        log_path = runtime / "health_server.log"
        # Give the child a moment to write its stdout.
        deadline = time.monotonic() + 5
        text = ""
        while time.monotonic() < deadline:
            if log_path.exists():
                text = log_path.read_text(encoding="utf-8", errors="replace")
                if "hello deploy" in text:
                    break
            time.sleep(0.2)
        assert "hello deploy" in text
    finally:
        stop_server(runtime / "health_server.pid")


# -- post_merge_deploy / post_merge_undeploy --


def test_post_merge_deploy_and_undeploy_roundtrip(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    status = post_merge_deploy(
        cmd=[sys.executable, "-c", "import time; time.sleep(60)"],
        runtime_dir=runtime,
        wait=False,
    )
    assert status["action"] == "deployed"
    assert status["running"] is True
    assert isinstance(status["pid"], int)

    undeploy_status = post_merge_undeploy(runtime_dir=runtime)
    assert undeploy_status["action"] == "undeployed"
    assert undeploy_status["running"] is False
    assert not (runtime / "health_server.pid").exists()


def test_post_merge_undeploy_noop_when_not_deployed(tmp_path: Path) -> None:
    status = post_merge_undeploy(runtime_dir=tmp_path)
    assert status["action"] == "undeployed"
    assert status["stopped_pid"] is None


# -- deploy_payload rendering --


def test_deploy_payload_is_sorted_json(tmp_path: Path) -> None:
    from app.deploy import deploy_payload

    status = deploy_status(tmp_path / "x.pid")
    text = deploy_payload(status)
    import json

    assert json.loads(text) == status
