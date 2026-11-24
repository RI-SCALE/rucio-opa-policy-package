# Licensed under the Apache License, Version 2.0
"""Rucio permission module that delegates every decision to OPA.

The policy decides from the action and the token's claims alone; nothing
here reads the Rucio catalog. Selected kwargs are forwarded so that OPA's
decision log records what each decision was about.
"""

import hashlib
import json
import logging
import os
import time
from enum import Enum
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from typing import Optional

    from rucio.common.types import InternalAccount
    from rucio.core.permission import PermissionResult
    from sqlalchemy.orm import Session

from rucio_opa_v1_policy.opa_client import query_opa

log = logging.getLogger(__name__)

# RUCIO_OPA_DEBUG_INPUT=1 logs every input document at WARNING level.
_DEBUG_INPUT = os.environ.get("RUCIO_OPA_DEBUG_INPUT", "").strip() in ("1", "true", "True")

# Forwarded as-is: acr for MFA-dependent policies, the rest for the decision log.
_SCALAR_CLAIMS: tuple[str, ...] = ("acr", "aud", "iss", "sub")

_PASSTHROUGH_KEYS: frozenset[str] = frozenset(
    {
        "account",
        "locked",
        "rse_expression",
        "source_rse_expression",
        "rule_id",
        "options",
        "rse",
        "parameters",
        "parameter",
        "rse_id",
        "scheme",
        "hostname",
        "data",
        "scope",
        "name",
        "dids",
        "attachments",
        "files",
    }
)

_USERINFO_TIMEOUT = float(os.environ.get("RUCIO_OPA_USERINFO_TIMEOUT", "3"))
_USERINFO_CACHE: dict[str, tuple[float, list[str]]] = {}  # sha256(token) -> (exp, entitlements)
_USERINFO_ENDPOINTS: dict[str, str] = {}  # iss -> userinfo_endpoint


def has_permission(
    issuer: "InternalAccount",
    action: str,
    kwargs: dict[str, Any],
    *,
    session: "Optional[Session]" = None,
) -> "PermissionResult":
    """Ask OPA whether *issuer* may perform *action*. Fails closed."""
    from rucio.core.permission import PermissionResult

    try:
        input_doc = _build_input(issuer, action, kwargs)
    except Exception:
        log.exception("OPA: input payload generation failed for action=%s", action)
        return PermissionResult(False, "Internal authorization failure: payload construction error")

    if _DEBUG_INPUT:
        log.warning("OPA input for action=%s: %s", action, input_doc)

    try:
        allowed = query_opa(input_doc)
    except Exception as err:
        log.critical("OPA query failed for action=%s: %s", action, err, exc_info=True)
        return PermissionResult(False, "Authorization engine unreachable (system degraded)")
    return PermissionResult(allowed, "" if allowed else "Access denied by OPA policy validation")


def _build_input(issuer: "InternalAccount", action: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "issuer": issuer.external,
        "action": action,
        "token": _token_claims(),
        "kwargs": _serialisable_kwargs(kwargs),
    }


def _request_claims() -> dict[str, Any]:
    """Return the decoded token of the current request, or {} without one.

    The claims are placed in ``request.environ["token_claims"]`` by the Rucio
    REST layer patch; userpass and daemon calls carry none.
    """
    try:
        from flask import has_request_context, request
    except ImportError:
        return {}
    if not has_request_context():
        return {}
    return request.environ.get("token_claims") or {}


def _as_list(value: Any) -> list[str]:
    """Normalise a list claim that may also arrive as a space-separated string."""
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    return list(value)


def _bearer_token() -> str:
    """Return the raw access token from X-Rucio-Auth-Token or Authorization."""
    from flask import request

    token = request.headers.get("X-Rucio-Auth-Token", "")
    auth = request.headers.get("Authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:]
    return token


def _userinfo_entitlements(claims: dict[str, Any]) -> list[str]:
    """Fetch entitlements from the issuer's userinfo endpoint.

    For IdPs that keep entitlements out of the access token (e.g. EGI
    Check-in). Cached per token until it expires; any failure yields [].
    """
    raw = _bearer_token()
    if not raw or "iss" not in claims:
        return []
    key = hashlib.sha256(raw.encode()).hexdigest()
    hit = _USERINFO_CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        iss = claims["iss"].rstrip("/")
        if iss not in _USERINFO_ENDPOINTS:
            with urlopen(
                f"{iss}/.well-known/openid-configuration", timeout=_USERINFO_TIMEOUT
            ) as resp:
                _USERINFO_ENDPOINTS[iss] = json.load(resp)["userinfo_endpoint"]
        req = Request(_USERINFO_ENDPOINTS[iss], headers={"Authorization": f"Bearer {raw}"})
        with urlopen(req, timeout=_USERINFO_TIMEOUT) as resp:
            info = json.load(resp)
            ents = _as_list(info.get("entitlements") or info.get("eduperson_entitlement"))
    except Exception as err:  # noqa: BLE001
        log.warning("OPA: userinfo lookup failed for iss=%s: %s", claims.get("iss"), err)
        return []
    if len(_USERINFO_CACHE) > 1000:
        _USERINFO_CACHE.clear()
    _USERINFO_CACHE[key] = (float(claims.get("exp", time.time() + 300)), ents)
    return ents


def _token_claims() -> dict[str, Any]:
    """Return the claims OPA decides on; entitlements fall back to userinfo."""
    claims = _request_claims()
    entitlements = _as_list(claims.get("entitlements") or claims.get("eduperson_entitlement"))
    if claims and not entitlements:
        entitlements = _userinfo_entitlements(claims)
    token: dict[str, Any] = {"entitlements": entitlements}
    for key in _SCALAR_CLAIMS:
        if key in claims:
            token[key] = claims[key]
    return token


def _externalise(value: Any) -> Any:
    if hasattr(value, "external"):
        return value.external
    if isinstance(value, Enum):
        return value.value  # e.g. DIDType inside dids[]; not JSON-serialisable
    if isinstance(value, dict):
        return {k: _externalise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_externalise(v) for v in value]
    return value


def _serialisable_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: _externalise(kwargs[key]) for key in _PASSTHROUGH_KEYS if key in kwargs}
