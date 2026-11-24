"""has_permission end to end against a real OPA with the contract policy."""

import enum

import pytest

from rucio_opa_v1_policy.permission import has_permission

pytestmark = pytest.mark.integration

REPORTER = "urn:test:group:reporter:role=member"
USER = "urn:test:group:user:role=member"


class DIDType(enum.Enum):
    FILE = "F"


def test_userpass_admin_without_token(account):
    assert has_permission(account("root"), "del_rse", {}).allowed


def test_root_with_token_is_not_userpass(account, request_ctx):
    with request_ctx({"sub": "x", "entitlements": []}):
        assert not has_permission(account("root"), "del_rse", {}).allowed


def test_entitlement_from_token(account, request_ctx):
    with request_ctx({"sub": "x", "entitlements": [REPORTER]}):
        assert has_permission(account("usage-reporter"), "list_requests_history", {}).allowed


def test_entitlement_from_eduperson_entitlement(account, request_ctx):
    with request_ctx({"sub": "x", "eduperson_entitlement": REPORTER}):
        assert has_permission(account("usage-reporter"), "list_requests_history", {}).allowed


def test_no_entitlement_denied(account, request_ctx):
    with request_ctx({"sub": "x", "entitlements": []}):
        res = has_permission(account("usage-reporter"), "list_requests_history", {})
    assert not res.allowed
    assert "Access denied" in res.message


def test_kwargs_reach_opa_as_json(account, request_ctx):
    dids = [{"scope": account("user.jdoe"), "type": DIDType.FILE}]
    with request_ctx({"sub": "x", "entitlements": [USER]}):
        assert has_permission(account("jdoe"), "attach_dids", {"dids": dids}).allowed


def test_undefined_policy_path_denies(account, monkeypatch):
    monkeypatch.setenv("OPA_POLICY_PATH", "no/such/rule")
    assert not has_permission(account("root"), "del_rse", {}).allowed
