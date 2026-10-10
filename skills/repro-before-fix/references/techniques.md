# Debugging techniques

Read this when a bug won't reproduce, reproduces only sometimes, or the cause isn't obvious.

## Shrinking a reproduction

Remove one thing at a time and rerun: an input row, a config key, a step, a dependency.
Keep the removal if it still fails; undo it if the failure disappears. Stop when every
remaining piece is necessary. The result usually points straight at the cause.

## Finding the commit that broke it: git bisect

When an older version worked:

```bash
git bisect start
git bisect bad                 # the current commit is broken
git bisect good v1.0.0         # this tag (or commit) worked
git bisect run python -m pytest -q tests/test_x.py::test_case
git bisect reset               # go back to where you started
```

`git bisect run` tries commits in a binary search and reads the exit code: 0 = good,
1–127 = bad, 125 = skip (e.g. the commit doesn't build). Ten steps cover about 1,000
commits. The test must exist at every commit it checks, so keep it outside the repo
(or in an untracked file) while bisecting.

## Flaky failures

`scripts/flaky.py --runs 50 -- <command>` gives the pass rate and groups failures by
their last output line. Different signatures usually mean different causes.

| Cause | Tell-tale sign | How to confirm |
|---|---|---|
| Test order / shared state | Fails only in the full suite, passes alone | Shuffle test order (the `pytest-randomly` plugin), or run the failing test right after its neighbour |
| Randomness | Failure output changes run to run | Fix the seed; if it then always fails or always passes, that's it |
| Time | Fails near midnight, month end, DST, or in another time zone | Freeze the clock (`freezegun`, `time-machine`) at the failing moment |
| Concurrency / timing | Fails more under load or on CI | Add a sleep at the suspected race point; if the failure rate jumps, that's the race |
| External service | Timeouts, connection resets, 429/503 | Replace the service with a local fake; if flakiness stops, handle the failure mode explicitly |
| Resource leak | Fails after N runs, not at first | Run it 200 times and watch open files, connections and memory |

Don't "fix" flakiness with retries unless the operation really is retryable (e.g. a
network call with backoff) and the retry is in product code, not only in the test.

## "Works on my machine"

Diff the two environments, not the code:

- Language and dependency versions: `pip freeze`, lock files, `node --version`
- Environment variables and config files, including ones read implicitly
- Data: database contents, fixtures, files on disk, caches (a stale cache or build
  artifact can make one machine run old code)
- OS, CPU architecture (arm64 vs x86_64), file system case sensitivity, line endings
- Time zone and locale
- Network: proxies, DNS, firewalls, which hosts are reachable

Make one machine match the other one difference at a time until the behaviour flips.

## Confirming a root cause

A cause is confirmed when it makes a prediction that comes true:

- "If the pool reuses dead connections, restarting the database between two queries
  will fail the second one." Then do it.
- "If the SDK only enables Origin checks for loopback binds, the same server bound to
  127.0.0.1 will reject the foreign origin." Then do it.

If the prediction fails, the cause is wrong, even if the fix seemed to work.

## Checking the check

Before trusting a green result, confirm the tool did real work:

- Tests: the count collected is what you expect (not `0 passed` or `no tests ran`).
- Type checkers and linters: they ran on the files you changed, against the installed
  dependencies (a failed editable install can make a type checker pass on stale code).
- CI: the job ran the step, rather than skipping it on a condition.
- After the fix, revert it locally: the regression test must fail again.
