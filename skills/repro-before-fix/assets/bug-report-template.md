## Bug: <one-line summary>

**Symptom:** <exact error text or wrong output>
**Expected:** <one sentence>
**Actual:** <one sentence>
**Where:** <version or commit, OS, runtime versions, relevant config>

### Reproduce

```bash
<smallest command that fails, from a clean checkout>
```

Reliability: <e.g. `flaky.py --runs 20`: 0/20 passed, always fails>

### Root cause

<Why it happens, down to the decision in code or config. Include the prediction you
checked to confirm it.>

### Fix

<What changed and why that addresses the cause. Note anything left for a follow-up issue.>

### Evidence

- Regression test: `<path::test_name>`: fails before the fix, passes after
- Full suite: <n passed>
- <For flaky bugs: `flaky.py --runs 50` after the fix: 50/50 passed>

### How it was found

<Test, log, probe, user report, CI run.>
