"""
Simulation configuration data model for EBL simulations
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import datetime

from .material_model import MaterialModel
from .beam_model import BeamModel


@dataclass
class SimulationModel:
    """Data model for complete simulation configuration"""
    
    material: MaterialModel = field(default_factory=lambda: MaterialModel.from_preset("PMMA"))
    beam: BeamModel = field(default_factory=BeamModel)
    
    # Simulation parameters
    num_events: int = 100000
    physics_list: str = "G4EmStandardPhysics_option4"
    step_limit: float = 1.0  # nm
    enable_fluorescence: bool = True
    enable_auger: bool = True
    enable_pixe: bool = True
    
    # Output configuration
    output_prefix: str = "ebl_sim"
    output_directory: str = "data/output"
    auto_increment: bool = True
    
    # Binning configuration
    radial_bins: int = 200
    depth_bins: int = 100
    max_radius: float = 100.0  # nm
    log_binning: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationModel':
        """Create simulation model from dictionary"""
        material_data = data.get("material", {})
        beam_data = data.get("beam", {})
        
        return cls(
            material=MaterialModel.from_dict(material_data),
            beam=BeamModel.from_dict(beam_data),
            num_events=data.get("num_events", 100000),
            physics_list=data.get("physics_list", "G4EmStandardPhysics_option4"),
            step_limit=data.get("step_limit", 1.0),
            enable_fluorescence=data.get("enable_fluorescence", True),
            enable_auger=data.get("enable_auger", True),
            enable_pixe=data.get("enable_pixe", True),
            output_prefix=data.get("output_prefix", "ebl_sim"),
            output_directory=data.get("output_directory", "data/output"),
            auto_increment=data.get("auto_increment", True),
            radial_bins=data.get("radial_bins", 200),
            depth_bins=data.get("depth_bins", 100),
            max_radius=data.get("max_radius", 100.0),
            log_binning=data.get("log_binning", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation model to dictionary"""
        return {
            "material": self.material.to_dict(),
            "beam": self.beam.to_dict(),
            "num_events": self.num_events,
            "physics_list": self.physics_list,
            "step_limit": self.step_limit,
            "enable_fluorescence": self.enable_fluorescence,
            "enable_auger": self.enable_auger,
            "enable_pixe": self.enable_pixe,
            "output_prefix": self.output_prefix,
            "output_directory": self.output_directory,
            "auto_increment": self.auto_increment,
            "radial_bins": self.radial_bins,
            "depth_bins": self.depth_bins,
            "max_radius": self.max_radius,
            "log_binning": self.log_binning
        }
    
    def validate(self) -> bool:
        """Validate all simulation parameters"""
        if not self.material.validate():
            return False
        if not self.beam.validate():
            return False
        if self.num_events <= 0:
            return False
        if self.step_limit <= 0:
            return False
        if self.radial_bins <= 0 or self.depth_bins <= 0:
            return False
        if self.max_radius <= 0:
            return False
        return True
    
    def get_output_filename(self, extension: str = "csv") -> str:
        """Generate output filename with optional auto-increment"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.auto_increment:
            return f"{self.output_prefix}_{timestamp}.{extension}"
        else:
            return f"{self.output_prefix}.{extension}"
    
    def get_output_path(self, extension: str = "csv") -> Path:
        """Get full output path"""
        filename = self.get_output_filename(extension)
        return Path(self.output_directory) / filename
    
    @property
    def estimated_runtime_minutes(self) -> float:
        """Estimate simulation runtime based on parameters"""
        # Rough estimate: 1000 events per second on modern hardware
        base_time = self.num_events / 1000.0 / 60.0  # minutes
        
        # Physics complexity factor
        physics_factor = 1.0
        if self.enable_fluorescence:
            physics_factor *= 1.2
        if self.enable_auger:
            physics_factor *= 1.1
        if self.enable_pixe:
            physics_factor *= 1.1
        
        # Step limit factor (smaller steps = longer simulation)
        step_factor = 2.0 / self.step_limit if self.step_limit < 2.0 else 1.0
        
        return base_time * physics_factor * step_factor