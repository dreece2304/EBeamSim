#!/usr/bin/env python3
"""
BEAMER PSF Format Converter
Consolidates all BEAMER conversion functionality into a single reusable class
"""

import numpy as np
import pandas as pd
from pathlib import Path
import re


class BEAMERConverter:
    """Handles conversion of EBL simulation PSF data to BEAMER format"""
    
    def __init__(self):
        self.psf_data = None
        self.alpha = None
        self.beta = None
        self.eta = None
        
    def load_psf_data(self, filepath):
        """Load PSF data from CSV file"""
        try:
            self.psf_data = pd.read_csv(filepath)
            return True
        except Exception as e:
            print(f"Error loading PSF data: {e}")
            return False
    
    def extract_parameters(self):
        """Extract BEAMER parameters (alpha, beta, eta) from PSF data"""
        if self.psf_data is None:
            return False
            
        try:
            # Get radius and energy deposition
            radius = self.psf_data['Radius(nm)'].values
            energy = self.psf_data['EnergyDeposition(eV/nm^2)'].values
            
            # Remove any NaN or invalid values
            mask = ~np.isnan(energy) & (energy > 0)
            radius = radius[mask]
            energy = energy[mask]
            
            if len(radius) == 0:
                return False
            
            # Calculate total energy
            total_energy = np.sum(energy)
            if total_energy == 0:
                return False
            
            # Normalize PSF
            psf_normalized = energy / total_energy
            
            # Calculate alpha (forward scatter fraction)
            # Typically within first 100-200 nm
            forward_mask = radius <= 200  # nm
            self.alpha = np.sum(psf_normalized[forward_mask])
            
            # Beta is backscatter fraction
            self.beta = 1.0 - self.alpha
            
            # Eta is the characteristic backscatter range
            # Use weighted average of backscatter region
            back_mask = radius > 200
            if np.sum(psf_normalized[back_mask]) > 0:
                self.eta = np.average(radius[back_mask], weights=psf_normalized[back_mask])
            else:
                self.eta = 1000  # Default 1 um
                
            return True
            
        except Exception as e:
            print(f"Error extracting parameters: {e}")
            return False
    
    def convert_to_beamer(self, input_file, output_file=None, 
                         beam_energy=None, resist_thickness=None,
                         alpha=None, beta=None, eta=None):
        """
        Convert PSF data to BEAMER format
        
        Args:
            input_file: Path to PSF CSV file
            output_file: Output path (optional, auto-generated if None)
            beam_energy: Beam energy in keV
            resist_thickness: Resist thickness in nm
            alpha: Forward scatter fraction (optional, auto-calculated if None)
            beta: Backscatter fraction (optional, auto-calculated if None)
            eta: Backscatter range in nm (optional, auto-calculated if None)
        """
        # Load data
        if not self.load_psf_data(input_file):
            return None
            
        # Extract parameters if not provided
        if alpha is None or beta is None or eta is None:
            if not self.extract_parameters():
                return None
        else:
            self.alpha = alpha
            self.beta = beta
            self.eta = eta
            
        # Generate output filename if not provided
        if output_file is None:
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_beamer.psf"
            
        # Extract beam energy and resist thickness from filename if not provided
        if beam_energy is None or resist_thickness is None:
            params = self._extract_params_from_filename(input_file)
            if beam_energy is None:
                beam_energy = params.get('energy', 100)
            if resist_thickness is None:
                resist_thickness = params.get('thickness', 30)
        
        # Write BEAMER format file
        try:
            with open(output_file, 'w') as f:
                f.write("; PSF for BEAMER - Generated from EBL simulation\n")
                f.write(f"; Beam Energy: {beam_energy} keV\n")
                f.write(f"; Resist Thickness: {resist_thickness} nm\n")
                f.write(";\n")
                f.write("; Two-Gaussian model parameters:\n")
                f.write(f"; alpha (forward scatter): {self.alpha:.6f}\n")
                f.write(f"; beta (backscatter): {self.beta:.6f}\n")
                f.write(f"; eta (backscatter range): {self.eta:.1f} nm\n")
                f.write(";\n")
                f.write("PSF 2 GAUSSIAN\n")
                f.write(f"{self.alpha:.6f} 1.0 {self.beta:.6f} {self.eta:.1f}\n")
                
            return str(output_file)
            
        except Exception as e:
            print(f"Error writing BEAMER file: {e}")
            return None
    
    def _extract_params_from_filename(self, filename):
        """Extract simulation parameters from filename"""
        params = {}
        filename = str(Path(filename).stem)
        
        # Try to extract energy (keV)
        energy_match = re.search(r'(\d+)keV', filename)
        if energy_match:
            params['energy'] = int(energy_match.group(1))
            
        # Try to extract thickness (nm)
        thickness_match = re.search(r'(\d+)nm', filename)
        if thickness_match:
            params['thickness'] = int(thickness_match.group(1))
            
        return params
    
    def get_parameters_dict(self):
        """Return current parameters as dictionary"""
        return {
            'alpha': self.alpha,
            'beta': self.beta,
            'eta': self.eta
        }
    
    def analyze_psf_quality(self):
        """Analyze PSF data quality and return diagnostics"""
        if self.psf_data is None:
            return None
            
        diagnostics = {
            'total_points': len(self.psf_data),
            'min_radius': self.psf_data['Radius(nm)'].min(),
            'max_radius': self.psf_data['Radius(nm)'].max(),
            'total_energy': self.psf_data['EnergyDeposition(eV/nm^2)'].sum(),
            'zero_values': (self.psf_data['EnergyDeposition(eV/nm^2)'] == 0).sum(),
            'parameters': self.get_parameters_dict()
        }
        
        return diagnostics


# Example usage functions for backward compatibility
def convert_psf_to_beamer(input_file, output_file=None, **kwargs):
    """Convenience function for direct conversion"""
    converter = BEAMERConverter()
    return converter.convert_to_beamer(input_file, output_file, **kwargs)


def extract_beamer_parameters(psf_file):
    """Convenience function to extract parameters"""
    converter = BEAMERConverter()
    if converter.load_psf_data(psf_file) and converter.extract_parameters():
        return converter.get_parameters_dict()
    return None


if __name__ == "__main__":
    # Test the converter
    import sys
    if len(sys.argv) > 1:
        result = convert_psf_to_beamer(sys.argv[1])
        if result:
            print(f"Converted to: {result}")
        else:
            print("Conversion failed")