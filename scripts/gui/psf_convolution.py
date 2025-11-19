#!/usr/bin/env python3
"""
PSF Convolution Module for Pattern Dose Calculation
Efficiently calculates dose distribution by convolving PSF with pattern
"""

import numpy as np
import pandas as pd
from scipy import signal, ndimage
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import logging

class PSFConvolution:
    """Handles PSF-based pattern dose calculations"""

    def __init__(self, psf_file=None):
        """Initialize with optional PSF file"""
        self.psf_data = None
        self.psf_radial = None
        self.psf_2d = None
        self.dose_map = None

        if psf_file:
            self.load_psf(psf_file)

    def load_psf(self, psf_file):
        """Load PSF data from CSV file"""
        try:
            # Read PSF data
            df = pd.read_csv(psf_file)

            # Extract radius and energy deposition
            self.psf_radial = {
                'radius': df['Radius(nm)'].values,
                'energy': df['EnergyDeposition(eV/nm^2)'].values
            }

            logging.info(f"Loaded PSF with {len(df)} radial bins")
            logging.info(f"PSF range: {df['Radius(nm)'].min():.2f} - {df['Radius(nm)'].max():.2f} nm")

        except Exception as e:
            logging.error(f"Error loading PSF: {e}")
            raise

    def radial_to_2d(self, max_radius_nm=100000, grid_size_nm=100):
        """
        Convert radial PSF to 2D grid

        Args:
            max_radius_nm: Maximum radius to consider (nm)
            grid_size_nm: Grid spacing (nm)
        """
        if self.psf_radial is None:
            raise ValueError("No PSF data loaded")

        # Create 2D grid
        n_points = int(2 * max_radius_nm / grid_size_nm) + 1
        center = n_points // 2

        # Initialize 2D PSF array
        psf_2d = np.zeros((n_points, n_points))

        # Create coordinate grids
        x = np.arange(n_points) - center
        y = np.arange(n_points) - center
        xx, yy = np.meshgrid(x * grid_size_nm, y * grid_size_nm)
        rr = np.sqrt(xx**2 + yy**2)

        # Interpolate radial PSF onto 2D grid
        from scipy.interpolate import interp1d

        # Create interpolation function (log-scale for better accuracy)
        # Handle zero/negative values
        mask = self.psf_radial['energy'] > 0
        r_valid = self.psf_radial['radius'][mask]
        e_valid = self.psf_radial['energy'][mask]

        if len(r_valid) > 1:
            # Use log interpolation for better accuracy in tails
            psf_interp = interp1d(r_valid, np.log10(e_valid + 1e-30),
                                  kind='linear', bounds_error=False,
                                  fill_value=-30)  # Very small value outside

            # Apply to 2D grid
            rr_flat = rr.flatten()
            psf_flat = np.zeros(len(rr_flat))

            # Only interpolate within valid radius range
            valid_mask = (rr_flat >= r_valid[0]) & (rr_flat <= r_valid[-1])
            psf_flat[valid_mask] = 10**psf_interp(rr_flat[valid_mask]) - 1e-30

            psf_2d = psf_flat.reshape(n_points, n_points)

        # Normalize PSF (should sum to 1 for convolution)
        psf_sum = psf_2d.sum()
        if psf_sum > 0:
            psf_2d /= psf_sum

        self.psf_2d = psf_2d
        self.grid_size_nm = grid_size_nm

        logging.info(f"Created 2D PSF: {n_points}x{n_points} grid, {grid_size_nm} nm spacing")

        return psf_2d

    def create_square_pattern(self, size_um=100, dose_uc_cm2=500, shot_pitch_nm=34):
        """
        Create a square pattern with uniform dose

        Args:
            size_um: Square size in micrometers
            dose_uc_cm2: Dose in µC/cm²
            shot_pitch_nm: Shot pitch in nm

        Returns:
            2D array of dose values
        """
        size_nm = size_um * 1000

        # Calculate pattern grid
        n_shots = int(size_nm / shot_pitch_nm)

        # Create pattern array (larger to accommodate PSF spreading)
        margin_nm = 100000  # 100 µm margin for PSF tails
        total_size_nm = size_nm + 2 * margin_nm

        # Match PSF grid if available
        if hasattr(self, 'grid_size_nm'):
            grid_size = self.grid_size_nm
        else:
            grid_size = 100  # Default 100 nm grid

        n_points = int(total_size_nm / grid_size) + 1
        pattern = np.zeros((n_points, n_points))

        # Calculate center and boundaries of square
        center = n_points // 2
        half_size = int(size_nm / (2 * grid_size))

        # Set uniform dose in square region
        # Convert µC/cm² to normalized dose for convolution
        # The PSF should be normalized so that convolution preserves dose
        pattern[center-half_size:center+half_size,
                center-half_size:center+half_size] = dose_uc_cm2

        self.pattern = pattern
        self.pattern_info = {
            'size_um': size_um,
            'dose_uc_cm2': dose_uc_cm2,
            'shot_pitch_nm': shot_pitch_nm,
            'n_shots_per_side': n_shots,
            'total_shots': n_shots * n_shots
        }

        logging.info(f"Created {size_um}µm square pattern: {n_shots}x{n_shots} shots")

        return pattern

    def convolve_pattern(self, pattern=None, psf_2d=None):
        """
        Convolve pattern with PSF to get dose distribution

        Args:
            pattern: 2D pattern array (uses self.pattern if None)
            psf_2d: 2D PSF array (uses self.psf_2d if None)
        """
        if pattern is None:
            pattern = self.pattern
        if psf_2d is None:
            psf_2d = self.psf_2d

        if pattern is None or psf_2d is None:
            raise ValueError("Pattern and PSF must be loaded/created first")

        logging.info("Performing 2D convolution...")

        # Use FFT convolution for speed with large arrays
        self.dose_map = signal.fftconvolve(pattern, psf_2d, mode='same')

        logging.info(f"Convolution complete. Dose range: {self.dose_map.min():.2e} - {self.dose_map.max():.2e}")

        return self.dose_map

    def plot_2d_dose(self, figsize=(12, 10), save_path=None):
        """Create 2D visualization of dose distribution"""
        if self.dose_map is None:
            raise ValueError("No dose map calculated yet")

        fig, axes = plt.subplots(2, 2, figsize=figsize)

        # Convert to physical units
        extent_um = np.array([-self.dose_map.shape[0]/2, self.dose_map.shape[0]/2,
                              -self.dose_map.shape[1]/2, self.dose_map.shape[1]/2]) * self.grid_size_nm / 1000

        # 1. Full dose map (log scale)
        im1 = axes[0, 0].imshow(np.log10(self.dose_map + 1e-10),
                                extent=extent_um, cmap='hot')
        axes[0, 0].set_title('Full Dose Map (log scale)')
        axes[0, 0].set_xlabel('X (µm)')
        axes[0, 0].set_ylabel('Y (µm)')
        plt.colorbar(im1, ax=axes[0, 0], label='log₁₀(Dose)')

        # 2. Zoomed center (linear scale)
        center = self.dose_map.shape[0] // 2
        zoom_range = int(60000 / self.grid_size_nm)  # ±60 µm

        dose_center = self.dose_map[center-zoom_range:center+zoom_range,
                                    center-zoom_range:center+zoom_range]

        extent_zoom = np.array([-zoom_range, zoom_range,
                               -zoom_range, zoom_range]) * self.grid_size_nm / 1000

        im2 = axes[0, 1].imshow(dose_center, extent=extent_zoom, cmap='viridis')
        axes[0, 1].set_title('Center Region (linear scale)')
        axes[0, 1].set_xlabel('X (µm)')
        axes[0, 1].set_ylabel('Y (µm)')
        plt.colorbar(im2, ax=axes[0, 1], label='Dose (µC/cm²)')

        # Add square boundary
        if hasattr(self, 'pattern_info'):
            half_size = self.pattern_info['size_um'] / 2
            rect = plt.Rectangle((-half_size, -half_size),
                                self.pattern_info['size_um'],
                                self.pattern_info['size_um'],
                                fill=False, edgecolor='red', linewidth=2)
            axes[0, 1].add_patch(rect)

        # 3. Horizontal line cut through center
        line_cut_h = self.dose_map[center, :]
        x_um = (np.arange(len(line_cut_h)) - center) * self.grid_size_nm / 1000

        axes[1, 0].plot(x_um, line_cut_h)
        axes[1, 0].set_title('Horizontal Cut Through Center')
        axes[1, 0].set_xlabel('X (µm)')
        axes[1, 0].set_ylabel('Dose (µC/cm²)')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].set_xlim(-150, 150)

        # Add vertical lines for square edges
        if hasattr(self, 'pattern_info'):
            half_size = self.pattern_info['size_um'] / 2
            axes[1, 0].axvline(-half_size, color='red', linestyle='--', alpha=0.5)
            axes[1, 0].axvline(half_size, color='red', linestyle='--', alpha=0.5)

        # 4. Statistics and analysis
        axes[1, 1].axis('off')

        # Calculate statistics
        if hasattr(self, 'pattern_info'):
            half_size_px = int(self.pattern_info['size_um'] * 1000 / (2 * self.grid_size_nm))

            # Dose inside square
            dose_inside = self.dose_map[center-half_size_px:center+half_size_px,
                                       center-half_size_px:center+half_size_px]

            # Dose in surrounding region (±10 µm)
            margin_px = int(10000 / self.grid_size_nm)  # 10 µm
            dose_surround = self.dose_map[center-half_size_px-margin_px:center+half_size_px+margin_px,
                                         center-half_size_px-margin_px:center+half_size_px+margin_px]

            stats_text = f"""Pattern Statistics:

Square: {self.pattern_info['size_um']} × {self.pattern_info['size_um']} µm
Target Dose: {self.pattern_info['dose_uc_cm2']:.1f} µC/cm²
Shot Pitch: {self.pattern_info['shot_pitch_nm']} nm
Total Shots: {self.pattern_info['total_shots']:,}

Actual Dose Distribution:
Inside Square:
  Center: {self.dose_map[center, center]:.1f} µC/cm²
  Mean: {dose_inside.mean():.1f} µC/cm²
  Min: {dose_inside.min():.1f} µC/cm²
  Max: {dose_inside.max():.1f} µC/cm²
  Std: {dose_inside.std():.1f} µC/cm²

Edge Effects:
  Center/Edge Ratio: {self.dose_map[center, center] / dose_inside.min():.2f}
  Uniformity: {(1 - dose_inside.std()/dose_inside.mean())*100:.1f}%

Proximity Effect (10 µm outside):
  Mean Dose: {dose_surround.mean():.1f} µC/cm²
  Max Dose: {dose_surround.max():.1f} µC/cm²
  % of Target: {dose_surround.mean() / self.pattern_info['dose_uc_cm2'] * 100:.1f}%
"""
        else:
            stats_text = "Pattern statistics not available"

        axes[1, 1].text(0.1, 0.9, stats_text, transform=axes[1, 1].transAxes,
                       fontsize=10, verticalalignment='top', family='monospace')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logging.info(f"Saved 2D dose plot to {save_path}")

        return fig

    def plot_3d_dose(self, figsize=(14, 10), save_path=None):
        """Create 3D visualization of dose distribution"""
        if self.dose_map is None:
            raise ValueError("No dose map calculated yet")

        fig = plt.figure(figsize=figsize)

        # Create two 3D subplots
        ax1 = fig.add_subplot(121, projection='3d')
        ax2 = fig.add_subplot(122, projection='3d')

        # Downsample for 3D plotting (too many points slow down rendering)
        downsample = 5
        dose_down = self.dose_map[::downsample, ::downsample]

        # Create mesh
        x = np.arange(dose_down.shape[0]) * downsample * self.grid_size_nm / 1000
        y = np.arange(dose_down.shape[1]) * downsample * self.grid_size_nm / 1000

        # Center the coordinates
        x = x - x.mean()
        y = y - y.mean()

        X, Y = np.meshgrid(x, y)

        # Plot 1: Full 3D surface
        surf1 = ax1.plot_surface(X, Y, dose_down, cmap='viridis',
                                 edgecolor='none', alpha=0.9)
        ax1.set_title('3D Dose Distribution')
        ax1.set_xlabel('X (µm)')
        ax1.set_ylabel('Y (µm)')
        ax1.set_zlabel('Dose (µC/cm²)')
        ax1.view_init(elev=30, azim=45)

        # Plot 2: Zoomed center with contours
        center = dose_down.shape[0] // 2
        zoom_range = int(60000 / (self.grid_size_nm * downsample))

        dose_center = dose_down[center-zoom_range:center+zoom_range,
                               center-zoom_range:center+zoom_range]

        x_zoom = np.arange(dose_center.shape[0]) * downsample * self.grid_size_nm / 1000
        y_zoom = np.arange(dose_center.shape[1]) * downsample * self.grid_size_nm / 1000
        x_zoom = x_zoom - x_zoom.mean()
        y_zoom = y_zoom - y_zoom.mean()

        X_zoom, Y_zoom = np.meshgrid(x_zoom, y_zoom)

        # Add contour plot at base
        levels = np.linspace(dose_center.min(), dose_center.max(), 20)
        ax2.contour(X_zoom, Y_zoom, dose_center, levels=levels,
                    cmap='plasma', linewidths=0.5, alpha=0.5, offset=0)

        surf2 = ax2.plot_surface(X_zoom, Y_zoom, dose_center, cmap='plasma',
                                 edgecolor='none', alpha=0.8)

        ax2.set_title('Center Region with Contours')
        ax2.set_xlabel('X (µm)')
        ax2.set_ylabel('Y (µm)')
        ax2.set_zlabel('Dose (µC/cm²)')
        ax2.view_init(elev=25, azim=60)

        # Add colorbars
        fig.colorbar(surf1, ax=ax1, shrink=0.5, aspect=5, pad=0.1)
        fig.colorbar(surf2, ax=ax2, shrink=0.5, aspect=5, pad=0.1)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logging.info(f"Saved 3D dose plot to {save_path}")

        return fig


def analyze_square_pattern(psf_file, size_um=100, dose_uc_cm2=500, shot_pitch_nm=34,
                          output_dir=None):
    """
    Complete analysis of square pattern dose distribution

    Args:
        psf_file: Path to PSF CSV file
        size_um: Square size in micrometers
        dose_uc_cm2: Nominal dose in µC/cm²
        shot_pitch_nm: Shot pitch in nm
        output_dir: Directory for output files
    """
    import os

    # Setup logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    # Create output directory
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

    # Initialize convolution engine
    logging.info("Initializing PSF convolution engine...")
    conv = PSFConvolution(psf_file)

    # Convert radial PSF to 2D
    logging.info("Converting radial PSF to 2D...")
    conv.radial_to_2d(max_radius_nm=150000, grid_size_nm=100)

    # Create square pattern
    logging.info(f"Creating {size_um}µm square pattern...")
    conv.create_square_pattern(size_um=size_um, dose_uc_cm2=dose_uc_cm2,
                               shot_pitch_nm=shot_pitch_nm)

    # Perform convolution
    logging.info("Calculating dose distribution via convolution...")
    conv.convolve_pattern()

    # Generate visualizations
    logging.info("Creating 2D visualization...")
    fig_2d = conv.plot_2d_dose(save_path=output_dir / f"dose_2d_{size_um}um.png")

    logging.info("Creating 3D visualization...")
    fig_3d = conv.plot_3d_dose(save_path=output_dir / f"dose_3d_{size_um}um.png")

    # Save dose map data
    dose_file = output_dir / f"dose_map_{size_um}um.npy"
    np.save(dose_file, conv.dose_map)
    logging.info(f"Saved dose map to {dose_file}")

    plt.show()

    return conv


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        psf_file = sys.argv[1]
    else:
        # Default PSF file
        psf_file = "psf_snmld_10k.csv"

    # Analyze 100 µm square with no proximity correction
    analyze_square_pattern(
        psf_file=psf_file,
        size_um=100,
        dose_uc_cm2=500,
        shot_pitch_nm=34,
        output_dir="pattern_analysis"
    )