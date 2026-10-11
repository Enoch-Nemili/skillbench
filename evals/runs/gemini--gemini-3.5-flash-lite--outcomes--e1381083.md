### gemini · gemini-3.5-flash-lite · outcomes · 3 trial(s) · e1381083

Overall: tasks fully passed 12% without the skill → 62% with it; mean check score 53% → 88%.

| Skill | Task | Passed without | Passed with | Checks without | Checks with |
|---|---|---:|---:|---:|---:|
| `mcp-server-hardening` | mcp-review-container | 67% (3) | 33% (3) | 93% | 87% |
| `mcp-server-hardening` | mcp-review-server | 0% (3) | 100% (3) | 71% | 100% |
| `release-polish` | release-publish-checklist | 0% (3) | 100% (3) | 28% | 100% |
| `release-polish` | release-semver | 33% (3) | 67% (3) | 75% | 92% |
| `repro-before-fix` | repro-cart-discount | 0% (3) | 100% (3) | 40% | 100% |
| `repro-before-fix` | repro-pagination | 0% (3) | 100% (3) | 40% | 100% |
| `retrieval-eval` | retrieval-build-eval | 0% (3) | 0% (3) | 20% | 53% |
| `retrieval-eval` | retrieval-compare-runs | 0% (3) | 0% (3) | 53% | 73% |

<details><summary>Failed checks</summary>

- mcp-review-container (without): secret_in_image ×1
- mcp-review-container (with): copies_everything ×2
- mcp-review-server (without): dns_rebinding ×3, token_passthrough ×3
- release-publish-checklist (without): ci_gate ×2, env_secret_rotated ×3, history_cleaned ×2, license_added ×3, readme_quickstart ×3
- release-semver (without): dated_heading ×2, major_version ×1
- release-semver (with): dated_heading ×1
- repro-cart-discount (without): test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- repro-pagination (without): test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- retrieval-build-eval (without): exact_and_plain ×3, held_out_set ×3, query_file ×3, rule_fixed_in_advance ×3
- retrieval-build-eval (with): exact_and_plain ×2, held_out_set ×3, query_file ×2
- retrieval-compare-runs (without): flags_small_sample ×1, mrr_correct ×3, recall5_correct ×3
- retrieval-compare-runs (with): flags_small_sample ×1, mrr_correct ×2, recall5_correct ×1

</details>
