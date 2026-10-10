### keyword · overlap · 1 trial(s) · catalog 84aa81bb

52 answers · accuracy 73% · recall 70% · false triggers 17% · parse errors 0

| Skill | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-server-hardening` | 100% | 60% | 75% | 6 | 0 | 4 |
| `release-polish` | 83% | 100% | 91% | 10 | 2 | 0 |
| `repro-before-fix` | 100% | 50% | 67% | 5 | 0 | 5 |
| `retrieval-eval` | 88% | 70% | 78% | 7 | 1 | 3 |

| Case kind | Answers | Accuracy |
|---|---:|---:|
| contextual | 13 | 62% |
| explicit | 8 | 100% |
| implicit | 19 | 63% |
| near-miss | 6 | 67% |
| unrelated | 6 | 100% |

<details><summary>Mistakes</summary>

| Case | Expected | Chosen | Prompt |
|---|---|---|---|
| retrieval-eval-05 | retrieval-eval | docx-editor | Our vector search keeps returning the wrong policy document for HR questions. I need a way to measure how often it gets the right one. |
| retrieval-eval-06 | retrieval-eval | release-polish | Help me write a set of test questions with known answers for our internal docs search. |
| retrieval-eval-09 | retrieval-eval | mcp-builder | Before we switch the knowledge base to the new embedding model, I want numbers showing search quality didn't regress. |
| mcp-server-hardening-05 | mcp-server-hardening | mcp-builder | Should my MCP server just forward the user's GitHub OAuth token to the GitHub API? |
| mcp-server-hardening-06 | mcp-server-hardening | mcp-builder | Someone said local MCP servers are vulnerable to DNS rebinding. How do I check mine? |
| mcp-server-hardening-08 | mcp-server-hardening | mcp-builder | We're about to let teammates connect to our internal MCP server over the office network. What needs to be locked down first? |
| mcp-server-hardening-10 | mcp-server-hardening | mcp-builder | When a tool fails, my MCP server sends the full Python traceback back to the client. Is that a problem? |
| repro-before-fix-03 | repro-before-fix | none | Getting KeyError: 'user_id' in production but I can't make it happen locally. |
| repro-before-fix-05 | repro-before-fix | none | The app crashes when I upload images bigger than about 20 MB. |
| repro-before-fix-07 | repro-before-fix | none | After upgrading pandas, our monthly report has NaNs in the revenue column. |
| repro-before-fix-08 | repro-before-fix | none | Users say that logging out sometimes doesn't clear their session. Here's the logout handler. |
| repro-before-fix-10 | repro-before-fix | none | Why does this endpoint return a 500 only on the first request after a deploy? |
| none-07 | none | retrieval-eval | What does MRR stand for in information retrieval? |
| none-11 | none | release-polish | What's a good name for my new open-source project? |

</details>
