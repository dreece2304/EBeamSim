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

            # Set up environment variables for Geant4
            env = os.environ.copy()
            g4_path = r"C:\Users\dreec\Geant4Projects\program_files"

            # Add Geant4 data paths
            env.update({
                'G4ABLADATA': f"{g4_path}\\share\\Geant4\\data\\G4ABLA3.3",
                'G4CHANNELINGDATA': f"{g4_path}\\share\\Geant4\\data\\G4CHANNELING1.0",
                'G4LEDATA': f"{g4_path}\\share\\Geant4\\data\\G4EMLOW8.6.1",
                'G4ENSDFSTATEDATA': f"{g4_path}\\share\\Geant4\\data\\G4ENSDFSTATE3.0",
                'G4INCLDATA': f"{g4_path}\\share\\Geant4\\data\\G4INCL1.2",
                'G4NEUTRONHPDATA': f"{g4_path}\\share\\Geant4\\data\\G4NDL4.7.1",
                'G4PARTICLEXSDATA': f"{g4_path}\\share\\Geant4\\data\\G4PARTICLEXS4.1",
                'G4PIIDATA': f"{g4_path}\\share\\Geant4\\data\\G4PII1.3",
                'G4RADIOACTIVEDATA': f"{g4_path}\\share\\Geant4\\data\\RadioactiveDecay6.1.2",
                'G4REALSURFACEDATA': f"{g4_path}\\share\\Geant4\\data\\RealSurface2.2",
                'G4SAIDXSDATA': f"{g4_path}\\share\\Geant4\\data\\G4SAIDDATA2.0",
                'G4LEVELGAMMADATA': f"{g4_path}\\share\\Geant4\\data\\PhotonEvaporation6.1",
                'PATH': f"{g4_path}\\bin;" + env.get('PATH', '')
            })

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