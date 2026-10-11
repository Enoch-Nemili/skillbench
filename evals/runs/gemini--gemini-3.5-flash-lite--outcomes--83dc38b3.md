### gemini · gemini-3.5-flash-lite · outcomes · 3 trial(s) · 83dc38b3

Overall: tasks fully passed 0% without the skill → 25% with it; mean check score 27% → 51%.

| Skill | Task | Passed without | Passed with | Checks without | Checks with |
|---|---|---:|---:|---:|---:|
| `mcp-server-hardening` | mcp-review-container | 0% (3) | 67% (3) | 60% | 87% |
| `mcp-server-hardening` | mcp-review-server | 0% (3) | 100% (3) | 71% | 100% |
| `release-polish` | release-publish-checklist | 0% (3) | 33% (3) | 22% | 83% |
| `release-polish` | release-semver | 0% (3) | 0% (3) | 25% | 67% |
| `repro-before-fix` | repro-cart-discount | 0% (3) | 0% (3) | 0% | 0% |
| `repro-before-fix` | repro-pagination | 0% (3) | 0% (3) | 13% | 0% |
| `retrieval-eval` | retrieval-build-eval | 0% (3) | 0% (3) | 0% | 0% |
| `retrieval-eval` | retrieval-compare-runs | 0% (3) | 0% (3) | 27% | 73% |

<details><summary>Failed checks</summary>

- mcp-review-container (without): copies_everything ×1, secret_in_image ×2, unpinned_base ×3
- mcp-review-container (with): secret_in_image ×1, unpinned_base ×1
- mcp-review-server (without): dns_rebinding ×3, token_passthrough ×3
- release-publish-checklist (without): ci_gate ×2, env_secret_rotated ×3, history_cleaned ×3, license_added ×3, readme_quickstart ×3
- release-publish-checklist (with): env_secret_rotated ×1, history_cleaned ×2
- release-semver (without): breaking_called_out ×2, changelog_sections ×3, dated_heading ×2, major_version ×2
- release-semver (with): changelog_sections ×3, dated_heading ×1
- repro-cart-discount (without): fix_passes_hidden_tests ×3, fix_provided ×3, test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- repro-cart-discount (with): fix_passes_hidden_tests ×3, fix_provided ×3, test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- repro-pagination (without): fix_passes_hidden_tests ×2, fix_provided ×2, test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- repro-pagination (with): fix_passes_hidden_tests ×3, fix_provided ×3, test_fails_on_bug ×3, test_passes_on_fix ×3, test_written ×3
- retrieval-build-eval (without): exact_and_plain ×3, held_out_set ×3, metrics_named ×3, query_file ×3, rule_fixed_in_advance ×3
- retrieval-build-eval (with): exact_and_plain ×3, held_out_set ×3, metrics_named ×3, query_file ×3, rule_fixed_in_advance ×3
- retrieval-compare-runs (without): flags_small_sample ×3, keeps_baseline ×3, mrr_correct ×3, recall5_correct ×2
- retrieval-compare-runs (with): mrr_correct ×2, recall5_correct ×2

</details>
