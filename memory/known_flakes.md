# Known Flakes

| Test ID | First Seen | Last Seen | Fail Rate | Pass Count | Fail Count | Suspected Cause | Status | Sample Failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tests/fixtures/flaky_demo_suite/test_flaky_demo.py::test_flaky_random_coin_flip | 2026-07-26 | 2026-07-26 | 60.0% | 8 | 12 | unknown | flaky | assert 0.4695907540789872 >= 0.5 + where 0.4695907540789872 = <built-in method … |
| tests/fixtures/flaky_demo_suite/test_flaky_demo.py::test_flaky_shared_temp_race | 2026-07-26 | 2026-07-26 | 70.0% | 6 | 14 | unknown | flaky | AssertionError: assert 'writer' == 'init' - init + writer |
| tests/fixtures/flaky_demo_suite/test_flaky_demo.py::test_flaky_timing_deadline | 2026-07-26 | 2026-07-26 | 30.0% | 14 | 6 | unknown | flaky | assert False |
