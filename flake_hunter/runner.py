"""Run a pytest suite repeatedly and record artifacts to disk."""

from __future__ import annotations

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path

from flake_hunter.models import RunManifest, RunRecord


def _run_once(run_index: int, suite_path: Path, output_dir: Path, timeout: float) -> RunRecord:
    json_report_path = output_dir / f"run_{run_index}.json"
    log_path = output_dir / f"run_{run_index}.log"

    started_at = datetime.now()
    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(suite_path),
                "-v",
                "--json-report",
                f"--json-report-file={json_report_path}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        log_path.write_text(result.stdout + result.stderr)
        exit_code = result.returncode
    except OSError as exc:
        log_path.write_text(f"flake-hunter: failed to launch pytest subprocess: {exc}")
        exit_code = -1
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(f"flake-hunter: pytest subprocess timed out after {timeout}s: {exc}")
        exit_code = -2
    duration = time.monotonic() - start

    return RunRecord(
        run_index=run_index,
        json_report_path=json_report_path,
        log_path=log_path,
        started_at=started_at,
        duration=duration,
        exit_code=exit_code,
    )


def run_suite_n_times(
    suite_path: Path,
    runs: int,
    parallel: int,
    output_dir: Path,
    timeout: float = 300.0,
) -> RunManifest:
    """Spawn pytest ``runs`` times against ``suite_path``.

    Writes a JSON report and raw console log per run under ``output_dir``
    and returns a manifest of artifact paths. Never returns log or report
    contents directly -- callers read them from disk as needed.

    Each invocation is its own OS process (via a thread pool of
    ``parallel`` workers), so a subprocess crash on one run is recorded on
    its ``RunRecord`` rather than raising and aborting the rest of the
    batch. Likewise, a run that hangs past ``timeout`` seconds (a
    plausible outcome for a suite this tool expects to contain
    timing-dependent or racy tests) is killed and recorded as a failed
    ``RunRecord`` rather than blocking the batch forever.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    worker = partial(_run_once, suite_path=suite_path, output_dir=output_dir, timeout=timeout)
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        records = list(pool.map(worker, range(runs)))

    return RunManifest(suite_path=suite_path, output_dir=output_dir, runs=records)
