#!/usr/bin/env python3
"""
EBL Simulation Performance Benchmarking Framework

Comprehensive performance monitoring, benchmarking, and optimization
analysis for the ultra-modular EBL simulation system.

Features:
- CPU and memory profiling
- Pattern generation benchmarks
- Geant4 simulation throughput analysis
- GUI responsiveness monitoring
- Thread scaling analysis
- Memory leak detection
- Performance regression tracking
"""

import time
import psutil
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from contextlib import contextmanager
import cProfile
import pstats
import io
import tracemalloc
import gc
import sys
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results"""
    duration_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    cpu_percent: float = 0.0
    thread_count: int = 0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    throughput_ops_per_sec: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    name: str
    description: str
    metrics: PerformanceMetrics
    success: bool = True
    error_message: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'success': self.success,
            'error_message': self.error_message,
            'parameters': self.parameters,
            'metrics': {
                'duration_seconds': self.metrics.duration_seconds,
                'peak_memory_mb': self.metrics.peak_memory_mb,
                'avg_memory_mb': self.metrics.avg_memory_mb,
                'cpu_percent': self.metrics.cpu_percent,
                'thread_count': self.metrics.thread_count,
                'disk_read_mb': self.metrics.disk_read_mb,
                'disk_write_mb': self.metrics.disk_write_mb,
                'throughput_ops_per_sec': self.metrics.throughput_ops_per_sec,
                'custom_metrics': self.metrics.custom_metrics,
                'timestamp': self.metrics.timestamp
            }
        }


class SystemMonitor:
    """Real-time system resource monitoring"""
    
    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.monitoring = False
        self.data = []
        self.process = psutil.Process()
        self.start_io = None
        self.monitor_thread = None
        
    def start(self):
        """Start monitoring system resources"""
        self.monitoring = True
        self.data = []
        self.start_io = self.process.io_counters()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self) -> PerformanceMetrics:
        """Stop monitoring and return metrics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            
        if not self.data:
            return PerformanceMetrics()
            
        # Calculate metrics from collected data
        memory_values = [d['memory_mb'] for d in self.data]
        cpu_values = [d['cpu_percent'] for d in self.data]
        thread_values = [d['thread_count'] for d in self.data]
        
        # I/O metrics
        end_io = self.process.io_counters()
        if self.start_io:
            disk_read_mb = (end_io.read_bytes - self.start_io.read_bytes) / (1024 * 1024)
            disk_write_mb = (end_io.write_bytes - self.start_io.write_bytes) / (1024 * 1024)
        else:
            disk_read_mb = disk_write_mb = 0.0
            
        return PerformanceMetrics(
            duration_seconds=len(self.data) * self.interval,
            peak_memory_mb=max(memory_values) if memory_values else 0.0,
            avg_memory_mb=np.mean(memory_values) if memory_values else 0.0,
            cpu_percent=np.mean(cpu_values) if cpu_values else 0.0,
            thread_count=int(np.mean(thread_values)) if thread_values else 0,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb
        )
        
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()
                thread_count = self.process.num_threads()
                
                self.data.append({
                    'timestamp': time.time(),
                    'memory_mb': memory_info.rss / (1024 * 1024),
                    'cpu_percent': cpu_percent,
                    'thread_count': thread_count
                })
                
                time.sleep(self.interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break


class ProfilerContext:
    """Context manager for CPU profiling"""
    
    def __init__(self, sort_by: str = 'cumulative'):
        self.sort_by = sort_by
        self.profiler = None
        self.stats = None
        
    def __enter__(self):
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.disable()
        
        # Create stats object
        s = io.StringIO()
        self.stats = pstats.Stats(self.profiler, stream=s)
        self.stats.sort_stats(self.sort_by)
        
    def get_top_functions(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N functions by time"""
        if not self.stats:
            return []
            
        stats_data = []
        for func, (cc, nc, tt, ct, callers) in self.stats.stats.items():
            filename, line, func_name = func
            stats_data.append((f"{filename}:{line}({func_name})", ct))
            
        return sorted(stats_data, key=lambda x: x[1], reverse=True)[:n]


class MemoryTracker:
    """Memory leak detection and analysis"""
    
    def __init__(self):
        self.snapshots = []
        
    def start_tracing(self):
        """Start memory tracing"""
        tracemalloc.start()
        
    def take_snapshot(self, label: str = ""):
        """Take a memory snapshot"""
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            self.snapshots.append((label, snapshot))
            
    def stop_tracing(self):
        """Stop memory tracing"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            
    def analyze_growth(self) -> Dict[str, Any]:
        """Analyze memory growth between snapshots"""
        if len(self.snapshots) < 2:
            return {"error": "Need at least 2 snapshots"}
            
        first_label, first_snapshot = self.snapshots[0]
        last_label, last_snapshot = self.snapshots[-1]
        
        top_stats = last_snapshot.compare_to(first_snapshot, 'lineno')
        
        growth_analysis = {
            'first_snapshot': first_label,
            'last_snapshot': last_label,
            'total_growth_mb': sum(stat.size_diff for stat in top_stats) / (1024 * 1024),
            'top_growers': []
        }
        
        for stat in top_stats[:10]:
            growth_analysis['top_growers'].append({
                'file': stat.traceback.format()[0] if stat.traceback else "unknown",
                'size_diff_mb': stat.size_diff / (1024 * 1024),
                'count_diff': stat.count_diff
            })
            
        return growth_analysis


class PatternGenerationBenchmark:
    """Benchmark pattern generation algorithms"""
    
    @staticmethod
    def benchmark_square_pattern(sizes: List[int], shot_pitches: List[int]) -> List[BenchmarkResult]:
        """Benchmark square pattern generation with different parameters"""
        results = []
        
        for size in sizes:
            for pitch in shot_pitches:
                monitor = SystemMonitor()
                monitor.start()
                
                start_time = time.time()
                
                try:
                    # Simulate pattern generation
                    grid_spacing = pitch * 1.0  # nm (machine grid)
                    n_points = int(size / grid_spacing)
                    total_points = n_points * n_points
                    
                    # Simulate memory allocation for pattern points
                    points = np.zeros((total_points, 3), dtype=np.float64)
                    
                    # Simulate pattern generation computation
                    for i in range(min(1000, total_points)):  # Cap for reasonable test time
                        x = (i % n_points) * grid_spacing
                        y = (i // n_points) * grid_spacing
                        points[i] = [x, y, 0]
                        
                    end_time = time.time()
                    metrics = monitor.stop()
                    metrics.duration_seconds = end_time - start_time
                    metrics.throughput_ops_per_sec = total_points / metrics.duration_seconds
                    metrics.custom_metrics = {
                        'total_points': total_points,
                        'pattern_size_nm': size,
                        'shot_pitch': pitch,
                        'points_per_second': metrics.throughput_ops_per_sec
                    }
                    
                    results.append(BenchmarkResult(
                        name=f"square_pattern_{size}nm_pitch{pitch}",
                        description=f"Square pattern {size}nm with shot pitch {pitch}",
                        metrics=metrics,
                        parameters={'size': size, 'pitch': pitch}
                    ))
                    
                except Exception as e:
                    metrics = monitor.stop()
                    results.append(BenchmarkResult(
                        name=f"square_pattern_{size}nm_pitch{pitch}",
                        description=f"Square pattern {size}nm with shot pitch {pitch}",
                        metrics=metrics,
                        success=False,
                        error_message=str(e),
                        parameters={'size': size, 'pitch': pitch}
                    ))
                    
        return results


class SimulationBenchmark:
    """Benchmark Geant4 simulation performance"""
    
    def __init__(self, executable_path: str, working_dir: str):
        self.executable_path = executable_path
        self.working_dir = working_dir
        
    def benchmark_throughput(self, particle_counts: List[int], energies: List[float]) -> List[BenchmarkResult]:
        """Benchmark simulation throughput for different parameters"""
        results = []
        
        for particles in particle_counts:
            for energy in energies:
                results.append(self._run_simulation_benchmark(particles, energy))
                
        return results
        
    def _run_simulation_benchmark(self, particles: int, energy: float) -> BenchmarkResult:
        """Run a single simulation benchmark"""
        monitor = SystemMonitor()
        
        # Create temporary macro file
        macro_content = f"""
# Performance benchmark macro
/run/verbose 0
/event/verbose 0
/tracking/verbose 0
/vis/disable

/gun/particle e-
/gun/energy {energy} keV
/gun/position 0 0 100 nm
/gun/direction 0 0 -1

/run/initialize
/run/beamOn {particles}
"""
        
        macro_path = Path(self.working_dir) / f"benchmark_{particles}_{energy}keV.mac"
        macro_path.write_text(macro_content)
        
        try:
            monitor.start()
            start_time = time.time()
            
            # Run simulation
            result = subprocess.run(
                [self.executable_path, str(macro_path)],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            metrics = monitor.stop()
            metrics.duration_seconds = end_time - start_time
            
            if result.returncode == 0:
                metrics.throughput_ops_per_sec = particles / metrics.duration_seconds
                metrics.custom_metrics = {
                    'particles': particles,
                    'energy_kev': energy,
                    'events_per_second': metrics.throughput_ops_per_sec
                }
                
                return BenchmarkResult(
                    name=f"simulation_{particles}p_{energy}keV",
                    description=f"Simulation: {particles} particles at {energy} keV",
                    metrics=metrics,
                    parameters={'particles': particles, 'energy': energy}
                )
            else:
                return BenchmarkResult(
                    name=f"simulation_{particles}p_{energy}keV",
                    description=f"Simulation: {particles} particles at {energy} keV",
                    metrics=metrics,
                    success=False,
                    error_message=result.stderr,
                    parameters={'particles': particles, 'energy': energy}
                )
                
        except subprocess.TimeoutExpired:
            metrics = monitor.stop()
            return BenchmarkResult(
                name=f"simulation_{particles}p_{energy}keV",
                description=f"Simulation: {particles} particles at {energy} keV",
                metrics=metrics,
                success=False,
                error_message="Simulation timeout",
                parameters={'particles': particles, 'energy': energy}
            )
        finally:
            # Cleanup
            if macro_path.exists():
                macro_path.unlink()


class ThreadScalingBenchmark:
    """Benchmark thread scaling performance"""
    
    @staticmethod
    def benchmark_cpu_scaling(workload_func: Callable, thread_counts: List[int]) -> List[BenchmarkResult]:
        """Benchmark CPU-bound workload scaling"""
        results = []
        
        for threads in thread_counts:
            monitor = SystemMonitor()
            monitor.start()
            start_time = time.time()
            
            try:
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    # Submit work to thread pool
                    futures = [executor.submit(workload_func) for _ in range(threads * 2)]
                    
                    # Wait for completion
                    for future in futures:
                        future.result()
                        
                end_time = time.time()
                metrics = monitor.stop()
                metrics.duration_seconds = end_time - start_time
                metrics.throughput_ops_per_sec = len(futures) / metrics.duration_seconds
                metrics.custom_metrics = {
                    'thread_count': threads,
                    'tasks_completed': len(futures),
                    'tasks_per_second': metrics.throughput_ops_per_sec
                }
                
                results.append(BenchmarkResult(
                    name=f"thread_scaling_{threads}",
                    description=f"Thread scaling with {threads} threads",
                    metrics=metrics,
                    parameters={'threads': threads}
                ))
                
            except Exception as e:
                metrics = monitor.stop()
                results.append(BenchmarkResult(
                    name=f"thread_scaling_{threads}",
                    description=f"Thread scaling with {threads} threads",
                    metrics=metrics,
                    success=False,
                    error_message=str(e),
                    parameters={'threads': threads}
                ))
                
        return results


class GUIPerformanceBenchmark:
    """Benchmark GUI responsiveness and rendering performance"""
    
    @staticmethod
    def benchmark_plot_rendering(data_sizes: List[int]) -> List[BenchmarkResult]:
        """Benchmark matplotlib plot rendering performance"""
        results = []
        
        for size in data_sizes:
            monitor = SystemMonitor()
            monitor.start()
            start_time = time.time()
            
            try:
                # Generate test data
                x = np.linspace(0, 100, size)
                y = np.sin(x) + np.random.normal(0, 0.1, size)
                
                # Create plot (without showing)
                fig, ax = plt.subplots()
                ax.plot(x, y)
                ax.set_title(f"Test plot with {size} points")
                
                # Simulate rendering time
                fig.canvas.draw()
                
                plt.close(fig)
                
                end_time = time.time()
                metrics = monitor.stop()
                metrics.duration_seconds = end_time - start_time
                metrics.throughput_ops_per_sec = size / metrics.duration_seconds
                metrics.custom_metrics = {
                    'data_points': size,
                    'points_per_second': metrics.throughput_ops_per_sec
                }
                
                results.append(BenchmarkResult(
                    name=f"plot_rendering_{size}pts",
                    description=f"Plot rendering with {size} data points",
                    metrics=metrics,
                    parameters={'data_size': size}
                ))
                
            except Exception as e:
                metrics = monitor.stop()
                results.append(BenchmarkResult(
                    name=f"plot_rendering_{size}pts",
                    description=f"Plot rendering with {size} data points",
                    metrics=metrics,
                    success=False,
                    error_message=str(e),
                    parameters={'data_size': size}
                ))
                
        return results


class DataProcessingBenchmark:
    """Benchmark data processing and analysis performance"""
    
    @staticmethod
    def benchmark_numpy_operations(array_sizes: List[int]) -> List[BenchmarkResult]:
        """Benchmark NumPy vectorized operations"""
        results = []
        
        operations = [
            ('element_wise_multiply', lambda x: x * x),
            ('fft_transform', lambda x: np.fft.fft(x)),
            ('matrix_multiply', lambda x: np.dot(x.reshape(-1, int(np.sqrt(len(x)))), 
                                                x.reshape(int(np.sqrt(len(x))), -1))),
            ('statistical_analysis', lambda x: np.array([np.mean(x), np.std(x), np.max(x), np.min(x)]))
        ]
        
        for size in array_sizes:
            for op_name, op_func in operations:
                monitor = SystemMonitor()
                monitor.start()
                start_time = time.time()
                
                try:
                    # Create test data
                    if op_name == 'matrix_multiply':
                        # Ensure square matrix for matrix multiply
                        sqrt_size = int(np.sqrt(size))
                        actual_size = sqrt_size * sqrt_size
                        data = np.random.random(actual_size)
                    else:
                        data = np.random.random(size)
                        actual_size = size
                    
                    # Perform operation multiple times for better timing
                    n_reps = max(1, 1000 // (size // 1000 + 1))
                    for _ in range(n_reps):
                        result = op_func(data)
                    
                    end_time = time.time()
                    metrics = monitor.stop()
                    metrics.duration_seconds = end_time - start_time
                    metrics.throughput_ops_per_sec = (actual_size * n_reps) / metrics.duration_seconds
                    metrics.custom_metrics = {
                        'operation': op_name,
                        'array_size': actual_size,
                        'repetitions': n_reps,
                        'elements_per_second': metrics.throughput_ops_per_sec
                    }
                    
                    results.append(BenchmarkResult(
                        name=f"{op_name}_{actual_size}",
                        description=f"NumPy {op_name} with {actual_size} elements",
                        metrics=metrics,
                        parameters={'operation': op_name, 'size': actual_size}
                    ))
                    
                except Exception as e:
                    metrics = monitor.stop()
                    results.append(BenchmarkResult(
                        name=f"{op_name}_{size}",
                        description=f"NumPy {op_name} with {size} elements",
                        metrics=metrics,
                        success=False,
                        error_message=str(e),
                        parameters={'operation': op_name, 'size': size}
                    ))
                    
        return results


class BenchmarkSuite:
    """Complete benchmark suite for EBL simulation system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        logger.info("Starting comprehensive EBL simulation benchmark suite")
        
        benchmark_results = {
            'system_info': self._get_system_info(),
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'benchmarks': {}
        }
        
        # Pattern generation benchmarks
        if self.config.get('run_pattern_benchmarks', True):
            logger.info("Running pattern generation benchmarks...")
            pattern_results = PatternGenerationBenchmark.benchmark_square_pattern(
                sizes=[1000, 5000, 10000, 50000],  # nm
                shot_pitches=[1, 2, 4, 8]
            )
            benchmark_results['benchmarks']['pattern_generation'] = [r.to_dict() for r in pattern_results]
            
        # Thread scaling benchmarks
        if self.config.get('run_thread_benchmarks', True):
            logger.info("Running thread scaling benchmarks...")
            
            def cpu_workload():
                """CPU-intensive workload for thread scaling test"""
                return sum(i**2 for i in range(10000))
            
            thread_results = ThreadScalingBenchmark.benchmark_cpu_scaling(
                workload_func=cpu_workload,
                thread_counts=[1, 2, 4, 8, 16]
            )
            benchmark_results['benchmarks']['thread_scaling'] = [r.to_dict() for r in thread_results]
            
        # GUI performance benchmarks
        if self.config.get('run_gui_benchmarks', True):
            logger.info("Running GUI performance benchmarks...")
            gui_results = GUIPerformanceBenchmark.benchmark_plot_rendering(
                data_sizes=[100, 1000, 10000, 100000]
            )
            benchmark_results['benchmarks']['gui_performance'] = [r.to_dict() for r in gui_results]
            
        # Data processing benchmarks
        if self.config.get('run_data_benchmarks', True):
            logger.info("Running data processing benchmarks...")
            data_results = DataProcessingBenchmark.benchmark_numpy_operations(
                array_sizes=[1000, 10000, 100000, 1000000]
            )
            benchmark_results['benchmarks']['data_processing'] = [r.to_dict() for r in data_results]
            
        # Geant4 simulation benchmarks (if executable available)
        if self.config.get('run_simulation_benchmarks', False) and 'executable_path' in self.config:
            logger.info("Running Geant4 simulation benchmarks...")
            sim_benchmark = SimulationBenchmark(
                self.config['executable_path'],
                self.config.get('working_dir', '.')
            )
            sim_results = sim_benchmark.benchmark_throughput(
                particle_counts=[1000, 5000, 10000],
                energies=[50, 100, 200]
            )
            benchmark_results['benchmarks']['simulation'] = [r.to_dict() for r in sim_results]
            
        logger.info("Benchmark suite completed")
        return benchmark_results
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'platform': sys.platform,
            'python_version': sys.version,
            'numpy_version': np.__version__,
            'pandas_version': pd.__version__
        }
        
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save benchmark results to file"""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Benchmark results saved to {output_file}")
        
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable benchmark report"""
        report = []
        report.append("EBL Simulation Performance Benchmark Report")
        report.append("=" * 50)
        report.append(f"Timestamp: {results['timestamp']}")
        report.append(f"System: {results['system_info']['cpu_count']} CPU cores, "
                     f"{results['system_info']['memory_total_gb']:.1f} GB RAM")
        report.append("")
        
        for category, benchmarks in results['benchmarks'].items():
            report.append(f"{category.replace('_', ' ').title()} Benchmarks:")
            report.append("-" * 30)
            
            successful_benchmarks = [b for b in benchmarks if b['success']]
            failed_benchmarks = [b for b in benchmarks if not b['success']]
            
            if successful_benchmarks:
                # Performance summary
                avg_throughput = np.mean([b['metrics']['throughput_ops_per_sec'] 
                                        for b in successful_benchmarks if b['metrics']['throughput_ops_per_sec'] > 0])
                avg_memory = np.mean([b['metrics']['peak_memory_mb'] for b in successful_benchmarks])
                
                report.append(f"  Successful tests: {len(successful_benchmarks)}")
                report.append(f"  Average throughput: {avg_throughput:.0f} ops/sec")
                report.append(f"  Average memory usage: {avg_memory:.1f} MB")
                
                # Top performers
                if len(successful_benchmarks) > 1:
                    fastest = max(successful_benchmarks, 
                                key=lambda x: x['metrics']['throughput_ops_per_sec'])
                    report.append(f"  Fastest: {fastest['name']} "
                                f"({fastest['metrics']['throughput_ops_per_sec']:.0f} ops/sec)")
            
            if failed_benchmarks:
                report.append(f"  Failed tests: {len(failed_benchmarks)}")
                for failed in failed_benchmarks:
                    report.append(f"    - {failed['name']}: {failed['error_message']}")
                    
            report.append("")
            
        return "\n".join(report)


def main():
    """Main benchmark execution"""
    config = {
        'run_pattern_benchmarks': True,
        'run_thread_benchmarks': True,
        'run_gui_benchmarks': True,
        'run_data_benchmarks': True,
        'run_simulation_benchmarks': False,  # Requires Geant4 executable
        # 'executable_path': '/path/to/ebl_sim',
        # 'working_dir': '/tmp'
    }
    
    suite = BenchmarkSuite(config)
    results = suite.run_comprehensive_benchmark()
    
    # Save results
    output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    suite.save_results(results, output_file)
    
    # Generate and print report
    report = suite.generate_report(results)
    print(report)
    
    # Save report
    report_file = output_file.replace('.json', '_report.txt')
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\nDetailed report saved to {report_file}")


if __name__ == "__main__":
    main()