#!/usr/bin/env python3
"""
Comprehensive Point Spread Function (PSF) Analysis Toolkit for EBL

Advanced PSF characterization and analysis tools for electron beam lithography
simulation results with industry-standard metrics and fitting algorithms.

Features:
- Multi-component PSF fitting (forward/backscatter separation)
- Advanced PSF metrics (FWHM, FWTM, asymmetry, tails)
- Statistical significance testing and confidence intervals
- Energy-dependent PSF analysis
- Temperature and material dependence studies
- Publication-quality visualization and reporting
- BEAMER PSF export format support
- Cross-platform performance optimization

Author: EBL Data Analysis Team
Version: 1.0.0
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
from typing import Dict, List, Tuple, Optional, Union, Callable, Any
from dataclasses import dataclass, field, asdict
from scipy import ndimage, optimize, stats, special, interpolate
from scipy.spatial.distance import cdist
import cv2
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import warnings
from numba import jit, prange
import time
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PSFParameters:
    """Comprehensive PSF parameter set"""
    # Forward scatter parameters
    forward_amplitude: float = 0.0
    forward_sigma: float = 0.0
    forward_amplitude_err: float = 0.0
    forward_sigma_err: float = 0.0
    
    # Backscatter parameters
    backscatter_amplitude: float = 0.0
    backscatter_sigma: float = 0.0
    backscatter_amplitude_err: float = 0.0
    backscatter_sigma_err: float = 0.0
    
    # Secondary backscatter (for thick substrates)
    secondary_amplitude: float = 0.0
    secondary_sigma: float = 0.0
    secondary_amplitude_err: float = 0.0
    secondary_sigma_err: float = 0.0
    
    # Derived metrics
    fwhm: float = 0.0
    fwtm: float = 0.0
    forward_fraction: float = 0.0
    backscatter_fraction: float = 0.0
    secondary_fraction: float = 0.0
    
    # Shape analysis
    asymmetry_x: float = 0.0
    asymmetry_y: float = 0.0
    ellipticity: float = 0.0
    peak_intensity: float = 0.0
    integrated_intensity: float = 0.0
    
    # Statistical measures
    r_squared: float = 0.0
    chi_squared: float = 0.0
    reduced_chi_squared: float = 0.0
    fit_residual_std: float = 0.0
    
    # Confidence intervals (95%)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    # Material and energy context
    beam_energy: float = 100.0  # keV
    substrate_material: str = "Si"
    resist_material: str = "PMMA"
    resist_thickness: float = 100.0  # nm
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PSFParameters':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class PSFQualityMetrics:
    """Quality assessment metrics for PSF analysis"""
    fit_quality: float = 0.0  # Overall fit quality score (0-1)
    data_quality: float = 0.0  # Data quality score (0-1)
    noise_level: float = 0.0  # Estimated noise level
    dynamic_range: float = 0.0  # Peak to noise ratio
    spatial_resolution: float = 0.0  # Effective spatial resolution
    sampling_adequacy: float = 0.0  # Nyquist sampling adequacy
    
    # Warning flags
    undersampled: bool = False
    noisy_data: bool = False
    poor_fit: bool = False
    asymmetric_psf: bool = False
    
    def overall_score(self) -> float:
        """Calculate overall quality score"""
        scores = [self.fit_quality, self.data_quality, 
                 1.0 - self.noise_level, self.sampling_adequacy]
        return np.mean(scores)

class PSFAnalysisToolkit:
    """Comprehensive PSF analysis and characterization toolkit"""
    
    def __init__(self, pixel_size: float = 1.0, unit: str = "nm"):
        """
        Initialize PSF analysis toolkit
        
        Args:
            pixel_size: Physical size of each pixel
            unit: Unit of measurement ("nm", "um", "mm")
        """
        self.pixel_size = pixel_size
        self.unit = unit
        self.analysis_cache: Dict = {}
        self.fitting_history: List = []
        
        # Analysis parameters
        self.radial_bins = 200
        self.angular_bins = 36
        self.max_iterations = 2000
        self.convergence_tolerance = 1e-8
        self.confidence_level = 0.95
        
        # Fitting models
        self.available_models = {
            'single_gaussian': self._single_gaussian_model,
            'double_gaussian': self._double_gaussian_model,
            'triple_gaussian': self._triple_gaussian_model,
            'gaussian_exponential': self._gaussian_exponential_model,
            'pearson_vii': self._pearson_vii_model,
            'voigt': self._voigt_model
        }
        
        # Visualization settings
        self.colormap = 'plasma'
        self.figure_size = (12, 8)
    
    def load_psf_data(self, data_source: Union[str, Path, np.ndarray], 
                     format_type: str = "auto") -> np.ndarray:
        """
        Load PSF data from various sources with validation
        
        Args:
            data_source: File path, numpy array, or data identifier
            format_type: Data format ("csv", "hdf5", "npy", "fits", "auto")
            
        Returns:
            2D PSF array with validation
        """
        if isinstance(data_source, np.ndarray):
            psf_data = data_source.copy()
        else:
            data_path = Path(data_source)
            
            if format_type == "auto":
                format_type = data_path.suffix.lower().lstrip('.')
            
            try:
                if format_type in ["csv"]:
                    df = pd.read_csv(data_path, comment='#')
                    if all(col in df.columns for col in ['x', 'y', 'intensity']):
                        psf_data = self._scatter_to_grid(df, 'x', 'y', 'intensity')
                    elif all(col in df.columns for col in ['X[nm]', 'Y[nm]', 'Energy[keV]']):
                        # EBL simulation format
                        psf_data = self._scatter_to_grid(df, 'X[nm]', 'Y[nm]', 'Energy[keV]')
                    else:
                        psf_data = df.values
                
                elif format_type in ["h5", "hdf5"]:
                    with h5py.File(data_path, 'r') as f:
                        # Try common dataset names
                        for name in ['psf', 'data', 'intensity', 'dose']:
                            if name in f:
                                psf_data = f[name][:]
                                break
                        else:
                            psf_data = list(f.values())[0][:]
                
                elif format_type == "npy":
                    psf_data = np.load(data_path)
                
                elif format_type == "fits":
                    try:
                        from astropy.io import fits
                        with fits.open(data_path) as hdul:
                            psf_data = hdul[0].data
                    except ImportError:
                        raise ImportError("astropy required for FITS file support")
                
                else:
                    raise ValueError(f"Unsupported format: {format_type}")
                    
            except Exception as e:
                logger.error(f"Error loading PSF data from {data_path}: {e}")
                raise
        
        # Validate PSF data
        psf_data = self._validate_psf_data(psf_data)
        return psf_data
    
    def _validate_psf_data(self, psf_data: np.ndarray) -> np.ndarray:
        """Validate and preprocess PSF data"""
        # Ensure 2D array
        if psf_data.ndim != 2:
            if psf_data.ndim == 3 and psf_data.shape[2] == 1:
                psf_data = psf_data.squeeze()
            else:
                raise ValueError(f"PSF data must be 2D, got shape {psf_data.shape}")
        
        # Check for negative values
        if np.any(psf_data < 0):
            logger.warning("Negative values found in PSF data, clipping to zero")
            psf_data = np.clip(psf_data, 0, None)
        
        # Check for NaN or infinite values
        if not np.all(np.isfinite(psf_data)):
            logger.warning("Non-finite values found in PSF data, replacing with zeros")
            psf_data = np.nan_to_num(psf_data, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Ensure non-zero peak
        if psf_data.max() == 0:
            raise ValueError("PSF data contains only zeros")
        
        return psf_data
    
    def _scatter_to_grid(self, df: pd.DataFrame, x_col: str, y_col: str, 
                        intensity_col: str) -> np.ndarray:
        """Convert scattered data points to regular grid"""
        x_coords = df[x_col].values
        y_coords = df[y_col].values
        intensity_values = df[intensity_col].values
        
        # Create regular grid
        x_unique = np.unique(x_coords)
        y_unique = np.unique(y_coords)
        
        # Handle irregular grids by interpolation
        if len(x_unique) * len(y_unique) != len(intensity_values):
            grid_size = int(np.sqrt(len(intensity_values)) * 1.2)
            x_grid = np.linspace(x_coords.min(), x_coords.max(), grid_size)
            y_grid = np.linspace(y_coords.min(), y_coords.max(), grid_size)
            
            # Use scipy griddata for interpolation
            from scipy.interpolate import griddata
            X_grid, Y_grid = np.meshgrid(x_grid, y_grid)
            intensity_grid = griddata((x_coords, y_coords), intensity_values,
                                    (X_grid, Y_grid), method='cubic', fill_value=0)
        else:
            # Regular grid - reshape
            intensity_grid = intensity_values.reshape(len(y_unique), len(x_unique))
        
        return intensity_grid
    
    def extract_radial_profile(self, psf_data: np.ndarray, 
                              center: Optional[Tuple[int, int]] = None,
                              method: str = "interpolated") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract high-quality radial profile from PSF data
        
        Args:
            psf_data: 2D PSF array
            center: Center coordinates (y, x). If None, use peak location
            method: Extraction method ("binned", "interpolated", "weighted")
            
        Returns:
            Tuple of (radius_array, intensity_profile, intensity_std)
        """
        if center is None:
            # Find peak location with sub-pixel accuracy
            peak_idx = np.unravel_index(np.argmax(psf_data), psf_data.shape)
            
            # Sub-pixel peak finding using centroid
            y_peak, x_peak = peak_idx
            window_size = 5
            y_min = max(0, y_peak - window_size)
            y_max = min(psf_data.shape[0], y_peak + window_size + 1)
            x_min = max(0, x_peak - window_size)
            x_max = min(psf_data.shape[1], x_peak + window_size + 1)
            
            region = psf_data[y_min:y_max, x_min:x_max]
            y_coords, x_coords = np.mgrid[y_min:y_max, x_min:x_max]
            
            total_intensity = region.sum()
            if total_intensity > 0:
                cy = (region * y_coords).sum() / total_intensity
                cx = (region * x_coords).sum() / total_intensity
            else:
                cy, cx = peak_idx
        else:
            cy, cx = center
        
        # Create coordinate arrays
        y_coords, x_coords = np.ogrid[:psf_data.shape[0], :psf_data.shape[1]]
        r_coords = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2) * self.pixel_size
        
        # Set radial range
        max_radius = min([cx, cy, psf_data.shape[1]-cx, psf_data.shape[0]-cy]) * self.pixel_size
        
        if method == "binned":
            # Traditional binned approach
            r_bins = np.linspace(0, max_radius, self.radial_bins)
            profile = np.zeros(len(r_bins) - 1)
            profile_std = np.zeros(len(r_bins) - 1)
            
            for i in range(len(r_bins) - 1):
                mask = (r_coords >= r_bins[i]) & (r_coords < r_bins[i+1])
                if mask.any():
                    values = psf_data[mask]
                    profile[i] = np.mean(values)
                    profile_std[i] = np.std(values) / np.sqrt(len(values))  # Standard error
            
            r_centers = (r_bins[:-1] + r_bins[1:]) / 2
            
        elif method == "interpolated":
            # High-resolution interpolated approach
            r_bins = np.linspace(0, max_radius, self.radial_bins * 4)
            
            # Use interpolation for smooth profile
            from scipy.interpolate import RectBivariateSpline
            
            x_range = np.arange(psf_data.shape[1]) * self.pixel_size
            y_range = np.arange(psf_data.shape[0]) * self.pixel_size
            
            # Create interpolator
            interp = RectBivariateSpline(y_range, x_range, psf_data, kx=3, ky=3)
            
            profile = np.zeros(len(r_bins))
            for i, r in enumerate(r_bins):
                if r == 0:
                    profile[i] = psf_data[int(cy), int(cx)]
                else:
                    # Sample points on circle
                    angles = np.linspace(0, 2*np.pi, 36, endpoint=False)
                    x_circle = cx * self.pixel_size + r * np.cos(angles)
                    y_circle = cy * self.pixel_size + r * np.sin(angles)
                    
                    # Filter points within bounds
                    valid_mask = ((x_circle >= 0) & (x_circle < psf_data.shape[1] * self.pixel_size) &
                                 (y_circle >= 0) & (y_circle < psf_data.shape[0] * self.pixel_size))
                    
                    if valid_mask.any():
                        values = interp.ev(y_circle[valid_mask], x_circle[valid_mask])
                        profile[i] = np.mean(values)
            
            r_centers = r_bins
            profile_std = np.gradient(profile) * 0.1  # Rough estimate
            
        else:  # weighted method
            # Distance-weighted averaging
            r_centers = np.linspace(0, max_radius, self.radial_bins)
            profile = np.zeros(len(r_centers))
            profile_std = np.zeros(len(r_centers))
            
            # Pre-compute distances for efficiency
            flat_r = r_coords.flatten()
            flat_psf = psf_data.flatten()
            
            for i, r_target in enumerate(r_centers):
                # Gaussian weighting function
                weights = np.exp(-0.5 * ((flat_r - r_target) / (self.pixel_size * 2))**2)
                weights /= weights.sum()
                
                profile[i] = np.sum(weights * flat_psf)
                # Weighted standard deviation
                variance = np.sum(weights * (flat_psf - profile[i])**2)
                profile_std[i] = np.sqrt(variance)
        
        return r_centers, profile, profile_std
    
    def fit_psf_model(self, radius: np.ndarray, profile: np.ndarray,
                     profile_std: Optional[np.ndarray] = None,
                     model: str = "double_gaussian",
                     initial_guess: Optional[Dict] = None) -> Tuple[PSFParameters, np.ndarray, Dict]:
        """
        Fit PSF model to radial profile with comprehensive error analysis
        
        Args:
            radius: Radial distance array
            profile: Intensity profile
            profile_std: Standard deviation of profile (for weighted fitting)
            model: Model type ("single_gaussian", "double_gaussian", etc.)
            initial_guess: Initial parameter guess dictionary
            
        Returns:
            Tuple of (PSFParameters, fitted_profile, fit_diagnostics)
        """
        if model not in self.available_models:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.available_models.keys())}")
        
        model_func = self.available_models[model]
        
        # Remove zero and negative values for fitting
        valid_mask = (profile > 0) & np.isfinite(profile) & np.isfinite(radius)
        if profile_std is not None:
            valid_mask &= (profile_std > 0) & np.isfinite(profile_std)
        
        r_fit = radius[valid_mask]
        p_fit = profile[valid_mask]
        
        if profile_std is not None:
            sigma_fit = profile_std[valid_mask]
        else:
            # Estimate noise from high-radius regions
            if len(r_fit) > 10:
                noise_region = r_fit > np.percentile(r_fit, 80)
                if noise_region.any():
                    noise_estimate = np.std(p_fit[noise_region])
                else:
                    noise_estimate = np.sqrt(np.mean(p_fit)) * 0.1  # Poisson-like noise
            else:
                noise_estimate = np.sqrt(np.mean(p_fit)) * 0.1
            
            sigma_fit = np.full_like(p_fit, noise_estimate)
        
        # Generate initial parameter guess
        if initial_guess is None:
            initial_guess = self._generate_initial_guess(r_fit, p_fit, model)
        
        # Convert to parameter array for fitting
        param_names, p0 = self._dict_to_params(initial_guess, model)
        
        # Define bounds
        bounds = self._get_parameter_bounds(model, p_fit.max(), r_fit.max())
        
        try:
            # Perform weighted least squares fitting
            popt, pcov = optimize.curve_fit(
                lambda r, *params: model_func(r, self._params_to_dict(params, param_names)),
                r_fit, p_fit, p0=p0, sigma=sigma_fit, absolute_sigma=True,
                bounds=bounds, maxfev=self.max_iterations,
                ftol=self.convergence_tolerance, xtol=self.convergence_tolerance
            )
            
            # Calculate fitted profile
            fitted_params = self._params_to_dict(popt, param_names)
            fitted_profile = model_func(radius, fitted_params)
            
            # Calculate parameter errors
            param_errors = np.sqrt(np.diag(pcov))
            
            # Calculate fit quality metrics
            residuals = p_fit - model_func(r_fit, fitted_params)
            chi_squared = np.sum((residuals / sigma_fit)**2)
            dof = len(r_fit) - len(popt)
            reduced_chi_squared = chi_squared / dof if dof > 0 else np.inf
            
            r_squared = r2_score(p_fit, model_func(r_fit, fitted_params))
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                popt, pcov, param_names, self.confidence_level
            )
            
            # Create PSF parameters object
            psf_params = self._create_psf_parameters(
                fitted_params, param_errors, param_names, model,
                r_squared, chi_squared, reduced_chi_squared,
                np.std(residuals), confidence_intervals
            )
            
            # Fit diagnostics
            fit_diagnostics = {
                'model': model,
                'iterations': self.max_iterations,  # Would need callback to track actual
                'convergence': True,
                'chi_squared': chi_squared,
                'reduced_chi_squared': reduced_chi_squared,
                'r_squared': r_squared,
                'residual_std': np.std(residuals),
                'parameter_correlations': pcov / np.outer(param_errors, param_errors),
                'residuals': residuals,
                'fitted_radius': r_fit,
                'initial_guess': initial_guess,
                'bounds': bounds
            }
            
            # Store in fitting history
            self.fitting_history.append({
                'timestamp': time.time(),
                'model': model,
                'parameters': psf_params.to_dict(),
                'diagnostics': fit_diagnostics
            })
            
            logger.info(f"PSF fitting completed: {model}, R² = {r_squared:.4f}, "
                       f"χ²ᵣ = {reduced_chi_squared:.4f}")
            
        except Exception as e:
            logger.error(f"PSF fitting failed: {e}")
            # Return default parameters with error flags
            psf_params = PSFParameters()
            fitted_profile = np.zeros_like(radius)
            fit_diagnostics = {
                'model': model,
                'convergence': False,
                'error': str(e),
                'chi_squared': np.inf,
                'r_squared': 0.0
            }
        
        return psf_params, fitted_profile, fit_diagnostics
    
    @staticmethod
    @jit(nopython=True)
    def _single_gaussian_model(r: np.ndarray, params: Dict) -> np.ndarray:
        """Single Gaussian PSF model - JIT optimized"""
        A = params['amplitude']
        sigma = params['sigma']
        return A * np.exp(-r**2 / (2 * sigma**2))
    
    @staticmethod
    @jit(nopython=True) 
    def _double_gaussian_model(r: np.ndarray, params: Dict) -> np.ndarray:
        """Double Gaussian PSF model (forward + backscatter) - JIT optimized"""
        A1 = params['forward_amplitude']
        sigma1 = params['forward_sigma']
        A2 = params['backscatter_amplitude']
        sigma2 = params['backscatter_sigma']
        
        forward = A1 * np.exp(-r**2 / (2 * sigma1**2))
        backscatter = A2 * np.exp(-r**2 / (2 * sigma2**2))
        
        return forward + backscatter
    
    def _triple_gaussian_model(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Triple Gaussian PSF model (forward + backscatter + secondary)"""
        forward = params['forward_amplitude'] * np.exp(-r**2 / (2 * params['forward_sigma']**2))
        backscatter = params['backscatter_amplitude'] * np.exp(-r**2 / (2 * params['backscatter_sigma']**2))
        secondary = params['secondary_amplitude'] * np.exp(-r**2 / (2 * params['secondary_sigma']**2))
        
        return forward + backscatter + secondary
    
    def _gaussian_exponential_model(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Gaussian + exponential PSF model (forward + backscatter)"""
        forward = params['forward_amplitude'] * np.exp(-r**2 / (2 * params['forward_sigma']**2))
        backscatter = params['backscatter_amplitude'] * np.exp(-r / params['backscatter_lambda'])
        
        return forward + backscatter
    
    def _pearson_vii_model(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Pearson VII PSF model"""
        A = params['amplitude']
        sigma = params['sigma']
        m = params['shape_parameter']
        
        return A * (1 + (r / sigma)**2)**(-m)
    
    def _voigt_model(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Voigt profile PSF model (convolution of Gaussian and Lorentzian)"""
        # Simplified Voigt approximation
        sigma_g = params['gaussian_width']
        gamma_l = params['lorentzian_width']
        A = params['amplitude']
        
        # Pseudo-Voigt approximation
        eta = 1.36603 * (gamma_l / (gamma_l + sigma_g)) - 0.47719 * (gamma_l / (gamma_l + sigma_g))**2 + 0.11116 * (gamma_l / (gamma_l + sigma_g))**3
        
        gaussian = np.exp(-r**2 / (2 * sigma_g**2))
        lorentzian = 1 / (1 + (r / gamma_l)**2)
        
        return A * (eta * lorentzian + (1 - eta) * gaussian)
    
    def _generate_initial_guess(self, radius: np.ndarray, profile: np.ndarray, 
                               model: str) -> Dict:
        """Generate intelligent initial parameter guess"""
        peak_intensity = profile.max()
        
        # Find FWHM for initial sigma estimate
        half_max = peak_intensity / 2
        above_half = profile > half_max
        if above_half.any():
            indices = np.where(above_half)[0]
            if len(indices) > 1:
                fwhm_estimate = radius[indices[-1]] - radius[indices[0]]
                sigma_estimate = fwhm_estimate / (2 * np.sqrt(2 * np.log(2)))
            else:
                sigma_estimate = radius.max() * 0.1
        else:
            sigma_estimate = radius.max() * 0.1
        
        # Find where intensity drops to 10% for backscatter estimate
        tenth_max = peak_intensity * 0.1
        above_tenth = profile > tenth_max
        if above_tenth.any():
            indices = np.where(above_tenth)[0]
            if len(indices) > 1:
                backscatter_range = radius[indices[-1]] - radius[indices[0]]
            else:
                backscatter_range = radius.max() * 0.5
        else:
            backscatter_range = radius.max() * 0.5
        
        # Model-specific initial guesses
        if model == "single_gaussian":
            return {
                'amplitude': peak_intensity,
                'sigma': sigma_estimate
            }
        
        elif model == "double_gaussian":
            return {
                'forward_amplitude': peak_intensity * 0.8,
                'forward_sigma': sigma_estimate,
                'backscatter_amplitude': peak_intensity * 0.2,
                'backscatter_sigma': backscatter_range / 2
            }
        
        elif model == "triple_gaussian":
            return {
                'forward_amplitude': peak_intensity * 0.7,
                'forward_sigma': sigma_estimate,
                'backscatter_amplitude': peak_intensity * 0.2,
                'backscatter_sigma': backscatter_range / 2,
                'secondary_amplitude': peak_intensity * 0.1,
                'secondary_sigma': backscatter_range
            }
        
        elif model == "gaussian_exponential":
            return {
                'forward_amplitude': peak_intensity * 0.8,
                'forward_sigma': sigma_estimate,
                'backscatter_amplitude': peak_intensity * 0.2,
                'backscatter_lambda': backscatter_range / 3
            }
        
        elif model == "pearson_vii":
            return {
                'amplitude': peak_intensity,
                'sigma': sigma_estimate,
                'shape_parameter': 2.0
            }
        
        elif model == "voigt":
            return {
                'amplitude': peak_intensity,
                'gaussian_width': sigma_estimate,
                'lorentzian_width': sigma_estimate * 0.5
            }
        
        else:
            raise ValueError(f"No initial guess generator for model: {model}")
    
    def _dict_to_params(self, param_dict: Dict, model: str) -> Tuple[List[str], List[float]]:
        """Convert parameter dictionary to arrays for fitting"""
        param_names = list(param_dict.keys())
        param_values = list(param_dict.values())
        return param_names, param_values
    
    def _params_to_dict(self, param_array: np.ndarray, param_names: List[str]) -> Dict:
        """Convert parameter array back to dictionary"""
        return dict(zip(param_names, param_array))
    
    def _get_parameter_bounds(self, model: str, max_intensity: float, 
                             max_radius: float) -> Tuple[List[float], List[float]]:
        """Get reasonable parameter bounds for fitting"""
        if model == "single_gaussian":
            lower = [0, 0.1]  # amplitude, sigma
            upper = [max_intensity * 2, max_radius]
        
        elif model == "double_gaussian":
            lower = [0, 0.1, 0, 0.1]  # f_amp, f_sig, b_amp, b_sig
            upper = [max_intensity * 2, max_radius / 10, max_intensity, max_radius]
        
        elif model == "triple_gaussian":
            lower = [0, 0.1, 0, 0.1, 0, 0.1]
            upper = [max_intensity * 2, max_radius / 10, max_intensity, max_radius, max_intensity, max_radius * 2]
        
        elif model == "gaussian_exponential":
            lower = [0, 0.1, 0, 0.1]
            upper = [max_intensity * 2, max_radius / 10, max_intensity, max_radius * 2]
        
        elif model == "pearson_vii":
            lower = [0, 0.1, 0.5]
            upper = [max_intensity * 2, max_radius, 10.0]
        
        elif model == "voigt":
            lower = [0, 0.1, 0.1]
            upper = [max_intensity * 2, max_radius, max_radius]
        
        else:
            # Default loose bounds
            n_params = len(self._generate_initial_guess(
                np.array([0, max_radius]), np.array([max_intensity, 0]), model
            ))
            lower = [0] * n_params
            upper = [max_intensity * 2] * n_params
        
        return lower, upper
    
    def _calculate_confidence_intervals(self, params: np.ndarray, covariance: np.ndarray,
                                      param_names: List[str], confidence_level: float) -> Dict:
        """Calculate confidence intervals for fitted parameters"""
        confidence_intervals = {}
        
        # Critical value for confidence interval
        alpha = 1 - confidence_level
        dof = len(params) - 1
        t_critical = stats.t.ppf(1 - alpha/2, dof)
        
        param_errors = np.sqrt(np.diag(covariance))
        
        for i, name in enumerate(param_names):
            margin = t_critical * param_errors[i]
            confidence_intervals[name] = (
                params[i] - margin,
                params[i] + margin
            )
        
        return confidence_intervals
    
    def _create_psf_parameters(self, fitted_params: Dict, param_errors: np.ndarray,
                              param_names: List[str], model: str, r_squared: float,
                              chi_squared: float, reduced_chi_squared: float,
                              residual_std: float, confidence_intervals: Dict) -> PSFParameters:
        """Create comprehensive PSF parameters object"""
        psf_params = PSFParameters()
        
        # Set fit quality metrics
        psf_params.r_squared = r_squared
        psf_params.chi_squared = chi_squared
        psf_params.reduced_chi_squared = reduced_chi_squared
        psf_params.fit_residual_std = residual_std
        psf_params.confidence_intervals = confidence_intervals
        
        # Extract model-specific parameters
        param_error_dict = dict(zip(param_names, param_errors))
        
        if 'forward_amplitude' in fitted_params:
            psf_params.forward_amplitude = fitted_params['forward_amplitude']
            psf_params.forward_amplitude_err = param_error_dict.get('forward_amplitude', 0)
        elif 'amplitude' in fitted_params:
            psf_params.forward_amplitude = fitted_params['amplitude']
            psf_params.forward_amplitude_err = param_error_dict.get('amplitude', 0)
        
        if 'forward_sigma' in fitted_params:
            psf_params.forward_sigma = fitted_params['forward_sigma']
            psf_params.forward_sigma_err = param_error_dict.get('forward_sigma', 0)
        elif 'sigma' in fitted_params:
            psf_params.forward_sigma = fitted_params['sigma']
            psf_params.forward_sigma_err = param_error_dict.get('sigma', 0)
        
        if 'backscatter_amplitude' in fitted_params:
            psf_params.backscatter_amplitude = fitted_params['backscatter_amplitude']
            psf_params.backscatter_amplitude_err = param_error_dict.get('backscatter_amplitude', 0)
        
        if 'backscatter_sigma' in fitted_params:
            psf_params.backscatter_sigma = fitted_params['backscatter_sigma']
            psf_params.backscatter_sigma_err = param_error_dict.get('backscatter_sigma', 0)
        
        if 'secondary_amplitude' in fitted_params:
            psf_params.secondary_amplitude = fitted_params['secondary_amplitude']
            psf_params.secondary_amplitude_err = param_error_dict.get('secondary_amplitude', 0)
        
        if 'secondary_sigma' in fitted_params:
            psf_params.secondary_sigma = fitted_params['secondary_sigma']
            psf_params.secondary_sigma_err = param_error_dict.get('secondary_sigma', 0)
        
        # Calculate derived metrics
        if psf_params.forward_sigma > 0:
            psf_params.fwhm = 2 * np.sqrt(2 * np.log(2)) * psf_params.forward_sigma
        
        if psf_params.forward_sigma > 0:
            psf_params.fwtm = 2 * np.sqrt(2 * np.log(10)) * psf_params.forward_sigma
        
        # Calculate fractions
        total_amplitude = (psf_params.forward_amplitude + 
                          psf_params.backscatter_amplitude + 
                          psf_params.secondary_amplitude)
        
        if total_amplitude > 0:
            psf_params.forward_fraction = psf_params.forward_amplitude / total_amplitude
            psf_params.backscatter_fraction = psf_params.backscatter_amplitude / total_amplitude
            psf_params.secondary_fraction = psf_params.secondary_amplitude / total_amplitude
        
        # Peak intensity
        psf_params.peak_intensity = psf_params.forward_amplitude
        
        # Integrated intensity (approximate for Gaussians)
        psf_params.integrated_intensity = (
            2 * np.pi * psf_params.forward_amplitude * psf_params.forward_sigma**2 +
            2 * np.pi * psf_params.backscatter_amplitude * psf_params.backscatter_sigma**2 +
            2 * np.pi * psf_params.secondary_amplitude * psf_params.secondary_sigma**2
        )
        
        return psf_params
    
    def assess_psf_quality(self, psf_data: np.ndarray, 
                          fitted_params: PSFParameters) -> PSFQualityMetrics:
        """Comprehensive PSF quality assessment"""
        quality = PSFQualityMetrics()
        
        # Fit quality assessment
        quality.fit_quality = max(0, min(1, fitted_params.r_squared))
        
        # Data quality assessment
        peak_value = psf_data.max()
        noise_estimate = np.std(psf_data[psf_data < peak_value * 0.01])
        quality.noise_level = min(1, noise_estimate / peak_value)
        quality.dynamic_range = peak_value / noise_estimate if noise_estimate > 0 else np.inf
        
        # Spatial resolution assessment
        nyquist_frequency = 1 / (2 * self.pixel_size)
        psf_frequency = 1 / (fitted_params.fwhm) if fitted_params.fwhm > 0 else 0
        quality.spatial_resolution = min(1, psf_frequency / nyquist_frequency)
        
        # Sampling adequacy
        if fitted_params.forward_sigma > 0:
            samples_per_sigma = fitted_params.forward_sigma / self.pixel_size
            quality.sampling_adequacy = min(1, samples_per_sigma / 3)  # Want at least 3 samples per sigma
        
        # Data quality score
        quality.data_quality = 1 - quality.noise_level
        
        # Warning flags
        quality.undersampled = quality.sampling_adequacy < 0.5
        quality.noisy_data = quality.noise_level > 0.1
        quality.poor_fit = quality.fit_quality < 0.8
        quality.asymmetric_psf = abs(fitted_params.asymmetry_x) > 0.1 or abs(fitted_params.asymmetry_y) > 0.1
        
        return quality
    
    def analyze_psf_asymmetry(self, psf_data: np.ndarray,
                             center: Optional[Tuple[int, int]] = None) -> Dict[str, float]:
        """Analyze PSF asymmetry and ellipticity"""
        if center is None:
            center = np.unravel_index(np.argmax(psf_data), psf_data.shape)
        
        cy, cx = center
        
        # Extract profiles along different axes
        profiles = {}
        angles = np.linspace(0, np.pi, 8, endpoint=False)
        
        for i, angle in enumerate(angles):
            # Create line coordinates
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            max_dist = min(cx, cy, psf_data.shape[1]-cx, psf_data.shape[0]-cy)
            
            distances = np.arange(0, max_dist)
            x_coords = cx + distances * cos_a
            y_coords = cy + distances * sin_a
            
            # Sample along line
            profile = ndimage.map_coordinates(psf_data, [y_coords, x_coords], order=1)
            profiles[f'angle_{i}'] = profile
        
        # Calculate asymmetry metrics
        x_profile = psf_data[cy, :]
        y_profile = psf_data[:, cx]
        
        # Asymmetry as difference between left/right, top/bottom
        if cx > 5 and cx < psf_data.shape[1] - 5:
            left_sum = np.sum(x_profile[:cx])
            right_sum = np.sum(x_profile[cx:])
            asymmetry_x = (right_sum - left_sum) / (right_sum + left_sum)
        else:
            asymmetry_x = 0
        
        if cy > 5 and cy < psf_data.shape[0] - 5:
            top_sum = np.sum(y_profile[:cy])
            bottom_sum = np.sum(y_profile[cy:])
            asymmetry_y = (bottom_sum - top_sum) / (bottom_sum + top_sum)
        else:
            asymmetry_y = 0
        
        # Ellipticity calculation using second moments
        y_coords, x_coords = np.mgrid[:psf_data.shape[0], :psf_data.shape[1]]
        x_coords = x_coords - cx
        y_coords = y_coords - cy
        
        total_intensity = psf_data.sum()
        if total_intensity > 0:
            # Second moments
            m20 = np.sum(psf_data * x_coords**2) / total_intensity
            m02 = np.sum(psf_data * y_coords**2) / total_intensity
            m11 = np.sum(psf_data * x_coords * y_coords) / total_intensity
            
            # Ellipticity parameters
            a = m20 + m02
            b = 4 * m11**2 + (m20 - m02)**2
            
            if b > 0:
                ellipticity = np.sqrt(b) / a if a > 0 else 0
            else:
                ellipticity = 0
        else:
            ellipticity = 0
        
        return {
            'asymmetry_x': asymmetry_x,
            'asymmetry_y': asymmetry_y,
            'ellipticity': ellipticity,
            'directional_profiles': profiles
        }
    
    def create_comprehensive_psf_plot(self, psf_data: np.ndarray,
                                     fitted_params: PSFParameters,
                                     fitted_profile: np.ndarray,
                                     radius: np.ndarray,
                                     save_path: Optional[Path] = None) -> plt.Figure:
        """Create comprehensive PSF analysis visualization"""
        fig = plt.figure(figsize=(16, 12))
        
        # 2D PSF image
        ax1 = plt.subplot(3, 4, (1, 2))
        im1 = ax1.imshow(psf_data, cmap=self.colormap, origin='lower')
        ax1.set_title('2D PSF Data')
        ax1.set_xlabel(f'X ({self.unit})')
        ax1.set_ylabel(f'Y ({self.unit})')
        plt.colorbar(im1, ax=ax1, label='Intensity')
        
        # Log scale PSF
        ax2 = plt.subplot(3, 4, (3, 4))
        im2 = ax2.imshow(psf_data + 1e-10, cmap=self.colormap, origin='lower', 
                        norm=LogNorm())
        ax2.set_title('2D PSF Data (Log Scale)')
        ax2.set_xlabel(f'X ({self.unit})')
        ax2.set_ylabel(f'Y ({self.unit})')
        plt.colorbar(im2, ax=ax2, label='Log(Intensity)')
        
        # Radial profile with fit
        ax3 = plt.subplot(3, 4, (5, 6))
        
        # Extract radial profile for plotting
        radius_plot, profile_plot, _ = self.extract_radial_profile(psf_data)
        
        ax3.semilogy(radius_plot, profile_plot, 'b-', alpha=0.7, label='Data')
        ax3.semilogy(radius, fitted_profile, 'r-', linewidth=2, label='Fit')
        
        # Add component breakdown if double/triple Gaussian
        if fitted_params.forward_amplitude > 0 and fitted_params.forward_sigma > 0:
            forward_component = fitted_params.forward_amplitude * np.exp(
                -radius**2 / (2 * fitted_params.forward_sigma**2)
            )
            ax3.semilogy(radius, forward_component, 'g--', alpha=0.8, label='Forward scatter')
        
        if fitted_params.backscatter_amplitude > 0 and fitted_params.backscatter_sigma > 0:
            backscatter_component = fitted_params.backscatter_amplitude * np.exp(
                -radius**2 / (2 * fitted_params.backscatter_sigma**2)
            )
            ax3.semilogy(radius, backscatter_component, 'm--', alpha=0.8, label='Backscatter')
        
        ax3.set_xlabel(f'Radius ({self.unit})')
        ax3.set_ylabel('Intensity')
        ax3.set_title('Radial Profile with Fit')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Fit residuals
        ax4 = plt.subplot(3, 4, 7)
        if len(radius) == len(fitted_profile) and len(radius_plot) == len(profile_plot):
            # Interpolate to common grid for residuals
            interp_fitted = np.interp(radius_plot, radius, fitted_profile)
            residuals = profile_plot - interp_fitted
            ax4.plot(radius_plot, residuals, 'ko-', markersize=3)
            ax4.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            ax4.set_xlabel(f'Radius ({self.unit})')
            ax4.set_ylabel('Residuals')
            ax4.set_title('Fit Residuals')
            ax4.grid(True, alpha=0.3)
        
        # Parameter summary
        ax5 = plt.subplot(3, 4, 8)
        ax5.axis('off')
        
        param_text = f"PSF Parameters:\n"
        param_text += f"FWHM: {fitted_params.fwhm:.2f} ± {fitted_params.forward_sigma_err*2.35:.2f} {self.unit}\n"
        param_text += f"Forward σ: {fitted_params.forward_sigma:.2f} ± {fitted_params.forward_sigma_err:.2f} {self.unit}\n"
        param_text += f"Backscatter σ: {fitted_params.backscatter_sigma:.2f} ± {fitted_params.backscatter_sigma_err:.2f} {self.unit}\n"
        param_text += f"Forward fraction: {fitted_params.forward_fraction:.3f}\n"
        param_text += f"Backscatter fraction: {fitted_params.backscatter_fraction:.3f}\n"
        param_text += f"R² = {fitted_params.r_squared:.4f}\n"
        param_text += f"χ²ᵣ = {fitted_params.reduced_chi_squared:.4f}"
        
        ax5.text(0.05, 0.95, param_text, transform=ax5.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        # Cross-sections
        center_y, center_x = np.unravel_index(np.argmax(psf_data), psf_data.shape)
        
        ax6 = plt.subplot(3, 4, 9)
        x_profile = psf_data[center_y, :]
        x_coords = np.arange(len(x_profile)) * self.pixel_size
        ax6.plot(x_coords, x_profile, 'b-', linewidth=2)
        ax6.set_xlabel(f'X ({self.unit})')
        ax6.set_ylabel('Intensity')
        ax6.set_title('Horizontal Cross-Section')
        ax6.grid(True, alpha=0.3)
        
        ax7 = plt.subplot(3, 4, 10)
        y_profile = psf_data[:, center_x]
        y_coords = np.arange(len(y_profile)) * self.pixel_size
        ax7.plot(y_coords, y_profile, 'r-', linewidth=2)
        ax7.set_xlabel(f'Y ({self.unit})')
        ax7.set_ylabel('Intensity')
        ax7.set_title('Vertical Cross-Section')
        ax7.grid(True, alpha=0.3)
        
        # Quality metrics
        quality = self.assess_psf_quality(psf_data, fitted_params)
        ax8 = plt.subplot(3, 4, 11)
        ax8.axis('off')
        
        quality_text = f"Quality Assessment:\n"
        quality_text += f"Fit Quality: {quality.fit_quality:.3f}\n"
        quality_text += f"Data Quality: {quality.data_quality:.3f}\n"
        quality_text += f"Dynamic Range: {quality.dynamic_range:.1f}\n"
        quality_text += f"Sampling: {quality.sampling_adequacy:.3f}\n"
        quality_text += f"Overall Score: {quality.overall_score():.3f}\n\n"
        
        if quality.undersampled:
            quality_text += "⚠ Undersampled\n"
        if quality.noisy_data:
            quality_text += "⚠ Noisy data\n"
        if quality.poor_fit:
            quality_text += "⚠ Poor fit\n"
        if quality.asymmetric_psf:
            quality_text += "⚠ Asymmetric PSF\n"
        
        ax8.text(0.05, 0.95, quality_text, transform=ax8.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
        
        # Energy distribution (if applicable)
        ax9 = plt.subplot(3, 4, 12)
        # Create a simple energy histogram based on radial distribution
        energy_hist = np.histogram(radius_plot, weights=profile_plot, bins=50)
        ax9.bar(energy_hist[1][:-1], energy_hist[0], width=np.diff(energy_hist[1]), alpha=0.7)
        ax9.set_xlabel(f'Radius ({self.unit})')
        ax9.set_ylabel('Energy Deposition')
        ax9.set_title('Energy Distribution')
        ax9.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"PSF analysis plot saved to {save_path}")
        
        return fig
    
    def export_beamer_psf(self, fitted_params: PSFParameters, 
                         output_file: Union[str, Path],
                         beam_energy: float = 100.0,
                         substrate_material: str = "Si") -> None:
        """Export PSF parameters in BEAMER format"""
        beamer_data = {
            "PSF_Version": "2.0",
            "BeamEnergy_keV": beam_energy,
            "SubstrateMaterial": substrate_material,
            "ForwardScatter": {
                "Amplitude": fitted_params.forward_amplitude,
                "Sigma_nm": fitted_params.forward_sigma,
                "AmplitudeError": fitted_params.forward_amplitude_err,
                "SigmaError": fitted_params.forward_sigma_err
            },
            "BackScatter": {
                "Amplitude": fitted_params.backscatter_amplitude,
                "Sigma_nm": fitted_params.backscatter_sigma,
                "AmplitudeError": fitted_params.backscatter_amplitude_err,
                "SigmaError": fitted_params.backscatter_sigma_err
            },
            "DerivedMetrics": {
                "FWHM_nm": fitted_params.fwhm,
                "FWTM_nm": fitted_params.fwtm,
                "ForwardFraction": fitted_params.forward_fraction,
                "BackscatterFraction": fitted_params.backscatter_fraction
            },
            "FitQuality": {
                "R_squared": fitted_params.r_squared,
                "ChiSquaredReduced": fitted_params.reduced_chi_squared,
                "ResidualStd": fitted_params.fit_residual_std
            },
            "ConfidenceIntervals_95pct": fitted_params.confidence_intervals
        }
        
        with open(output_file, 'w') as f:
            json.dump(beamer_data, f, indent=2)
        
        logger.info(f"BEAMER PSF file exported to {output_file}")
    
    def batch_psf_analysis(self, data_files: List[Union[str, Path]],
                          output_dir: Union[str, Path],
                          model: str = "double_gaussian",
                          parallel: bool = True) -> pd.DataFrame:
        """Batch process multiple PSF datasets"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        results = []
        
        def analyze_single_file(file_path):
            try:
                # Load and analyze PSF
                psf_data = self.load_psf_data(file_path)
                radius, profile, profile_std = self.extract_radial_profile(psf_data)
                fitted_params, fitted_profile, diagnostics = self.fit_psf_model(
                    radius, profile, profile_std, model
                )
                
                # Quality assessment
                quality = self.assess_psf_quality(psf_data, fitted_params)
                
                # Create comprehensive plot
                fig = self.create_comprehensive_psf_plot(
                    psf_data, fitted_params, fitted_profile, radius,
                    output_path / f"{Path(file_path).stem}_analysis.png"
                )
                plt.close(fig)
                
                # Export BEAMER format
                self.export_beamer_psf(
                    fitted_params, 
                    output_path / f"{Path(file_path).stem}_beamer.json"
                )
                
                # Compile results
                result = {
                    'filename': Path(file_path).name,
                    'file_path': str(file_path),
                    'analysis_success': True,
                    **fitted_params.to_dict(),
                    'quality_score': quality.overall_score(),
                    'fit_quality': quality.fit_quality,
                    'data_quality': quality.data_quality,
                    'dynamic_range': quality.dynamic_range,
                    'warnings': [
                        'undersampled' if quality.undersampled else '',
                        'noisy' if quality.noisy_data else '',
                        'poor_fit' if quality.poor_fit else '',
                        'asymmetric' if quality.asymmetric_psf else ''
                    ]
                }
                
                logger.info(f"Successfully analyzed: {Path(file_path).name}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                return {
                    'filename': Path(file_path).name,
                    'file_path': str(file_path),
                    'analysis_success': False,
                    'error': str(e)
                }
        
        # Process files
        if parallel and len(data_files) > 1:
            with ThreadPoolExecutor(max_workers=min(8, len(data_files))) as executor:
                results = list(tqdm(
                    executor.map(analyze_single_file, data_files),
                    total=len(data_files),
                    desc="Analyzing PSF files"
                ))
        else:
            results = [analyze_single_file(f) for f in tqdm(data_files, desc="Analyzing PSF files")]
        
        # Create summary DataFrame
        df_results = pd.DataFrame(results)
        
        # Save results
        summary_file = output_path / "psf_analysis_summary.csv"
        df_results.to_csv(summary_file, index=False)
        
        # Create summary statistics
        successful_analyses = df_results[df_results['analysis_success'] == True]
        if len(successful_analyses) > 0:
            summary_stats = {
                'total_files': len(data_files),
                'successful_analyses': len(successful_analyses),
                'mean_fwhm': successful_analyses['fwhm'].mean(),
                'std_fwhm': successful_analyses['fwhm'].std(),
                'mean_forward_fraction': successful_analyses['forward_fraction'].mean(),
                'mean_fit_quality': successful_analyses['fit_quality'].mean(),
                'files_with_warnings': (successful_analyses['warnings'].apply(
                    lambda x: any(w for w in x if w)
                )).sum()
            }
            
            with open(output_path / "batch_summary.json", 'w') as f:
                json.dump(summary_stats, f, indent=2)
        
        logger.info(f"Batch PSF analysis complete. Results saved to {output_path}")
        return df_results


def main():
    """Demonstration of PSF analysis toolkit"""
    print("EBL PSF Analysis Toolkit Demo")
    print("=" * 40)
    
    # Initialize toolkit
    toolkit = PSFAnalysisToolkit(pixel_size=1.0, unit="nm")
    
    # Create synthetic PSF data for demonstration
    def create_synthetic_psf(size=128, forward_sigma=5, backscatter_sigma=25, 
                           forward_amp=1.0, backscatter_frac=0.3):
        """Create synthetic PSF data"""
        center = size // 2
        Y, X = np.ogrid[:size, :size]
        
        # Forward scatter
        r_forward = np.sqrt((X - center)**2 + (Y - center)**2)
        forward = forward_amp * np.exp(-r_forward**2 / (2 * forward_sigma**2))
        
        # Backscatter
        r_backscatter = np.sqrt((X - center)**2 + (Y - center)**2)
        backscatter = forward_amp * backscatter_frac * np.exp(-r_backscatter**2 / (2 * backscatter_sigma**2))
        
        # Add some noise
        noise = np.random.normal(0, forward_amp * 0.01, (size, size))
        
        return forward + backscatter + noise
    
    # Create test PSF
    print("\nCreating synthetic PSF data...")
    psf_data = create_synthetic_psf(size=256, forward_sigma=3, backscatter_sigma=20)
    
    # Extract radial profile
    print("Extracting radial profile...")
    radius, profile, profile_std = toolkit.extract_radial_profile(psf_data, method="interpolated")
    
    # Fit PSF model
    print("Fitting double Gaussian model...")
    fitted_params, fitted_profile, diagnostics = toolkit.fit_psf_model(
        radius, profile, profile_std, model="double_gaussian"
    )
    
    # Display results
    print(f"\nPSF Analysis Results:")
    print(f"FWHM: {fitted_params.fwhm:.2f} ± {fitted_params.forward_sigma_err*2.35:.2f} nm")
    print(f"Forward scatter σ: {fitted_params.forward_sigma:.2f} ± {fitted_params.forward_sigma_err:.2f} nm")
    print(f"Backscatter σ: {fitted_params.backscatter_sigma:.2f} ± {fitted_params.backscatter_sigma_err:.2f} nm")
    print(f"Forward fraction: {fitted_params.forward_fraction:.3f}")
    print(f"Backscatter fraction: {fitted_params.backscatter_fraction:.3f}")
    print(f"Fit quality (R²): {fitted_params.r_squared:.4f}")
    print(f"Reduced χ²: {fitted_params.reduced_chi_squared:.4f}")
    
    # Quality assessment
    quality = toolkit.assess_psf_quality(psf_data, fitted_params)
    print(f"\nQuality Assessment:")
    print(f"Overall score: {quality.overall_score():.3f}")
    print(f"Dynamic range: {quality.dynamic_range:.1f}")
    print(f"Sampling adequacy: {quality.sampling_adequacy:.3f}")
    
    # Asymmetry analysis
    asymmetry = toolkit.analyze_psf_asymmetry(psf_data)
    print(f"\nAsymmetry Analysis:")
    print(f"X asymmetry: {asymmetry['asymmetry_x']:.3f}")
    print(f"Y asymmetry: {asymmetry['asymmetry_y']:.3f}")
    print(f"Ellipticity: {asymmetry['ellipticity']:.3f}")
    
    # Create comprehensive visualization
    print("\nGenerating comprehensive PSF analysis plot...")
    fig = toolkit.create_comprehensive_psf_plot(
        psf_data, fitted_params, fitted_profile, radius,
        save_path=Path("psf_analysis_demo.png")
    )
    
    # Export BEAMER format
    print("Exporting BEAMER PSF format...")
    toolkit.export_beamer_psf(fitted_params, "demo_psf_beamer.json", 
                             beam_energy=100.0, substrate_material="Si")
    
    print("\nPSF Analysis Toolkit demonstration complete!")
    print("Generated files:")
    print("- psf_analysis_demo.png (comprehensive analysis plot)")
    print("- demo_psf_beamer.json (BEAMER PSF format)")
    
    plt.show()


if __name__ == "__main__":
    main()