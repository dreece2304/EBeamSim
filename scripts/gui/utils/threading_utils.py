"""
Threading utilities for simulation execution - CANONICAL SimulationWorker implementation

This module provides the authoritative SimulationWorker class used throughout the GUI.
Other modules should import from here rather than defining their own versions.
"""

import os
import re
import time
import platform
import subprocess
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QMutex


class SimulationWorker(QObject):
    """
    Worker thread for running simulations with optimized progress tracking.

    This is the canonical implementation - import this class rather than
    creating duplicate versions in other modules.

    Features:
    - Pre-compiled regex patterns for performance
    - Thread-safe signal emission with QMutex
    - Cross-platform Geant4 environment detection
    - Adaptive progress tracking for simulations of any size
    - Smart output filtering for large simulations
    """
    output = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)

    # Pre-compiled regex patterns (compiled once at class load, used many times)
    RE_TOTAL_EVENTS = re.compile(r'(\d+)\s+events?\s+will be processed')
    RE_PROCESSING_EVENT = re.compile(r'Processing event\s+(\d+)')
    RE_MILESTONE_EVENTS = re.compile(r'(\d+)/(\d+) events')
    RE_PATTERN_EVENT = re.compile(r'Pattern (?:exposure|milestone):.*Event\s+(\d+)/')

    # Simulation size thresholds
    LARGE_SIMULATION_THRESHOLD = 100000
    VERY_LARGE_SIMULATION_THRESHOLD = 1000000
    MAX_GUI_LINES = 3000

    def __init__(self, executable_path: str, macro_path: str, working_dir: str,
                 g4_path: Optional[str] = None, expected_events: Optional[int] = None):
        super().__init__()
        self.executable_path = executable_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.g4_path = g4_path
        self.process: Optional[subprocess.Popen] = None
        self.should_stop = False
        # The GUI wrote the macro, so it knows the event count exactly; stdout
        # parsing (RE_TOTAL_EVENTS) is only a fallback.
        self.total_events: Optional[int] = expected_events
        self.last_reported_progress = -1
        self.mutex = QMutex()  # Thread-safe access to shared state

    def _safe_emit(self, signal, *args):
        """Thread-safe signal emission with stop check"""
        self.mutex.lock()
        try:
            if not self.should_stop:
                signal.emit(*args)
        finally:
            self.mutex.unlock()

    def _emit_finished(self, success: bool, message: str):
        """Emit the terminal signal unconditionally.

        Must NOT go through _safe_emit: after stop() sets should_stop, the
        suppression there would swallow the finished signal and leave the GUI
        stuck with the Run button disabled.
        """
        self.mutex.lock()
        try:
            self.finished.emit(success, message)
        finally:
            self.mutex.unlock()

    def stop(self):
        """Request worker to stop - thread-safe. Escalates terminate -> kill."""
        self.mutex.lock()
        try:
            self.should_stop = True
        finally:
            self.mutex.unlock()

        if self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass

    def _setup_geant4_environment(self) -> dict:
        """Setup Geant4 environment variables in a cross-platform way"""
        env = os.environ.copy()

        # Use provided path or try to find installation automatically
        g4_path = self.g4_path or self._find_geant4_installation()

        if g4_path:
            g4_path = Path(g4_path)
            data_dir = g4_path / "share" / "Geant4" / "data"

            if data_dir.exists():
                # Auto-detect data directories by scanning
                for item in data_dir.iterdir():
                    if item.is_dir():
                        name = item.name
                        if name.startswith("G4ABLA"):
                            env['G4ABLADATA'] = str(item)
                        elif name.startswith("G4EMLOW"):
                            env['G4LEDATA'] = str(item)
                        elif name.startswith("G4ENSDFSTATE"):
                            env['G4ENSDFSTATEDATA'] = str(item)
                        elif name.startswith("G4INCL"):
                            env['G4INCLDATA'] = str(item)
                        elif name.startswith("G4NDL"):
                            env['G4NEUTRONHPDATA'] = str(item)
                        elif name.startswith("G4PARTICLEXS"):
                            env['G4PARTICLEXSDATA'] = str(item)
                        elif name.startswith("G4PII"):
                            env['G4PIIDATA'] = str(item)
                        elif name.startswith("RadioactiveDecay"):
                            env['G4RADIOACTIVEDATA'] = str(item)
                        elif name.startswith("RealSurface"):
                            env['G4REALSURFACEDATA'] = str(item)
                        elif name.startswith("G4SAIDDATA"):
                            env['G4SAIDXSDATA'] = str(item)
                        elif name.startswith("PhotonEvaporation"):
                            env['G4LEVELGAMMADATA'] = str(item)

            # Add bin directory to PATH
            bin_dir = g4_path / "bin"
            path_sep = ";" if platform.system() == "Windows" else ":"
            if bin_dir.exists():
                env['PATH'] = str(bin_dir) + path_sep + env.get('PATH', '')

            # Add lib directory to library path
            lib_dir = g4_path / "lib"
            if lib_dir.exists():
                if platform.system() == "Windows":
                    env['PATH'] = str(lib_dir) + path_sep + env.get('PATH', '')
                else:
                    env['LD_LIBRARY_PATH'] = str(lib_dir) + path_sep + env.get('LD_LIBRARY_PATH', '')

        return env

    def _find_geant4_installation(self) -> Optional[str]:
        """Try to automatically find Geant4 installation"""
        # Check environment variable first (highest priority)
        if 'G4INSTALL' in os.environ:
            return os.environ['G4INSTALL']

        # Common installation paths by platform
        home = Path.home()
        common_paths = []

        if platform.system() == "Windows":
            common_paths = [
                home / "Geant4Projects" / "program_files",
                home / "geant4-install",
                Path(r"C:\Program Files\Geant4"),
                Path(r"C:\Geant4"),
            ]
        elif platform.system() == "Linux":
            common_paths = [
                home / "geant4" / "install",
                home / "geant4-install",
                Path("/opt/geant4"),
                Path("/usr/local/geant4"),
            ]
        elif platform.system() == "Darwin":  # macOS
            common_paths = [
                home / "geant4-install",
                home / "geant4" / "install",
                Path("/opt/geant4"),
                Path("/usr/local/geant4"),
            ]

        # Check common paths
        for path in common_paths:
            if path.exists():
                return str(path)

        # Try relative path from executable location
        exe_path = Path(self.executable_path)
        potential_g4_path = exe_path.parent.parent.parent / "program_files"
        if potential_g4_path.exists():
            return str(potential_g4_path)

        return None

    def run_simulation(self):
        """Run the simulation in this thread with optimized progress tracking"""
        try:
            args = [self.executable_path, self.macro_path]
            env = self._setup_geant4_environment()

            # Platform-specific subprocess flags
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=self.working_dir,
                env=env,
                creationflags=creation_flags
            )

            # Progress tracking variables
            line_count = 0
            last_event_number = 0
            energy_reports_count = 0
            track_reports_count = 0
            estimated_progress = 0

            # Keywords for filtering important output
            important_keywords = [
                "Processing event", "Progress:", "Resist energy deposits:",
                "StackingAction:", "ERROR", "WARNING", "Complete", "MeV", "Milestone"
            ]

            while True:
                if self.should_stop:
                    self.process.terminate()
                    break

                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if line:
                    # Smart output filtering for large simulations
                    should_show_line = True
                    if self.total_events and self.total_events > self.LARGE_SIMULATION_THRESHOLD:
                        should_show_line = any(keyword in line for keyword in important_keywords)

                    if should_show_line and line_count < self.MAX_GUI_LINES:
                        self._safe_emit(self.output, line)
                    elif line_count == self.MAX_GUI_LINES:
                        self._safe_emit(self.output, "... (output filtered for large simulation performance)")

                    # Parse for total events
                    if "events will be processed" in line or "event will be processed" in line:
                        match = self.RE_TOTAL_EVENTS.search(line)
                        if match:
                            self.total_events = int(match.group(1))
                            self._safe_emit(self.output, f">>> Total events to process: {self.total_events}")

                    # ENHANCED PROGRESS TRACKING
                    progress_updated = False

                    # Method 1: Direct "Processing event X" messages
                    if "Processing event" in line and "complete" in line:
                        match = self.RE_PROCESSING_EVENT.search(line)
                        if match:
                            # max(): in MT mode worker threads report out of order
                            event_num = max(int(match.group(1)), last_event_number)
                            last_event_number = event_num
                            self._safe_emit(self.progress, event_num)
                            progress_updated = True

                    # Method 2: Milestone messages for very large sims
                    elif "Milestone:" in line and "Pattern" not in line:
                        match = self.RE_MILESTONE_EVENTS.search(line)
                        if match:
                            event_num = max(int(match.group(1)), last_event_number)
                            last_event_number = event_num
                            self._safe_emit(self.progress, event_num)
                            progress_updated = True

                    # Method 2b: Pattern-mode progress ("Pattern exposure: ... Event N/total")
                    elif "Pattern exposure:" in line or "Pattern milestone:" in line:
                        match = self.RE_PATTERN_EVENT.search(line)
                        if match:
                            event_num = max(int(match.group(1)), last_event_number)
                            last_event_number = event_num
                            self._safe_emit(self.progress, event_num)
                            progress_updated = True

                    # Method 3: Use energy deposition reports for estimation
                    elif "Resist energy deposits:" in line and "Total energy:" in line:
                        energy_reports_count += 1

                        if self.total_events and self.total_events > 50000:
                            if self.total_events <= 100000:
                                estimate_factor = 8000
                            elif self.total_events <= 1000000:
                                estimate_factor = 12000
                            else:
                                estimate_factor = 20000

                            estimated_events = energy_reports_count * estimate_factor
                            if estimated_events > last_event_number:
                                estimated_progress = min(estimated_events, self.total_events)
                                self._safe_emit(self.progress, int(estimated_progress))
                                progress_updated = True

                    # Method 4: Use track processing reports for very large sims
                    elif "StackingAction: Processed" in line and "tracks" in line:
                        track_reports_count += 1

                        if self.total_events and self.total_events >= self.VERY_LARGE_SIMULATION_THRESHOLD:
                            estimated_from_tracks = track_reports_count * 3000
                            if estimated_from_tracks > max(last_event_number, estimated_progress):
                                estimated_progress = min(estimated_from_tracks, self.total_events)
                                if abs(estimated_progress - last_event_number) > 5000:
                                    self._safe_emit(self.progress, int(estimated_progress))
                                    progress_updated = True

                    # Report percentage progress with adaptive thresholds
                    if progress_updated and self.total_events and self.total_events > 0:
                        current_progress = max(last_event_number, estimated_progress)
                        percentage = (current_progress / self.total_events) * 100

                        if self.total_events > 2000000:
                            report_threshold = 0.5
                        elif self.total_events > 500000:
                            report_threshold = 1.0
                        elif self.total_events > 50000:
                            report_threshold = 2.0
                        else:
                            report_threshold = 5.0

                        if percentage - self.last_reported_progress >= report_threshold:
                            self._safe_emit(self.output, f">>> Progress: {percentage:.1f}% ({current_progress:,}/{self.total_events:,})")
                            self.last_reported_progress = percentage

                    # Track important physics messages
                    if "Fluorescence:" in line or "Auger:" in line or "PIXE:" in line:
                        self._safe_emit(self.output, f">>> PHYSICS: {line}")

                    # Highlight warnings and errors
                    if "WARNING" in line or "Warning" in line:
                        self._safe_emit(self.output, f"[WARNING] {line}")
                    elif "ERROR" in line or "Error" in line:
                        self._safe_emit(self.output, f"[ERROR] {line}")

                    line_count += 1

            return_code = self.process.wait()

            if return_code == 0 and not self.should_stop:
                self._emit_finished(True, "Simulation completed successfully")
            elif self.should_stop:
                self._emit_finished(False, "Simulation stopped by user")
            else:
                self._emit_finished(False, f"Simulation failed (code: {return_code})")

        except Exception as e:
            self._emit_finished(False, f"Error: {str(e)}")
