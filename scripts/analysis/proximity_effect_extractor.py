#!/usr/bin/env python3
"""
Proximity Effect Parameter Extraction Toolkit

Advanced extraction and statistical analysis of proximity effect parameters from EBL simulation
data with comprehensive uncertainty quantification and statistical significance testing.

Features:
- Multi-scale proximity effect analysis (forward/backscatter separation)
- Statistical significance testing with multiple correction methods
- Bootstrap confidence intervals and uncertainty propagation
- Energy-dependent proximity parameter extraction
- Material-dependent parameter characterization
- Cross-validation and model selection
- Automated parameter optimization and fitting
- Industry-standard proximity correction models
- Publication-quality statistical reporting

Author: EBL Data Analysis Team
Version: 1.0.0
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, field, asdict
from scipy import optimize, stats, special, ndimage, integrate
from scipy.interpolate import interp1d, interp2d, RectBivariateSpline
from sklearn.model_selection import cross_val_score, KFold, StratifiedKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
import time
from tqdm import tqdm
from numba import jit, prange
import h5py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProximityParameters:
    """Comprehensive proximity effect parameters with uncertainties"""
    # Forward scatter parameters
    forward_range: float = 0.0  # nm
    forward_range_err: float = 0.0
    forward_amplitude: float = 0.0
    forward_amplitude_err: float = 0.0
    
    # Backscatter parameters  
    backscatter_range: float = 0.0  # nm
    backscatter_range_err: float = 0.0
    backscatter_amplitude: float = 0.0
    backscatter_amplitude_err: float = 0.0
    
    # Derived parameters
    eta: float = 0.0  # Backscatter ratio
    eta_err: float = 0.0
    alpha: float = 0.0  # Forward/backscatter range ratio
    alpha_err: float = 0.0
    beta: float = 0.0  # Proximity function parameter
    beta_err: float = 0.0
    
    # Material and energy context
    beam_energy: float = 100.0  # keV
    substrate_material: str = "Si"
    resist_material: str = "PMMA"
    resist_thickness: float = 100.0  # nm
    substrate_thickness: float = 1000.0  # nm
    
    # Statistical measures
    r_squared: float = 0.0
    chi_squared: float = 0.0
    reduced_chi_squared: float = 0.0
    p_value: float = 1.0
    
    # Confidence intervals (95% by default)
    confidence_level: float = 0.95
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    # Cross-validation results
    cv_scores: List[float] = field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0
    
    # Model selection metrics
    aic: float = np.inf  # Akaike Information Criterion
    bic: float = np.inf  # Bayesian Information Criterion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProximityParameters':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class StatisticalTestResults:
    """Results of statistical significance tests"""
    test_name: str
    statistic: float
    p_value: float
    critical_value: float
    significant: bool
    effect_size: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    interpretation: str = ""

class ProximityEffectExtractor:
    """Advanced proximity effect parameter extraction with statistical analysis"""
    
    def __init__(self, confidence_level: float = 0.95, n_bootstrap: int = 1000):
        """
        Initialize proximity effect extractor
        
        Args:
            confidence_level: Confidence level for uncertainty estimation
            n_bootstrap: Number of bootstrap samples for uncertainty quantification
        """
        self.confidence_level = confidence_level
        self.n_bootstrap = n_bootstrap
        
        # Statistical test configuration
        self.alpha = 1 - confidence_level
        self.multiple_testing_correction = 'bonferroni'  # 'bonferroni', 'benjamini_hochberg', 'holm'
        
        # Model fitting parameters
        self.max_iterations = 5000
        self.convergence_tolerance = 1e-10
        self.outlier_threshold = 3.0  # Z-score threshold for outlier detection
        
        # Available proximity models
        self.proximity_models = {
            'single_gaussian': self._single_gaussian_proximity,
            'double_gaussian': self._double_gaussian_proximity,
            'gaussian_exponential': self._gaussian_exponential_proximity,
            'power_law': self._power_law_proximity,
            'voigt': self._voigt_proximity,
            'bethe_bloch': self._bethe_bloch_proximity
        }
        
        # Physical constants for parameter validation
        self.physical_bounds = {
            'forward_range': (1.0, 100.0),  # nm
            'backscatter_range': (10.0, 10000.0),  # nm
            'eta': (0.0, 1.0),  # Backscatter ratio
            'alpha': (0.01, 100.0)  # Range ratio
        }
    
    def extract_proximity_parameters(self, dose_data: Union[np.ndarray, pd.DataFrame],
                                   coordinates: Optional[np.ndarray] = None,
                                   model: str = 'double_gaussian',
                                   beam_energy: float = 100.0,
                                   material_info: Optional[Dict] = None) -> ProximityParameters:
        """
        Extract proximity effect parameters with comprehensive statistical analysis
        
        Args:
            dose_data: 2D dose distribution or DataFrame with dose data
            coordinates: Coordinate arrays if dose_data is 2D array
            model: Proximity model type
            beam_energy: Beam energy in keV
            material_info: Material properties dictionary
            
        Returns:
            ProximityParameters with uncertainties and statistical metrics
        """
        logger.info(f"Extracting proximity parameters using {model} model")
        start_time = time.time()
        
        # Prepare data
        if isinstance(dose_data, pd.DataFrame):
            radius, dose_profile, dose_std = self._prepare_dataframe_data(dose_data)
        else:
            radius, dose_profile, dose_std = self._prepare_array_data(dose_data, coordinates)
        
        # Validate data
        self._validate_input_data(radius, dose_profile, dose_std)
        
        # Remove outliers
        radius_clean, dose_clean, dose_std_clean = self._remove_outliers(
            radius, dose_profile, dose_std
        )
        
        logger.info(f"Data preparation complete: {len(radius_clean)} points after outlier removal")
        
        # Fit proximity model with uncertainty quantification
        params, fit_diagnostics = self._fit_proximity_model_with_uncertainty(
            radius_clean, dose_clean, dose_std_clean, model
        )
        
        # Perform statistical significance tests
        statistical_tests = self._perform_statistical_tests(
            radius_clean, dose_clean, dose_std_clean, params, model
        )
        
        # Cross-validation analysis
        cv_results = self._cross_validation_analysis(
            radius_clean, dose_clean, dose_std_clean, model
        )
        
        # Model selection metrics
        model_metrics = self._calculate_model_selection_metrics(
            radius_clean, dose_clean, params, model
        )
        
        # Create comprehensive parameter object
        proximity_params = self._create_proximity_parameters(
            params, fit_diagnostics, statistical_tests, cv_results, model_metrics,
            beam_energy, material_info
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Proximity parameter extraction complete in {processing_time:.2f}s")
        
        return proximity_params
    
    def _prepare_dataframe_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data from DataFrame format"""
        # Detect column types
        x_cols = [col for col in df.columns if 'X' in col.upper() or 'x' in col]
        y_cols = [col for col in df.columns if 'Y' in col.upper() or 'y' in col]
        dose_cols = [col for col in df.columns if 'DOSE' in col.upper() or 'dose' in col or 'ENERGY' in col.upper()]
        
        if not (x_cols and y_cols and dose_cols):
            raise ValueError("DataFrame must contain X, Y, and dose columns")
        
        x_data = df[x_cols[0]].values
        y_data = df[y_cols[0]].values
        dose_data = df[dose_cols[0]].values
        
        # Calculate radial distance from center of mass
        dose_mask = dose_data > 0
        if dose_mask.any():
            x_center = np.average(x_data[dose_mask], weights=dose_data[dose_mask])
            y_center = np.average(y_data[dose_mask], weights=dose_data[dose_mask])
        else:
            x_center = np.mean(x_data)
            y_center = np.mean(y_data)
        
        radius = np.sqrt((x_data - x_center)**2 + (y_data - y_center)**2)
        
        # Create radial profile by binning
        max_radius = np.percentile(radius, 95)  # Ignore extreme outliers
        n_bins = min(200, len(radius) // 50)  # Adaptive binning
        
        bins = np.linspace(0, max_radius, n_bins)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        dose_profile = np.zeros(len(bin_centers))
        dose_std = np.zeros(len(bin_centers))
        
        for i in range(len(bin_centers)):
            mask = (radius >= bins[i]) & (radius < bins[i+1]) & (dose_data > 0)
            if mask.any():
                dose_values = dose_data[mask]
                dose_profile[i] = np.mean(dose_values)
                dose_std[i] = np.std(dose_values) / np.sqrt(len(dose_values))  # Standard error
        
        # Remove empty bins
        valid_mask = dose_profile > 0
        return bin_centers[valid_mask], dose_profile[valid_mask], dose_std[valid_mask]
    
    def _prepare_array_data(self, dose_array: np.ndarray, 
                          coordinates: Optional[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data from 2D array format"""
        if dose_array.ndim != 2:
            raise ValueError("Dose array must be 2D")
        
        # Find center of dose distribution
        dose_normalized = dose_array / dose_array.max()
        threshold = 0.1
        above_threshold = dose_normalized > threshold
        
        if above_threshold.any():
            y_indices, x_indices = np.where(above_threshold)
            weights = dose_array[above_threshold]
            y_center = np.average(y_indices, weights=weights)
            x_center = np.average(x_indices, weights=weights)
        else:
            y_center, x_center = np.array(dose_array.shape) / 2
        
        # Create coordinate grids
        if coordinates is not None:
            x_coords, y_coords = coordinates
        else:
            y_coords, x_coords = np.ogrid[:dose_array.shape[0], :dose_array.shape[1]]
        
        # Calculate radial distances
        r_coords = np.sqrt((x_coords - x_center)**2 + (y_coords - y_center)**2)
        
        # Extract radial profile
        max_radius = min(x_center, y_center, dose_array.shape[1]-x_center, dose_array.shape[0]-y_center)
        n_bins = min(100, int(max_radius))
        
        radius_bins = np.linspace(0, max_radius, n_bins)
        bin_centers = (radius_bins[:-1] + radius_bins[1:]) / 2
        
        dose_profile = np.zeros(len(bin_centers))
        dose_std = np.zeros(len(bin_centers))
        
        for i in range(len(bin_centers)):
            mask = (r_coords >= radius_bins[i]) & (r_coords < radius_bins[i+1])
            if mask.any():
                dose_values = dose_array[mask]
                dose_values = dose_values[dose_values > 0]
                if len(dose_values) > 0:
                    dose_profile[i] = np.mean(dose_values)
                    dose_std[i] = np.std(dose_values) / np.sqrt(len(dose_values))
        
        # Remove empty bins
        valid_mask = dose_profile > 0
        return bin_centers[valid_mask], dose_profile[valid_mask], dose_std[valid_mask]
    
    def _validate_input_data(self, radius: np.ndarray, dose_profile: np.ndarray, 
                           dose_std: np.ndarray) -> None:
        """Validate input data for analysis"""
        if len(radius) != len(dose_profile) or len(radius) != len(dose_std):
            raise ValueError("All input arrays must have the same length")
        
        if len(radius) < 10:
            raise ValueError("Insufficient data points for reliable analysis (minimum 10 required)")
        
        if not np.all(np.isfinite(radius)) or not np.all(np.isfinite(dose_profile)):
            raise ValueError("Input data contains non-finite values")
        
        if np.any(radius < 0) or np.any(dose_profile <= 0):
            raise ValueError("Radius and dose values must be positive")
        
        # Check for monotonic decrease (typical of proximity functions)
        if not self._is_approximately_monotonic_decreasing(dose_profile):
            logger.warning("Dose profile is not monotonically decreasing - may indicate data issues")
    
    def _is_approximately_monotonic_decreasing(self, profile: np.ndarray, tolerance: float = 0.1) -> bool:
        """Check if profile is approximately monotonically decreasing"""
        increases = 0
        for i in range(1, len(profile)):
            if profile[i] > profile[i-1] * (1 + tolerance):
                increases += 1
        
        return increases / len(profile) < 0.2  # Allow up to 20% violations
    
    def _remove_outliers(self, radius: np.ndarray, dose_profile: np.ndarray,
                        dose_std: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Remove outliers using statistical methods"""
        # Z-score based outlier detection
        log_dose = np.log(dose_profile + 1e-10)
        z_scores = np.abs(stats.zscore(log_dose))
        
        outlier_mask = z_scores < self.outlier_threshold
        
        # Also remove points with extremely high uncertainty
        if np.any(dose_std > 0):
            relative_error = dose_std / dose_profile
            error_threshold = np.percentile(relative_error, 95)  # Remove top 5%
            outlier_mask &= (relative_error <= error_threshold)
        
        n_removed = len(radius) - np.sum(outlier_mask)
        if n_removed > 0:
            logger.info(f"Removed {n_removed} outlier points ({n_removed/len(radius)*100:.1f}%)")
        
        return radius[outlier_mask], dose_profile[outlier_mask], dose_std[outlier_mask]
    
    def _fit_proximity_model_with_uncertainty(self, radius: np.ndarray, dose_profile: np.ndarray,
                                            dose_std: np.ndarray, model: str) -> Tuple[Dict, Dict]:
        """Fit proximity model with comprehensive uncertainty quantification"""
        if model not in self.proximity_models:
            raise ValueError(f"Unknown model: {model}")
        
        model_func = self.proximity_models[model]
        
        # Generate initial parameter guess
        initial_params = self._generate_initial_guess(radius, dose_profile, model)
        param_names = list(initial_params.keys())
        p0 = list(initial_params.values())
        
        # Define parameter bounds
        bounds = self._get_parameter_bounds(model, dose_profile.max(), radius.max())
        
        # Weighted least squares fitting
        def fitting_function(r, *params):
            param_dict = dict(zip(param_names, params))
            return model_func(r, param_dict)
        
        try:
            # Main fit
            popt, pcov = optimize.curve_fit(
                fitting_function, radius, dose_profile, p0=p0,
                sigma=dose_std, absolute_sigma=True, bounds=bounds,
                maxfev=self.max_iterations, ftol=self.convergence_tolerance
            )
            
            # Calculate fitted values
            fitted_profile = fitting_function(radius, *popt)
            
            # Bootstrap uncertainty estimation
            bootstrap_params = self._bootstrap_uncertainty_estimation(
                radius, dose_profile, dose_std, fitting_function, popt, pcov
            )
            
            # Calculate comprehensive diagnostics
            diagnostics = self._calculate_fit_diagnostics(
                radius, dose_profile, dose_std, fitted_profile, popt, pcov, param_names
            )
            
            # Combine parameters with bootstrap uncertainties
            fitted_params = {}
            for i, name in enumerate(param_names):
                fitted_params[name] = popt[i]
                fitted_params[f'{name}_err'] = np.sqrt(pcov[i, i])
                fitted_params[f'{name}_bootstrap_err'] = np.std(bootstrap_params[:, i])
                
                # Confidence intervals from bootstrap
                ci_lower = np.percentile(bootstrap_params[:, i], (1-self.confidence_level)/2 * 100)
                ci_upper = np.percentile(bootstrap_params[:, i], (1-(1-self.confidence_level)/2) * 100)
                fitted_params[f'{name}_ci'] = (ci_lower, ci_upper)
            
            diagnostics['bootstrap_results'] = {
                'bootstrap_samples': bootstrap_params,
                'bootstrap_statistics': self._calculate_bootstrap_statistics(bootstrap_params, param_names)
            }
            
            return fitted_params, diagnostics
            
        except Exception as e:
            logger.error(f"Model fitting failed: {e}")
            # Return default parameters with error indicators
            fitted_params = {name: 0.0 for name in param_names}
            for name in param_names:
                fitted_params[f'{name}_err'] = np.inf
                fitted_params[f'{name}_ci'] = (0.0, 0.0)
            
            diagnostics = {
                'convergence': False,
                'error': str(e),
                'r_squared': 0.0,
                'chi_squared': np.inf,
                'p_value': 1.0
            }
            
            return fitted_params, diagnostics
    
    def _bootstrap_uncertainty_estimation(self, radius: np.ndarray, dose_profile: np.ndarray,
                                        dose_std: np.ndarray, fitting_function: Callable,
                                        best_params: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """Perform bootstrap uncertainty estimation"""
        n_data = len(radius)
        n_params = len(best_params)
        bootstrap_params = np.zeros((self.n_bootstrap, n_params))
        
        logger.info(f"Performing bootstrap uncertainty estimation with {self.n_bootstrap} samples...")
        
        for i in tqdm(range(self.n_bootstrap), desc="Bootstrap sampling", leave=False):
            # Bootstrap resampling
            indices = np.random.choice(n_data, size=n_data, replace=True)
            r_boot = radius[indices]
            dose_boot = dose_profile[indices]
            std_boot = dose_std[indices]
            
            # Add noise based on uncertainties
            dose_boot_noisy = dose_boot + np.random.normal(0, std_boot)
            dose_boot_noisy = np.maximum(dose_boot_noisy, dose_boot * 0.01)  # Prevent negative values
            
            try:
                # Fit to bootstrap sample
                popt_boot, _ = optimize.curve_fit(
                    fitting_function, r_boot, dose_boot_noisy, p0=best_params,
                    sigma=std_boot, absolute_sigma=True, maxfev=1000,
                    ftol=self.convergence_tolerance * 10  # Relaxed tolerance for bootstrap
                )
                bootstrap_params[i] = popt_boot
                
            except:
                # If fit fails, use parameters from multivariate normal based on covariance
                bootstrap_params[i] = np.random.multivariate_normal(best_params, covariance)
        
        return bootstrap_params
    
    def _calculate_bootstrap_statistics(self, bootstrap_params: np.ndarray, 
                                      param_names: List[str]) -> Dict:
        """Calculate bootstrap statistics"""
        stats_dict = {}
        
        for i, name in enumerate(param_names):
            param_samples = bootstrap_params[:, i]
            
            stats_dict[name] = {
                'mean': float(np.mean(param_samples)),
                'std': float(np.std(param_samples)),
                'median': float(np.median(param_samples)),
                'mad': float(stats.median_abs_deviation(param_samples)),
                'skewness': float(stats.skew(param_samples)),
                'kurtosis': float(stats.kurtosis(param_samples)),
                'confidence_interval': (
                    float(np.percentile(param_samples, (1-self.confidence_level)/2 * 100)),
                    float(np.percentile(param_samples, (1-(1-self.confidence_level)/2) * 100))
                )
            }
        
        return stats_dict
    
    def _calculate_fit_diagnostics(self, radius: np.ndarray, dose_profile: np.ndarray,
                                 dose_std: np.ndarray, fitted_profile: np.ndarray,
                                 params: np.ndarray, covariance: np.ndarray,
                                 param_names: List[str]) -> Dict:
        """Calculate comprehensive fit diagnostics"""
        # Basic fit metrics
        residuals = dose_profile - fitted_profile
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((dose_profile - np.mean(dose_profile))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Weighted metrics
        if np.any(dose_std > 0):
            weights = 1 / dose_std**2
            chi_squared = np.sum(weights * residuals**2)
            dof = len(radius) - len(params)
            reduced_chi_squared = chi_squared / dof if dof > 0 else np.inf
        else:
            chi_squared = ss_res
            reduced_chi_squared = chi_squared / (len(radius) - len(params))
        
        # Statistical significance test (F-test)
        f_statistic = (r_squared / (len(params) - 1)) / ((1 - r_squared) / (len(radius) - len(params)))
        p_value = 1 - stats.f.cdf(f_statistic, len(params) - 1, len(radius) - len(params))
        
        # Parameter correlation matrix
        param_errors = np.sqrt(np.diag(covariance))
        correlation_matrix = covariance / np.outer(param_errors, param_errors)
        
        # Residual analysis
        residual_stats = {
            'mean': float(np.mean(residuals)),
            'std': float(np.std(residuals)),
            'skewness': float(stats.skew(residuals)),
            'kurtosis': float(stats.kurtosis(residuals)),
            'jarque_bera_test': stats.jarque_bera(residuals),
            'durbin_watson': self._durbin_watson_statistic(residuals)
        }
        
        return {
            'convergence': True,
            'r_squared': float(r_squared),
            'chi_squared': float(chi_squared),
            'reduced_chi_squared': float(reduced_chi_squared),
            'f_statistic': float(f_statistic),
            'p_value': float(p_value),
            'residual_std': float(np.std(residuals)),
            'parameter_correlation': correlation_matrix.tolist(),
            'parameter_names': param_names,
            'residual_analysis': residual_stats,
            'condition_number': float(np.linalg.cond(covariance))
        }
    
    def _durbin_watson_statistic(self, residuals: np.ndarray) -> float:
        """Calculate Durbin-Watson statistic for autocorrelation test"""
        if len(residuals) < 2:
            return 2.0
        
        diff_residuals = np.diff(residuals)
        dw = np.sum(diff_residuals**2) / np.sum(residuals**2)
        return float(dw)
    
    def _perform_statistical_tests(self, radius: np.ndarray, dose_profile: np.ndarray,
                                 dose_std: np.ndarray, fitted_params: Dict,
                                 model: str) -> List[StatisticalTestResults]:
        """Perform comprehensive statistical significance tests"""
        tests = []
        
        # Goodness of fit tests
        model_func = self.proximity_models[model]
        param_dict = {k: v for k, v in fitted_params.items() if not k.endswith('_err') and not k.endswith('_ci')}
        fitted_values = model_func(radius, param_dict)
        
        # Kolmogorov-Smirnov test for residual normality
        residuals = dose_profile - fitted_values
        if len(residuals) > 7:  # Minimum for KS test
            ks_stat, ks_p = stats.kstest(residuals, 'norm', args=(np.mean(residuals), np.std(residuals)))
            tests.append(StatisticalTestResults(
                test_name="Kolmogorov-Smirnov (Residual Normality)",
                statistic=ks_stat,
                p_value=ks_p,
                critical_value=stats.ksone.ppf(1-self.alpha, len(residuals)),
                significant=ks_p < self.alpha,
                interpretation="Tests if residuals follow normal distribution"
            ))
        
        # Shapiro-Wilk test for residual normality (more powerful for small samples)
        if 3 <= len(residuals) <= 5000:
            sw_stat, sw_p = stats.shapiro(residuals)
            tests.append(StatisticalTestResults(
                test_name="Shapiro-Wilk (Residual Normality)",
                statistic=sw_stat,
                p_value=sw_p,
                critical_value=0.0,  # No simple critical value
                significant=sw_p < self.alpha,
                interpretation="Tests if residuals follow normal distribution"
            ))
        
        # Anderson-Darling test for residual normality
        ad_stat, ad_critical, ad_significance = stats.anderson(residuals, dist='norm')
        ad_p = self._anderson_darling_p_value(ad_stat, len(residuals))
        tests.append(StatisticalTestResults(
            test_name="Anderson-Darling (Residual Normality)",
            statistic=ad_stat,
            p_value=ad_p,
            critical_value=ad_critical[2],  # 5% significance level
            significant=ad_stat > ad_critical[2],
            interpretation="Tests if residuals follow normal distribution"
        ))
        
        # Breusch-Pagan test for heteroscedasticity
        if len(residuals) > 10:
            bp_stat, bp_p = self._breusch_pagan_test(residuals, fitted_values)
            tests.append(StatisticalTestResults(
                test_name="Breusch-Pagan (Heteroscedasticity)",
                statistic=bp_stat,
                p_value=bp_p,
                critical_value=stats.chi2.ppf(1-self.alpha, 1),
                significant=bp_p < self.alpha,
                interpretation="Tests for constant variance in residuals"
            ))
        
        # Runs test for randomness of residuals
        runs_stat, runs_p = self._runs_test(residuals)
        tests.append(StatisticalTestResults(
            test_name="Runs Test (Residual Randomness)",
            statistic=runs_stat,
            p_value=runs_p,
            critical_value=1.96,  # For normal approximation
            significant=abs(runs_stat) > 1.96,
            interpretation="Tests for randomness in residual sequence"
        ))
        
        # Parameter significance tests (t-tests)
        for param_name in param_dict.keys():
            if f'{param_name}_err' in fitted_params:
                param_value = fitted_params[param_name]
                param_error = fitted_params[f'{param_name}_err']
                
                if param_error > 0:
                    t_stat = param_value / param_error
                    dof = len(radius) - len(param_dict)
                    t_p = 2 * (1 - stats.t.cdf(abs(t_stat), dof))  # Two-tailed test
                    
                    tests.append(StatisticalTestResults(
                        test_name=f"Parameter Significance ({param_name})",
                        statistic=t_stat,
                        p_value=t_p,
                        critical_value=stats.t.ppf(1-self.alpha/2, dof),
                        significant=t_p < self.alpha,
                        effect_size=abs(param_value) / param_error,
                        interpretation=f"Tests if {param_name} is significantly different from zero"
                    ))
        
        # Apply multiple testing correction
        if len(tests) > 1:
            tests = self._apply_multiple_testing_correction(tests)
        
        return tests
    
    def _anderson_darling_p_value(self, statistic: float, n: int) -> float:
        """Approximate p-value for Anderson-Darling test"""
        # Approximation based on empirical formulas
        if statistic < 0.2:
            return 1 - np.exp(-13.436 + 101.14 * statistic - 223.73 * statistic**2)
        elif statistic < 0.34:
            return 1 - np.exp(-8.318 + 42.796 * statistic - 59.938 * statistic**2)
        elif statistic < 0.6:
            return np.exp(0.9177 - 4.279 * statistic - 1.38 * statistic**2)
        else:
            return np.exp(1.2937 - 5.709 * statistic + 0.0186 * statistic**2)
    
    def _breusch_pagan_test(self, residuals: np.ndarray, fitted_values: np.ndarray) -> Tuple[float, float]:
        """Breusch-Pagan test for heteroscedasticity"""
        n = len(residuals)
        
        # Regress squared residuals on fitted values
        y = residuals**2
        X = np.column_stack([np.ones(n), fitted_values])
        
        try:
            # Least squares regression
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            y_pred = X @ beta
            
            # Calculate test statistic
            ss_explained = np.sum((y_pred - np.mean(y))**2)
            ss_total = np.sum((y - np.mean(y))**2)
            
            if ss_total > 0:
                lm_statistic = n * (ss_explained / ss_total)
                p_value = 1 - stats.chi2.cdf(lm_statistic, 1)
            else:
                lm_statistic = 0.0
                p_value = 1.0
            
            return lm_statistic, p_value
            
        except np.linalg.LinAlgError:
            return 0.0, 1.0
    
    def _runs_test(self, residuals: np.ndarray) -> Tuple[float, float]:
        """Runs test for randomness"""
        n = len(residuals)
        median = np.median(residuals)
        
        # Convert to sequence of + and - signs
        signs = (residuals > median).astype(int)
        
        # Count runs
        runs = 1
        for i in range(1, n):
            if signs[i] != signs[i-1]:
                runs += 1
        
        # Calculate expected runs and variance
        n1 = np.sum(signs)  # Number of + signs
        n2 = n - n1        # Number of - signs
        
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0
        
        expected_runs = (2 * n1 * n2) / n + 1
        variance_runs = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n**2 * (n - 1))
        
        if variance_runs <= 0:
            return 0.0, 1.0
        
        # Z-statistic
        z_stat = (runs - expected_runs) / np.sqrt(variance_runs)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        return z_stat, p_value
    
    def _apply_multiple_testing_correction(self, tests: List[StatisticalTestResults]) -> List[StatisticalTestResults]:
        """Apply multiple testing correction to p-values"""
        p_values = [test.p_value for test in tests]
        
        if self.multiple_testing_correction == 'bonferroni':
            corrected_p_values = [min(1.0, p * len(tests)) for p in p_values]
        elif self.multiple_testing_correction == 'benjamini_hochberg':
            corrected_p_values = self._benjamini_hochberg_correction(p_values)
        elif self.multiple_testing_correction == 'holm':
            corrected_p_values = self._holm_correction(p_values)
        else:
            corrected_p_values = p_values
        
        # Update test results with corrected p-values
        for i, test in enumerate(tests):
            test.p_value = corrected_p_values[i]
            test.significant = corrected_p_values[i] < self.alpha
            test.interpretation += f" (p-value corrected using {self.multiple_testing_correction})"
        
        return tests
    
    def _benjamini_hochberg_correction(self, p_values: List[float]) -> List[float]:
        """Benjamini-Hochberg false discovery rate correction"""
        n = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_p_values = np.array(p_values)[sorted_indices]
        
        corrected = np.zeros(n)
        corrected[sorted_indices[-1]] = sorted_p_values[-1]
        
        for i in range(n-2, -1, -1):
            corrected[sorted_indices[i]] = min(
                sorted_p_values[i] * n / (i + 1),
                corrected[sorted_indices[i + 1]]
            )
        
        return corrected.tolist()
    
    def _holm_correction(self, p_values: List[float]) -> List[float]:
        """Holm step-down correction"""
        n = len(p_values)
        sorted_indices = np.argsort(p_values)
        
        corrected = np.zeros(n)
        for i, idx in enumerate(sorted_indices):
            corrected[idx] = min(1.0, p_values[idx] * (n - i))
            if i > 0:
                corrected[idx] = max(corrected[idx], corrected[sorted_indices[i-1]])
        
        return corrected.tolist()
    
    def _cross_validation_analysis(self, radius: np.ndarray, dose_profile: np.ndarray,
                                 dose_std: np.ndarray, model: str) -> Dict:
        """Perform cross-validation analysis"""
        logger.info("Performing cross-validation analysis...")
        
        model_func = self.proximity_models[model]
        
        # K-fold cross-validation
        n_folds = min(10, len(radius) // 3)  # Ensure sufficient data per fold
        kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
        
        cv_scores = []
        cv_params = []
        
        for train_idx, test_idx in kf.split(radius):
            try:
                # Split data
                r_train, r_test = radius[train_idx], radius[test_idx]
                dose_train, dose_test = dose_profile[train_idx], dose_profile[test_idx]
                std_train, std_test = dose_std[train_idx], dose_std[test_idx]
                
                # Fit model on training data
                initial_params = self._generate_initial_guess(r_train, dose_train, model)
                param_names = list(initial_params.keys())
                p0 = list(initial_params.values())
                bounds = self._get_parameter_bounds(model, dose_train.max(), r_train.max())
                
                def fitting_function(r, *params):
                    param_dict = dict(zip(param_names, params))
                    return model_func(r, param_dict)
                
                popt, _ = optimize.curve_fit(
                    fitting_function, r_train, dose_train, p0=p0,
                    sigma=std_train, bounds=bounds, maxfev=1000
                )
                
                # Evaluate on test data
                dose_pred = fitting_function(r_test, *popt)
                score = r2_score(dose_test, dose_pred)
                
                cv_scores.append(score)
                cv_params.append(popt)
                
            except Exception as e:
                logger.warning(f"Cross-validation fold failed: {e}")
                continue
        
        if cv_scores:
            return {
                'cv_scores': cv_scores,
                'cv_mean': float(np.mean(cv_scores)),
                'cv_std': float(np.std(cv_scores)),
                'cv_params': cv_params,
                'n_successful_folds': len(cv_scores),
                'n_total_folds': n_folds
            }
        else:
            return {
                'cv_scores': [],
                'cv_mean': 0.0,
                'cv_std': 0.0,
                'cv_params': [],
                'n_successful_folds': 0,
                'n_total_folds': n_folds
            }
    
    def _calculate_model_selection_metrics(self, radius: np.ndarray, dose_profile: np.ndarray,
                                         fitted_params: Dict, model: str) -> Dict:
        """Calculate AIC, BIC, and other model selection metrics"""
        model_func = self.proximity_models[model]
        param_dict = {k: v for k, v in fitted_params.items() if not k.endswith('_err') and not k.endswith('_ci')}
        
        fitted_values = model_func(radius, param_dict)
        residuals = dose_profile - fitted_values
        
        n = len(radius)
        k = len(param_dict)  # Number of parameters
        
        # Log-likelihood (assuming normal distribution)
        rss = np.sum(residuals**2)
        sigma_sq = rss / n
        log_likelihood = -0.5 * n * (np.log(2 * np.pi * sigma_sq) + 1)
        
        # Information criteria
        aic = 2 * k - 2 * log_likelihood
        bic = k * np.log(n) - 2 * log_likelihood
        aicc = aic + (2 * k * (k + 1)) / (n - k - 1) if n > k + 1 else np.inf  # Corrected AIC
        
        return {
            'log_likelihood': float(log_likelihood),
            'aic': float(aic),
            'bic': float(bic),
            'aicc': float(aicc),
            'n_parameters': k,
            'n_observations': n
        }
    
    def _create_proximity_parameters(self, fitted_params: Dict, fit_diagnostics: Dict,
                                   statistical_tests: List[StatisticalTestResults],
                                   cv_results: Dict, model_metrics: Dict,
                                   beam_energy: float, material_info: Optional[Dict]) -> ProximityParameters:
        """Create comprehensive proximity parameters object"""
        params = ProximityParameters()
        
        # Basic parameters
        params.beam_energy = beam_energy
        if material_info:
            params.substrate_material = material_info.get('substrate', 'Si')
            params.resist_material = material_info.get('resist', 'PMMA')
            params.resist_thickness = material_info.get('resist_thickness', 100.0)
            params.substrate_thickness = material_info.get('substrate_thickness', 1000.0)
        
        # Extract fitted parameters
        if 'forward_range' in fitted_params:
            params.forward_range = fitted_params['forward_range']
            params.forward_range_err = fitted_params.get('forward_range_err', 0.0)
        
        if 'backscatter_range' in fitted_params:
            params.backscatter_range = fitted_params['backscatter_range']
            params.backscatter_range_err = fitted_params.get('backscatter_range_err', 0.0)
        
        if 'forward_amplitude' in fitted_params:
            params.forward_amplitude = fitted_params['forward_amplitude']
            params.forward_amplitude_err = fitted_params.get('forward_amplitude_err', 0.0)
        
        if 'backscatter_amplitude' in fitted_params:
            params.backscatter_amplitude = fitted_params['backscatter_amplitude']
            params.backscatter_amplitude_err = fitted_params.get('backscatter_amplitude_err', 0.0)
        
        # Calculate derived parameters
        total_amplitude = params.forward_amplitude + params.backscatter_amplitude
        if total_amplitude > 0:
            params.eta = params.backscatter_amplitude / total_amplitude
            # Error propagation for eta
            if params.forward_amplitude_err > 0 and params.backscatter_amplitude_err > 0:
                eta_var = (params.backscatter_amplitude_err / total_amplitude)**2 + \
                         (params.eta * params.forward_amplitude_err / total_amplitude)**2
                params.eta_err = np.sqrt(eta_var)
        
        if params.forward_range > 0 and params.backscatter_range > 0:
            params.alpha = params.backscatter_range / params.forward_range
            # Error propagation for alpha
            if params.forward_range_err > 0 and params.backscatter_range_err > 0:
                alpha_var = (params.backscatter_range_err / params.forward_range)**2 + \
                           (params.alpha * params.forward_range_err / params.forward_range)**2
                params.alpha_err = np.sqrt(alpha_var)
        
        # Beta parameter (proximity function parameter)
        if params.eta > 0 and params.alpha > 0:
            params.beta = params.eta / (1 + params.alpha**2)
            # Simplified error propagation
            params.beta_err = params.eta_err / (1 + params.alpha**2)
        
        # Statistical measures
        params.r_squared = fit_diagnostics.get('r_squared', 0.0)
        params.chi_squared = fit_diagnostics.get('chi_squared', np.inf)
        params.reduced_chi_squared = fit_diagnostics.get('reduced_chi_squared', np.inf)
        params.p_value = fit_diagnostics.get('p_value', 1.0)
        
        # Cross-validation results
        params.cv_scores = cv_results.get('cv_scores', [])
        params.cv_mean = cv_results.get('cv_mean', 0.0)
        params.cv_std = cv_results.get('cv_std', 0.0)
        
        # Model selection metrics
        params.aic = model_metrics.get('aic', np.inf)
        params.bic = model_metrics.get('bic', np.inf)
        
        # Confidence intervals
        params.confidence_level = self.confidence_level
        for key, value in fitted_params.items():
            if key.endswith('_ci'):
                param_name = key[:-3]  # Remove '_ci' suffix
                params.confidence_intervals[param_name] = value
        
        return params
    
    # Proximity models
    def _single_gaussian_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Single Gaussian proximity function"""
        A = params.get('amplitude', 1.0)
        sigma = params.get('range', 1.0)
        return A * np.exp(-r**2 / (2 * sigma**2))
    
    def _double_gaussian_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Double Gaussian proximity function (forward + backscatter)"""
        A_f = params.get('forward_amplitude', 1.0)
        sigma_f = params.get('forward_range', 1.0)
        A_b = params.get('backscatter_amplitude', 0.3)
        sigma_b = params.get('backscatter_range', 10.0)
        
        forward = A_f * np.exp(-r**2 / (2 * sigma_f**2))
        backscatter = A_b * np.exp(-r**2 / (2 * sigma_b**2))
        
        return forward + backscatter
    
    def _gaussian_exponential_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Gaussian + exponential proximity function"""
        A_f = params.get('forward_amplitude', 1.0)
        sigma_f = params.get('forward_range', 1.0)
        A_b = params.get('backscatter_amplitude', 0.3)
        lambda_b = params.get('backscatter_decay', 10.0)
        
        forward = A_f * np.exp(-r**2 / (2 * sigma_f**2))
        backscatter = A_b * np.exp(-r / lambda_b)
        
        return forward + backscatter
    
    def _power_law_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Power law proximity function"""
        A = params.get('amplitude', 1.0)
        r0 = params.get('characteristic_range', 1.0)
        gamma = params.get('power_index', 2.0)
        
        return A / (1 + (r / r0)**gamma)
    
    def _voigt_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Voigt profile proximity function"""
        A = params.get('amplitude', 1.0)
        sigma = params.get('gaussian_width', 1.0)
        gamma = params.get('lorentzian_width', 1.0)
        
        # Simplified Voigt approximation (pseudo-Voigt)
        eta = 1.36603 * (gamma / (gamma + sigma)) - 0.47719 * (gamma / (gamma + sigma))**2 + \
              0.11116 * (gamma / (gamma + sigma))**3
        
        gaussian = np.exp(-r**2 / (2 * sigma**2))
        lorentzian = 1 / (1 + (r / gamma)**2)
        
        return A * (eta * lorentzian + (1 - eta) * gaussian)
    
    def _bethe_bloch_proximity(self, r: np.ndarray, params: Dict) -> np.ndarray:
        """Bethe-Bloch inspired proximity function"""
        A = params.get('amplitude', 1.0)
        r0 = params.get('characteristic_range', 1.0)
        n = params.get('power_parameter', 1.5)
        
        return A * (r0 / (r + r0))**n
    
    def _generate_initial_guess(self, radius: np.ndarray, dose_profile: np.ndarray, 
                               model: str) -> Dict:
        """Generate intelligent initial parameter guess"""
        peak_dose = dose_profile.max()
        
        # Find characteristic ranges
        half_max = peak_dose / 2
        above_half = dose_profile > half_max
        if above_half.any():
            forward_range_estimate = radius[above_half].max()
        else:
            forward_range_estimate = radius.max() * 0.1
        
        tenth_max = peak_dose * 0.1
        above_tenth = dose_profile > tenth_max
        if above_tenth.any():
            backscatter_range_estimate = radius[above_tenth].max()
        else:
            backscatter_range_estimate = radius.max() * 0.5
        
        # Model-specific initial guesses
        if model == 'single_gaussian':
            return {
                'amplitude': peak_dose,
                'range': forward_range_estimate
            }
        
        elif model == 'double_gaussian':
            return {
                'forward_amplitude': peak_dose * 0.8,
                'forward_range': forward_range_estimate,
                'backscatter_amplitude': peak_dose * 0.2,
                'backscatter_range': backscatter_range_estimate
            }
        
        elif model == 'gaussian_exponential':
            return {
                'forward_amplitude': peak_dose * 0.8,
                'forward_range': forward_range_estimate,
                'backscatter_amplitude': peak_dose * 0.2,
                'backscatter_decay': backscatter_range_estimate
            }
        
        elif model == 'power_law':
            return {
                'amplitude': peak_dose,
                'characteristic_range': forward_range_estimate,
                'power_index': 2.0
            }
        
        elif model == 'voigt':
            return {
                'amplitude': peak_dose,
                'gaussian_width': forward_range_estimate,
                'lorentzian_width': forward_range_estimate * 0.5
            }
        
        elif model == 'bethe_bloch':
            return {
                'amplitude': peak_dose,
                'characteristic_range': forward_range_estimate,
                'power_parameter': 1.5
            }
        
        else:
            raise ValueError(f"No initial guess generator for model: {model}")
    
    def _get_parameter_bounds(self, model: str, max_dose: float, max_radius: float) -> Tuple[List, List]:
        """Get reasonable parameter bounds for fitting"""
        if model == 'single_gaussian':
            lower = [0, 0.1]
            upper = [max_dose * 2, max_radius]
        
        elif model == 'double_gaussian':
            lower = [0, 0.1, 0, 1.0]
            upper = [max_dose * 2, max_radius * 0.1, max_dose, max_radius]
        
        elif model == 'gaussian_exponential':
            lower = [0, 0.1, 0, 1.0]
            upper = [max_dose * 2, max_radius * 0.1, max_dose, max_radius * 2]
        
        elif model == 'power_law':
            lower = [0, 0.1, 0.5]
            upper = [max_dose * 2, max_radius, 10.0]
        
        elif model == 'voigt':
            lower = [0, 0.1, 0.1]
            upper = [max_dose * 2, max_radius, max_radius]
        
        elif model == 'bethe_bloch':
            lower = [0, 0.1, 0.5]
            upper = [max_dose * 2, max_radius, 5.0]
        
        else:
            # Default bounds
            n_params = 4  # Assume most models have ~4 parameters
            lower = [0] * n_params
            upper = [max_dose * 2] * n_params
        
        return lower, upper


def main():
    """Demonstration of proximity effect parameter extraction"""
    print("Proximity Effect Parameter Extraction Toolkit Demo")
    print("=" * 55)
    
    # Initialize extractor
    extractor = ProximityEffectExtractor(confidence_level=0.95, n_bootstrap=100)  # Reduced for demo
    
    # Create synthetic proximity effect data
    def create_synthetic_proximity_data(n_points: int = 1000):
        """Create synthetic proximity effect data"""
        print("Creating synthetic proximity effect data...")
        
        # True parameters
        true_params = {
            'forward_amplitude': 100.0,
            'forward_range': 5.0,
            'backscatter_amplitude': 30.0,
            'backscatter_range': 50.0
        }
        
        # Generate radial coordinates
        radius = np.linspace(0.1, 200, n_points)
        
        # Generate true proximity function (double Gaussian)
        forward = true_params['forward_amplitude'] * np.exp(-radius**2 / (2 * true_params['forward_range']**2))
        backscatter = true_params['backscatter_amplitude'] * np.exp(-radius**2 / (2 * true_params['backscatter_range']**2))
        
        true_dose = forward + backscatter
        
        # Add realistic noise
        noise_level = 0.05  # 5% noise
        noise = np.random.normal(0, true_dose * noise_level)
        dose_with_noise = true_dose + noise
        dose_with_noise = np.maximum(dose_with_noise, true_dose * 0.01)  # Prevent negative values
        
        # Estimate uncertainties
        dose_std = true_dose * noise_level + 0.1  # Minimum uncertainty
        
        print(f"Generated {n_points} data points with true parameters:")
        for param, value in true_params.items():
            print(f"  {param}: {value}")
        
        return radius, dose_with_noise, dose_std, true_params
    
    # Generate test data
    radius, dose_profile, dose_std, true_params = create_synthetic_proximity_data(500)
    
    # Create test DataFrame
    test_df = pd.DataFrame({
        'X[nm]': radius * np.cos(np.linspace(0, 2*np.pi, len(radius))),
        'Y[nm]': radius * np.sin(np.linspace(0, 2*np.pi, len(radius))),
        'Dose[uC/cm^2]': dose_profile
    })
    
    try:
        # Extract proximity parameters
        print("\nExtracting proximity effect parameters...")
        
        material_info = {
            'substrate': 'Si',
            'resist': 'PMMA',
            'resist_thickness': 100.0,
            'substrate_thickness': 1000.0
        }
        
        proximity_params = extractor.extract_proximity_parameters(
            test_df,
            model='double_gaussian',
            beam_energy=100.0,
            material_info=material_info
        )
        
        # Display results
        print(f"\nExtraction Results:")
        print(f"Forward range: {proximity_params.forward_range:.2f} ± {proximity_params.forward_range_err:.2f} nm")
        print(f"  True value: {true_params['forward_range']:.2f} nm")
        print(f"  Relative error: {abs(proximity_params.forward_range - true_params['forward_range'])/true_params['forward_range']*100:.1f}%")
        
        print(f"\nBackscatter range: {proximity_params.backscatter_range:.2f} ± {proximity_params.backscatter_range_err:.2f} nm")
        print(f"  True value: {true_params['backscatter_range']:.2f} nm")
        print(f"  Relative error: {abs(proximity_params.backscatter_range - true_params['backscatter_range'])/true_params['backscatter_range']*100:.1f}%")
        
        print(f"\nForward amplitude: {proximity_params.forward_amplitude:.2f} ± {proximity_params.forward_amplitude_err:.2f}")
        print(f"  True value: {true_params['forward_amplitude']:.2f}")
        
        print(f"\nBackscatter amplitude: {proximity_params.backscatter_amplitude:.2f} ± {proximity_params.backscatter_amplitude_err:.2f}")
        print(f"  True value: {true_params['backscatter_amplitude']:.2f}")
        
        print(f"\nDerived Parameters:")
        print(f"η (backscatter ratio): {proximity_params.eta:.3f} ± {proximity_params.eta_err:.3f}")
        true_eta = true_params['backscatter_amplitude'] / (true_params['forward_amplitude'] + true_params['backscatter_amplitude'])
        print(f"  True value: {true_eta:.3f}")
        
        print(f"α (range ratio): {proximity_params.alpha:.2f} ± {proximity_params.alpha_err:.2f}")
        true_alpha = true_params['backscatter_range'] / true_params['forward_range']
        print(f"  True value: {true_alpha:.2f}")
        
        print(f"\nStatistical Quality:")
        print(f"R²: {proximity_params.r_squared:.4f}")
        print(f"Reduced χ²: {proximity_params.reduced_chi_squared:.4f}")
        print(f"p-value: {proximity_params.p_value:.2e}")
        
        print(f"\nCross-validation:")
        print(f"CV score: {proximity_params.cv_mean:.4f} ± {proximity_params.cv_std:.4f}")
        print(f"Successful folds: {len(proximity_params.cv_scores)}")
        
        print(f"\nModel Selection:")
        print(f"AIC: {proximity_params.aic:.2f}")
        print(f"BIC: {proximity_params.bic:.2f}")
        
        # Create visualization
        print("\nGenerating proximity effect visualization...")
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Plot 1: Data and fit
        fitted_dose = extractor._double_gaussian_proximity(radius, {
            'forward_amplitude': proximity_params.forward_amplitude,
            'forward_range': proximity_params.forward_range,
            'backscatter_amplitude': proximity_params.backscatter_amplitude,
            'backscatter_range': proximity_params.backscatter_range
        })
        
        ax1.errorbar(radius, dose_profile, yerr=dose_std, fmt='o', alpha=0.5, markersize=3, label='Data')
        ax1.plot(radius, fitted_dose, 'r-', linewidth=2, label='Fitted Model')
        
        # Plot components
        forward_component = proximity_params.forward_amplitude * np.exp(-radius**2 / (2 * proximity_params.forward_range**2))
        backscatter_component = proximity_params.backscatter_amplitude * np.exp(-radius**2 / (2 * proximity_params.backscatter_range**2))
        
        ax1.plot(radius, forward_component, 'g--', alpha=0.7, label='Forward scatter')
        ax1.plot(radius, backscatter_component, 'm--', alpha=0.7, label='Backscatter')
        
        ax1.set_xlabel('Radius [nm]')
        ax1.set_ylabel('Dose [uC/cm²]')
        ax1.set_title('Proximity Effect Fit')
        ax1.legend()
        ax1.set_yscale('log')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Residuals
        residuals = dose_profile - fitted_dose
        ax2.plot(radius, residuals, 'ko', markersize=3, alpha=0.6)
        ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Radius [nm]')
        ax2.set_ylabel('Residuals')
        ax2.set_title('Fit Residuals')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Parameter confidence intervals
        param_names = ['Forward\nRange', 'Backscatter\nRange', 'Forward\nAmplitude', 'Backscatter\nAmplitude']
        param_values = [proximity_params.forward_range, proximity_params.backscatter_range,
                       proximity_params.forward_amplitude, proximity_params.backscatter_amplitude]
        param_errors = [proximity_params.forward_range_err, proximity_params.backscatter_range_err,
                       proximity_params.forward_amplitude_err, proximity_params.backscatter_amplitude_err]
        
        x_pos = np.arange(len(param_names))
        ax3.bar(x_pos, param_values, yerr=param_errors, capsize=5, alpha=0.7)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(param_names)
        ax3.set_ylabel('Parameter Value')
        ax3.set_title('Extracted Parameters with Uncertainties')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Cross-validation scores
        if proximity_params.cv_scores:
            ax4.hist(proximity_params.cv_scores, bins=min(10, len(proximity_params.cv_scores)), 
                    alpha=0.7, edgecolor='black')
            ax4.axvline(proximity_params.cv_mean, color='red', linestyle='--', 
                       label=f'Mean: {proximity_params.cv_mean:.3f}')
            ax4.set_xlabel('R² Score')
            ax4.set_ylabel('Frequency')
            ax4.set_title('Cross-Validation Scores')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'No CV results', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Cross-Validation Results')
        
        plt.tight_layout()
        plt.savefig('proximity_effect_analysis.png', dpi=150, bbox_inches='tight')
        
        # Save results
        results_dict = proximity_params.to_dict()
        with open('proximity_parameters.json', 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        
        print("Results saved:")
        print("- proximity_effect_analysis.png (visualization)")
        print("- proximity_parameters.json (extracted parameters)")
        
        plt.show()
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nProximity effect parameter extraction demonstration complete!")


if __name__ == "__main__":
    main()