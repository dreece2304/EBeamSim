"""
Plotting widgets for EBL GUI
Modular plotting components extracted from monolithic file
"""

from .plot_widget import PlotWidget
from .enhanced_2d_plot import Enhanced2DPlotWidget

__all__ = [
    'PlotWidget',
    'Enhanced2DPlotWidget'
]