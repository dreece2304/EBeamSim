"""
Threading utilities for simulation execution
"""

import os
import re
import time
import platform
import subprocess
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal


class SimulationWorker(QObject):
    """Worker thread for running simulations with optimized progress tracking and cross-platform support"""
    output = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, executable_path: str, macro_path: str, working_dir: str):
        super().__init__()
        self.executable_path = executable_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.process: Optional[subprocess.Popen] = None
        self.should_stop = False
        self.total_events: Optional[int] = None
        self.last_reported_progress = -1

    def _setup_geant4_environment(self) -> dict:
        """Setup Geant4 environment variables in a cross-platform way"""
        env = os.environ.copy()
        
        # Try to find Geant4 installation automatically
        g4_path = self._find_geant4_installation()
        
        if g4_path:
            # Add Geant4 data paths (cross-platform)
            data_dir = Path(g4_path) / "share" / "Geant4" / "data"
            
            # Auto-detect data versions or use the ones actually installed
            # These match the Geant4 11.1.3 installation
            env['G4ABLADATA'] = str(data_dir / "G4ABLA3.1")
            env['G4LEDATA'] = str(data_dir / "G4EMLOW8.2")
            env['G4ENSDFSTATEDATA'] = str(data_dir / "G4ENSDFSTATE2.3")
            env['G4INCLDATA'] = str(data_dir / "G4INCL1.0")
            env['G4NEUTRONHPDATA'] = str(data_dir / "G4NDL4.7")
            env['G4PARTICLEXSDATA'] = str(data_dir / "G4PARTICLEXS4.0")
            env['G4PIIDATA'] = str(data_dir / "G4PII1.3")
            env['G4RADIOACTIVEDATA'] = str(data_dir / "RadioactiveDecay5.6")
            env['G4REALSURFACEDATA'] = str(data_dir / "RealSurface2.2")
            env['G4SAIDXSDATA'] = str(data_dir / "G4SAIDDATA2.0")
            env['G4LEVELGAMMADATA'] = str(data_dir / "PhotonEvaporation5.7")

            # Add bin directory to PATH
            bin_dir = Path(g4_path) / "bin"
            path_sep = ";" if platform.system() == "Windows" else ":"
            env['PATH'] = str(bin_dir) + path_sep + env.get('PATH', '')
            
            # Add lib directory to LD_LIBRARY_PATH (Linux/macOS) or PATH (Windows)
            lib_dir = Path(g4_path) / "lib"
            if platform.system() == "Windows":
                # On Windows, DLLs are found via PATH
                env['PATH'] = str(lib_dir) + path_sep + env.get('PATH', '')
            else:
                # On Linux/macOS, use LD_LIBRARY_PATH
                env['LD_LIBRARY_PATH'] = str(lib_dir) + path_sep + env.get('LD_LIBRARY_PATH', '')
            
        return env

    def _find_geant4_installation(self) -> Optional[str]:
        """Try to automatically find Geant4 installation"""
        # Common installation paths by platform
        common_paths = []
        
        if platform.system() == "Windows":
            common_paths = [
                r"C:\Users\dreec\Geant4Projects\program_files",
                r"C:\Program Files\Geant4",
                r"C:\Geant4",
            ]
        elif platform.system() == "Linux":
            common_paths = [
                "/opt/geant4",
                "/usr/local/geant4",
                "/home/dreece23/geant4/install",  # Actual installation path
                "/home/dreece23/geant4-install",
                str(Path.home() / "geant4-install"),
                str(Path.home() / "geant4/install"),
            ]
        elif platform.system() == "Darwin":  # macOS
            common_paths = [
                "/opt/geant4",
                "/usr/local/geant4",
                str(Path.home() / "geant4-install"),
            ]
        
        # Check environment variable first
        if 'G4INSTALL' in os.environ:
            return os.environ['G4INSTALL']
        
        # Check common paths
        for path in common_paths:
            if Path(path).exists():
                return path
                
        # Try to use relative path from executable location
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

            # OPTIMIZED progress tracking for large simulations
            line_count = 0
            max_gui_lines = 3000  # Reduce GUI overhead for large sims

            # Enhanced tracking variables
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
                    if self.total_events and self.total_events > 100000:
                        # For large sims, filter output aggressively
                        should_show_line = any(keyword in line for keyword in important_keywords)

                    if should_show_line and line_count < max_gui_lines:
                        self.output.emit(line)
                    elif line_count == max_gui_lines:
                        self.output.emit("... (output filtered for large simulation performance)")

                    # Parse for total events
                    if "events will be processed" in line or "event will be processed" in line:
                        match = re.search(r'(\d+)\s+events?\s+will be processed', line)
                        if match:
                            self.total_events = int(match.group(1))
                            self.output.emit(f">>> Total events to process: {self.total_events}")

                    # ENHANCED PROGRESS TRACKING
                    progress_updated = False

                    # Method 1: Direct "Processing event X" messages
                    if "Processing event" in line and "complete" in line:
                        match = re.search(r'Processing event\s+(\d+)', line)
                        if match:
                            event_num = int(match.group(1))
                            last_event_number = event_num
                            self.progress.emit(event_num)
                            progress_updated = True

                    # Method 2: Milestone messages for very large sims
                    elif "Milestone:" in line:
                        match = re.search(r'(\d+)/(\d+) events', line)
                        if match:
                            event_num = int(match.group(1))
                            last_event_number = event_num
                            self.progress.emit(event_num)
                            progress_updated = True

                    # Method 3: Use energy deposition reports for estimation
                    elif "Resist energy deposits:" in line and "Total energy:" in line:
                        energy_reports_count += 1

                        # Estimate based on energy reports (they come every ~10-20k events)
                        if self.total_events and self.total_events > 50000:
                            # Dynamic estimation based on simulation size
                            if self.total_events <= 100000:
                                estimate_factor = 8000
                            elif self.total_events <= 1000000:
                                estimate_factor = 12000
                            else:
                                estimate_factor = 20000  # For very large sims

                            estimated_events = energy_reports_count * estimate_factor
                            if estimated_events > last_event_number:
                                estimated_progress = min(estimated_events, self.total_events)
                                self.progress.emit(int(estimated_progress))
                                progress_updated = True

                    # Method 4: Use track processing reports for very large sims
                    elif "StackingAction: Processed" in line and "tracks" in line:
                        track_reports_count += 1

                        # For 1M+ events, use track reports as backup indicator
                        if self.total_events and self.total_events >= 1000000:
                            estimated_from_tracks = track_reports_count * 3000
                            if estimated_from_tracks > max(last_event_number, estimated_progress):
                                estimated_progress = min(estimated_from_tracks, self.total_events)
                                if abs(estimated_progress - last_event_number) > 5000:
                                    self.progress.emit(int(estimated_progress))
                                    progress_updated = True

                    # Report percentage progress with adaptive thresholds
                    if progress_updated and self.total_events and self.total_events > 0:
                        current_progress = max(last_event_number, estimated_progress)
                        percentage = (current_progress / self.total_events) * 100

                        # Dynamic reporting threshold based on simulation size
                        if self.total_events > 2000000:
                            report_threshold = 0.5  # Every 0.5% for very large sims
                        elif self.total_events > 500000:
                            report_threshold = 1.0  # Every 1% for large sims
                        elif self.total_events > 50000:
                            report_threshold = 2.0  # Every 2% for medium sims
                        else:
                            report_threshold = 5.0  # Every 5% for smaller sims

                        if percentage - self.last_reported_progress >= report_threshold:
                            self.output.emit(f">>> Progress: {percentage:.1f}% ({current_progress:,}/{self.total_events:,})")
                            self.last_reported_progress = percentage

                    # Track important physics messages
                    if "Fluorescence:" in line or "Auger:" in line or "PIXE:" in line:
                        self.output.emit(f">>> PHYSICS: {line}")

                    # Highlight warnings and errors
                    if "WARNING" in line or "Warning" in line:
                        self.output.emit(f"[WARNING] {line}")
                    elif "ERROR" in line or "Error" in line:
                        self.output.emit(f"[ERROR] {line}")

                    line_count += 1

            return_code = self.process.wait()

            if return_code == 0 and not self.should_stop:
                self.finished.emit(True, "Simulation completed successfully")
            else:
                self.finished.emit(False, f"Simulation failed (code: {return_code})")

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

    def stop(self):
        """Stop the simulation"""
        self.should_stop = True
        if self.process:
            try:
                self.process.terminate()
            except:
                pass