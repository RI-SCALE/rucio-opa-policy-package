import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rucio_opa_v1_policy.opa_client import query_opa


@pytest.fixture
def opa(monkeypatch):
    """Minimal OPA stand-in: records requests, answers with a configurable body."""
    state = {"body": {"result": True}, "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            state["requests"].append((self.path, json.loads(self.rfile.read(length))))
            raw = json.dumps(state["body"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("OPA_URL", f"http://127.0.0.1:{server.server_port}/")
    monkeypatch.setenv("OPA_POLICY_PATH", "vo/authz/v1/allow")
    yield state
    server.shutdown()


def test_posts_input_to_policy_path(opa):
    assert query_opa({"action": "add_rule"}) is True
    assert opa["requests"] == [("/v1/data/vo/authz/v1/allow", {"input": {"action": "add_rule"}})]


@pytest.mark.parametrize("body", [{"result": False}, {}])
def test_false_or_undefined_denies(opa, body):
    opa["body"] = body
    assert query_opa({}) is False


def test_unreachable_fails_closed(monkeypatch):
    monkeypatch.setenv("OPA_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("OPA_TIMEOUT", "0.5")
    assert query_opa({}) is False
