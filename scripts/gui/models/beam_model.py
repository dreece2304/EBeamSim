"""
Beam parameter data model for EBL simulations
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any


@dataclass
class BeamModel:
    """Data model for electron beam parameters"""
    
    energy: float = 100.0  # keV
    beam_size: float = 2.0  # nm
    position: Tuple[float, float, float] = (0.0, 0.0, 100.0)  # nm
    direction: Tuple[float, float, float] = (0.0, 0.0, -1.0)  # normalized
    particle_type: str = "e-"
    
    # Energy presets for common EBL systems
    ENERGY_PRESETS = {
        "Low Energy (30 keV)": 30.0,
        "Medium Energy (100 keV)": 100.0,
        "High Energy (200 keV)": 200.0,
        "JEOL JBX-9500FS (100 keV)": 100.0,
        "Raith EBPG5200 (100 keV)": 100.0,
        "Elionix ELS-G100 (100 keV)": 100.0
    }
    
    @classmethod
    def from_preset(cls, preset_name: str) -> 'BeamModel':
        """Create beam model from energy preset"""
        if preset_name not in cls.ENERGY_PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        energy = cls.ENERGY_PRESETS[preset_name]
        return cls(energy=energy)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeamModel':
        """Create beam model from dictionary"""
        return cls(
            energy=data.get("energy", 100.0),
            beam_size=data.get("beam_size", 2.0),
            position=tuple(data.get("position", [0.0, 0.0, 100.0])),
            direction=tuple(data.get("direction", [0.0, 0.0, -1.0])),
            particle_type=data.get("particle_type", "e-")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert beam model to dictionary"""
        return {
            "energy": self.energy,
            "beam_size": self.beam_size,
            "position": list(self.position),
            "direction": list(self.direction),
            "particle_type": self.particle_type
        }
    
    def validate(self) -> bool:
        """Validate beam parameters"""
        if self.energy <= 0:
            return False
        if self.beam_size <= 0:
            return False
        if len(self.position) != 3 or len(self.direction) != 3:
            return False
        return True
    
    @property
    def position_x(self) -> float:
        return self.position[0]
    
    @property
    def position_y(self) -> float:
        return self.position[1]
    
    @property
    def position_z(self) -> float:
        return self.position[2]
    
    @property
    def direction_x(self) -> float:
        return self.direction[0]
    
    @property
    def direction_y(self) -> float:
        return self.direction[1]
    
    @property
    def direction_z(self) -> float:
        return self.direction[2]
    
    def set_position(self, x: float, y: float, z: float):
        """Set beam position"""
        self.position = (x, y, z)
    
    def set_direction(self, x: float, y: float, z: float):
        """Set beam direction"""
        self.direction = (x, y, z)