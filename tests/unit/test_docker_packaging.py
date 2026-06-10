"""Guard tests for the Docker packaging (STORY_018).

These assert the *contents* of the Dockerfile and docker-compose.yml rather than
building an image — fast, offline, no Docker required. They lock in the fix that
makes the container actually boot:

  - The runtime image must include alembic.ini + migrations/, because the app runs
    migrations_runner.upgrade_to_head() on startup and loads them from the image root.
    Omitting them (the original bug) crashes the container before it serves.
  - Compose must bind-mount the host ./data so the container uses the operator's real
    SQLite DB and shoot folders, and writes persist back to the host.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # tests/unit/ -> repo root
_DOCKERFILE = (_ROOT / "Dockerfile").read_text()
_COMPOSE = (_ROOT / "docker-compose.yml").read_text()
_MAKEFILE = (_ROOT / "Makefile").read_text()


def test_dockerfile_copies_alembic_config() -> None:
    assert "COPY alembic.ini" in _DOCKERFILE, (
        "Dockerfile must copy alembic.ini into the image — the startup migration "
        "loads it from the image root, so without it the container crashes on boot."
    )


def test_dockerfile_copies_migrations_directory() -> None:
    assert "COPY migrations" in _DOCKERFILE, (
        "Dockerfile must copy the migrations/ directory into the image — "
        "migrations_runner.upgrade_to_head() needs the revision scripts at startup."
    )


def test_compose_bind_mounts_host_data_directory() -> None:
    assert "./data:/app/data" in _COMPOSE, (
        "docker-compose.yml must bind-mount the host ./data onto /app/data so the "
        "container uses the real SQLite DB and shoot folders, and writes persist."
    )


def test_compose_does_not_use_the_old_named_volume() -> None:
    assert "app-data:/app/data" not in _COMPOSE, (
        "The named-volume mount was replaced by the ./data bind mount (STORY_018); "
        "a stray app-data mount would hide the operator's real data."
    )


def test_makefile_has_detached_docker_up_target() -> None:
    assert "docker-up:" in _MAKEFILE and "docker compose up -d" in _MAKEFILE, (
        "Makefile must define a docker-up target that runs `docker compose up -d` "
        "(detached) so the app can run in the background (STORY_019)."
    )


def test_makefile_has_docker_down_target() -> None:
    assert "docker-down:" in _MAKEFILE and "docker compose down" in _MAKEFILE, (
        "Makefile must define a docker-down target to stop the background container."
    )


def test_compose_publishes_configurable_port_defaulting_to_9001() -> None:
    assert "${WEB_PORT:-9001}:8000" in _COMPOSE, (
        "docker-compose.yml must publish the container's internal :8000 on the host via "
        "${WEB_PORT:-9001} — default host port 9001, overridable with WEB_PORT (STORY_020)."
    )


def test_compose_no_longer_hardcodes_port_8000_on_the_host() -> None:
    assert '"8000:8000"' not in _COMPOSE, (
        "The fixed 8000:8000 mapping was replaced by ${WEB_PORT:-9001}:8000; a leftover "
        "8000:8000 would publish on the wrong host port."
    )
