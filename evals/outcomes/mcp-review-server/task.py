"""A server with 7 planted problems. Graded on which problems the review names."""

from skillbench.grading import check_mentions

SKILL = "mcp-server-hardening"

SERVER = '''\
import os
import subprocess
import traceback
import urllib.request

from mcp.server.fastmcp import FastMCP

from db import run_query

mcp = FastMCP("team-tools")
DOCS = "/srv/docs"
DB_URL = os.environ["DATABASE_URL"]


@mcp.tool()
def read_doc(path: str) -> str:
    """Read a document from the shared docs folder."""
    with open(os.path.join(DOCS, path)) as f:
        return f.read()


@mcp.tool()
def fetch(url: str) -> str:
    """Fetch a web page so the assistant can read it."""
    return urllib.request.urlopen(url).read().decode()


@mcp.tool()
def grep_logs(pattern: str) -> str:
    """Search today's application log."""
    cmd = f"grep '{pattern}' /var/log/app.log"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


@mcp.tool()
def list_repos(user_token: str) -> str:
    """List the user's GitHub repos with the token their client sends us."""
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    return urllib.request.urlopen(req).read().decode()


@mcp.tool()
def report(name: str) -> str:
    """Run one of the saved reports."""
    try:
        return run_query(DB_URL, name)
    except Exception:
        return traceback.format_exc() + f"\\n(database: {DB_URL})"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
'''

PROMPT = f"""
We're about to deploy this MCP server so everyone on the team can connect to it over the office
network. Can you review it before we do?

```python
# file: server.py
{SERVER}```
"""

FINDINGS = {
    "no_auth_on_network": (
        r"(no|missing|without|lacks?|zero)\b[^.\n]{0,50}\b(auth|authentication|token|credential)"
        r"|unauthenticated|anyone[^.\n]{0,40}(network|can (call|reach|connect|use))"
    ),
    "path_traversal": r"path traversal|directory traversal|\.\./|outside (the )?(docs|base|allowed)",
    "ssrf": (
        r"\bssrf\b|server[- ]side request forgery|169\.254|metadata (endpoint|service)"
        r"|internal (urls?|network|services?|addresses|hosts)|private (ip|address|network)"
    ),
    "shell_injection": (
        r"shell\s*=\s*true|(command|shell) injection|inject[^.\n]{0,40}(command|shell)"
        r"|arbitrary (shell )?commands?"
    ),
    "error_leak": (
        r"traceback|stack ?trace|(leak|expos|reveal)\w*[^.\n]{0,60}"
        r"(database|db_url|connection string|credential|password|internals)"
    ),
    "token_passthrough": (
        r"pass-?through|forward\w*[^.\n]{0,40}token|token[^.\n]{0,60}(audience|issued (for|to))"
        r"|confused deputy"
    ),
    "dns_rebinding": r"dns[- ]rebinding|origin header|validat\w* (the )?origin",
}


def grade(output: str):
    return [check_mentions(name, output, pattern) for name, pattern in FINDINGS.items()]
