import io
import json
import time

from rucio_opa_v1_policy import permission
from rucio_opa_v1_policy.permission import _as_list, _token_claims

ISS = "https://idp.example.org/realms/x"
UI = "https://idp.example.org/userinfo"


class FakeUrlopen:
    """Serves discovery and userinfo; records calls."""

    def __init__(self, userinfo, fail=False):
        self.userinfo = userinfo
        self.fail = fail
        self.calls = []

    def __call__(self, req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        self.calls.append(url)
        if self.fail:
            raise OSError("down")
        if url.endswith("/.well-known/openid-configuration"):
            return io.BytesIO(json.dumps({"userinfo_endpoint": UI}).encode())
        return io.BytesIO(json.dumps(self.userinfo).encode())


def test_no_request_context_gives_no_claims():
    assert _token_claims() == {"entitlements": []}


def test_entitlements_claim_and_scalars(request_ctx):
    claims = {"entitlements": ["urn:a"], "sub": "s", "iss": ISS, "acr": "mfa", "aud": "rucio"}
    with request_ctx(claims):
        assert _token_claims() == {
            "entitlements": ["urn:a"],
            "sub": "s",
            "iss": ISS,
            "acr": "mfa",
            "aud": "rucio",
        }


def test_eduperson_entitlement_fallback(request_ctx, monkeypatch):
    fake = FakeUrlopen({"entitlements": ["urn:never"]})
    monkeypatch.setattr(permission, "urlopen", fake)
    with request_ctx({"eduperson_entitlement": "urn:a urn:b", "iss": ISS}):
        assert _token_claims()["entitlements"] == ["urn:a", "urn:b"]
    assert fake.calls == []  # userinfo not needed


def test_userinfo_prefers_entitlements(request_ctx, monkeypatch):
    fake = FakeUrlopen({"entitlements": ["urn:new"], "eduperson_entitlement": ["urn:old"]})
    monkeypatch.setattr(permission, "urlopen", fake)
    with request_ctx({"iss": ISS, "exp": time.time() + 60}):
        assert _token_claims()["entitlements"] == ["urn:new"]


def test_userinfo_eduperson_entitlement(request_ctx, monkeypatch):
    monkeypatch.setattr(permission, "urlopen", FakeUrlopen({"eduperson_entitlement": ["urn:old"]}))
    with request_ctx({"iss": ISS, "exp": time.time() + 60}):
        assert _token_claims()["entitlements"] == ["urn:old"]


def test_userinfo_cached_per_token(request_ctx, monkeypatch):
    fake = FakeUrlopen({"entitlements": ["urn:a"]})
    monkeypatch.setattr(permission, "urlopen", fake)
    claims = {"iss": ISS, "exp": time.time() + 60}
    for _ in range(3):
        with request_ctx(claims):
            _token_claims()
    assert fake.calls.count(UI) == 1


def test_userinfo_failure_fails_closed(request_ctx, monkeypatch):
    monkeypatch.setattr(permission, "urlopen", FakeUrlopen({}, fail=True))
    with request_ctx({"iss": ISS}):
        assert _token_claims()["entitlements"] == []


def test_no_bearer_token_skips_userinfo(request_ctx, monkeypatch):
    fake = FakeUrlopen({"entitlements": ["urn:a"]})
    monkeypatch.setattr(permission, "urlopen", fake)
    with request_ctx({"iss": ISS}, token=None):
        assert _token_claims()["entitlements"] == []
    assert fake.calls == []


def test_as_list():
    assert _as_list(None) == []
    assert _as_list("a b") == ["a", "b"]
    assert _as_list(("a",)) == ["a"]
