"""Real OPA for the integration tests.

Set POLICY_TEST_OPA_URL to reuse a running OPA (e.g. `make up`); otherwise
testcontainers starts docker/docker-compose.yml for the session.
"""

import os
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

COMPOSE_DIR = Path(__file__).resolve().parents[2] / "docker"


def _healthy(url: str) -> bool:
    try:
        with urlopen(f"{url}/health", timeout=2):  # noqa: S310
            return True
    except OSError:
        return False


def _wait_healthy(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while not _healthy(url):
        if time.monotonic() > deadline:
            raise TimeoutError(f"OPA at {url} not healthy after {timeout}s")
        time.sleep(0.5)


@pytest.fixture(scope="session")
def opa_url():
    url = os.environ.get("POLICY_TEST_OPA_URL")
    if url:
        _wait_healthy(url)
        yield url.rstrip("/")
        return

    from testcontainers.compose import DockerCompose

    with DockerCompose(str(COMPOSE_DIR), wait=True) as compose:
        host, port = compose.get_service_host_and_port("opa", 8181)
        url = f"http://{host}:{port}"
        _wait_healthy(url)
        yield url


@pytest.fixture(autouse=True)
def _point_at_opa(opa_url, monkeypatch):
    monkeypatch.setenv("OPA_URL", opa_url)
    monkeypatch.setenv("OPA_POLICY_PATH", "vo/authz/v1/allow")
