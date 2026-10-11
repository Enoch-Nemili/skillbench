### gemini · gemini-3.5-flash-lite · triggers-hard · 3 trial(s) · catalog 967862e6

114 answers · accuracy 96% · recall 93% · false triggers 0% · parse errors 0 · consistency 92% · median 0.61 s/answer

| Skill | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-server-hardening` | 100% | 100% | 100% | 21 | 0 | 0 |
| `release-polish` | 100% | 100% | 100% | 21 | 0 | 0 |
| `repro-before-fix` | 100% | 85% | 92% | 23 | 0 | 4 |
| `retrieval-eval` | 100% | 95% | 98% | 20 | 0 | 1 |

| Case kind | Answers | Accuracy |
|---|---:|---:|
| concept | 18 | 100% |
| confusable | 18 | 78% |
| long | 12 | 100% |
| multi | 15 | 100% |
| neighbour | 21 | 100% |
| non-english | 12 | 100% |
| terse | 18 | 94% |

<details><summary>Mistakes</summary>

| Case | Expected | Chosen | Prompt |
|---|---|---|---|
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-confusable-01 | repro-before-fix | retrieval-eval | Recall@5 dropped from 0.94 to 0.61 overnight and nobody touched the retrieval config. Find what broke. |
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-confusable-04 | repro-before-fix | mcp-server-hardening | The MCP server works on my machine but refuses connections inside Docker. |
| hard-terse-04 | retrieval-eval | none | top-1 accuracy of our doc search: how do I even measure that |

</details>
