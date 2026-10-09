# MCP server hardening checklist

Severity: **critical** = exploitable remotely or leaks data; **high** = exploitable with some
access or by a malicious document; **medium** = defense in depth.

Spec references are to the MCP specification, version 2025-11-25:
[Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) and
[Security best practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices).

## Transport and network

| # | Check | Severity | Spec |
|---|---|---|---|
| T1 | HTTP mode binds to `127.0.0.1` unless explicitly configured otherwise | critical | Transports: servers SHOULD bind only to localhost when running locally |
| T2 | Server refuses to start on a non-loopback address without auth configured | critical | |
| T3 | `Origin` header validated on every request; invalid origin gets 403 | critical | Transports: MUST validate Origin; MUST respond 403 if present and invalid |
| T4 | https for any non-loopback deployment (TLS at the server or a reverse proxy) | high | |
| T5 | stdio servers write logs to stderr only | medium | Transports: server MUST NOT write non-MCP output to stdout |
| T6 | Session IDs, if used, are random and never used for authentication | high | Security: MUST NOT use sessions for authentication |

## Authentication and authorization

| # | Check | Severity | Spec |
|---|---|---|---|
| A1 | Every HTTP request requires a credential; missing or wrong token gets 401 | critical | Transports: SHOULD implement proper authentication |
| A2 | Static tokens are long and random (≥ 32 chars) and compared in constant time | high | |
| A3 | OAuth tokens are checked for audience: issued for *this* server | critical | Security: MUST NOT accept tokens not issued for the MCP server |
| A4 | Client tokens are never forwarded to downstream APIs | critical | Security: token passthrough is forbidden |
| A5 | Scopes are minimal; write tools need a separate scope from read tools | medium | Security: scope minimization |
| A6 | 401 responses include `WWW-Authenticate` (needed for OAuth discovery) | medium | Authorization spec |

## Tools

| # | Check | Severity |
|---|---|---|
| I1 | Every argument is typed and bounded (ranges, max lengths, enums) | high |
| I2 | File paths resolved and checked to stay inside one allowed folder (blocks `../` and symlinks) | critical |
| I3 | Uploaded/added files checked for size and real signature, not just extension | medium |
| I4 | URL fetching restricted to an allowlist; private, loopback and link-local IPs blocked; redirects re-checked | critical |
| I5 | No shell commands built from arguments; subprocess gets an argument list | critical |
| I6 | Database access uses parameterized queries | critical |
| I7 | Result size capped so one call can't flood the client's context | medium |
| I8 | Tool annotations match behaviour (read-only, destructive, idempotent, open-world) | medium |
| I9 | Destructive tools require an explicit confirmation argument or are left out | high |

## Errors, secrets and logging

| # | Check | Severity |
|---|---|---|
| E1 | Expected failures return tool errors with a helpful message, not stack traces | medium |
| E2 | Errors and logs never contain tokens, passwords or connection strings | high |
| E3 | Partial writes are rolled back on failure | medium |
| E4 | Secrets come from environment variables or a secret store; `.env` is git-ignored | critical |
| E5 | Tool calls are logged with arguments (minus secrets) for auditing | medium |

## Content from tools

| # | Check | Severity |
|---|---|---|
| P1 | Text from documents, web pages or emails is returned as labelled data with its source | high |
| P2 | Tool descriptions are static and contain no user-controlled text | high |
| P3 | Changing the tool list at runtime (`tools/list_changed`) is avoided or justified | medium |

## Container and supply chain

| # | Check | Severity |
|---|---|---|
| C1 | Runs as a non-root user | high |
| C2 | Base image pinned; dependencies pinned with a lock or requirements file | medium |
| C3 | Image contains no secrets, `.env`, or `.git` (`.dockerignore`) | critical |
| C4 | CI proves the critical checks: no-token start is refused, no-token request gets 401 | high |
| C5 | Dependabot or similar keeps dependencies and actions updated | medium |

## Example fixes (MCP Python SDK)

Constant-time static token check:

```python
import hmac


class StaticTokenVerifier:
    def __init__(self, token: str):
        if len(token) < 32:
            raise ValueError("token must be at least 32 characters")
        self._token = token.encode()

    async def verify_token(self, token: str):
        if hmac.compare_digest(token.encode(), self._token):
            return AccessToken(token=token, client_id="local", scopes=["app"])
        return None
```

Refuse an open server on the network:

```python
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
if host not in LOOPBACK and not os.getenv("APP_TOKEN"):
    sys.exit(f"Refusing to listen on {host} without APP_TOKEN set.")
```

Keep file access inside one folder:

```python
def file_inside(folder: Path, filename: str) -> Path:
    path = (folder / filename).resolve()
    if path.parent != folder.resolve():
        raise ToolError(f"Only files directly inside {folder.name}/ are allowed.")
    return path
```
