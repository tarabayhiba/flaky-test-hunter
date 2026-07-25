"""Ground-truth fixture suite for flake-hunter.

Deliberately plants three flaky tests, each flaky for a genuinely
different reason, plus two stable controls. Every module in flake_hunter
is tested against this suite: the aggregator must flag exactly the three
flaky tests below and neither control.

This suite is not part of the project's own unit-test run -- pytest's
testpaths excludes tests/fixtures/ -- because it is meant to be run
*against* by flake-hunter, not collected as part of its own passing suite.
"""

from __future__ import annotations

import os
import random
import tempfile
import threading
import time
from pathlib import Path


def test_flaky_random_coin_flip() -> None:
    """Flaky: fails on a direct coin-flip RNG draw, ~50% of runs."""
    assert random.random() >= 0.5


def test_flaky_shared_temp_race() -> None:
    """Flaky: a genuine race on a shared (non-isolated) temp file.

    A background thread overwrites the file while the main thread reads
    it back; which write "wins" depends on real thread-scheduling order,
    not on pytest's own concurrency model. Scoped by pid (not a single
    fixed path) so that running many invocations concurrently -- exactly
    what runner.py's `parallel` does -- races within each process as
    intended instead of also racing *across* unrelated processes sharing
    the same machine.
    """
    race_file = Path(tempfile.gettempdir()) / f"flake_hunter_demo_race_{os.getpid()}.txt"
    try:
        race_file.write_text("init")

        def writer() -> None:
            time.sleep(random.uniform(0, 0.005))
            race_file.write_text("writer")

        racer = threading.Thread(target=writer)
        racer.start()
        time.sleep(random.uniform(0, 0.005))
        seen = race_file.read_text()
        racer.join()

        assert seen == "init"
    finally:
        race_file.unlink(missing_ok=True)


def test_flaky_timing_deadline() -> None:
    """Flaky: a worker sometimes misses a tight wall-clock deadline.

    Models the classic "operation usually completes within its SLA, but
    not always" flake: a worker thread's scheduling delay is drawn from a
    range that straddles the deadline, so whether it's on time depends on
    real thread-scheduling variance each run, the assertion itself is on
    elapsed time against a budget, not on a raw RNG draw.
    """
    done = threading.Event()

    def worker() -> None:
        time.sleep(random.uniform(0, 0.001))
        done.set()

    threading.Thread(target=worker).start()
    finished_in_time = done.wait(timeout=0.0005)

    assert finished_in_time


def test_always_passes() -> None:
    """Control: consistently passing, 0% fail rate not flaky."""
    assert 1 + 1 == 2


def test_always_fails() -> None:
    """Control: consistently failing, 100% fail rate not flaky."""
    raise AssertionError("deliberately always-failing control for flake-hunter's ground truth")
