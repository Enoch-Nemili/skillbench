#!/usr/bin/env python3
"""
Probe a running MCP server's Streamable HTTP endpoint from the outside. Standard library only.

    python probe_http.py http://127.0.0.1:8765/mcp
    MCP_TOKEN=... python probe_http.py http://127.0.0.1:8765/mcp
    python probe_http.py https://host/mcp --token-env PAPERMIND_TOKEN

The token is read from an environment variable, never from the command line, so it doesn't
end up in shell history. Each check prints PASS, FAIL, WARN or SKIP; exit code 1 if any FAIL.

Checks:
  auth-missing   request with no token          -> expect 401
  auth-wrong     request with a wrong token     -> expect 401
  auth-valid     request with the real token    -> expect 200 (needs the token)
  origin         request from a foreign Origin  -> expect 403 (MCP spec: servers MUST validate
                                                   Origin to stop DNS rebinding)
  www-auth       401 carries WWW-Authenticate   -> expected by the MCP authorization spec
  transport      plain http to a non-loopback host -> WARN: token travels in clear text
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
FOREIGN_ORIGIN = "https://attacker.example"
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "mcp-probe", "version": "0.1.0"},
    },
}


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN | SKIP
    detail: str


@dataclass
class Response:
    status: int
    headers: dict


def post(url: str, headers: dict, timeout: float) -> Response:
    """POST an initialize request; return only the status and headers (never the stream)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(INITIALIZE).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **headers,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return Response(resp.status, {k.lower(): v for k, v in resp.headers.items()})
    except urllib.error.HTTPError as err:
        return Response(err.code, {k.lower(): v for k, v in err.headers.items()})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def run_checks(url: str, token: str | None, timeout: float = 5.0) -> list[Check]:
    checks: list[Check] = []

    missing = post(url, {}, timeout)
    if missing.status == 401:
        checks.append(Check("auth-missing", "PASS", "no token -> 401"))
    elif 200 <= missing.status < 300:
        checks.append(
            Check("auth-missing", "FAIL", f"no token -> {missing.status}: anyone can call it")
        )
    else:
        checks.append(Check("auth-missing", "WARN", f"no token -> {missing.status} (expected 401)"))

    if missing.status == 401:
        if "www-authenticate" in missing.headers:
            checks.append(Check("www-auth", "PASS", "401 includes WWW-Authenticate"))
        else:
            checks.append(
                Check(
                    "www-auth",
                    "WARN",
                    "401 lacks WWW-Authenticate; OAuth clients can't discover how to log in",
                )
            )

    wrong = post(url, bearer("not-the-real-token-" + "x" * 24), timeout)
    if wrong.status == 401:
        checks.append(Check("auth-wrong", "PASS", "wrong token -> 401"))
    elif 200 <= wrong.status < 300:
        checks.append(
            Check("auth-wrong", "FAIL", f"wrong token -> {wrong.status}: token not checked")
        )
    else:
        checks.append(Check("auth-wrong", "WARN", f"wrong token -> {wrong.status} (expected 401)"))

    auth = bearer(token) if token else {}
    if token:
        valid = post(url, auth, timeout)
        if 200 <= valid.status < 300:
            checks.append(Check("auth-valid", "PASS", f"real token -> {valid.status}"))
        else:
            checks.append(
                Check("auth-valid", "FAIL", f"real token -> {valid.status}; check the token")
            )
    else:
        checks.append(Check("auth-valid", "SKIP", "no token in the environment"))

    origin = post(url, {**auth, "Origin": FOREIGN_ORIGIN}, timeout)
    if origin.status == 403:
        checks.append(Check("origin", "PASS", f"Origin {FOREIGN_ORIGIN} -> 403"))
    elif 200 <= origin.status < 300:
        checks.append(
            Check(
                "origin",
                "FAIL",
                f"Origin {FOREIGN_ORIGIN} -> {origin.status}: a web page could reach this server "
                "through DNS rebinding",
            )
        )
    elif origin.status == 401 and not token:
        checks.append(
            Check("origin", "SKIP", "rejected by auth first; set the token to test Origin")
        )
    else:
        checks.append(
            Check("origin", "WARN", f"Origin {FOREIGN_ORIGIN} -> {origin.status} (expected 403)")
        )

    parsed = urlparse(url)
    if parsed.scheme == "http" and parsed.hostname not in LOOPBACK:
        checks.append(
            Check(
                "transport", "WARN", f"plain http to {parsed.hostname}: use https off this machine"
            )
        )
    else:
        checks.append(Check("transport", "PASS", f"{parsed.scheme} to {parsed.hostname}"))

    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe an MCP server's HTTP auth and Origin checks."
    )
    parser.add_argument("url", help="the MCP endpoint, e.g. http://127.0.0.1:8765/mcp")
    parser.add_argument("--token-env", default="MCP_TOKEN", help="env var holding the bearer token")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        checks = run_checks(args.url, os.environ.get(args.token_env), args.timeout)
    except (urllib.error.URLError, OSError) as exc:
        print(f"error: can't reach {args.url}: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([c.__dict__ for c in checks], indent=2))
    else:
        for c in checks:
            print(f"{c.status:<4}  {c.name:<12}  {c.detail}")
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
