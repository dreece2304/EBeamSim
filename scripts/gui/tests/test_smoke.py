"""Smoke test: the GUI imports and the main window constructs offscreen."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


def test_main_window_constructs():
    from PySide6.QtWidgets import QApplication
    import ebl_gui

    app = QApplication.instance() or QApplication([])
    window = ebl_gui.EBLMainWindow()
    try:
        # Outputs must default to the repo's output/ dir, not a build dir
        assert window.working_dir.endswith(os.sep + "output")
    finally:
        window.close()


def test_composition_parse_handles_decimals_and_bad_tokens():
    from PySide6.QtWidgets import QApplication
    import ebl_gui

    app = QApplication.instance() or QApplication([])
    window = ebl_gui.EBLMainWindow()
    try:
        parsed = window.parse_composition("Si:1,H:1,O:1.5")
        assert parsed == {"Si": 1.0, "H": 1.0, "O": 1.5}
        # Malformed token is skipped, not fatal
        parsed = window.parse_composition("Si:1,bogus,O:x")
        assert parsed == {"Si": 1.0}
    finally:
        window.close()
