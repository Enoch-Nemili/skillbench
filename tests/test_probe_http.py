"""Tests for the probe bundled with the mcp-server-hardening skill, against fake servers."""

import importlib.util
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/mcp-server-hardening/scripts/probe_http.py"
spec = importlib.util.spec_from_file_location("probe_http", SCRIPT)
probe = importlib.util.module_from_spec(spec)
sys.modules["probe_http"] = probe  # dataclasses look the module up by name
spec.loader.exec_module(probe)

TOKEN = "s" * 40


def make_handler(require_auth: bool, check_origin: bool, www_authenticate: bool):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (name required by BaseHTTPRequestHandler)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            origin = self.headers.get("Origin")
            if check_origin and origin and origin != "http://127.0.0.1":
                return self._reply(403)
            if require_auth and self.headers.get("Authorization") != f"Bearer {TOKEN}":
                extra = {"WWW-Authenticate": 'Bearer realm="mcp"'} if www_authenticate else {}
                return self._reply(401, extra)
            return self._reply(200)

        def _reply(self, status, headers=None):
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    return Handler


@contextmanager
def server(**behaviour):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(**behaviour))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/mcp"
    finally:
        httpd.shutdown()
        httpd.server_close()


def statuses(checks):
    return {c.name: c.status for c in checks}


def test_hardened_server_passes():
    with server(require_auth=True, check_origin=True, www_authenticate=True) as url:
        result = statuses(probe.run_checks(url, TOKEN))
    assert result == {
        "auth-missing": "PASS",
        "www-auth": "PASS",
        "auth-wrong": "PASS",
        "auth-valid": "PASS",
        "origin": "PASS",
        "transport": "PASS",
    }


def test_open_server_fails_auth_and_origin():
    with server(require_auth=False, check_origin=False, www_authenticate=False) as url:
        result = statuses(probe.run_checks(url, None))
    assert result["auth-missing"] == "FAIL"
    assert result["auth-wrong"] == "FAIL"
    assert result["origin"] == "FAIL"
    assert result["auth-valid"] == "SKIP"


def test_auth_without_origin_check_is_caught_with_token():
    with server(require_auth=True, check_origin=False, www_authenticate=True) as url:
        result = statuses(probe.run_checks(url, TOKEN))
    assert result["auth-missing"] == "PASS"
    assert result["origin"] == "FAIL"


def test_origin_is_skipped_without_token():
    with server(require_auth=True, check_origin=False, www_authenticate=False) as url:
        result = statuses(probe.run_checks(url, None))
    assert result["origin"] == "SKIP"
    assert result["www-auth"] == "WARN"


def test_wrong_real_token_fails():
    with server(require_auth=True, check_origin=True, www_authenticate=True) as url:
        result = statuses(probe.run_checks(url, "t" * 40))
    assert result["auth-valid"] == "FAIL"


def test_plain_http_to_remote_host_warns(monkeypatch):
    monkeypatch.setattr(probe, "post", lambda *a, **k: probe.Response(401, {}))
    result = statuses(probe.run_checks("http://example.com/mcp", None))
    assert result["transport"] == "WARN"


def test_main_exit_codes(monkeypatch, capsys):
    with server(require_auth=False, check_origin=False, www_authenticate=False) as url:
        assert probe.main([url]) == 1
    with server(require_auth=True, check_origin=True, www_authenticate=True) as url:
        monkeypatch.setenv("MCP_TOKEN", TOKEN)
        assert probe.main([url]) == 0
    assert probe.main(["http://127.0.0.1:9/mcp", "--timeout", "1"]) == 2
