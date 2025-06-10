"""
Widget modules for EBL GUI
"""

from .material_widget import MaterialWidget
from .beam_widget import BeamWidget
from .simulation_widget import SimulationWidget
from .output_widget import OutputWidget
from .plot_widget import PlotWidget

__all__ = [
    'MaterialWidget',
    'BeamWidget',
    'SimulationWidget',
    'OutputWidget',
    'PlotWidget'
]