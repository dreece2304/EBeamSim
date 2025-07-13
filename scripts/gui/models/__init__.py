"""
Data models for EBL simulation GUI
"""

from .material_model import MaterialModel
from .beam_model import BeamModel
from .simulation_model import SimulationModel

__all__ = ['MaterialModel', 'BeamModel', 'SimulationModel']