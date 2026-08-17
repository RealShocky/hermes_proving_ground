from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is not a hard test dep
    yaml = None  # type: ignore[assignment]


def _repo_root() -> Path:
    # backend/tests/test_docker.py -> <repo>
    return Path(__file__).resolve().parent.parent.parent


def test_dockerfile_exists_and_is_nonempty() -> None:
    dockerfile = _repo_root() / "Dockerfile"
    assert dockerfile.exists()
    assert dockerfile.stat().st_size > 0


def test_dockerfile_uses_pinned_slim_base_image() -> None:
    content = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    from_lines = [line for line in content.splitlines() if line.startswith("FROM")]
    assert from_lines, "Dockerfile must declare a base image"
    assert from_lines[0] == "FROM python:3.11-slim"


def test_dockerfile_sets_runtime_layout_and_path() -> None:
    content = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    assert "WORKDIR /app" in content
    assert "COPY backend/ ./backend/" in content
    assert "COPY frontend/ ./frontend/" in content
    # The app must be importable as the "app" package from inside the image.
    assert "PYTHONPATH=/app/backend" in content


def test_dockerfile_exposes_service_port_and_command() -> None:
    content = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    assert "EXPOSE 8765" in content
    # The CMD is written as a JSON exec array; assert the host and port tokens.
    assert '"--host", "0.0.0.0"' in content
    assert '"--port", "8765"' in content
    assert "app.health_server" in content


def test_dockerfile_has_a_healthcheck() -> None:
    content = (_repo_root() / "Dockerfile").read_text(encoding="utf-8")
    assert "HEALTHCHECK" in content
    assert "python -m app.health_server --check" in content


def test_compose_file_exists_and_is_nonempty() -> None:
    compose = _repo_root() / "docker-compose.yml"
    assert compose.exists()
    assert compose.stat().st_size > 0


def test_compose_builds_the_local_image() -> None:
    content = (_repo_root() / "docker-compose.yml").read_text(encoding="utf-8")
    assert "services:" in content
    assert "app:" in content
    assert "dockerfile: Dockerfile" in content
    assert "context: ." in content


def test_compose_exposes_port_and_healthchecks() -> None:
    content = (_repo_root() / "docker-compose.yml").read_text(encoding="utf-8")
    assert "8765:8765" in content
    assert "healthcheck:" in content


def test_compose_structure_when_yaml_available() -> None:
    if yaml is None:
        import pytest
        pytest.skip("PyYAML not installed; structural check skipped")

    data = yaml.safe_load(
        (_repo_root() / "docker-compose.yml").read_text(encoding="utf-8")
    )
    assert "services" in data
    app = data["services"]["app"]
    assert app["build"]["context"] == "."
    assert app["build"]["dockerfile"] == "Dockerfile"
    assert app["ports"] == ["8765:8765"]
    assert app["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-m",
        "app.health_server",
        "--check",
    ]
