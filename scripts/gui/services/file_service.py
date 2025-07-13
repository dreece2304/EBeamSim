"""
File I/O service for EBL simulation data
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np

from ..models.simulation_model import SimulationModel


class FileService:
    """Service for file I/O operations"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.json', '.txt']
    
    def load_simulation_config(self, config_path: Path) -> SimulationModel:
        """Load simulation configuration from JSON file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        return SimulationModel.from_dict(data)
    
    def save_simulation_config(self, sim_model: SimulationModel, config_path: Path) -> None:
        """Save simulation configuration to JSON file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(sim_model.to_dict(), f, indent=2)
    
    def load_psf_data(self, data_path: Path) -> pd.DataFrame:
        """Load PSF data from CSV file"""
        if not data_path.exists():
            raise FileNotFoundError(f"PSF data file not found: {data_path}")
        
        try:
            # Try to load with pandas first
            df = pd.read_csv(data_path)
            return df
        except Exception as e:
            # Fallback to manual CSV parsing
            return self._load_csv_manual(data_path)
    
    def _load_csv_manual(self, data_path: Path) -> pd.DataFrame:
        """Manual CSV loading with error handling"""
        data = []
        with open(data_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                try:
                    # Convert to float where possible
                    converted_row = []
                    for value in row:
                        try:
                            converted_row.append(float(value))
                        except ValueError:
                            converted_row.append(value)
                    data.append(converted_row)
                except Exception:
                    continue  # Skip malformed rows
        
        if header:
            return pd.DataFrame(data, columns=header)
        else:
            return pd.DataFrame(data)
    
    def save_psf_data(self, data: pd.DataFrame, output_path: Path) -> None:
        """Save PSF data to CSV file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(output_path, index=False)
    
    def load_2d_psf_data(self, data_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load 2D PSF data and return radius, depth, and intensity arrays"""
        df = self.load_psf_data(data_path)
        
        # Assuming columns are: radius, depth, energy or intensity
        if len(df.columns) >= 3:
            radius = df.iloc[:, 0].values
            depth = df.iloc[:, 1].values
            intensity = df.iloc[:, 2].values
            return radius, depth, intensity
        else:
            raise ValueError("PSF data must have at least 3 columns (radius, depth, intensity)")
    
    def export_beamer_format(self, psf_data: pd.DataFrame, output_path: Path, 
                           pixel_size: float = 1.0) -> None:
        """Export PSF data in BEAMER format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            # BEAMER header
            f.write(f"# BEAMER PSF file\n")
            f.write(f"# Pixel size: {pixel_size} nm\n")
            f.write(f"# Data points: {len(psf_data)}\n")
            f.write("#\n")
            
            # Data export
            for _, row in psf_data.iterrows():
                if len(row) >= 2:
                    radius = row.iloc[0]
                    intensity = row.iloc[1] if len(row) > 1 else row.iloc[0]
                    f.write(f"{radius:.6f}\t{intensity:.6e}\n")
    
    def validate_psf_file(self, data_path: Path) -> Tuple[bool, str]:
        """Validate PSF data file"""
        try:
            if not data_path.exists():
                return False, "File does not exist"
            
            if data_path.suffix not in self.supported_formats:
                return False, f"Unsupported file format: {data_path.suffix}"
            
            df = self.load_psf_data(data_path)
            
            if df.empty:
                return False, "File is empty"
            
            if len(df.columns) < 2:
                return False, "File must have at least 2 columns"
            
            # Check for numeric data
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) < 2:
                return False, "File must contain numeric data"
            
            return True, "Valid PSF file"
            
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def get_file_info(self, data_path: Path) -> Dict[str, Any]:
        """Get information about a data file"""
        if not data_path.exists():
            return {"exists": False}
        
        try:
            df = self.load_psf_data(data_path)
            return {
                "exists": True,
                "size_bytes": data_path.stat().st_size,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "data_types": df.dtypes.to_dict(),
                "file_format": data_path.suffix
            }
        except Exception as e:
            return {
                "exists": True,
                "error": str(e),
                "size_bytes": data_path.stat().st_size
            }
    
    def find_output_files(self, output_dir: Path, prefix: str = "") -> List[Path]:
        """Find all output files in directory matching prefix"""
        if not output_dir.exists():
            return []
        
        pattern = f"{prefix}*" if prefix else "*"
        files = []
        
        for ext in self.supported_formats:
            files.extend(output_dir.glob(f"{pattern}{ext}"))
        
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    def backup_file(self, file_path: Path, backup_dir: Optional[Path] = None) -> Path:
        """Create backup of file"""
        if backup_dir is None:
            backup_dir = file_path.parent / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = file_path.stat().st_mtime
        backup_name = f"{file_path.stem}_{int(timestamp)}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        
        backup_path.write_bytes(file_path.read_bytes())
        return backup_path