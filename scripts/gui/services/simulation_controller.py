"""
Simulation execution and monitoring controller
"""

import os
import subprocess
import threading
import queue
import re
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QWidget

from ..models.simulation_model import SimulationModel
from .macro_generator import MacroGeneratorService
from .file_service import FileService


class SimulationWorker(QObject):
    """Worker thread for running simulations"""
    output = Signal(str)
    progress = Signal(int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, executable_path: str, macro_path: str, working_dir: str):
        super().__init__()
        self.executable_path = executable_path
        self.macro_path = macro_path
        self.working_dir = working_dir
        self.process = None
        self.should_stop = False
        self.total_events = None
        self.last_reported_progress = -1

    def run_simulation(self):
        """Run the simulation in this thread"""
        try:
            args = [self.executable_path, self.macro_path]

            # Set up environment - use existing env which should have Geant4 paths
            # The main GUI's Geant4 detector handles finding and setting up paths
            env = os.environ.copy()

            # If G4 data paths aren't in environment, try to find them
            if 'G4LEDATA' not in env:
                g4_path = self._find_geant4_path()
                if g4_path:
                    data_dir = Path(g4_path) / "share" / "Geant4" / "data"
                    if data_dir.exists():
                        # Auto-detect data directories
                        for item in data_dir.iterdir():
                            if item.is_dir():
                                name = item.name
                                if name.startswith("G4ABLA"):
                                    env['G4ABLADATA'] = str(item)
                                elif name.startswith("G4EMLOW"):
                                    env['G4LEDATA'] = str(item)
                                elif name.startswith("G4ENSDFSTATE"):
                                    env['G4ENSDFSTATEDATA'] = str(item)
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

            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.working_dir,
                env=env,
                bufsize=1
            )

            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.should_stop:
                    self.process.terminate()
                    break
                
                line = line.strip()
                if line:
                    self.output.emit(line)
                    self._parse_progress(line)

            # Wait for process to complete
            return_code = self.process.wait()
            
            if self.should_stop:
                self.finished.emit(False, "Simulation stopped by user")
            elif return_code == 0:
                self.finished.emit(True, "Simulation completed successfully")
            else:
                self.finished.emit(False, f"Simulation failed with return code {return_code}")

        except Exception as e:
            self.error.emit(f"Failed to run simulation: {str(e)}")
            self.finished.emit(False, str(e))

    def _parse_progress(self, line: str):
        """Parse output line for progress information"""
        # Look for event progress patterns
        event_patterns = [
            r"Event (\d+) of (\d+)",
            r"Processing event (\d+)/(\d+)",
            r"Run (\d+) Event (\d+)"
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) >= 2:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.total_events = total
                    progress = int((current / total) * 100)
                    
                    # Only emit if progress changed significantly
                    if progress > self.last_reported_progress + 1:
                        self.progress.emit(progress)
                        self.last_reported_progress = progress
                    break

    def _find_geant4_path(self):
        """Try to find Geant4 installation path"""
        import platform

        # Check environment variable first
        if 'G4INSTALL' in os.environ:
            return os.environ['G4INSTALL']

        # Common paths by platform (no hardcoded usernames)
        home = Path.home()
        common_paths = []

        if platform.system() == "Windows":
            common_paths = [
                home / "Geant4Projects" / "program_files",
                home / "geant4-install",
                Path(r"C:\Program Files\Geant4"),
            ]
        elif platform.system() == "Linux":
            common_paths = [
                home / "geant4" / "install",
                home / "geant4-install",
                Path("/opt/geant4"),
                Path("/usr/local/geant4"),
            ]
        elif platform.system() == "Darwin":
            common_paths = [
                home / "geant4-install",
                home / "geant4" / "install",
                Path("/opt/geant4"),
            ]

        for path in common_paths:
            if path.exists():
                return str(path)

        return None

    def stop_simulation(self):
        """Stop the running simulation"""
        self.should_stop = True
        if self.process:
            self.process.terminate()


class SimulationController(QObject):
    """High-level controller for simulation execution"""
    
    simulation_started = Signal()
    simulation_finished = Signal(bool, str)
    simulation_progress = Signal(int)
    simulation_output = Signal(str)
    simulation_error = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.macro_generator = MacroGeneratorService()
        self.file_service = FileService()
        
        self.worker = None
        self.worker_thread = None
        self.is_running = False
        
        # Default paths
        self.executable_path = ""
        self.working_directory = Path.cwd()
        
    def set_executable_path(self, path: str):
        """Set path to simulation executable"""
        self.executable_path = path
        
    def set_working_directory(self, path: str):
        """Set working directory for simulations"""
        self.working_directory = Path(path)
        
    def run_simulation(self, sim_model: SimulationModel) -> bool:
        """Run simulation with given model"""
        if self.is_running:
            self.simulation_error.emit("Simulation already running")
            return False
            
        if not self.executable_path:
            self.simulation_error.emit("Executable path not set")
            return False
            
        if not Path(self.executable_path).exists():
            self.simulation_error.emit(f"Executable not found: {self.executable_path}")
            return False
            
        try:
            # Validate simulation model
            if not sim_model.validate():
                self.simulation_error.emit("Invalid simulation parameters")
                return False
                
            # Generate macro file
            macro_path = self.working_directory / "temp_simulation.mac"
            output_path = sim_model.get_output_path()
            
            self.macro_generator.save_macro(sim_model, macro_path, output_path)
            
            # Create worker thread
            self.worker = SimulationWorker(
                self.executable_path,
                str(macro_path),
                str(self.working_directory)
            )
            
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals
            self.worker.output.connect(self.simulation_output.emit)
            self.worker.progress.connect(self.simulation_progress.emit)
            self.worker.finished.connect(self._on_simulation_finished)
            self.worker.error.connect(self.simulation_error.emit)
            
            self.worker_thread.started.connect(self.worker.run_simulation)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            
            # Start simulation
            self.is_running = True
            self.simulation_started.emit()
            self.worker_thread.start()
            
            return True
            
        except Exception as e:
            self.simulation_error.emit(f"Failed to start simulation: {str(e)}")
            return False
    
    def stop_simulation(self):
        """Stop running simulation"""
        if self.worker and self.is_running:
            self.worker.stop_simulation()
    
    def _on_simulation_finished(self, success: bool, message: str):
        """Handle simulation completion"""
        self.is_running = False
        
        # Clean up worker thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
        
        self.simulation_finished.emit(success, message)
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        return {
            "is_running": self.is_running,
            "executable_path": self.executable_path,
            "working_directory": str(self.working_directory),
            "has_worker": self.worker is not None
        }
    
    def validate_setup(self) -> tuple[bool, str]:
        """Validate simulation setup"""
        if not self.executable_path:
            return False, "Executable path not set"
            
        if not Path(self.executable_path).exists():
            return False, f"Executable not found: {self.executable_path}"
            
        if not self.working_directory.exists():
            return False, f"Working directory not found: {self.working_directory}"
            
        return True, "Setup valid"