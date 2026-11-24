# Licensed under the Apache License, Version 2.0
"""Minimal synchronous OPA REST client.

Configured through the environment:

- ``OPA_URL``: OPA base URL (default ``http://localhost:8181``)
- ``OPA_POLICY_PATH``: rule to query (default ``vo/authz/v1/allow``)
- ``OPA_TIMEOUT``: HTTP timeout in seconds (default ``2``)
"""

import json
import logging
import os
from typing import Any
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


def _decision_url() -> str:
    base = os.environ.get("OPA_URL", "http://localhost:8181").rstrip("/")
    path = os.environ.get("OPA_POLICY_PATH", "vo/authz/v1/allow")
    return f"{base}/v1/data/{path}"


def query_opa(input_doc: dict[str, Any]) -> bool:
    """Return True only if OPA evaluates the rule to ``true``.

    An undefined or non-boolean result, a transport error or an invalid
    response all yield False (fail closed).
    """
    url = _decision_url()
    req = Request(
        url,
        data=json.dumps({"input": input_doc}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=float(os.environ.get("OPA_TIMEOUT", "2"))) as resp:
            result = json.load(resp).get("result")
    except (OSError, ValueError) as exc:
        log.error("OPA query to %s failed, denying: %s", url, exc)
        return False
    log.debug("OPA %s input=%s result=%s", url, input_doc, result)
    return result is True
