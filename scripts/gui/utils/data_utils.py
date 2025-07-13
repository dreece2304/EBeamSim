"""
Data processing utilities for EBL simulation GUI
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any, Optional
import scipy.interpolate
import scipy.signal


class DataUtils:
    """Utility functions for data processing and analysis"""
    
    @staticmethod
    def normalize_data(data: np.ndarray, method: str = 'max') -> np.ndarray:
        """Normalize data using different methods"""
        if len(data) == 0:
            return data
        
        if method == 'max':
            max_val = np.max(data)
            return data / max_val if max_val != 0 else data
        elif method == 'sum':
            sum_val = np.sum(data)
            return data / sum_val if sum_val != 0 else data
        elif method == 'unit':
            # Normalize to unit vector
            norm = np.linalg.norm(data)
            return data / norm if norm != 0 else data
        else:
            return data
    
    @staticmethod
    def smooth_data(data: np.ndarray, window_size: int = 5, method: str = 'savgol') -> np.ndarray:
        """Smooth data using different methods"""
        if len(data) < window_size:
            return data
        
        if method == 'savgol':
            # Ensure window_size is odd
            if window_size % 2 == 0:
                window_size += 1
            poly_order = min(3, window_size - 1)
            return scipy.signal.savgol_filter(data, window_size, poly_order)
        elif method == 'moving_average':
            return np.convolve(data, np.ones(window_size)/window_size, mode='same')
        elif method == 'gaussian':
            sigma = window_size / 4.0
            return scipy.signal.gaussian_filter1d(data, sigma)
        else:
            return data
    
    @staticmethod
    def interpolate_data(
        x: np.ndarray, 
        y: np.ndarray, 
        x_new: np.ndarray, 
        method: str = 'linear'
    ) -> np.ndarray:
        """Interpolate data to new x values"""
        try:
            interpolator = scipy.interpolate.interp1d(
                x, y, kind=method, bounds_error=False, fill_value=0.0
            )
            return interpolator(x_new)
        except Exception:
            # Fallback to nearest neighbor
            interpolator = scipy.interpolate.interp1d(
                x, y, kind='nearest', bounds_error=False, fill_value=0.0
            )
            return interpolator(x_new)
    
    @staticmethod
    def calculate_fwhm(x: np.ndarray, y: np.ndarray) -> float:
        """Calculate Full Width Half Maximum"""
        if len(y) == 0:
            return 0.0
        
        max_val = np.max(y)
        half_max = max_val / 2.0
        
        # Find indices where y >= half_max
        indices = np.where(y >= half_max)[0]
        
        if len(indices) == 0:
            return 0.0
        
        # FWHM is the width of the region above half maximum
        x_min = x[indices[0]]
        x_max = x[indices[-1]]
        
        return x_max - x_min
    
    @staticmethod
    def calculate_statistics(data: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive statistics for data"""
        if len(data) == 0:
            return {}
        
        valid_data = data[np.isfinite(data)]
        
        if len(valid_data) == 0:
            return {}
        
        return {
            'mean': np.mean(valid_data),
            'median': np.median(valid_data),
            'std': np.std(valid_data),
            'min': np.min(valid_data),
            'max': np.max(valid_data),
            'q25': np.percentile(valid_data, 25),
            'q75': np.percentile(valid_data, 75),
            'count': len(valid_data),
            'sum': np.sum(valid_data)
        }
    
    @staticmethod
    def create_log_bins(min_val: float, max_val: float, num_bins: int) -> np.ndarray:
        """Create logarithmically spaced bins"""
        if min_val <= 0:
            min_val = 1e-9  # Small positive value
        
        return np.logspace(np.log10(min_val), np.log10(max_val), num_bins)
    
    @staticmethod
    def create_linear_bins(min_val: float, max_val: float, num_bins: int) -> np.ndarray:
        """Create linearly spaced bins"""
        return np.linspace(min_val, max_val, num_bins)
    
    @staticmethod
    def bin_data_2d(
        x: np.ndarray, 
        y: np.ndarray, 
        values: np.ndarray,
        x_bins: np.ndarray, 
        y_bins: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bin 2D data and return binned coordinates and values"""
        # Create 2D histogram
        hist, x_edges, y_edges = np.histogram2d(x, y, bins=[x_bins, y_bins], weights=values)
        counts, _, _ = np.histogram2d(x, y, bins=[x_bins, y_bins])
        
        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            hist = np.divide(hist, counts, out=np.zeros_like(hist), where=counts!=0)
        
        # Create coordinate arrays for bin centers
        x_centers = (x_edges[:-1] + x_edges[1:]) / 2
        y_centers = (y_edges[:-1] + y_edges[1:]) / 2
        
        X, Y = np.meshgrid(x_centers, y_centers)
        
        return X, Y, hist.T
    
    @staticmethod
    def remove_outliers(data: np.ndarray, method: str = 'iqr', factor: float = 1.5) -> np.ndarray:
        """Remove outliers from data"""
        if len(data) == 0:
            return data
        
        if method == 'iqr':
            q25, q75 = np.percentile(data, [25, 75])
            iqr = q75 - q25
            lower_bound = q25 - factor * iqr
            upper_bound = q75 + factor * iqr
            return data[(data >= lower_bound) & (data <= upper_bound)]
        
        elif method == 'zscore':
            z_scores = np.abs((data - np.mean(data)) / np.std(data))
            return data[z_scores < factor]
        
        else:
            return data
    
    @staticmethod
    def resample_data(
        x: np.ndarray, 
        y: np.ndarray, 
        target_points: int,
        method: str = 'linear'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Resample data to target number of points"""
        if len(x) <= target_points:
            return x, y
        
        x_new = np.linspace(x.min(), x.max(), target_points)
        y_new = DataUtils.interpolate_data(x, y, x_new, method)
        
        return x_new, y_new
    
    @staticmethod
    def find_peaks(data: np.ndarray, prominence: float = 0.1) -> np.ndarray:
        """Find peaks in data"""
        if len(data) < 3:
            return np.array([])
        
        # Normalize prominence relative to data range
        data_range = np.max(data) - np.min(data)
        abs_prominence = prominence * data_range
        
        peaks, _ = scipy.signal.find_peaks(data, prominence=abs_prominence)
        return peaks
    
    @staticmethod
    def calculate_centroid(x: np.ndarray, y: np.ndarray) -> float:
        """Calculate centroid (weighted average) position"""
        if len(x) != len(y) or len(x) == 0:
            return 0.0
        
        total_weight = np.sum(y)
        if total_weight == 0:
            return np.mean(x)
        
        return np.sum(x * y) / total_weight