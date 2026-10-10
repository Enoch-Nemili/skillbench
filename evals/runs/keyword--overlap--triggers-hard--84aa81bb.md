### keyword · overlap · triggers-hard · 1 trial(s) · catalog 84aa81bb

38 answers · accuracy 37% · recall 28% · false triggers 46% · parse errors 0

| Skill | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-server-hardening` | 75% | 43% | 55% | 3 | 1 | 4 |
| `release-polish` | 80% | 57% | 67% | 4 | 1 | 3 |
| `repro-before-fix` | 40% | 22% | 29% | 2 | 3 | 7 |
| `retrieval-eval` | 60% | 43% | 50% | 3 | 2 | 4 |

| Case kind | Answers | Accuracy |
|---|---:|---:|
| concept | 6 | 50% |
| confusable | 6 | 33% |
| long | 4 | 50% |
| multi | 5 | 0% |
| neighbour | 7 | 57% |
| non-english | 4 | 0% |
| terse | 6 | 50% |

<details><summary>Mistakes</summary>

| Case | Expected | Chosen | Prompt |
|---|---|---|---|
| hard-multi-01 | mcp-server-hardening, release-polish | release-polish | Harden our MCP server before we tag v1.0 and publish release notes. |
| hard-multi-02 | release-polish, repro-before-fix | release-polish | CI started failing right before the release. Find out why, then cut v2.1.0. |
| hard-multi-03 | repro-before-fix, retrieval-eval | retrieval-eval | After the reranker change our eval script crashes with IndexError on half the queries. Fix the crash, then tell me whether the reranker actually helped. |
| hard-multi-04 | mcp-server-hardening, retrieval-eval | mcp-server-hardening | Security-review the search tool our MCP server exposes, and measure whether its new hybrid ranking beats plain vector search. |
| hard-multi-05 | mcp-server-hardening, release-polish | release-polish | Clean up this repo so we can open-source it, and make sure the MCP server inside it isn't exposing anything it shouldn't. |
| hard-confusable-02 | repro-before-fix | mcp-builder | Our MCP server crashes with a KeyError whenever a tool gets an empty argument. |
| hard-confusable-03 | retrieval-eval | release-polish | We're about to release, but I'm not sure our search is as good as the README claims. Can you check the numbers before we publish them? |
| hard-confusable-04 | repro-before-fix | mcp-builder | The MCP server works on my machine but refuses connections inside Docker. |
| hard-confusable-05 | release-polish | repro-before-fix | Add a CHANGELOG entry for the bug fix I just merged. |
| hard-neighbour-02 | none | mcp-server-hardening | Add a list_tickets tool to my MCP server. |
| hard-neighbour-03 | none | retrieval-eval | Make a line chart of recall@k for k from 1 to 10 using this CSV. |
| hard-neighbour-07 | none | repro-before-fix | Summarize this bug report PDF in five bullet points. |
| hard-concept-02 | none | retrieval-eval | What's the difference between hit@1 and recall@5? |
| hard-concept-04 | none | release-polish | What does semantic versioning mean by a major version? |
| hard-concept-06 | none | repro-before-fix | Explain what git bisect does. |
| hard-terse-02 | mcp-server-hardening | mcp-builder | safe to expose? it's the FastMCP server from earlier |
| hard-terse-05 | repro-before-fix | none | 500s since this morning, logs attached |
| hard-terse-06 | retrieval-eval | none | numbers please: is the new chunker better or not |
| hard-non-english-01 | mcp-server-hardening | none | Mi servidor MCP acepta conexiones desde cualquier IP. ¿Cómo lo aseguro? |
| hard-non-english-02 | repro-before-fix | none | हमारा एक टेस्ट कभी पास होता है, कभी फेल। इसकी असली वजह कैसे पता करें? |
| hard-non-english-03 | release-polish | none | Quiero publicar mi proyecto en GitHub como código abierto. ¿Qué me falta? |
| hard-non-english-04 | retrieval-eval | docx-editor | Comment savoir si mon moteur de recherche RAG trouve les bons documents ? |
| hard-long-03 | repro-before-fix | none | Every few days our nightly import job dies with 'connection reset by peer' around 3am, and by the time anyone looks it works again. It's been going on for a month. We've added retries twice and it still happens. I want to actually understand it this time. |
| hard-long-04 | release-polish | none | We built a small CLI for converting lab instrument files to CSV. Three other labs want to use it next month. Right now it's a folder on my laptop with a script, some test data and a notes.txt. What needs to happen before we hand it over? |

</details>
