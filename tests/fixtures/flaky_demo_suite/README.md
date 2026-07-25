# flaky_demo_suite

Ground-truth fixture for flake-hunter. Not part of this project's own
passing test suite -- `pytest.ini_options.testpaths` excludes
`tests/fixtures/`, so it's never collected by `pytest` at the repo root.
It exists to be run *by* flake-hunter (`suite_path` in `flake_hunter.toml`
points here), so every module has a known-correct answer to check against.

Empirically verified over 40 runs each (`pytest -v --tb=no`, repeated):

| Test | Expected | Mechanism |
| --- | --- | --- |
| `test_flaky_random_coin_flip` | flaky (~50%) | asserts directly on `random.random()` |
| `test_flaky_shared_temp_race` | flaky (~50%) | real thread race on a fixed shared temp file |
| `test_flaky_timing_deadline` | flaky (~50%) | worker sometimes misses a tight wall-clock deadline |
| `test_always_passes` | never flaky (0% fail) | stable control |
| `test_always_fails` | never flaky (100% fail) | stable control |

`aggregate()` must flag exactly the three flaky tests and neither control.
