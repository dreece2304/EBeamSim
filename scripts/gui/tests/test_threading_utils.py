"""Tests for SimulationWorker: progress parsing, stop behavior, finished signal."""

import os
import sys
import stat
import textwrap
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from utils.threading_utils import SimulationWorker  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def _make_fake_sim(tmp_path, script_body):
    """Create a fake ebl_sim executable printing canned output."""
    exe = tmp_path / "fake_sim.sh"
    exe.write_text("#!/bin/bash\n" + textwrap.dedent(script_body))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


def _run_worker(worker):
    """Run the worker synchronously and collect signal emissions."""
    results = {"progress": [], "output": [], "finished": None}
    worker.progress.connect(lambda v: results["progress"].append(v))
    worker.output.connect(lambda s: results["output"].append(s))
    worker.finished.connect(lambda ok, msg: results.update(finished=(ok, msg)))
    worker.run_simulation()
    return results


def test_expected_events_seeds_total(qapp, tmp_path):
    exe = _make_fake_sim(tmp_path, "echo hello\n")
    worker = SimulationWorker(exe, "macro.mac", str(tmp_path), expected_events=12345)
    assert worker.total_events == 12345


def test_psf_progress_parsing(qapp, tmp_path):
    exe = _make_fake_sim(
        tmp_path,
        """
        echo "Processing event 100 - 10.0% complete"
        echo "Processing event 500 - 50.0% complete"
        echo "Processing event 900 - 90.0% complete"
        """,
    )
    worker = SimulationWorker(exe, "m.mac", str(tmp_path), expected_events=1000)
    results = _run_worker(worker)
    assert results["progress"] == [100, 500, 900]
    assert results["finished"] == (True, "Simulation completed successfully")


def test_progress_is_monotonic(qapp, tmp_path):
    # MT builds can emit out-of-order event numbers
    exe = _make_fake_sim(
        tmp_path,
        """
        echo "Processing event 500 - 50.0% complete"
        echo "Processing event 300 - 30.0% complete"
        echo "Processing event 800 - 80.0% complete"
        """,
    )
    worker = SimulationWorker(exe, "m.mac", str(tmp_path), expected_events=1000)
    results = _run_worker(worker)
    assert results["progress"] == sorted(results["progress"])


def test_pattern_mode_progress(qapp, tmp_path):
    exe = _make_fake_sim(
        tmp_path,
        """
        echo "Pattern exposure: Point 5/100 (5.0%) - Event 5000/1e+05 (5.0%)"
        echo ">>> Pattern milestone: 50/100 points complete (50.0%) - Event 50000/100000"
        """,
    )
    worker = SimulationWorker(exe, "m.mac", str(tmp_path), expected_events=100000)
    results = _run_worker(worker)
    assert results["progress"] == [5000, 50000]


def test_finished_fires_after_stop(qapp, tmp_path):
    """Regression: finished must be emitted even when should_stop is set,
    otherwise the GUI is left with the Run button permanently disabled."""
    # exec so the signal hits the long-running process itself, matching the
    # real single-process ebl_sim binary
    exe = _make_fake_sim(
        tmp_path,
        """
        echo "starting"
        exec sleep 30
        """,
    )
    worker = SimulationWorker(exe, "m.mac", str(tmp_path), expected_events=100)
    results = {"finished": None}
    worker.finished.connect(lambda ok, msg: results.update(finished=(ok, msg)))

    thread = threading.Thread(target=worker.run_simulation)
    thread.start()
    # Wait for the subprocess to exist, then stop
    deadline = time.time() + 10
    while worker.process is None and time.time() < deadline:
        time.sleep(0.05)
    time.sleep(0.2)
    worker.stop()
    thread.join(timeout=15)
    # Cross-thread signal delivery is queued; spin the event loop to receive it
    QCoreApplication.processEvents()

    assert not thread.is_alive(), "worker thread did not exit after stop()"
    assert results["finished"] is not None, "finished signal was never emitted after stop()"
    assert results["finished"][0] is False
    assert worker.process.poll() is not None, "child process still running after stop()"


def test_failure_exit_code_reported(qapp, tmp_path):
    exe = _make_fake_sim(tmp_path, "echo boom\nexit 3\n")
    worker = SimulationWorker(exe, "m.mac", str(tmp_path), expected_events=10)
    results = _run_worker(worker)
    assert results["finished"] == (False, "Simulation failed (code: 3)")
