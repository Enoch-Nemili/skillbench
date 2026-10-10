### gemini · gemini-3.5-flash-lite · triggers-hard · 3 trial(s) · catalog 84aa81bb

114 answers · accuracy 93% · recall 96% · false triggers 13% · parse errors 0 · consistency 95% · median 0.61 s/answer

| Skill | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-server-hardening` | 100% | 100% | 100% | 21 | 0 | 0 |
| `release-polish` | 100% | 100% | 100% | 21 | 0 | 0 |
| `repro-before-fix` | 100% | 89% | 94% | 24 | 0 | 3 |
| `retrieval-eval` | 81% | 100% | 89% | 21 | 5 | 0 |

| Case kind | Answers | Accuracy |
|---|---:|---:|
| concept | 18 | 72% |
| confusable | 18 | 83% |
| long | 12 | 100% |
| multi | 15 | 100% |
| neighbour | 21 | 100% |
| non-english | 12 | 100% |
| terse | 18 | 100% |

<details><summary>Mistakes</summary>

| Case | Expected | Chosen | Prompt |
|---|---|---|---|
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-concept-02 | none | retrieval-eval | What's the difference between hit@1 and recall@5? |
| hard-concept-05 | none | retrieval-eval | Write a Python function that computes MRR from a list of ranks. |
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-concept-02 | none | retrieval-eval | What's the difference between hit@1 and recall@5? |
| hard-concept-05 | none | retrieval-eval | Write a Python function that computes MRR from a list of ranks. |
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-concept-02 | none | retrieval-eval | What's the difference between hit@1 and recall@5? |

</details>
