# Security

## Reporting a vulnerability

Please report privately through GitHub: the repository's **Security** tab →
**Report a vulnerability**. Don't open a public issue. I aim to reply within a week.

## Know this before you run skillbench

- **Outcome grading runs model-written code.** For the debugging tasks, `skillbench outcomes`
  and `skillbench grade` write the answer's files to a temporary folder and run pytest on them,
  with a 60-second timeout. That is not a sandbox: the code runs with your user's permissions.
  Only grade answers from providers you trust, or run the harness inside a container.
- **API keys** are read from the environment or a git-ignored `.env` and are never written to
  run files. Run files hold answers and timings only.
- **`probe_http.py`** (in `mcp-server-hardening`) sends requests to the URL you give it,
  including one with a foreign `Origin` header. Only probe servers you own or are allowed to
  test.
- **`release_check.py`** (in `release-polish`) only reads the repository.
