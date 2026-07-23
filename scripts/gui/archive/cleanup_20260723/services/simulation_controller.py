"""
Simulation execution and monitoring controller
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QWidget

from ..models.simulation_model import SimulationModel
from .macro_generator import MacroGeneratorService
from .file_service import FileService

# Import canonical SimulationWorker from threading_utils
from ..utils.threading_utils import SimulationWorker


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