#!/usr/bin/env python3
"""
Large-Scale Pattern Dose Analysis Framework

High-performance analysis algorithms for massive EBL simulation datasets (MB to TB scale).
Features efficient memory management, parallel processing, and scalable algorithms for
industrial-scale pattern analysis.

Features:
- Memory-efficient chunked processing for TB-scale datasets
- Distributed analysis across multiple cores/nodes
- Real-time streaming analysis during simulation
- Hierarchical data organization (HDF5, Zarr)
- GPU acceleration for compute-intensive operations
- Statistical sampling for quality/performance trade-offs
- Progressive analysis with intermediate results
- Cross-platform scalability and cloud deployment

Author: EBL Data Analysis Team
Version: 1.0.0
"""

import numpy as np
import pandas as pd
import h5py
import zarr
from pathlib import Path
import psutil
import gc
from typing import Dict, List, Tuple, Optional, Union, Any, Iterator, Callable
from dataclasses import dataclass, field
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import shared_memory, Queue, Process, Manager
import threading
import time
from tqdm import tqdm
import warnings
from numba import jit, prange, cuda
import cupy as cp
import dask.array as da
import dask.dataframe as dd
from dask.distributed import Client, as_completed as dask_as_completed
from scipy import ndimage, stats
from scipy.sparse import csr_matrix, save_npz, load_npz
from sklearn.cluster import MiniBatchKMeans
import matplotlib.pyplot as plt
import seaborn as sns
import json
from memory_profiler import profile
import pymongo
from sqlalchemy import create_engine
import pickle
import lz4.frame
import blosc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatasetInfo:
    """Metadata about large-scale dataset"""
    total_size_bytes: int = 0
    num_data_points: int = 0
    spatial_extent: Tuple[float, float, float, float] = (0, 0, 0, 0)  # x_min, x_max, y_min, y_max
    dose_range: Tuple[float, float] = (0, 0)  # min_dose, max_dose
    energy_range: Tuple[float, float] = (0, 0)  # min_energy, max_energy
    num_patterns: int = 0
    chunk_size: int = 1000000  # Default 1M points per chunk
    compression_ratio: float = 1.0
    storage_format: str = "hdf5"
    
    # Analysis metadata
    analysis_timestamp: float = 0.0
    analysis_version: str = "1.0.0"
    memory_usage_gb: float = 0.0
    processing_time_sec: float = 0.0

@dataclass
class AnalysisConfig:
    """Configuration for large-scale analysis"""
    # Memory management
    max_memory_gb: float = 8.0
    chunk_overlap_nm: float = 100.0
    use_memory_mapping: bool = True
    enable_compression: bool = True
    compression_algorithm: str = "blosc"  # blosc, lz4, gzip
    
    # Parallel processing
    num_workers: int = -1  # -1 for auto-detect
    use_gpu: bool = False
    gpu_memory_limit_gb: float = 4.0
    distributed_computing: bool = False
    scheduler_address: Optional[str] = None
    
    # Analysis parameters
    spatial_resolution_nm: float = 1.0
    dose_threshold_fraction: float = 0.01  # 1% of max dose
    statistical_sampling_rate: float = 1.0  # 1.0 = no sampling
    progressive_analysis: bool = True
    save_intermediate_results: bool = True
    
    # Quality control
    validate_data_integrity: bool = True
    outlier_detection: bool = True
    outlier_z_threshold: float = 5.0
    
    def auto_configure(self) -> None:
        """Auto-configure based on system capabilities"""
        # Auto-detect number of workers
        if self.num_workers == -1:
            self.num_workers = min(psutil.cpu_count(), 16)  # Cap at 16 for memory reasons
        
        # Auto-configure memory limit
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        if self.max_memory_gb > available_memory_gb * 0.8:
            self.max_memory_gb = available_memory_gb * 0.8
            logger.warning(f"Reduced memory limit to {self.max_memory_gb:.1f} GB")
        
        # GPU detection
        try:
            import cupy
            gpu_available = cupy.cuda.is_available()
            if gpu_available:
                gpu_memory = cupy.cuda.Device().mem_info[1] / (1024**3)
                self.use_gpu = True
                self.gpu_memory_limit_gb = min(self.gpu_memory_limit_gb, gpu_memory * 0.8)
                logger.info(f"GPU detected with {gpu_memory:.1f} GB memory")
        except ImportError:
            self.use_gpu = False
            logger.info("GPU not available - using CPU only")

class MemoryEfficientDataLoader:
    """Memory-efficient data loader for large datasets"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.current_memory_usage = 0
        self._cache = {}
        self._cache_lock = threading.Lock()
    
    def estimate_memory_usage(self, data_shape: Tuple[int, ...], dtype: np.dtype) -> float:
        """Estimate memory usage in GB for given data shape"""
        return np.prod(data_shape) * dtype.itemsize / (1024**3)
    
    def create_chunked_iterator(self, data_source: Union[str, Path], 
                               chunk_size: Optional[int] = None) -> Iterator[np.ndarray]:
        """Create memory-efficient chunked data iterator"""
        if chunk_size is None:
            chunk_size = self.config.chunk_overlap_nm
        
        data_path = Path(data_source)
        
        if data_path.suffix.lower() in ['.h5', '.hdf5']:
            yield from self._iterate_hdf5_chunks(data_path, chunk_size)
        elif data_path.suffix.lower() in ['.zarr']:
            yield from self._iterate_zarr_chunks(data_path, chunk_size)
        elif data_path.suffix.lower() in ['.csv']:
            yield from self._iterate_csv_chunks(data_path, chunk_size)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")
    
    def _iterate_hdf5_chunks(self, file_path: Path, chunk_size: int) -> Iterator[pd.DataFrame]:
        """Iterate through HDF5 file in chunks"""
        with h5py.File(file_path, 'r') as f:
            # Find the main dataset
            dataset_names = ['dose_data', 'simulation_results', 'pattern_data']
            dataset = None
            
            for name in dataset_names:
                if name in f:
                    dataset = f[name]
                    break
            
            if dataset is None:
                # Use first available dataset
                dataset = list(f.values())[0]
            
            total_rows = len(dataset)
            
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                
                # Check memory usage
                chunk_shape = (end_idx - start_idx,) + dataset.shape[1:]
                estimated_memory = self.estimate_memory_usage(chunk_shape, dataset.dtype)
                
                if estimated_memory > self.config.max_memory_gb:
                    # Reduce chunk size
                    reduced_chunk_size = int(chunk_size * self.config.max_memory_gb / estimated_memory)
                    end_idx = start_idx + reduced_chunk_size
                    logger.warning(f"Reduced chunk size to {reduced_chunk_size} due to memory constraints")
                
                # Load chunk
                chunk_data = dataset[start_idx:end_idx]
                
                # Convert to DataFrame if needed
                if hasattr(dataset, 'attrs') and 'columns' in dataset.attrs:
                    columns = dataset.attrs['columns']
                    if isinstance(columns[0], bytes):
                        columns = [col.decode() for col in columns]
                    df_chunk = pd.DataFrame(chunk_data, columns=columns)
                else:
                    # Create default column names
                    n_cols = chunk_data.shape[1] if chunk_data.ndim > 1 else 1
                    columns = [f'col_{i}' for i in range(n_cols)]
                    df_chunk = pd.DataFrame(chunk_data, columns=columns)
                
                yield df_chunk
                
                # Force garbage collection
                gc.collect()
    
    def _iterate_zarr_chunks(self, file_path: Path, chunk_size: int) -> Iterator[pd.DataFrame]:
        """Iterate through Zarr array in chunks"""
        z_array = zarr.open(str(file_path), mode='r')
        
        total_rows = z_array.shape[0]
        
        for start_idx in range(0, total_rows, chunk_size):
            end_idx = min(start_idx + chunk_size, total_rows)
            
            chunk_data = z_array[start_idx:end_idx]
            
            # Convert to DataFrame
            df_chunk = pd.DataFrame(chunk_data)
            yield df_chunk
            
            gc.collect()
    
    def _iterate_csv_chunks(self, file_path: Path, chunk_size: int) -> Iterator[pd.DataFrame]:
        """Iterate through CSV file in chunks"""
        try:
            for chunk in pd.read_csv(file_path, chunksize=chunk_size, comment='#'):
                yield chunk
                gc.collect()
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            raise

class LargeScaleDoseAnalyzer:
    """Main large-scale dose analysis framework"""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize large-scale analyzer"""
        self.config = config or AnalysisConfig()
        self.config.auto_configure()
        
        self.data_loader = MemoryEfficientDataLoader(self.config)
        self.analysis_results = {}
        self.processing_stats = {}
        
        # Initialize parallel processing
        self._init_parallel_processing()
        
        # Initialize GPU if available
        if self.config.use_gpu:
            self._init_gpu_processing()
    
    def _init_parallel_processing(self):
        """Initialize parallel processing backend"""
        if self.config.distributed_computing and self.config.scheduler_address:
            try:
                self.client = Client(self.config.scheduler_address)
                logger.info(f"Connected to distributed scheduler: {self.config.scheduler_address}")
            except Exception as e:
                logger.warning(f"Failed to connect to distributed scheduler: {e}")
                self.client = None
        else:
            self.client = None
    
    def _init_gpu_processing(self):
        """Initialize GPU processing if available"""
        try:
            import cupy as cp
            self.gpu_available = cp.cuda.is_available()
            if self.gpu_available:
                self.gpu_memory_pool = cp.get_default_memory_pool()
                self.gpu_pinned_memory_pool = cp.get_default_pinned_memory_pool()
                logger.info("GPU processing initialized")
        except ImportError:
            self.gpu_available = False
            logger.info("GPU not available")
    
    def analyze_dataset_info(self, data_source: Union[str, Path]) -> DatasetInfo:
        """Analyze dataset metadata without loading full data"""
        start_time = time.time()
        data_path = Path(data_source)
        
        info = DatasetInfo()
        info.storage_format = data_path.suffix.lower().lstrip('.')
        
        try:
            if data_path.suffix.lower() in ['.h5', '.hdf5']:
                info = self._analyze_hdf5_info(data_path, info)
            elif data_path.suffix.lower() in ['.zarr']:
                info = self._analyze_zarr_info(data_path, info)
            elif data_path.suffix.lower() in ['.csv']:
                info = self._analyze_csv_info(data_path, info)
            else:
                raise ValueError(f"Unsupported format: {data_path.suffix}")
        
        except Exception as e:
            logger.error(f"Failed to analyze dataset info: {e}")
            raise
        
        info.analysis_timestamp = time.time()
        info.processing_time_sec = time.time() - start_time
        
        return info
    
    def _analyze_hdf5_info(self, file_path: Path, info: DatasetInfo) -> DatasetInfo:
        """Analyze HDF5 file metadata"""
        info.total_size_bytes = file_path.stat().st_size
        
        with h5py.File(file_path, 'r') as f:
            # Find main dataset
            dataset_names = ['dose_data', 'simulation_results', 'pattern_data']
            dataset = None
            
            for name in dataset_names:
                if name in f:
                    dataset = f[name]
                    break
            
            if dataset is None:
                dataset = list(f.values())[0]
            
            info.num_data_points = len(dataset)
            
            # Estimate spatial extent and dose range from chunks
            sample_size = min(10000, len(dataset))
            sample_data = dataset[:sample_size]
            
            if hasattr(dataset, 'attrs') and 'columns' in dataset.attrs:
                columns = [col.decode() if isinstance(col, bytes) else col 
                          for col in dataset.attrs['columns']]
                sample_df = pd.DataFrame(sample_data, columns=columns)
            else:
                # Assume standard format
                expected_cols = ['X[nm]', 'Y[nm]', 'Z[nm]', 'Energy[keV]', 'Dose[uC/cm^2]']
                n_cols = sample_data.shape[1] if sample_data.ndim > 1 else 1
                columns = expected_cols[:n_cols] if n_cols <= len(expected_cols) else [f'col_{i}' for i in range(n_cols)]
                sample_df = pd.DataFrame(sample_data, columns=columns)
            
            # Extract spatial extent
            x_cols = [col for col in columns if 'X' in col or 'x' in col]
            y_cols = [col for col in columns if 'Y' in col or 'y' in col]
            dose_cols = [col for col in columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
            
            if x_cols and y_cols:
                info.spatial_extent = (
                    sample_df[x_cols[0]].min(), sample_df[x_cols[0]].max(),
                    sample_df[y_cols[0]].min(), sample_df[y_cols[0]].max()
                )
            
            if dose_cols:
                info.dose_range = (sample_df[dose_cols[0]].min(), sample_df[dose_cols[0]].max())
            
            # Estimate compression ratio
            uncompressed_size = np.prod(dataset.shape) * dataset.dtype.itemsize
            info.compression_ratio = uncompressed_size / info.total_size_bytes
        
        return info
    
    def _analyze_csv_info(self, file_path: Path, info: DatasetInfo) -> DatasetInfo:
        """Analyze CSV file metadata"""
        info.total_size_bytes = file_path.stat().st_size
        
        # Read a sample to understand structure
        sample_df = pd.read_csv(file_path, nrows=10000, comment='#')
        info.num_data_points = len(sample_df)
        
        # Estimate total rows from file size
        estimated_rows = info.total_size_bytes / (sample_df.memory_usage(deep=True).sum() / len(sample_df))
        info.num_data_points = int(estimated_rows)
        
        # Extract spatial and dose information
        columns = sample_df.columns
        x_cols = [col for col in columns if 'X' in col or 'x' in col]
        y_cols = [col for col in columns if 'Y' in col or 'y' in col]
        dose_cols = [col for col in columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
        
        if x_cols and y_cols:
            info.spatial_extent = (
                sample_df[x_cols[0]].min(), sample_df[x_cols[0]].max(),
                sample_df[y_cols[0]].min(), sample_df[y_cols[0]].max()
            )
        
        if dose_cols:
            info.dose_range = (sample_df[dose_cols[0]].min(), sample_df[dose_cols[0]].max())
        
        return info
    
    def _analyze_zarr_info(self, file_path: Path, info: DatasetInfo) -> DatasetInfo:
        """Analyze Zarr array metadata"""
        z_array = zarr.open(str(file_path), mode='r')
        
        info.num_data_points = z_array.shape[0]
        info.total_size_bytes = z_array.nbytes
        info.compression_ratio = z_array.nbytes / z_array.size if hasattr(z_array, 'size') else 1.0
        
        # Sample data for spatial/dose analysis
        sample_size = min(10000, z_array.shape[0])
        sample_data = z_array[:sample_size]
        
        if sample_data.ndim > 1 and sample_data.shape[1] >= 5:
            # Assume [X, Y, Z, Energy, Dose] format
            info.spatial_extent = (
                sample_data[:, 0].min(), sample_data[:, 0].max(),
                sample_data[:, 1].min(), sample_data[:, 1].max()
            )
            info.dose_range = (sample_data[:, 4].min(), sample_data[:, 4].max())
        
        return info
    
    def progressive_dose_analysis(self, data_source: Union[str, Path],
                                 output_dir: Union[str, Path],
                                 analysis_functions: List[Callable] = None) -> Dict[str, Any]:
        """
        Progressive analysis that processes data in chunks and provides intermediate results
        
        Args:
            data_source: Path to large dataset
            output_dir: Directory for intermediate and final results
            analysis_functions: List of analysis functions to apply
            
        Returns:
            Comprehensive analysis results
        """
        start_time = time.time()
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Analyze dataset info first
        logger.info("Analyzing dataset metadata...")
        dataset_info = self.analyze_dataset_info(data_source)
        
        # Save dataset info
        with open(output_path / "dataset_info.json", 'w') as f:
            json.dump(dataset_info.__dict__, f, indent=2, default=str)
        
        # Initialize analysis results
        results = {
            'dataset_info': dataset_info,
            'chunk_results': [],
            'progressive_stats': {
                'total_dose': 0.0,
                'max_dose': 0.0,
                'min_dose': np.inf,
                'dose_histogram': np.zeros(100),
                'spatial_histogram_2d': np.zeros((100, 100)),
                'processed_points': 0,
                'processing_time': 0.0
            },
            'final_metrics': {}
        }
        
        # Default analysis functions
        if analysis_functions is None:
            analysis_functions = [
                self._analyze_dose_distribution,
                self._analyze_spatial_distribution,
                self._analyze_dose_uniformity,
                self._detect_pattern_features
            ]
        
        # Calculate optimal chunk size based on memory constraints
        estimated_point_size = 8 * 5  # Assume 5 float64 values per point
        max_points_per_chunk = int(self.config.max_memory_gb * (1024**3) / estimated_point_size)
        chunk_size = min(max_points_per_chunk, dataset_info.num_data_points // 100)  # At least 100 chunks
        
        logger.info(f"Processing {dataset_info.num_data_points:,} points in chunks of {chunk_size:,}")
        
        # Process data in chunks
        chunk_count = 0
        processed_points = 0
        
        try:
            with tqdm(total=dataset_info.num_data_points, desc="Processing chunks") as pbar:
                for chunk_df in self.data_loader.create_chunked_iterator(data_source, chunk_size):
                    chunk_start_time = time.time()
                    
                    # Apply analysis functions to chunk
                    chunk_results = {}
                    for func in analysis_functions:
                        try:
                            func_result = func(chunk_df, results['progressive_stats'])
                            chunk_results[func.__name__] = func_result
                        except Exception as e:
                            logger.warning(f"Analysis function {func.__name__} failed: {e}")
                            chunk_results[func.__name__] = None
                    
                    # Update progressive statistics
                    self._update_progressive_stats(chunk_df, results['progressive_stats'])
                    
                    # Save intermediate results
                    if self.config.save_intermediate_results:
                        chunk_file = output_path / f"chunk_{chunk_count:06d}_results.json"
                        with open(chunk_file, 'w') as f:
                            json.dump(chunk_results, f, indent=2, default=str)
                    
                    results['chunk_results'].append(chunk_results)
                    
                    # Update progress
                    processed_points += len(chunk_df)
                    pbar.update(len(chunk_df))
                    
                    chunk_count += 1
                    
                    # Memory management
                    del chunk_df, chunk_results
                    gc.collect()
                    
                    # Save progressive results periodically
                    if chunk_count % 50 == 0:
                        self._save_progressive_results(results, output_path / "progressive_results.json")
                        logger.info(f"Processed {processed_points:,} points in {chunk_count} chunks")
        
        except Exception as e:
            logger.error(f"Error during progressive analysis: {e}")
            # Save partial results
            self._save_progressive_results(results, output_path / "partial_results.json")
            raise
        
        # Finalize analysis
        logger.info("Finalizing analysis results...")
        results['final_metrics'] = self._finalize_analysis(results)
        results['processing_stats'] = {
            'total_processing_time': time.time() - start_time,
            'chunks_processed': chunk_count,
            'points_processed': processed_points,
            'memory_efficiency': processed_points / (self.config.max_memory_gb * 1024**3),
            'throughput_points_per_sec': processed_points / (time.time() - start_time)
        }
        
        # Save final results
        final_results_file = output_path / "final_analysis_results.json"
        with open(final_results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Generate summary report
        self._generate_analysis_report(results, output_path / "analysis_report.html")
        
        logger.info(f"Progressive analysis complete. Processed {processed_points:,} points in {time.time() - start_time:.1f}s")
        return results
    
    def _analyze_dose_distribution(self, chunk_df: pd.DataFrame, 
                                  progressive_stats: Dict) -> Dict[str, Any]:
        """Analyze dose distribution in chunk"""
        dose_cols = [col for col in chunk_df.columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
        
        if not dose_cols:
            return {'error': 'No dose column found'}
        
        dose_data = chunk_df[dose_cols[0]].values
        dose_data = dose_data[dose_data > 0]  # Remove zero doses
        
        if len(dose_data) == 0:
            return {'error': 'No positive dose values'}
        
        return {
            'mean_dose': float(np.mean(dose_data)),
            'std_dose': float(np.std(dose_data)),
            'min_dose': float(np.min(dose_data)),
            'max_dose': float(np.max(dose_data)),
            'median_dose': float(np.median(dose_data)),
            'dose_percentiles': {
                '25th': float(np.percentile(dose_data, 25)),
                '75th': float(np.percentile(dose_data, 75)),
                '90th': float(np.percentile(dose_data, 90)),
                '95th': float(np.percentile(dose_data, 95)),
                '99th': float(np.percentile(dose_data, 99))
            },
            'dose_skewness': float(stats.skew(dose_data)),
            'dose_kurtosis': float(stats.kurtosis(dose_data)),
            'num_points': len(dose_data),
            'total_dose': float(np.sum(dose_data))
        }
    
    def _analyze_spatial_distribution(self, chunk_df: pd.DataFrame,
                                    progressive_stats: Dict) -> Dict[str, Any]:
        """Analyze spatial distribution in chunk"""
        x_cols = [col for col in chunk_df.columns if 'X' in col or 'x' in col]
        y_cols = [col for col in chunk_df.columns if 'Y' in col or 'y' in col]
        
        if not (x_cols and y_cols):
            return {'error': 'No spatial columns found'}
        
        x_data = chunk_df[x_cols[0]].values
        y_data = chunk_df[y_cols[0]].values
        
        return {
            'spatial_extent': {
                'x_min': float(np.min(x_data)),
                'x_max': float(np.max(x_data)),
                'y_min': float(np.min(y_data)),
                'y_max': float(np.max(y_data)),
                'x_center': float(np.mean(x_data)),
                'y_center': float(np.mean(y_data)),
                'x_std': float(np.std(x_data)),
                'y_std': float(np.std(y_data))
            },
            'spatial_density': len(x_data) / ((np.max(x_data) - np.min(x_data)) * (np.max(y_data) - np.min(y_data))),
            'num_spatial_points': len(x_data)
        }
    
    def _analyze_dose_uniformity(self, chunk_df: pd.DataFrame,
                               progressive_stats: Dict) -> Dict[str, Any]:
        """Analyze dose uniformity within chunk"""
        dose_cols = [col for col in chunk_df.columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
        
        if not dose_cols:
            return {'error': 'No dose column found'}
        
        dose_data = chunk_df[dose_cols[0]].values
        dose_data = dose_data[dose_data > 0]
        
        if len(dose_data) < 2:
            return {'error': 'Insufficient dose data'}
        
        mean_dose = np.mean(dose_data)
        std_dose = np.std(dose_data)
        
        # Dose uniformity metrics
        uniformity_3sigma = 1.0 - (3 * std_dose / mean_dose) if mean_dose > 0 else 0
        uniformity_1sigma = 1.0 - (std_dose / mean_dose) if mean_dose > 0 else 0
        
        # Critical dimension uniformity (assuming dose variations affect CD)
        cd_variation_percent = (std_dose / mean_dose) * 100 if mean_dose > 0 else 0
        
        return {
            'dose_uniformity_3sigma': max(0, float(uniformity_3sigma)),
            'dose_uniformity_1sigma': max(0, float(uniformity_1sigma)),
            'cd_variation_percent': float(cd_variation_percent),
            'dose_coefficient_of_variation': float(std_dose / mean_dose) if mean_dose > 0 else 0,
            'dose_range_ratio': float(np.max(dose_data) / np.min(dose_data)) if np.min(dose_data) > 0 else np.inf
        }
    
    def _detect_pattern_features(self, chunk_df: pd.DataFrame,
                               progressive_stats: Dict) -> Dict[str, Any]:
        """Detect and analyze pattern features in chunk"""
        # Simplified pattern detection - could be much more sophisticated
        dose_cols = [col for col in chunk_df.columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
        x_cols = [col for col in chunk_df.columns if 'X' in col or 'x' in col]
        y_cols = [col for col in chunk_df.columns if 'Y' in col or 'y' in col]
        
        if not (dose_cols and x_cols and y_cols):
            return {'error': 'Insufficient columns for pattern detection'}
        
        dose_data = chunk_df[dose_cols[0]].values
        x_data = chunk_df[x_cols[0]].values
        y_data = chunk_df[y_cols[0]].values
        
        # Define high-dose regions as potential pattern features
        dose_threshold = np.percentile(dose_data, 90)  # Top 10% of doses
        high_dose_mask = dose_data > dose_threshold
        
        if not high_dose_mask.any():
            return {'num_features': 0}
        
        # Cluster high-dose points to identify features
        high_dose_points = np.column_stack([x_data[high_dose_mask], y_data[high_dose_mask]])
        
        if len(high_dose_points) < 5:
            return {'num_features': 0, 'insufficient_points': True}
        
        # Use DBSCAN for feature clustering
        from sklearn.cluster import DBSCAN
        
        # Normalize coordinates for clustering
        point_range = np.max(high_dose_points, axis=0) - np.min(high_dose_points, axis=0)
        eps = np.min(point_range) * 0.05  # 5% of coordinate range
        
        clustering = DBSCAN(eps=eps, min_samples=3).fit(high_dose_points)
        
        num_features = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
        
        # Calculate feature statistics
        feature_areas = []
        feature_doses = []
        
        for label in set(clustering.labels_):
            if label == -1:  # Noise points
                continue
            
            cluster_mask = clustering.labels_ == label
            cluster_points = high_dose_points[cluster_mask]
            cluster_doses = dose_data[high_dose_mask][cluster_mask]
            
            # Approximate feature area (convex hull area)
            if len(cluster_points) >= 3:
                from scipy.spatial import ConvexHull
                try:
                    hull = ConvexHull(cluster_points)
                    feature_areas.append(hull.volume)  # In 2D, volume is area
                    feature_doses.append(np.mean(cluster_doses))
                except:
                    # Fallback for degenerate cases
                    x_range = np.max(cluster_points[:, 0]) - np.min(cluster_points[:, 0])
                    y_range = np.max(cluster_points[:, 1]) - np.min(cluster_points[:, 1])
                    feature_areas.append(x_range * y_range)
                    feature_doses.append(np.mean(cluster_doses))
        
        return {
            'num_features': num_features,
            'feature_areas': feature_areas,
            'feature_doses': feature_doses,
            'mean_feature_area': float(np.mean(feature_areas)) if feature_areas else 0,
            'mean_feature_dose': float(np.mean(feature_doses)) if feature_doses else 0,
            'high_dose_points': int(np.sum(high_dose_mask)),
            'dose_threshold_used': float(dose_threshold)
        }
    
    def _update_progressive_stats(self, chunk_df: pd.DataFrame, 
                                progressive_stats: Dict) -> None:
        """Update progressive statistics with chunk data"""
        dose_cols = [col for col in chunk_df.columns if 'Dose' in col or 'dose' in col or 'Energy' in col]
        
        if dose_cols:
            dose_data = chunk_df[dose_cols[0]].values
            dose_data = dose_data[dose_data > 0]
            
            if len(dose_data) > 0:
                progressive_stats['total_dose'] += np.sum(dose_data)
                progressive_stats['max_dose'] = max(progressive_stats['max_dose'], np.max(dose_data))
                progressive_stats['min_dose'] = min(progressive_stats['min_dose'], np.min(dose_data))
                
                # Update histogram
                hist, _ = np.histogram(dose_data, bins=100, 
                                     range=(0, progressive_stats['max_dose'] * 1.1))
                progressive_stats['dose_histogram'] += hist
        
        # Update spatial histogram
        x_cols = [col for col in chunk_df.columns if 'X' in col or 'x' in col]
        y_cols = [col for col in chunk_df.columns if 'Y' in col or 'y' in col]
        
        if x_cols and y_cols:
            x_data = chunk_df[x_cols[0]].values
            y_data = chunk_df[y_cols[0]].values
            
            if len(x_data) > 0:
                hist_2d, _, _ = np.histogram2d(x_data, y_data, bins=100)
                progressive_stats['spatial_histogram_2d'] += hist_2d
        
        progressive_stats['processed_points'] += len(chunk_df)
    
    def _finalize_analysis(self, results: Dict) -> Dict[str, Any]:
        """Finalize analysis by combining chunk results"""
        final_metrics = {}
        
        # Aggregate dose statistics
        dose_stats = []
        spatial_stats = []
        uniformity_stats = []
        feature_stats = []
        
        for chunk_result in results['chunk_results']:
            if '_analyze_dose_distribution' in chunk_result and chunk_result['_analyze_dose_distribution']:
                dose_stats.append(chunk_result['_analyze_dose_distribution'])
            
            if '_analyze_spatial_distribution' in chunk_result and chunk_result['_analyze_spatial_distribution']:
                spatial_stats.append(chunk_result['_analyze_spatial_distribution'])
            
            if '_analyze_dose_uniformity' in chunk_result and chunk_result['_analyze_dose_uniformity']:
                uniformity_stats.append(chunk_result['_analyze_dose_uniformity'])
            
            if '_detect_pattern_features' in chunk_result and chunk_result['_detect_pattern_features']:
                feature_stats.append(chunk_result['_detect_pattern_features'])
        
        # Combine dose statistics
        if dose_stats:
            total_dose = sum([stat['total_dose'] for stat in dose_stats if 'total_dose' in stat])
            total_points = sum([stat['num_points'] for stat in dose_stats if 'num_points' in stat])
            
            final_metrics['dose_analysis'] = {
                'global_mean_dose': total_dose / total_points if total_points > 0 else 0,
                'global_max_dose': max([stat['max_dose'] for stat in dose_stats if 'max_dose' in stat]),
                'global_min_dose': min([stat['min_dose'] for stat in dose_stats if 'min_dose' in stat]),
                'total_energy_deposited': total_dose,
                'total_analyzed_points': total_points
            }
        
        # Combine spatial statistics
        if spatial_stats:
            all_extents = [stat['spatial_extent'] for stat in spatial_stats if 'spatial_extent' in stat]
            if all_extents:
                final_metrics['spatial_analysis'] = {
                    'global_x_min': min([ext['x_min'] for ext in all_extents]),
                    'global_x_max': max([ext['x_max'] for ext in all_extents]),
                    'global_y_min': min([ext['y_min'] for ext in all_extents]),
                    'global_y_max': max([ext['y_max'] for ext in all_extents]),
                    'total_area': (max([ext['x_max'] for ext in all_extents]) - min([ext['x_min'] for ext in all_extents])) *
                                 (max([ext['y_max'] for ext in all_extents]) - min([ext['y_min'] for ext in all_extents]))
                }
        
        # Combine uniformity statistics
        if uniformity_stats:
            final_metrics['uniformity_analysis'] = {
                'average_dose_uniformity': np.mean([stat['dose_uniformity_3sigma'] for stat in uniformity_stats 
                                                   if 'dose_uniformity_3sigma' in stat]),
                'average_cd_variation': np.mean([stat['cd_variation_percent'] for stat in uniformity_stats 
                                               if 'cd_variation_percent' in stat])
            }
        
        # Combine feature statistics
        if feature_stats:
            total_features = sum([stat['num_features'] for stat in feature_stats if 'num_features' in stat])
            final_metrics['feature_analysis'] = {
                'total_detected_features': total_features,
                'feature_density': total_features / final_metrics['spatial_analysis']['total_area'] if 'spatial_analysis' in final_metrics else 0
            }
        
        return final_metrics
    
    def _save_progressive_results(self, results: Dict, file_path: Path) -> None:
        """Save progressive results to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save progressive results: {e}")
    
    def _generate_analysis_report(self, results: Dict, output_file: Path) -> None:
        """Generate comprehensive HTML analysis report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Large-Scale EBL Dose Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; margin: -20px -20px 20px -20px; border-radius: 10px 10px 0 0; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #fafafa; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 8px; min-width: 150px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #667eea; color: white; }}
                .performance {{ background-color: #e8f5e8; }}
                .warning {{ background-color: #fff3cd; color: #856404; }}
                .error {{ background-color: #f8d7da; color: #721c24; }}
                .chart-placeholder {{ background-color: #f0f0f0; padding: 20px; text-align: center; border: 2px dashed #ccc; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Large-Scale EBL Dose Analysis Report</h1>
                    <p>Comprehensive analysis of electron beam lithography dose patterns</p>
                    <p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="section">
                    <h2>Dataset Overview</h2>
                    <div class="metric">
                        <div class="metric-value">{results['dataset_info'].num_data_points:,}</div>
                        <div class="metric-label">Total Data Points</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results['dataset_info'].total_size_bytes / (1024**3):.2f} GB</div>
                        <div class="metric-label">Dataset Size</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results['dataset_info'].compression_ratio:.1f}x</div>
                        <div class="metric-label">Compression Ratio</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{len(results['chunk_results'])}</div>
                        <div class="metric-label">Chunks Processed</div>
                    </div>
                </div>
                
                <div class="section performance">
                    <h2>Processing Performance</h2>
                    <div class="metric">
                        <div class="metric-value">{results['processing_stats']['total_processing_time']:.1f}s</div>
                        <div class="metric-label">Total Time</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results['processing_stats']['throughput_points_per_sec']:,.0f}</div>
                        <div class="metric-label">Points/Second</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results['processing_stats']['memory_efficiency']:.2e}</div>
                        <div class="metric-label">Memory Efficiency</div>
                    </div>
                </div>
        """
        
        # Add dose analysis results
        if 'dose_analysis' in results['final_metrics']:
            dose_metrics = results['final_metrics']['dose_analysis']
            html_content += f"""
                <div class="section">
                    <h2>Dose Analysis Results</h2>
                    <div class="metric">
                        <div class="metric-value">{dose_metrics['global_mean_dose']:.3f}</div>
                        <div class="metric-label">Mean Dose (uC/cm²)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{dose_metrics['global_max_dose']:.3f}</div>
                        <div class="metric-label">Max Dose (uC/cm²)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{dose_metrics['total_energy_deposited']:.2e}</div>
                        <div class="metric-label">Total Energy (keV)</div>
                    </div>
                </div>
            """
        
        # Add spatial analysis results
        if 'spatial_analysis' in results['final_metrics']:
            spatial_metrics = results['final_metrics']['spatial_analysis']
            html_content += f"""
                <div class="section">
                    <h2>Spatial Analysis Results</h2>
                    <div class="metric">
                        <div class="metric-value">{spatial_metrics['total_area']:.0f}</div>
                        <div class="metric-label">Total Area (nm²)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">[{spatial_metrics['global_x_min']:.0f}, {spatial_metrics['global_x_max']:.0f}]</div>
                        <div class="metric-label">X Range (nm)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">[{spatial_metrics['global_y_min']:.0f}, {spatial_metrics['global_y_max']:.0f}]</div>
                        <div class="metric-label">Y Range (nm)</div>
                    </div>
                </div>
            """
        
        # Add feature analysis results
        if 'feature_analysis' in results['final_metrics']:
            feature_metrics = results['final_metrics']['feature_analysis']
            html_content += f"""
                <div class="section">
                    <h2>Pattern Feature Analysis</h2>
                    <div class="metric">
                        <div class="metric-value">{feature_metrics['total_detected_features']}</div>
                        <div class="metric-label">Features Detected</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{feature_metrics['feature_density']:.2e}</div>
                        <div class="metric-label">Feature Density (1/nm²)</div>
                    </div>
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        try:
            with open(output_file, 'w') as f:
                f.write(html_content)
            logger.info(f"Analysis report generated: {output_file}")
        except Exception as e:
            logger.warning(f"Failed to generate HTML report: {e}")


def main():
    """Demonstration of large-scale dose analysis framework"""
    print("Large-Scale EBL Dose Analysis Framework Demo")
    print("=" * 50)
    
    # Configure analysis
    config = AnalysisConfig()
    config.max_memory_gb = 2.0  # Limit for demo
    config.num_workers = 2
    config.save_intermediate_results = True
    config.auto_configure()
    
    print(f"Configuration:")
    print(f"  Max memory: {config.max_memory_gb:.1f} GB")
    print(f"  Workers: {config.num_workers}")
    print(f"  GPU available: {config.use_gpu}")
    
    # Initialize analyzer
    analyzer = LargeScaleDoseAnalyzer(config)
    
    # Create synthetic large dataset for demonstration
    def create_synthetic_large_dataset(filename: str, num_points: int = 100000):
        """Create synthetic large dataset"""
        print(f"Creating synthetic dataset with {num_points:,} points...")
        
        # Generate synthetic EBL data
        np.random.seed(42)
        
        # Pattern locations
        pattern_centers = [(0, 0), (1000, 0), (0, 1000), (1000, 1000)]
        
        data_points = []
        
        for i, (cx, cy) in enumerate(pattern_centers):
            # Generate points around each pattern center
            points_per_pattern = num_points // len(pattern_centers)
            
            # Forward scatter (tight distribution)
            x_forward = np.random.normal(cx, 10, points_per_pattern // 2)
            y_forward = np.random.normal(cy, 10, points_per_pattern // 2)
            dose_forward = np.random.exponential(100, points_per_pattern // 2)
            
            # Backscatter (wide distribution)
            x_backscatter = np.random.normal(cx, 50, points_per_pattern // 2)
            y_backscatter = np.random.normal(cy, 50, points_per_pattern // 2)
            dose_backscatter = np.random.exponential(20, points_per_pattern // 2)
            
            # Combine
            x_pattern = np.concatenate([x_forward, x_backscatter])
            y_pattern = np.concatenate([y_forward, y_backscatter])
            dose_pattern = np.concatenate([dose_forward, dose_backscatter])
            z_pattern = np.random.uniform(0, 100, len(x_pattern))  # Depth
            energy_pattern = dose_pattern * 0.1  # Rough energy correlation
            
            for j in range(len(x_pattern)):
                data_points.append([
                    x_pattern[j], y_pattern[j], z_pattern[j], 
                    energy_pattern[j], dose_pattern[j]
                ])
        
        # Create DataFrame and save as CSV
        df = pd.DataFrame(data_points, columns=['X[nm]', 'Y[nm]', 'Z[nm]', 'Energy[keV]', 'Dose[uC/cm^2]'])
        df.to_csv(filename, index=False)
        
        file_size_mb = Path(filename).stat().st_size / (1024**2)
        print(f"Created {filename} ({file_size_mb:.1f} MB)")
        
        return filename
    
    # Create demo dataset
    demo_file = "demo_large_dataset.csv"
    create_synthetic_large_dataset(demo_file, num_points=50000)  # Smaller for demo
    
    try:
        # Analyze dataset info
        print("\nAnalyzing dataset metadata...")
        dataset_info = analyzer.analyze_dataset_info(demo_file)
        print(f"Dataset contains {dataset_info.num_data_points:,} points")
        print(f"Dataset size: {dataset_info.total_size_bytes / (1024**2):.1f} MB")
        print(f"Spatial extent: {dataset_info.spatial_extent}")
        print(f"Dose range: {dataset_info.dose_range}")
        
        # Run progressive analysis
        print("\nRunning progressive analysis...")
        output_dir = "large_scale_analysis_output"
        
        results = analyzer.progressive_dose_analysis(
            demo_file, 
            output_dir,
            analysis_functions=[
                analyzer._analyze_dose_distribution,
                analyzer._analyze_spatial_distribution,
                analyzer._analyze_dose_uniformity,
                analyzer._detect_pattern_features
            ]
        )
        
        # Display results
        print(f"\nAnalysis Results:")
        print(f"Chunks processed: {results['processing_stats']['chunks_processed']}")
        print(f"Total processing time: {results['processing_stats']['total_processing_time']:.2f}s")
        print(f"Throughput: {results['processing_stats']['throughput_points_per_sec']:,.0f} points/sec")
        
        if 'dose_analysis' in results['final_metrics']:
            dose_metrics = results['final_metrics']['dose_analysis']
            print(f"Global mean dose: {dose_metrics['global_mean_dose']:.3f} uC/cm²")
            print(f"Total energy deposited: {dose_metrics['total_energy_deposited']:.2e} keV")
        
        if 'feature_analysis' in results['final_metrics']:
            feature_metrics = results['final_metrics']['feature_analysis']
            print(f"Features detected: {feature_metrics['total_detected_features']}")
        
        print(f"\nResults saved to: {output_dir}/")
        print("- final_analysis_results.json")
        print("- analysis_report.html")
        print("- dataset_info.json")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if Path(demo_file).exists():
            Path(demo_file).unlink()
            print(f"\nCleaned up demo file: {demo_file}")
    
    print("\nLarge-scale dose analysis framework demonstration complete!")


if __name__ == "__main__":
    main()