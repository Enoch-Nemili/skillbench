"""A container setup with 5 planted problems. Graded on which problems the review names."""

from skillbench.grading import check_mentions

SKILL = "mcp-server-hardening"

DOCKERFILE = """\
FROM python:latest
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV OPENAI_API_KEY=example-not-a-real-key
EXPOSE 8000
CMD ["python", "server.py", "--http", "--host", "0.0.0.0", "--port", "8000"]
"""

COMPOSE = """\
services:
  mcp:
    build: .
    ports:
      - "8000:8000"
"""

PROMPT = f"""
This is how we containerize our MCP server before rolling it out to the team. The server itself
has no login yet. Anything we should change?

```dockerfile
# file: Dockerfile
{DOCKERFILE}```

```yaml
# file: docker-compose.yml
{COMPOSE}```
"""

FINDINGS = {
    "runs_as_root": r"as root|root (user|privileges)|non-?root|\bUSER\s+\w|unprivileged",
    "secret_in_image": (
        r"(secret|key|token|credential)s?[^.\n]{0,80}(image|layer|baked|build time|ENV\b|docker history)"
        r"|(ENV\b|image|layer)[^.\n]{0,80}(secret|api key|token|credential)"
    ),
    "copies_everything": r"\.dockerignore|COPY \. \.|cop(y|ies) (the )?(whole|entire|everything)",
    "exposed_without_auth": (
        r"127\.0\.0\.1|localhost|(no|missing|without|lacks?)\b[^.\n]{0,50}\b(auth|authentication|token)"
        r"|unauthenticated|all (network )?interfaces"
    ),
    "unpinned_base": r":latest|\blatest\b[^.\n]{0,40}(tag|image)|pin\w*[^.\n]{0,40}(version|base|image|digest)",
}


def grade(output: str):
    return [check_mentions(name, output, pattern) for name, pattern in FINDINGS.items()]
