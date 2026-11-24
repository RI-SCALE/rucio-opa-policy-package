"""Fakes for the parts of Rucio the package imports, so tests need no Rucio install."""

import sys
import types
from dataclasses import dataclass

import pytest


@dataclass
class PermissionResult:
    allowed: bool
    message: str = ""

    def __bool__(self) -> bool:
        return self.allowed


class InternalAccount:
    def __init__(self, external: str) -> None:
        self.external = external


def _install_fake_rucio() -> None:
    rucio = types.ModuleType("rucio")
    core = types.ModuleType("rucio.core")
    permission = types.ModuleType("rucio.core.permission")
    permission.PermissionResult = PermissionResult  # type: ignore[attr-defined]
    sys.modules.setdefault("rucio", rucio)
    sys.modules.setdefault("rucio.core", core)
    sys.modules.setdefault("rucio.core.permission", permission)


_install_fake_rucio()


@pytest.fixture(autouse=True)
def _clear_caches():
    from rucio_opa_v1_policy import permission

    permission._USERINFO_CACHE.clear()
    permission._USERINFO_ENDPOINTS.clear()
    yield


@pytest.fixture
def request_ctx():
    """Flask request context carrying decoded claims, as the patched REST layer sets them."""
    import flask

    app = flask.Flask(__name__)

    def _ctx(claims=None, token="raw.jwt.token"):
        environ = {"token_claims": claims} if claims is not None else {}
        return app.test_request_context(
            headers={"X-Rucio-Auth-Token": token} if token else {},
            environ_overrides=environ,
        )

    return _ctx


@pytest.fixture
def account():
    return InternalAccount
