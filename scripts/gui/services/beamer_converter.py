"""
BEAMER format conversion service
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import scipy.interpolate


class BeamerConverterService:
    """Service for converting PSF data to BEAMER format"""
    
    def __init__(self):
        self.default_pixel_size = 1.0  # nm
        self.default_grid_size = 256
    
    def convert_psf_to_beamer(
        self, 
        psf_data: pd.DataFrame, 
        output_path: Path,
        pixel_size: float = 1.0,
        grid_size: int = 256,
        normalize: bool = True
    ) -> bool:
        """Convert PSF data to BEAMER format"""
        try:
            # Extract radius and intensity data
            if len(psf_data.columns) < 2:
                raise ValueError("PSF data must have at least 2 columns (radius, intensity)")
            
            radius = psf_data.iloc[:, 0].values
            intensity = psf_data.iloc[:, 1].values
            
            # Remove invalid data points
            valid_mask = (radius >= 0) & (intensity >= 0) & np.isfinite(radius) & np.isfinite(intensity)
            radius = radius[valid_mask]
            intensity = intensity[valid_mask]
            
            if len(radius) == 0:
                raise ValueError("No valid data points found")
            
            # Sort by radius
            sort_indices = np.argsort(radius)
            radius = radius[sort_indices]
            intensity = intensity[sort_indices]
            
            # Normalize if requested
            if normalize and np.max(intensity) > 0:
                intensity = intensity / np.max(intensity)
            
            # Interpolate to regular grid
            max_radius = np.max(radius)
            beamer_radius = np.linspace(0, max_radius, grid_size)
            
            # Use interpolation for smooth PSF
            interpolator = scipy.interpolate.interp1d(
                radius, intensity, 
                kind='linear', 
                bounds_error=False, 
                fill_value=0.0
            )
            beamer_intensity = interpolator(beamer_radius)
            
            # Ensure non-negative values
            beamer_intensity = np.maximum(beamer_intensity, 0.0)
            
            # Save BEAMER format
            self._save_beamer_file(beamer_radius, beamer_intensity, output_path, pixel_size)
            
            return True
            
        except Exception as e:
            print(f"Error converting to BEAMER format: {e}")
            return False
    
    def _save_beamer_file(
        self, 
        radius: np.ndarray, 
        intensity: np.ndarray, 
        output_path: Path,
        pixel_size: float
    ):
        """Save data in BEAMER format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            # BEAMER header
            f.write("# BEAMER Point Spread Function\n")
            f.write(f"# Pixel size: {pixel_size:.3f} nm\n")
            f.write(f"# Grid points: {len(radius)}\n")
            f.write(f"# Max radius: {np.max(radius):.3f} nm\n")
            f.write("# Format: radius[nm] intensity[normalized]\n")
            f.write("#\n")
            
            # Data
            for r, i in zip(radius, intensity):
                f.write(f"{r:.6f}\t{i:.6e}\n")
    
    def convert_2d_psf_to_beamer(
        self,
        radius: np.ndarray,
        depth: np.ndarray, 
        intensity: np.ndarray,
        output_path: Path,
        pixel_size: float = 1.0,
        integrate_depth: bool = True
    ) -> bool:
        """Convert 2D PSF data to BEAMER format"""
        try:
            if integrate_depth:
                # Integrate over depth to get radial PSF
                radial_psf = self._integrate_radial_psf(radius, depth, intensity)
                return self.convert_psf_to_beamer(radial_psf, output_path, pixel_size)
            else:
                # Save 2D PSF (custom format)
                return self._save_2d_beamer_file(radius, depth, intensity, output_path, pixel_size)
                
        except Exception as e:
            print(f"Error converting 2D PSF to BEAMER format: {e}")
            return False
    
    def _integrate_radial_psf(
        self, 
        radius: np.ndarray, 
        depth: np.ndarray, 
        intensity: np.ndarray
    ) -> pd.DataFrame:
        """Integrate 2D PSF over depth to get radial profile"""
        # Create DataFrame for easier manipulation
        df = pd.DataFrame({
            'radius': radius,
            'depth': depth,
            'intensity': intensity
        })
        
        # Group by radius and sum intensities
        radial_profile = df.groupby('radius')['intensity'].sum().reset_index()
        
        return radial_profile
    
    def _save_2d_beamer_file(
        self,
        radius: np.ndarray,
        depth: np.ndarray,
        intensity: np.ndarray,
        output_path: Path,
        pixel_size: float
    ) -> bool:
        """Save 2D PSF in extended BEAMER format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                # Extended BEAMER header for 2D data
                f.write("# BEAMER 2D Point Spread Function\n")
                f.write(f"# Pixel size: {pixel_size:.3f} nm\n")
                f.write(f"# Data points: {len(radius)}\n")
                f.write(f"# Max radius: {np.max(radius):.3f} nm\n")
                f.write(f"# Max depth: {np.max(depth):.3f} nm\n")
                f.write("# Format: radius[nm] depth[nm] intensity[a.u.]\n")
                f.write("#\n")
                
                # Data
                for r, d, i in zip(radius, depth, intensity):
                    f.write(f"{r:.6f}\t{d:.6f}\t{i:.6e}\n")
                    
            return True
            
        except Exception as e:
            print(f"Error saving 2D BEAMER file: {e}")
            return False
    
    def validate_beamer_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validate BEAMER format file"""
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            if len(lines) < 5:
                return False, "File too short"
            
            # Check header
            if not lines[0].startswith("# BEAMER"):
                return False, "Missing BEAMER header"
            
            # Count data lines
            data_lines = [line for line in lines if not line.startswith('#') and line.strip()]
            
            if len(data_lines) == 0:
                return False, "No data found"
            
            # Validate data format
            for i, line in enumerate(data_lines[:5]):  # Check first 5 lines
                parts = line.strip().split()
                if len(parts) < 2:
                    return False, f"Invalid data format at line {i+1}"
                
                try:
                    float(parts[0])  # radius
                    float(parts[1])  # intensity
                except ValueError:
                    return False, f"Non-numeric data at line {i+1}"
            
            return True, f"Valid BEAMER file with {len(data_lines)} data points"
            
        except Exception as e:
            return False, f"Error validating file: {str(e)}"
    
    def get_beamer_info(self, file_path: Path) -> Dict[str, Any]:
        """Get information about BEAMER file"""
        info = {
            "valid": False,
            "pixel_size": None,
            "data_points": 0,
            "max_radius": None,
            "format": "unknown"
        }
        
        try:
            is_valid, message = self.validate_beamer_file(file_path)
            info["valid"] = is_valid
            info["message"] = message
            
            if not is_valid:
                return info
            
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Parse header information
            for line in lines:
                if line.startswith("# Pixel size:"):
                    try:
                        pixel_size = float(line.split(":")[1].split()[0])
                        info["pixel_size"] = pixel_size
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("# Max radius:"):
                    try:
                        max_radius = float(line.split(":")[1].split()[0])
                        info["max_radius"] = max_radius
                    except (ValueError, IndexError):
                        pass
            
            # Count data points
            data_lines = [line for line in lines if not line.startswith('#') and line.strip()]
            info["data_points"] = len(data_lines)
            
            # Determine format (1D or 2D)
            if data_lines:
                first_line_parts = data_lines[0].strip().split()
                if len(first_line_parts) == 2:
                    info["format"] = "1D (radius, intensity)"
                elif len(first_line_parts) == 3:
                    info["format"] = "2D (radius, depth, intensity)"
                else:
                    info["format"] = f"Unknown ({len(first_line_parts)} columns)"
            
        except Exception as e:
            info["error"] = str(e)
        
        return info