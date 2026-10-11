### gemini · gemini-3.5-flash-lite · triggers · 3 trial(s) · catalog 967862e6

156 answers · accuracy 99% · recall 100% · false triggers 3% · parse errors 0 · consistency 98% · median 0.7 s/answer

| Skill | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-server-hardening` | 100% | 100% | 100% | 30 | 0 | 0 |
| `release-polish` | 100% | 100% | 100% | 30 | 0 | 0 |
| `repro-before-fix` | 97% | 100% | 98% | 30 | 1 | 0 |
| `retrieval-eval` | 100% | 100% | 100% | 30 | 0 | 0 |

| Case kind | Answers | Accuracy |
|---|---:|---:|
| contextual | 39 | 100% |
| explicit | 24 | 100% |
| implicit | 57 | 100% |
| near-miss | 18 | 94% |
| unrelated | 18 | 100% |

<details><summary>Mistakes</summary>

| Case | Expected | Chosen | Prompt |
|---|---|---|---|
| none-09 | none | repro-before-fix | Write unit tests for the new pagination helper. |

</details>
