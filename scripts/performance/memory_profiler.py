#!/usr/bin/env python3
"""
Memory Profiling and Leak Detection for EBL Simulation System

Comprehensive memory analysis, leak detection, and optimization tools
for both C++ Geant4 backend and Python GUI components.

Features:
- Real-time memory monitoring
- Memory leak detection and analysis
- Memory allocation pattern analysis
- Memory pool optimization recommendations
- Garbage collection optimization for Python
- Integration with system profilers (valgrind, AddressSanitizer)
"""

import psutil
import gc
import sys
import os
import time
import threading
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import tracemalloc
import weakref
import pickle
import gzip


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""
    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    shared_mb: float
    private_mb: float
    swap_mb: float
    python_objects: int
    cpp_allocations: Optional[int] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryLeak:
    """Detected memory leak information"""
    location: str
    size_bytes: int
    allocation_count: int
    growth_rate_mb_per_sec: float
    stack_trace: List[str]
    first_seen: float
    last_seen: float
    leak_type: str  # 'python', 'cpp', 'system'


class MemoryProfiler:
    """Comprehensive memory profiling and analysis"""
    
    def __init__(self, sample_interval: float = 1.0, max_samples: int = 10000):
        self.sample_interval = sample_interval
        self.max_samples = max_samples
        self.snapshots = deque(maxlen=max_samples)
        self.is_profiling = False
        self.profile_thread = None
        self.start_time = None
        self.process = psutil.Process()
        
        # Tracemalloc for Python memory tracking
        self.python_snapshots = []
        self.baseline_snapshot = None
        
        # Leak detection
        self.detected_leaks = []
        self.allocation_patterns = defaultdict(list)
        
        # C++ integration
        self.cpp_profiler = CppMemoryProfiler()
        
    def start_profiling(self, enable_python_tracing: bool = True):
        """Start memory profiling"""
        if self.is_profiling:
            return
            
        self.is_profiling = True
        self.start_time = time.time()
        self.snapshots.clear()
        
        # Start Python memory tracing
        if enable_python_tracing:
            tracemalloc.start()
            self.baseline_snapshot = tracemalloc.take_snapshot()
            
        # Start profiling thread
        self.profile_thread = threading.Thread(target=self._profiling_loop)
        self.profile_thread.daemon = True
        self.profile_thread.start()
        
        print(f"Memory profiling started (interval: {self.sample_interval}s)")
        
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return analysis"""
        if not self.is_profiling:
            return {}
            
        self.is_profiling = False
        
        if self.profile_thread:
            self.profile_thread.join(timeout=5.0)
            
        # Stop Python tracing
        if tracemalloc.is_tracing():
            final_snapshot = tracemalloc.take_snapshot()
            self.python_snapshots.append(('final', final_snapshot))
            tracemalloc.stop()
            
        # Analyze results
        analysis = self._analyze_memory_usage()
        
        print("Memory profiling stopped")
        return analysis
        
    def take_snapshot(self, label: str = ""):
        """Take a manual memory snapshot"""
        try:
            memory_info = self.process.memory_info()
            memory_full = self.process.memory_full_info()
            
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                shared_mb=memory_full.shared / (1024 * 1024),
                private_mb=memory_full.private / (1024 * 1024),
                swap_mb=memory_full.swap / (1024 * 1024),
                python_objects=len(gc.get_objects())
            )
            
            # Add C++ memory info if available
            cpp_info = self.cpp_profiler.get_memory_info()
            if cpp_info:
                snapshot.cpp_allocations = cpp_info.get('allocation_count', 0)
                snapshot.custom_metrics.update(cpp_info)
                
            self.snapshots.append(snapshot)
            
            # Take Python tracemalloc snapshot
            if tracemalloc.is_tracing():
                py_snapshot = tracemalloc.take_snapshot()
                self.python_snapshots.append((label or f"snapshot_{len(self.python_snapshots)}", py_snapshot))
                
            return snapshot
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error taking memory snapshot: {e}")
            return None
            
    def _profiling_loop(self):
        """Background profiling loop"""
        while self.is_profiling:
            self.take_snapshot()
            time.sleep(self.sample_interval)
            
            # Detect leaks periodically
            if len(self.snapshots) > 10:
                self._detect_leaks()
                
    def _detect_leaks(self):
        """Detect memory leaks from snapshots"""
        if len(self.snapshots) < 10:
            return
            
        # Analyze last 10 snapshots for trends
        recent_snapshots = list(self.snapshots)[-10:]
        
        # Check for consistent memory growth
        rss_values = [s.rss_mb for s in recent_snapshots]
        vms_values = [s.vms_mb for s in recent_snapshots]
        
        # Linear regression to detect growth trends
        x = np.arange(len(rss_values))
        rss_slope = np.polyfit(x, rss_values, 1)[0]
        vms_slope = np.polyfit(x, vms_values, 1)[0]
        
        # Detect significant growth (>1MB per 10 samples)
        if rss_slope > 0.1:  # 0.1 MB per sample
            leak = MemoryLeak(
                location="system_memory",
                size_bytes=int(rss_slope * 1024 * 1024),
                allocation_count=1,
                growth_rate_mb_per_sec=rss_slope / self.sample_interval,
                stack_trace=["Memory growth detected in system RSS"],
                first_seen=recent_snapshots[0].timestamp,
                last_seen=recent_snapshots[-1].timestamp,
                leak_type="system"
            )
            
            # Check if this is a new leak
            if not any(l.location == leak.location for l in self.detected_leaks):
                self.detected_leaks.append(leak)
                print(f"MEMORY LEAK DETECTED: {leak.growth_rate_mb_per_sec:.2f} MB/s growth in {leak.location}")
                
    def analyze_python_memory(self) -> Dict[str, Any]:
        """Analyze Python memory usage patterns"""
        if not self.python_snapshots or not self.baseline_snapshot:
            return {"error": "No Python memory snapshots available"}
            
        analysis = {
            "snapshots_analyzed": len(self.python_snapshots),
            "top_allocators": [],
            "memory_growth": [],
            "potential_leaks": []
        }
        
        try:
            # Compare against baseline
            for label, snapshot in self.python_snapshots[-5:]:  # Last 5 snapshots
                top_stats = snapshot.compare_to(self.baseline_snapshot, 'lineno')
                
                growth_info = {
                    "label": label,
                    "total_growth_mb": sum(stat.size_diff for stat in top_stats) / (1024 * 1024),
                    "top_growers": []
                }
                
                for stat in top_stats[:10]:
                    if stat.size_diff > 1024 * 1024:  # > 1MB growth
                        grower_info = {
                            "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                            "size_diff_mb": stat.size_diff / (1024 * 1024),
                            "count_diff": stat.count_diff,
                            "size_diff_per_allocation": stat.size_diff / max(1, stat.count_diff)
                        }
                        growth_info["top_growers"].append(grower_info)
                        
                        # Detect potential leaks
                        if stat.count_diff > 1000 and stat.size_diff / stat.count_diff > 1024:
                            analysis["potential_leaks"].append({
                                "location": grower_info["file"],
                                "growth_mb": grower_info["size_diff_mb"],
                                "allocations": stat.count_diff,
                                "avg_size_bytes": grower_info["size_diff_per_allocation"]
                            })
                
                analysis["memory_growth"].append(growth_info)
                
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _analyze_memory_usage(self) -> Dict[str, Any]:
        """Comprehensive memory usage analysis"""
        if not self.snapshots:
            return {"error": "No memory snapshots available"}
            
        snapshots_list = list(self.snapshots)
        
        # Basic statistics
        rss_values = [s.rss_mb for s in snapshots_list]
        vms_values = [s.vms_mb for s in snapshots_list]
        python_objects = [s.python_objects for s in snapshots_list]
        
        analysis = {
            "profiling_duration": snapshots_list[-1].timestamp - snapshots_list[0].timestamp,
            "total_snapshots": len(snapshots_list),
            "memory_statistics": {
                "rss_mb": {
                    "min": min(rss_values),
                    "max": max(rss_values),
                    "mean": np.mean(rss_values),
                    "std": np.std(rss_values),
                    "growth": max(rss_values) - min(rss_values)
                },
                "vms_mb": {
                    "min": min(vms_values),
                    "max": max(vms_values),
                    "mean": np.mean(vms_values),
                    "std": np.std(vms_values),
                    "growth": max(vms_values) - min(vms_values)
                },
                "python_objects": {
                    "min": min(python_objects),
                    "max": max(python_objects),
                    "mean": np.mean(python_objects),
                    "growth": max(python_objects) - min(python_objects)
                }
            },
            "detected_leaks": [
                {
                    "location": leak.location,
                    "growth_rate_mb_per_sec": leak.growth_rate_mb_per_sec,
                    "total_size_mb": leak.size_bytes / (1024 * 1024),
                    "leak_type": leak.leak_type
                }
                for leak in self.detected_leaks
            ],
            "python_analysis": self.analyze_python_memory()
        }
        
        return analysis
        
    def generate_memory_report(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable memory analysis report"""
        if "error" in analysis:
            return f"Memory Analysis Error: {analysis['error']}"
            
        report = []
        report.append("EBL Simulation Memory Analysis Report")
        report.append("=" * 50)
        report.append(f"Profiling duration: {analysis['profiling_duration']:.1f} seconds")
        report.append(f"Total snapshots: {analysis['total_snapshots']}")
        report.append("")
        
        # Memory statistics
        stats = analysis["memory_statistics"]
        report.append("Memory Usage Statistics:")
        report.append(f"  RSS Memory:")
        report.append(f"    Peak: {stats['rss_mb']['max']:.1f} MB")
        report.append(f"    Average: {stats['rss_mb']['mean']:.1f} MB")
        report.append(f"    Growth: {stats['rss_mb']['growth']:.1f} MB")
        
        report.append(f"  Virtual Memory:")
        report.append(f"    Peak: {stats['vms_mb']['max']:.1f} MB")
        report.append(f"    Growth: {stats['vms_mb']['growth']:.1f} MB")
        
        report.append(f"  Python Objects:")
        report.append(f"    Peak: {stats['python_objects']['max']:,}")
        report.append(f"    Growth: {stats['python_objects']['growth']:,}")
        report.append("")
        
        # Leak detection
        leaks = analysis["detected_leaks"]
        if leaks:
            report.append("MEMORY LEAKS DETECTED:")
            for i, leak in enumerate(leaks, 1):
                report.append(f"  {i}. {leak['location']}")
                report.append(f"     Growth rate: {leak['growth_rate_mb_per_sec']:.3f} MB/s")
                report.append(f"     Total leaked: {leak['total_size_mb']:.1f} MB")
                report.append(f"     Type: {leak['leak_type']}")
        else:
            report.append("No memory leaks detected")
        report.append("")
        
        # Python analysis
        py_analysis = analysis["python_analysis"]
        if "potential_leaks" in py_analysis and py_analysis["potential_leaks"]:
            report.append("Python Memory Issues:")
            for leak in py_analysis["potential_leaks"]:
                report.append(f"  - {leak['location']}: {leak['growth_mb']:.1f} MB growth")
        
        return "\n".join(report)
        
    def plot_memory_usage(self, output_dir: str = "."):
        """Generate memory usage visualization"""
        if not self.snapshots:
            print("No memory data to plot")
            return
            
        snapshots_list = list(self.snapshots)
        timestamps = [(s.timestamp - snapshots_list[0].timestamp) / 60 for s in snapshots_list]  # Minutes
        rss_values = [s.rss_mb for s in snapshots_list]
        vms_values = [s.vms_mb for s in snapshots_list]
        python_objects = [s.python_objects for s in snapshots_list]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # RSS memory over time
        ax1.plot(timestamps, rss_values, 'b-', linewidth=2)
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('RSS Memory (MB)')
        ax1.set_title('Resident Set Size Over Time')
        ax1.grid(True, alpha=0.3)
        
        # Virtual memory over time
        ax2.plot(timestamps, vms_values, 'r-', linewidth=2)
        ax2.set_xlabel('Time (minutes)')
        ax2.set_ylabel('Virtual Memory (MB)')
        ax2.set_title('Virtual Memory Size Over Time')
        ax2.grid(True, alpha=0.3)
        
        # Python objects over time
        ax3.plot(timestamps, python_objects, 'g-', linewidth=2)
        ax3.set_xlabel('Time (minutes)')
        ax3.set_ylabel('Python Objects Count')
        ax3.set_title('Python Objects Over Time')
        ax3.grid(True, alpha=0.3)
        
        # Memory composition (latest snapshot)
        if len(snapshots_list) > 0:
            latest = snapshots_list[-1]
            memory_types = ['RSS', 'Shared', 'Private', 'Swap']
            memory_values = [latest.rss_mb, latest.shared_mb, latest.private_mb, latest.swap_mb]
            memory_values = [max(0, v) for v in memory_values]  # Ensure non-negative
            
            ax4.pie(memory_values, labels=memory_types, autopct='%1.1f%%')
            ax4.set_title('Memory Composition (Latest)')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/memory_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Memory analysis plot saved to {output_dir}/memory_analysis.png")
        
    def save_snapshots(self, filename: str):
        """Save memory snapshots to file"""
        data = {
            'snapshots': [
                {
                    'timestamp': s.timestamp,
                    'rss_mb': s.rss_mb,
                    'vms_mb': s.vms_mb,
                    'shared_mb': s.shared_mb,
                    'private_mb': s.private_mb,
                    'python_objects': s.python_objects,
                    'custom_metrics': s.custom_metrics
                }
                for s in self.snapshots
            ],
            'detected_leaks': [
                {
                    'location': leak.location,
                    'size_bytes': leak.size_bytes,
                    'growth_rate': leak.growth_rate_mb_per_sec,
                    'leak_type': leak.leak_type,
                    'first_seen': leak.first_seen,
                    'last_seen': leak.last_seen
                }
                for leak in self.detected_leaks
            ]
        }
        
        with gzip.open(filename, 'wt') as f:
            json.dump(data, f, indent=2)
        
        print(f"Memory snapshots saved to {filename}")


class CppMemoryProfiler:
    """C++ memory profiling integration"""
    
    def __init__(self):
        self.valgrind_enabled = self._check_valgrind()
        self.asan_enabled = self._check_asan()
        
    def _check_valgrind(self) -> bool:
        """Check if running under valgrind"""
        return os.environ.get('VALGRIND_COMMAND') is not None
        
    def _check_asan(self) -> bool:
        """Check if AddressSanitizer is enabled"""
        return os.environ.get('ASAN_OPTIONS') is not None
        
    def get_memory_info(self) -> Optional[Dict[str, Any]]:
        """Get C++ memory information if available"""
        info = {}
        
        # Try to get malloc info (Linux)
        if sys.platform.startswith('linux'):
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmPeak:'):
                            info['vm_peak_kb'] = int(line.split()[1])
                        elif line.startswith('VmHWM:'):
                            info['vm_hwm_kb'] = int(line.split()[1])
                        elif line.startswith('VmData:'):
                            info['vm_data_kb'] = int(line.split()[1])
                            
            except (IOError, ValueError):
                pass
                
        return info if info else None
        
    def run_valgrind_analysis(self, executable: str, args: List[str], 
                             output_dir: str = ".") -> Dict[str, Any]:
        """Run valgrind memory analysis"""
        if not self._find_valgrind():
            return {"error": "Valgrind not found"}
            
        log_file = Path(output_dir) / "valgrind_memcheck.log"
        
        valgrind_cmd = [
            'valgrind',
            '--tool=memcheck',
            '--leak-check=full',
            '--show-leak-kinds=all',
            '--track-origins=yes',
            '--log-file=str(log_file)',
            executable
        ] + args
        
        try:
            print(f"Running valgrind analysis: {' '.join(valgrind_cmd)}")
            result = subprocess.run(valgrind_cmd, capture_output=True, text=True, timeout=3600)
            
            # Parse valgrind output
            analysis = self._parse_valgrind_output(log_file)
            analysis['return_code'] = result.returncode
            analysis['log_file'] = str(log_file)
            
            return analysis
            
        except subprocess.TimeoutExpired:
            return {"error": "Valgrind analysis timed out"}
        except Exception as e:
            return {"error": f"Valgrind analysis failed: {str(e)}"}
            
    def _find_valgrind(self) -> bool:
        """Check if valgrind is available"""
        try:
            result = subprocess.run(['valgrind', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
            
    def _parse_valgrind_output(self, log_file: Path) -> Dict[str, Any]:
        """Parse valgrind log file"""
        if not log_file.exists():
            return {"error": "Valgrind log file not found"}
            
        analysis = {
            "leaks_detected": 0,
            "total_leaked_bytes": 0,
            "leak_details": [],
            "error_summary": {}
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
            # Parse leak summary
            import re
            leak_pattern = r'(\d+) bytes in (\d+) blocks are definitely lost'
            matches = re.findall(leak_pattern, content)
            
            for match in matches:
                bytes_lost = int(match[0])
                blocks_lost = int(match[1])
                analysis["total_leaked_bytes"] += bytes_lost
                analysis["leaks_detected"] += blocks_lost
                
            # Parse error summary
            error_pattern = r'ERROR SUMMARY: (\d+) errors from (\d+) contexts'
            error_match = re.search(error_pattern, content)
            if error_match:
                analysis["error_summary"] = {
                    "total_errors": int(error_match.group(1)),
                    "contexts": int(error_match.group(2))
                }
                
        except Exception as e:
            analysis["error"] = f"Failed to parse valgrind output: {str(e)}"
            
        return analysis


class GuiMemoryOptimizer:
    """GUI-specific memory optimization for PySide6 applications"""
    
    def __init__(self):
        self.widget_refs = weakref.WeakSet()
        self.plot_cache = {}
        self.data_cache = {}
        
    def optimize_matplotlib_memory(self):
        """Optimize matplotlib memory usage"""
        import matplotlib
        matplotlib.use('Agg')  # Use non-GUI backend when possible
        
        # Configure matplotlib for memory efficiency
        matplotlib.rcParams['figure.max_open_warning'] = 10
        matplotlib.rcParams['figure.figsize'] = [8, 6]  # Reasonable default size
        
        # Clear font cache periodically
        matplotlib.font_manager._get_font.cache_clear()
        
    def optimize_pandas_memory(self):
        """Optimize pandas memory usage"""
        # Configure pandas for memory efficiency
        pd.set_option('mode.chained_assignment', None)  # Reduce warning overhead
        pd.set_option('compute.use_bottleneck', True)   # Use optimized functions
        pd.set_option('compute.use_numexpr', True)      # Use fast evaluation
        
    def monitor_widget_leaks(self, widget):
        """Monitor widget for memory leaks"""
        self.widget_refs.add(widget)
        
        # Add cleanup callback
        if hasattr(widget, 'destroyed'):
            widget.destroyed.connect(lambda: self._widget_destroyed(widget))
            
    def _widget_destroyed(self, widget):
        """Handle widget destruction"""
        # Clear any cached data related to this widget
        widget_id = id(widget)
        self.plot_cache.pop(widget_id, None)
        self.data_cache.pop(widget_id, None)
        
    def clear_caches(self):
        """Clear all memory caches"""
        self.plot_cache.clear()
        self.data_cache.clear()
        gc.collect()  # Force garbage collection
        
    def get_memory_recommendations(self) -> List[str]:
        """Get memory optimization recommendations"""
        return [
            "Use matplotlib 'Agg' backend for non-interactive plots",
            "Implement plot caching for frequently accessed visualizations", 
            "Clear matplotlib figure cache regularly",
            "Use pandas categorical data types for string columns",
            "Implement data chunking for large datasets",
            "Use weak references for callback connections",
            "Monitor and limit concurrent plot windows",
            "Implement lazy loading for visualization data",
            "Use memory mapping for very large data files",
            "Regular garbage collection in long-running GUI sessions"
        ]


def main():
    """Demonstrate memory profiling capabilities"""
    print("EBL Simulation Memory Profiler Demo")
    print("=" * 40)
    
    # Create profiler
    profiler = MemoryProfiler(sample_interval=0.5)
    
    # Start profiling
    profiler.start_profiling()
    
    # Simulate memory usage patterns
    print("Simulating memory usage patterns...")
    
    # Pattern 1: Gradual growth (normal usage)
    data_list = []
    for i in range(100):
        data_list.append(np.random.random(1000))
        time.sleep(0.1)
        
    profiler.take_snapshot("after_data_allocation")
    
    # Pattern 2: Large allocation (simulation data)
    large_array = np.random.random((10000, 1000))
    profiler.take_snapshot("after_large_allocation")
    
    # Pattern 3: Memory leak simulation
    leaked_objects = []
    for i in range(50):
        leaked_objects.append([np.random.random(100) for _ in range(10)])
        time.sleep(0.05)
        
    profiler.take_snapshot("after_leak_simulation")
    
    # Stop profiling and analyze
    print("\nStopping profiler and analyzing results...")
    analysis = profiler.stop_profiling()
    
    # Generate report
    report = profiler.generate_memory_report(analysis)
    print("\n" + report)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profiler.save_snapshots(f"memory_snapshots_{timestamp}.json.gz")
    profiler.plot_memory_usage(".")
    
    # Save analysis
    with open(f"memory_analysis_{timestamp}.json", 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nMemory profiling complete. Results saved with timestamp {timestamp}")
    
    # GUI optimization recommendations
    gui_optimizer = GuiMemoryOptimizer()
    recommendations = gui_optimizer.get_memory_recommendations()
    
    print("\nGUI Memory Optimization Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")


if __name__ == "__main__":
    main()