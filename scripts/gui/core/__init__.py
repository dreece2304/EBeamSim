"""
Core modules for EBL GUI
"""

from .config import Config
from .file_manager import FileManager

# Note: simulation_runner and data_manager may not exist yet - consolidating from monolithic file

__all__ = [
    'Config',
    'FileManager'
]