"""
Material data model for EBL simulations
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import json


@dataclass
class MaterialModel:
    """Data model for resist materials"""
    
    name: str
    composition: str
    density: float
    thickness: float = 50.0
    description: str = ""
    
    # Default material presets
    PRESETS = {
        "PMMA": {
            "composition": "C:5,H:8,O:2",
            "density": 1.19,
            "description": "Standard PMMA resist"
        },
        "HSQ": {
            "composition": "Si:1,H:1,O:1.5",
            "density": 1.4,
            "description": "Hydrogen silsesquioxane negative resist"
        },
        "Alucone (XPS)": {
            "composition": "Al:1,C:5,H:4,O:2",
            "density": 1.35,
            "description": "Alucone based on XPS characterization"
        },
        "Alucone (Exposed)": {
            "composition": "Al:1,C:5,H:4,O:3",
            "density": 1.40,
            "description": "Exposed Alucone with extra oxygen"
        },
        "Sn-MLD": {
            "composition": "Sn:1,C:8,H:8,O:4",
            "density": 2.0,
            "description": "Organic-inorganic hybrid Sn resist via MLD (TDMASn + 2-butyne-1,4-diol), ideal [-Sn(O-C4H4-O)2-] repeating unit"
        },
        "Zincone": {
            "composition": "Zn:1,C:2,H:4,O:2",
            "density": 2.1,
            "description": "Zinc-based MLD hybrid material (DEZ + ethylene glycol), [-Zn-O-CH2-CH2-O-] repeating unit"
        }
    }
    
    @classmethod
    def from_preset(cls, preset_name: str, thickness: float = 50.0) -> 'MaterialModel':
        """Create material from preset"""
        if preset_name not in cls.PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        preset = cls.PRESETS[preset_name]
        return cls(
            name=preset_name,
            composition=preset["composition"],
            density=preset["density"],
            thickness=thickness,
            description=preset["description"]
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaterialModel':
        """Create material from dictionary"""
        return cls(
            name=data.get("name", "Custom"),
            composition=data["composition"],
            density=data["density"],
            thickness=data.get("thickness", 50.0),
            description=data.get("description", "")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert material to dictionary"""
        return {
            "name": self.name,
            "composition": self.composition,
            "density": self.density,
            "thickness": self.thickness,
            "description": self.description
        }
    
    def validate(self) -> bool:
        """Validate material parameters"""
        if not self.composition:
            return False
        if self.density <= 0:
            return False
        if self.thickness <= 0:
            return False
        return True
    
    @property
    def elements(self) -> Dict[str, float]:
        """Parse composition string into elements dictionary"""
        elements = {}
        try:
            for part in self.composition.split(','):
                element, ratio = part.strip().split(':')
                elements[element.strip()] = float(ratio.strip())
        except (ValueError, IndexError):
            pass
        return elements