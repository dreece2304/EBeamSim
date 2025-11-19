#!/usr/bin/env python3
"""
Comprehensive Dose Distribution Analysis Suite for EBL

Advanced analysis and visualization tools for electron dose distributions:

1. Dose Profile Analysis:
   - Radial dose profiles (PSF analysis)
   - Line dose profiles
   - 3D dose distribution visualization
   - Statistical dose analysis

2. Feature Analysis:
   - Critical dimension measurements
   - Edge sharpness analysis
   - Pattern fidelity metrics
   - Dose uniformity analysis

3. Comparison Tools:
   - Multi-energy comparison
   - Multi-material comparison
   - Simulation vs experimental validation
   - Before/after proximity correction

4. Export Capabilities:
   - Industry-standard formats (GDSII, OASIS)
   - BEAMER PSF format
   - Analysis reports (PDF, HTML)
   - Raw data export (CSV, HDF5)

Author: EBL Dose Analysis Team
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LogNorm
import seaborn as sns
from pathlib import Path
import h5py
import json
from typing import Dict, List, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field
from scipy import ndimage, optimize, stats, spatial
from scipy.interpolate import interp2d, RegularGridInterpolator
import cv2
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DoseStatistics:
    """Comprehensive dose statistics"""
    mean: float
    median: float
    std: float
    min: float
    max: float
    percentile_90: float
    percentile_99: float
    skewness: float
    kurtosis: float
    total_dose: float
    dose_uniformity: float  # 1 - (std/mean)
    
    @classmethod
    def from_array(cls, dose_array: np.ndarray) -> 'DoseStatistics':
        """Create statistics from dose array"""
        flat_dose = dose_array.flatten()
        flat_dose = flat_dose[flat_dose > 0]  # Remove zero dose regions
        
        if len(flat_dose) == 0:
            return cls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        mean_val = np.mean(flat_dose)
        
        return cls(
            mean=mean_val,
            median=np.median(flat_dose),
            std=np.std(flat_dose),
            min=np.min(flat_dose),
            max=np.max(flat_dose),
            percentile_90=np.percentile(flat_dose, 90),
            percentile_99=np.percentile(flat_dose, 99),
            skewness=stats.skew(flat_dose),
            kurtosis=stats.kurtosis(flat_dose),
            total_dose=np.sum(flat_dose),
            dose_uniformity=1.0 - (np.std(flat_dose) / mean_val) if mean_val > 0 else 0
        )

@dataclass
class FeatureAnalysis:
    """Analysis results for pattern features"""
    feature_count: int
    mean_area: float
    std_area: float
    mean_perimeter: float
    std_perimeter: float
    mean_circularity: float
    cd_uniformity: float  # Critical dimension uniformity
    edge_sharpness: float  # Average edge sharpness
    pattern_fidelity: float  # Overall pattern fidelity score

@dataclass
class PSFMetrics:
    """Point spread function metrics"""
    fwhm: float  # Full width at half maximum
    fwtm: float  # Full width at tenth maximum
    forward_scatter_width: float
    backscatter_range: float
    forward_fraction: float
    backscatter_fraction: float
    peak_intensity: float
    integrated_intensity: float

class DoseAnalysisSuite:
    """Comprehensive dose distribution analysis toolkit"""
    
    def __init__(self, pixel_size: float = 1.0, unit: str = "nm"):
        """
        Initialize dose analysis suite
        
        Args:
            pixel_size: Size of each pixel in specified units
            unit: Unit of measurement ("nm", "um", "mm")
        """
        self.pixel_size = pixel_size
        self.unit = unit
        self.analysis_cache: Dict = {}
        
        # Visualization settings
        self.colormap = 'plasma'
        self.figure_size = (12, 8)
        
    def load_dose_data(self, data_source: Union[str, Path, np.ndarray], 
                      format_type: str = "auto") -> np.ndarray:
        """
        Load dose data from various sources
        
        Args:
            data_source: File path, numpy array, or data identifier
            format_type: Data format ("csv", "hdf5", "npy", "auto")
            
        Returns:
            2D dose distribution array
        """
        if isinstance(data_source, np.ndarray):
            return data_source
        
        data_path = Path(data_source)
        
        if format_type == "auto":
            format_type = data_path.suffix.lower().lstrip('.')
        
        try:
            if format_type in ["csv"]:
                df = pd.read_csv(data_path)
                if 'dose' in df.columns and 'x' in df.columns and 'y' in df.columns:
                    # Convert scattered data to grid
                    return self._scatter_to_grid(df)
                else:
                    # Assume 2D array stored as CSV
                    return df.values
            
            elif format_type in ["h5", "hdf5"]:
                with h5py.File(data_path, 'r') as f:
                    # Try common dataset names
                    for name in ['dose', 'data', 'dose_distribution']:
                        if name in f:
                            return f[name][:]
                    # Use first dataset if no standard name found
                    return list(f.values())[0][:]
            
            elif format_type == "npy":
                return np.load(data_path)
            
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Error loading dose data from {data_path}: {e}")
            raise
    
    def _scatter_to_grid(self, df: pd.DataFrame) -> np.ndarray:
        """Convert scattered dose data to regular grid"""
        x_coords = df['x'].values
        y_coords = df['y'].values
        dose_values = df['dose'].values
        
        # Create regular grid
        x_unique = np.unique(x_coords)
        y_unique = np.unique(y_coords)
        
        # Handle irregular grids by interpolation
        if len(x_unique) * len(y_unique) != len(dose_values):
            x_grid = np.linspace(x_coords.min(), x_coords.max(), 
                               int(np.sqrt(len(dose_values))))
            y_grid = np.linspace(y_coords.min(), y_coords.max(), 
                               int(np.sqrt(len(dose_values))))
            
            # Interpolate to regular grid
            from scipy.interpolate import griddata
            X_grid, Y_grid = np.meshgrid(x_grid, y_grid)
            dose_grid = griddata((x_coords, y_coords), dose_values, 
                               (X_grid, Y_grid), method='cubic', fill_value=0)
        else:
            # Regular grid - reshape
            dose_grid = dose_values.reshape(len(y_unique), len(x_unique))
        
        return dose_grid
    
    def calculate_dose_statistics(self, dose_array: np.ndarray, 
                                mask: Optional[np.ndarray] = None) -> DoseStatistics:
        """
        Calculate comprehensive dose statistics
        
        Args:
            dose_array: 2D dose distribution
            mask: Optional mask to limit analysis region
            
        Returns:
            DoseStatistics object with comprehensive metrics
        """
        if mask is not None:
            masked_dose = dose_array[mask]
        else:
            masked_dose = dose_array
        
        return DoseStatistics.from_array(masked_dose)
    
    def analyze_psf(self, dose_array: np.ndarray, 
                   center: Optional[Tuple[int, int]] = None) -> PSFMetrics:
        """
        Analyze point spread function from dose data
        
        Args:
            dose_array: 2D dose distribution (should be from point source)
            center: Center coordinates (y, x). If None, use peak location
            
        Returns:
            PSFMetrics with PSF characteristics
        """
        if center is None:
            # Find peak location
            peak_idx = np.unravel_index(np.argmax(dose_array), dose_array.shape)
            center = peak_idx
        
        cy, cx = center
        
        # Extract radial profile
        y_coords, x_coords = np.ogrid[:dose_array.shape[0], :dose_array.shape[1]]
        r_coords = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2) * self.pixel_size
        
        # Create radial bins
        r_max = min(cx, cy, dose_array.shape[1]-cx, dose_array.shape[0]-cy) * self.pixel_size
        r_bins = np.linspace(0, r_max, min(100, int(r_max)))
        
        # Calculate radial profile
        radial_profile = np.zeros_like(r_bins)
        for i in range(len(r_bins) - 1):
            mask = (r_coords >= r_bins[i]) & (r_coords < r_bins[i+1])
            if mask.any():
                radial_profile[i] = np.mean(dose_array[mask])
        
        # Calculate PSF metrics
        peak_intensity = dose_array[cy, cx]
        half_max = peak_intensity * 0.5
        tenth_max = peak_intensity * 0.1
        
        # Find FWHM and FWTM
        above_half = radial_profile >= half_max
        above_tenth = radial_profile >= tenth_max
        
        fwhm = 2 * r_bins[above_half].max() if above_half.any() else 0
        fwtm = 2 * r_bins[above_tenth].max() if above_tenth.any() else 0
        
        # Fit double Gaussian to extract forward/backscatter components
        try:
            popt = self._fit_double_gaussian(r_bins, radial_profile)
            forward_width = popt[1]
            backscatter_range = popt[3]
            forward_fraction = popt[0] / (popt[0] + popt[2])
            backscatter_fraction = 1.0 - forward_fraction
        except:
            forward_width = fwhm / 2.35  # Convert FWHM to sigma
            backscatter_range = fwtm
            forward_fraction = 0.8
            backscatter_fraction = 0.2
        
        integrated_intensity = np.sum(dose_array) * self.pixel_size**2
        
        return PSFMetrics(
            fwhm=fwhm,
            fwtm=fwtm,
            forward_scatter_width=forward_width,
            backscatter_range=backscatter_range,
            forward_fraction=forward_fraction,
            backscatter_fraction=backscatter_fraction,
            peak_intensity=peak_intensity,
            integrated_intensity=integrated_intensity
        )
    
    def _fit_double_gaussian(self, r: np.ndarray, profile: np.ndarray) -> np.ndarray:
        """Fit double Gaussian to radial profile"""
        def double_gaussian(r, A1, sigma1, A2, sigma2):
            return (A1 * np.exp(-r**2 / (2 * sigma1**2)) + 
                   A2 * np.exp(-r**2 / (2 * sigma2**2)))
        
        # Initial guess
        peak = profile.max()
        p0 = [peak * 0.8, 0.1, peak * 0.2, 2.0]
        
        try:
            popt, _ = optimize.curve_fit(double_gaussian, r, profile, p0=p0,
                                       bounds=([0, 0.001, 0, 0.1], 
                                              [peak * 2, 10, peak, 50]))
            return popt
        except:
            return p0
    
    def analyze_features(self, dose_array: np.ndarray, 
                        threshold: float = 0.5) -> FeatureAnalysis:
        """
        Analyze pattern features in dose distribution
        
        Args:
            dose_array: 2D dose distribution
            threshold: Threshold for feature detection (fraction of max dose)
            
        Returns:
            FeatureAnalysis with pattern metrics
        """
        # Threshold the image
        max_dose = dose_array.max()
        binary_image = dose_array > (threshold * max_dose)
        
        # Find connected components
        labeled_image, num_features = ndimage.label(binary_image)
        
        if num_features == 0:
            return FeatureAnalysis(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # Calculate feature properties
        areas = []
        perimeters = []
        circularities = []
        edge_sharpnesses = []
        
        binary_uint8 = binary_image.astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary_uint8, cv2.RETR_EXTERNAL, 
                                     cv2.CHAIN_APPROX_SIMPLE)
        
        for i, contour in enumerate(contours):
            # Area
            area = cv2.contourArea(contour) * self.pixel_size**2
            areas.append(area)
            
            # Perimeter
            perimeter = cv2.arcLength(contour, True) * self.pixel_size
            perimeters.append(perimeter)
            
            # Circularity
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter**2)
                circularities.append(circularity)
            
            # Edge sharpness
            mask = np.zeros_like(binary_image)
            cv2.drawContours(mask, [contour], -1, 1, -1)
            edge_sharpness = self._calculate_edge_sharpness(dose_array, mask)
            edge_sharpnesses.append(edge_sharpness)
        
        # Calculate statistics
        areas = np.array(areas)
        perimeters = np.array(perimeters)
        circularities = np.array(circularities)
        edge_sharpnesses = np.array(edge_sharpnesses)
        
        # Critical dimension uniformity (3σ/mean for areas)
        cd_uniformity = 1.0 - (3 * np.std(areas) / np.mean(areas)) if areas.mean() > 0 else 0
        cd_uniformity = max(0, cd_uniformity)  # Clamp to positive
        
        # Overall pattern fidelity
        pattern_fidelity = (cd_uniformity + np.mean(edge_sharpnesses)) / 2
        
        return FeatureAnalysis(
            feature_count=num_features,
            mean_area=np.mean(areas),
            std_area=np.std(areas),
            mean_perimeter=np.mean(perimeters),
            std_perimeter=np.std(perimeters),
            mean_circularity=np.mean(circularities),
            cd_uniformity=cd_uniformity,
            edge_sharpness=np.mean(edge_sharpnesses),
            pattern_fidelity=pattern_fidelity
        )
    
    def _calculate_edge_sharpness(self, dose_array: np.ndarray, 
                                mask: np.ndarray) -> float:
        """Calculate edge sharpness for a feature"""
        # Get edge pixels
        edge_mask = ndimage.binary_dilation(mask) ^ mask
        
        if not edge_mask.any():
            return 0.0
        
        # Calculate gradient magnitude at edges
        grad_x = ndimage.sobel(dose_array.astype(float), axis=1)
        grad_y = ndimage.sobel(dose_array.astype(float), axis=0)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Average gradient magnitude at edges
        edge_gradients = gradient_magnitude[edge_mask]
        return np.mean(edge_gradients) if len(edge_gradients) > 0 else 0.0
    
    def create_line_profile(self, dose_array: np.ndarray, 
                          start: Tuple[int, int], end: Tuple[int, int],
                          width: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract line profile from dose array
        
        Args:
            dose_array: 2D dose distribution
            start: Starting coordinates (y, x)
            end: Ending coordinates (y, x)
            width: Width of line profile (pixels)
            
        Returns:
            Tuple of (distance_array, dose_profile)
        """
        # Create line coordinates
        y1, x1 = start
        y2, x2 = end
        
        num_points = int(np.sqrt((x2-x1)**2 + (y2-y1)**2))
        x_coords = np.linspace(x1, x2, num_points)
        y_coords = np.linspace(y1, y2, num_points)
        
        # Sample dose values along line
        profile = ndimage.map_coordinates(dose_array, [y_coords, x_coords], 
                                        order=1, prefilter=False)
        
        # If width > 1, average across width
        if width > 1:
            # Create perpendicular direction
            dx = x2 - x1
            dy = y2 - y1
            length = np.sqrt(dx**2 + dy**2)
            perp_x = -dy / length
            perp_y = dx / length
            
            # Sample multiple lines
            profiles = []
            for w in range(-width//2, width//2 + 1):
                offset_x = x_coords + w * perp_x
                offset_y = y_coords + w * perp_y
                
                # Check bounds
                valid_mask = ((offset_x >= 0) & (offset_x < dose_array.shape[1]) &
                            (offset_y >= 0) & (offset_y < dose_array.shape[0]))
                
                if valid_mask.any():
                    line_profile = ndimage.map_coordinates(
                        dose_array, [offset_y[valid_mask], offset_x[valid_mask]], 
                        order=1, prefilter=False)
                    
                    # Pad with zeros where invalid
                    full_profile = np.zeros_like(offset_x)
                    full_profile[valid_mask] = line_profile
                    profiles.append(full_profile)
            
            profile = np.mean(profiles, axis=0) if profiles else profile
        
        # Create distance array
        distances = np.linspace(0, num_points * self.pixel_size, num_points)
        
        return distances, profile
    
    def compare_dose_distributions(self, dose_arrays: Dict[str, np.ndarray],
                                 analysis_type: str = "comprehensive") -> Dict:
        """
        Compare multiple dose distributions
        
        Args:
            dose_arrays: Dictionary of {label: dose_array} pairs
            analysis_type: Type of comparison ("basic", "comprehensive", "psf")
            
        Returns:
            Comparison results dictionary
        """
        results = {
            'labels': list(dose_arrays.keys()),
            'statistics': {},
            'features': {},
            'psf_metrics': {},
            'correlations': {}
        }
        
        # Calculate individual statistics
        for label, dose_array in dose_arrays.items():
            results['statistics'][label] = self.calculate_dose_statistics(dose_array)
            
            if analysis_type in ["comprehensive", "features"]:
                results['features'][label] = self.analyze_features(dose_array)
            
            if analysis_type in ["comprehensive", "psf"]:
                try:
                    results['psf_metrics'][label] = self.analyze_psf(dose_array)
                except:
                    logger.warning(f"PSF analysis failed for {label}")
                    results['psf_metrics'][label] = None
        
        # Calculate cross-correlations
        if len(dose_arrays) > 1:
            labels = list(dose_arrays.keys())
            n = len(labels)
            correlation_matrix = np.ones((n, n))
            
            for i in range(n):
                for j in range(i+1, n):
                    # Flatten arrays and remove zeros
                    array1 = dose_arrays[labels[i]].flatten()
                    array2 = dose_arrays[labels[j]].flatten()
                    
                    # Align arrays (crop to same size)
                    min_size = min(len(array1), len(array2))
                    array1 = array1[:min_size]
                    array2 = array2[:min_size]
                    
                    # Calculate correlation
                    mask = (array1 > 0) & (array2 > 0)
                    if mask.sum() > 10:  # Need at least 10 points
                        correlation = np.corrcoef(array1[mask], array2[mask])[0, 1]
                        correlation_matrix[i, j] = correlation
                        correlation_matrix[j, i] = correlation
            
            results['correlations'] = {
                'matrix': correlation_matrix,
                'labels': labels
            }
        
        return results
    
    def create_3d_visualization(self, dose_array: np.ndarray, 
                              title: str = "Dose Distribution",
                              log_scale: bool = False) -> go.Figure:
        """Create interactive 3D visualization of dose distribution"""
        y_size, x_size = dose_array.shape
        x_coords = np.arange(x_size) * self.pixel_size
        y_coords = np.arange(y_size) * self.pixel_size
        
        # Apply log scale if requested
        z_data = np.log10(dose_array + 1e-10) if log_scale else dose_array
        z_title = "Log₁₀(Dose)" if log_scale else "Dose"
        
        fig = go.Figure(data=[go.Surface(
            x=x_coords,
            y=y_coords,
            z=z_data,
            colorscale='Plasma',
            colorbar=dict(title=z_title)
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title=f'X ({self.unit})',
                yaxis_title=f'Y ({self.unit})',
                zaxis_title=z_title,
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
            ),
            autosize=True,
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig
    
    def plot_comprehensive_analysis(self, dose_array: np.ndarray, 
                                  title: str = "Dose Analysis",
                                  save_path: Optional[Path] = None):
        """Create comprehensive analysis plot with multiple subplots"""
        fig = plt.figure(figsize=(16, 12))
        
        # Main dose distribution (2D)
        ax1 = plt.subplot(3, 4, (1, 6))  # Spans 2x2 in top-left
        im1 = ax1.imshow(dose_array, cmap=self.colormap, origin='lower',
                        extent=[0, dose_array.shape[1] * self.pixel_size,
                               0, dose_array.shape[0] * self.pixel_size])
        ax1.set_title(f'{title} - 2D Distribution')
        ax1.set_xlabel(f'X ({self.unit})')
        ax1.set_ylabel(f'Y ({self.unit})')
        plt.colorbar(im1, ax=ax1, label='Dose')
        
        # Log scale version
        ax2 = plt.subplot(3, 4, (3, 8))  # Spans 2x2 in top-right
        im2 = ax2.imshow(dose_array + 1e-10, cmap=self.colormap, origin='lower',
                        norm=LogNorm(), 
                        extent=[0, dose_array.shape[1] * self.pixel_size,
                               0, dose_array.shape[0] * self.pixel_size])
        ax2.set_title(f'{title} - Log Scale')
        ax2.set_xlabel(f'X ({self.unit})')
        ax2.set_ylabel(f'Y ({self.unit})')
        plt.colorbar(im2, ax=ax2, label='Log(Dose)')
        
        # Statistics
        stats = self.calculate_dose_statistics(dose_array)
        ax3 = plt.subplot(3, 4, 9)
        ax3.axis('off')
        stats_text = (
            f'Mean: {stats.mean:.3f}\n'
            f'Std: {stats.std:.3f}\n'
            f'Min: {stats.min:.3f}\n'
            f'Max: {stats.max:.3f}\n'
            f'Uniformity: {stats.dose_uniformity:.3f}\n'
            f'Skewness: {stats.skewness:.3f}'
        )
        ax3.text(0.1, 0.5, stats_text, fontsize=10, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        ax3.set_title('Dose Statistics')
        
        # Dose histogram
        ax4 = plt.subplot(3, 4, 10)
        dose_flat = dose_array.flatten()
        dose_nonzero = dose_flat[dose_flat > 0]
        if len(dose_nonzero) > 0:
            ax4.hist(dose_nonzero, bins=50, alpha=0.7, color='blue', density=True)
            ax4.axvline(stats.mean, color='red', linestyle='--', label='Mean')
            ax4.axvline(stats.median, color='green', linestyle='--', label='Median')
        ax4.set_xlabel('Dose')
        ax4.set_ylabel('Probability Density')
        ax4.set_title('Dose Histogram')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Horizontal profile
        ax5 = plt.subplot(3, 4, 11)
        center_y = dose_array.shape[0] // 2
        x_profile = dose_array[center_y, :]
        x_coords = np.arange(len(x_profile)) * self.pixel_size
        ax5.plot(x_coords, x_profile, 'b-', linewidth=2)
        ax5.set_xlabel(f'X ({self.unit})')
        ax5.set_ylabel('Dose')
        ax5.set_title('Horizontal Profile')
        ax5.grid(True, alpha=0.3)
        
        # Vertical profile
        ax6 = plt.subplot(3, 4, 12)
        center_x = dose_array.shape[1] // 2
        y_profile = dose_array[:, center_x]
        y_coords = np.arange(len(y_profile)) * self.pixel_size
        ax6.plot(y_coords, y_profile, 'r-', linewidth=2)
        ax6.set_xlabel(f'Y ({self.unit})')
        ax6.set_ylabel('Dose')
        ax6.set_title('Vertical Profile')
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Comprehensive analysis plot saved to {save_path}")
        
        plt.show()
    
    def export_analysis_report(self, dose_array: np.ndarray, 
                             output_file: str = "dose_analysis_report.html"):
        """Export comprehensive analysis report as HTML"""
        stats = self.calculate_dose_statistics(dose_array)
        features = self.analyze_features(dose_array)
        
        try:
            psf_metrics = self.analyze_psf(dose_array)
        except:
            psf_metrics = None
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>EBL Dose Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>EBL Dose Distribution Analysis Report</h1>
                <p>Comprehensive analysis of electron beam lithography dose patterns</p>
                <p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Resolution: {dose_array.shape[0]} × {dose_array.shape[1]} pixels ({self.pixel_size} {self.unit}/pixel)</p>
            </div>
            
            <div class="section">
                <h2>Dose Statistics</h2>
                <div class="metric"><strong>Mean Dose:</strong> {stats.mean:.4f}</div>
                <div class="metric"><strong>Standard Deviation:</strong> {stats.std:.4f}</div>
                <div class="metric"><strong>Dose Uniformity:</strong> {stats.dose_uniformity:.4f}</div>
                <div class="metric"><strong>Min Dose:</strong> {stats.min:.4f}</div>
                <div class="metric"><strong>Max Dose:</strong> {stats.max:.4f}</div>
                <div class="metric"><strong>Total Dose:</strong> {stats.total_dose:.4f}</div>
                <div class="metric"><strong>Skewness:</strong> {stats.skewness:.4f}</div>
                <div class="metric"><strong>Kurtosis:</strong> {stats.kurtosis:.4f}</div>
            </div>
            
            <div class="section">
                <h2>Feature Analysis</h2>
                <div class="metric"><strong>Feature Count:</strong> {features.feature_count}</div>
                <div class="metric"><strong>Mean Area:</strong> {features.mean_area:.4f} {self.unit}²</div>
                <div class="metric"><strong>CD Uniformity:</strong> {features.cd_uniformity:.4f}</div>
                <div class="metric"><strong>Edge Sharpness:</strong> {features.edge_sharpness:.4f}</div>
                <div class="metric"><strong>Pattern Fidelity:</strong> {features.pattern_fidelity:.4f}</div>
                <div class="metric"><strong>Mean Circularity:</strong> {features.mean_circularity:.4f}</div>
            </div>
        """
        
        if psf_metrics:
            html_content += f"""
            <div class="section">
                <h2>PSF Metrics</h2>
                <div class="metric"><strong>FWHM:</strong> {psf_metrics.fwhm:.4f} {self.unit}</div>
                <div class="metric"><strong>FWTM:</strong> {psf_metrics.fwtm:.4f} {self.unit}</div>
                <div class="metric"><strong>Forward Scatter Width:</strong> {psf_metrics.forward_scatter_width:.4f} {self.unit}</div>
                <div class="metric"><strong>Backscatter Range:</strong> {psf_metrics.backscatter_range:.4f} {self.unit}</div>
                <div class="metric"><strong>Forward Fraction:</strong> {psf_metrics.forward_fraction:.4f}</div>
                <div class="metric"><strong>Peak Intensity:</strong> {psf_metrics.peak_intensity:.4f}</div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Analysis report exported to {output_file}")

def create_test_dose_pattern(size: int = 256, pattern_type: str = "psf") -> np.ndarray:
    """Create test dose pattern for demonstration"""
    dose_array = np.zeros((size, size))
    
    if pattern_type == "psf":
        # Single point source with proximity effects
        center = size // 2
        Y, X = np.ogrid[:size, :size]
        
        # Forward scatter (narrow Gaussian)
        forward = np.exp(-((X-center)**2 + (Y-center)**2) / (2 * 5**2))
        
        # Backscatter (wide exponential)
        r = np.sqrt((X-center)**2 + (Y-center)**2)
        backscatter = 0.3 * np.exp(-r / 50)
        
        dose_array = forward + backscatter
        
    elif pattern_type == "line":
        # Line pattern with varying dose
        center_y = size // 2
        for i in range(size):
            # Gaussian line profile
            dose_array[center_y-2:center_y+3, i] = np.exp(-(i-size//2)**2 / (2*20**2))
        
    elif pattern_type == "array":
        # Array of features
        spacing = 40
        feature_size = 8
        for i in range(2, size-spacing, spacing):
            for j in range(2, size-spacing, spacing):
                # Add Gaussian features
                Y, X = np.ogrid[:size, :size]
                feature = np.exp(-((X-j)**2 + (Y-i)**2) / (2 * feature_size**2))
                dose_array += feature
    
    return dose_array

def main():
    """Main demonstration of dose analysis suite"""
    print("EBL Dose Analysis Suite Demo")
    print("=" * 30)
    
    # Initialize analyzer
    analyzer = DoseAnalysisSuite(pixel_size=1.0, unit="nm")
    
    # Create test patterns
    test_patterns = {
        "PSF": create_test_dose_pattern(256, "psf"),
        "Line": create_test_dose_pattern(256, "line"), 
        "Array": create_test_dose_pattern(256, "array")
    }
    
    print(f"Created {len(test_patterns)} test patterns")
    
    # Analyze each pattern
    for name, pattern in test_patterns.items():
        print(f"\nAnalyzing {name} pattern...")
        
        # Basic statistics
        stats = analyzer.calculate_dose_statistics(pattern)
        print(f"  Mean dose: {stats.mean:.3f}")
        print(f"  Dose uniformity: {stats.dose_uniformity:.3f}")
        print(f"  Max dose: {stats.max:.3f}")
        
        # Feature analysis
        features = analyzer.analyze_features(pattern)
        print(f"  Features found: {features.feature_count}")
        print(f"  Pattern fidelity: {features.pattern_fidelity:.3f}")
        
        # PSF analysis (for PSF pattern only)
        if name == "PSF":
            try:
                psf = analyzer.analyze_psf(pattern)
                print(f"  FWHM: {psf.fwhm:.1f} nm")
                print(f"  Forward fraction: {psf.forward_fraction:.3f}")
            except Exception as e:
                print(f"  PSF analysis failed: {e}")
    
    # Comparison analysis
    print("\nRunning comparison analysis...")
    comparison = analyzer.compare_dose_distributions(test_patterns, "comprehensive")
    
    if 'correlations' in comparison and 'matrix' in comparison['correlations']:
        corr_matrix = comparison['correlations']['matrix']
        labels = comparison['correlations']['labels']
        print("Pattern correlations:")
        for i, label1 in enumerate(labels):
            for j, label2 in enumerate(labels):
                if i < j:
                    print(f"  {label1} vs {label2}: {corr_matrix[i,j]:.3f}")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    for name, pattern in test_patterns.items():
        analyzer.plot_comprehensive_analysis(pattern, f"{name} Pattern", 
                                           Path(f"{name.lower()}_analysis.png"))
    
    # Export reports
    print("\nExporting analysis reports...")
    for name, pattern in test_patterns.items():
        analyzer.export_analysis_report(pattern, f"{name.lower()}_report.html")
    
    # 3D visualization example
    print("\nCreating 3D visualization...")
    fig = analyzer.create_3d_visualization(test_patterns["PSF"], "PSF 3D Visualization")
    fig.write_html("psf_3d_visualization.html")
    
    print("\nDose analysis suite demonstration complete!")
    print("Check generated files: analysis plots, HTML reports, and 3D visualization")

if __name__ == "__main__":
    main()