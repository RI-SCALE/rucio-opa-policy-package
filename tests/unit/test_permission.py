import enum
import json

from rucio_opa_v1_policy import permission
from rucio_opa_v1_policy.permission import has_permission


class DIDType(enum.Enum):
    FILE = "F"


def _capture(monkeypatch, result=True):
    seen = {}

    def fake_query(doc):
        seen["doc"] = doc
        return result

    monkeypatch.setattr(permission, "query_opa", fake_query)
    return seen


def test_input_contract(monkeypatch, account, request_ctx):
    seen = _capture(monkeypatch)
    with request_ctx({"entitlements": ["urn:a"], "sub": "s"}):
        res = has_permission(account("root"), "add_rule", {"account": account("jdoe"), "x": 1})
    assert res.allowed
    assert seen["doc"] == {
        "issuer": "root",
        "action": "add_rule",
        "token": {"entitlements": ["urn:a"], "sub": "s"},
        "kwargs": {"account": "jdoe"},  # only passthrough keys, externalised
    }


def test_kwargs_serialisable(monkeypatch, account):
    seen = _capture(monkeypatch)
    dids = [{"scope": account("user.jdoe"), "type": DIDType.FILE}]
    has_permission(account("root"), "attach_dids", {"dids": dids})
    json.dumps(seen["doc"])  # must not raise
    assert seen["doc"]["kwargs"]["dids"] == [{"scope": "user.jdoe", "type": "F"}]


def test_denied(monkeypatch, account):
    _capture(monkeypatch, result=False)
    res = has_permission(account("root"), "del_rse", {})
    assert not res.allowed
    assert "Access denied" in res.message


def test_opa_error_fails_closed(monkeypatch, account):
    def boom(doc):
        raise RuntimeError("down")

    monkeypatch.setattr(permission, "query_opa", boom)
    res = has_permission(account("root"), "add_rule", {})
    assert not res.allowed
    assert "unreachable" in res.message


def test_payload_error_fails_closed(monkeypatch, account):
    _capture(monkeypatch)
    res = has_permission(object(), "add_rule", {})  # issuer without .external
    assert not res.allowed
    assert "payload" in res.message
