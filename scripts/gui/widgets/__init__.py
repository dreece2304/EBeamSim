"""
Widget modules for EBL GUI
"""

from .enhanced_beam_widget import EnhancedBeamWidget
from .resist_properties_widget import ResistPropertiesWidget
from .output_widget import OutputWidget
from .plotting import PlotWidget, Enhanced2DPlotWidget

# Legacy alias for backward compatibility
BeamWidget = EnhancedBeamWidget

__all__ = [
    'BeamWidget',
    'EnhancedBeamWidget', 
    'ResistPropertiesWidget',
    'OutputWidget',
    'PlotWidget',
    'Enhanced2DPlotWidget'
]