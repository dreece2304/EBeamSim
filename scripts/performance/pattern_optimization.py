#!/usr/bin/env python3
"""
Pattern Generation Performance Optimization Analysis

Comprehensive analysis and optimization recommendations for the PatternGenerator.cc
component based on performance profiling and algorithmic analysis.

Key optimization opportunities identified:
1. Memory pre-allocation and pool management
2. Vectorized calculations using SIMD
3. Parallel pattern generation for large patterns
4. Caching of frequently used calculations
5. Reduced memory allocations in hot paths
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import time
import cProfile
import pstats
from pathlib import Path


@dataclass
class PatternOptimizationResult:
    """Results from pattern generation optimization analysis"""
    original_time: float
    optimized_time: float
    speedup_factor: float
    memory_reduction_mb: float
    optimization_technique: str
    pattern_size: int
    shot_pitch: int


class PatternGeneratorOptimizer:
    """Pattern generation performance optimizer and analyzer"""

    def __init__(self):
        self.results = []
        
    def analyze_current_implementation(self) -> Dict[str, Any]:
        """
        Analyze the current PatternGenerator.cc implementation for bottlenecks
        
        Based on code review, key bottlenecks identified:
        1. Individual G4ThreeVector construction in loops (lines 114, 231, 252)
        2. Repeated calculation of grid spacing (can be cached)
        3. Dynamic vector resizing during pattern generation
        4. Redundant parameter validation in hot paths
        """
        
        analysis = {
            "bottlenecks": [
                {
                    "location": "GenerateSquarePattern() lines 110-116",
                    "issue": "Individual G4ThreeVector construction in nested loops",
                    "impact": "HIGH - O(n²) allocations for square patterns",
                    "recommendation": "Pre-allocate vector, use bulk initialization"
                },
                {
                    "location": "CalculateDwellTime() lines 119-143", 
                    "issue": "Repeated floating-point calculations",
                    "impact": "MEDIUM - Called for every pattern generation",
                    "recommendation": "Cache grid spacing, use constexpr for constants"
                },
                {
                    "location": "Vector growth in pattern generation",
                    "issue": "Dynamic resizing of fExposurePoints vector",
                    "impact": "MEDIUM - Memory reallocations during growth",
                    "recommendation": "Reserve exact capacity upfront"
                },
                {
                    "location": "GenerateCustomPattern() lines 237-265",
                    "issue": "Redundant duplicate point checking",
                    "impact": "LOW - Only affects custom patterns",
                    "recommendation": "Use hash set for O(1) duplicate detection"
                }
            ],
            "optimization_opportunities": [
                {
                    "technique": "SIMD Vectorization",
                    "expected_speedup": "2-4x for large patterns",
                    "applicability": "Square and line pattern generation"
                },
                {
                    "technique": "Memory Pool Allocation",
                    "expected_speedup": "1.5-2x for repeated generations", 
                    "applicability": "All pattern types"
                },
                {
                    "technique": "Parallel Generation",
                    "expected_speedup": "Linear with cores for large patterns",
                    "applicability": "Patterns with >10,000 points"
                },
                {
                    "technique": "Template Specialization",
                    "expected_speedup": "1.2-1.5x via compile-time optimization",
                    "applicability": "Common pattern types"
                }
            ]
        }
        
        return analysis

    def benchmark_original_algorithm(self, pattern_sizes: List[int], shot_pitches: List[int]) -> List[Dict[str, Any]]:
        """Benchmark the original pattern generation algorithm (Python simulation)"""
        results = []
        
        for size in pattern_sizes:
            for pitch in shot_pitches:
                # Simulate original algorithm
                start_time = time.time()
                points = self._simulate_original_square_pattern(size, pitch)
                end_time = time.time()
                
                result = {
                    'pattern_size': size,
                    'shot_pitch': pitch, 
                    'total_points': len(points),
                    'generation_time': end_time - start_time,
                    'points_per_second': len(points) / (end_time - start_time),
                    'memory_mb': len(points) * 24 / (1024 * 1024)  # 3 doubles per point
                }
                results.append(result)
                
        return results

    def benchmark_optimized_algorithms(self, pattern_sizes: List[int], shot_pitches: List[int]) -> List[PatternOptimizationResult]:
        """Benchmark optimized pattern generation algorithms"""
        results = []
        
        # Test different optimization techniques
        optimizations = [
            ("vectorized_numpy", self._optimized_vectorized_pattern),
            ("preallocated_memory", self._optimized_preallocated_pattern),
            ("parallel_generation", self._optimized_parallel_pattern),
            ("cached_calculations", self._optimized_cached_pattern)
        ]
        
        for size in pattern_sizes:
            for pitch in shot_pitches:
                # Benchmark original
                original_time, original_points = self._time_pattern_generation(
                    self._simulate_original_square_pattern, size, pitch
                )
                original_memory = len(original_points) * 24 / (1024 * 1024)
                
                # Benchmark each optimization
                for opt_name, opt_func in optimizations:
                    try:
                        optimized_time, optimized_points = self._time_pattern_generation(
                            opt_func, size, pitch
                        )
                        optimized_memory = len(optimized_points) * 24 / (1024 * 1024)
                        
                        speedup = original_time / optimized_time if optimized_time > 0 else 1.0
                        memory_reduction = original_memory - optimized_memory
                        
                        results.append(PatternOptimizationResult(
                            original_time=original_time,
                            optimized_time=optimized_time,
                            speedup_factor=speedup,
                            memory_reduction_mb=memory_reduction,
                            optimization_technique=opt_name,
                            pattern_size=size,
                            shot_pitch=pitch
                        ))
                        
                    except Exception as e:
                        print(f"Error in {opt_name} optimization: {e}")
                        
        return results

    def _simulate_original_square_pattern(self, pattern_size: int, shot_pitch: int) -> np.ndarray:
        """Simulate the original PatternGenerator square pattern algorithm"""
        # Mimic the C++ implementation
        grid_spacing = shot_pitch * 1.0  # Machine grid (1 nm)
        n_points = int(pattern_size / grid_spacing)
        if n_points == 0:
            n_points = 1
            
        points = []
        half_size = (n_points - 1) * grid_spacing / 2.0
        
        # Simulate the nested loop from lines 110-116
        for i in range(n_points):
            for j in range(n_points):
                x = -half_size + i * grid_spacing
                y = -half_size + j * grid_spacing
                z = 0.0
                points.append([x, y, z])  # Simulate G4ThreeVector construction
                
        return np.array(points)

    def _optimized_vectorized_pattern(self, pattern_size: int, shot_pitch: int) -> np.ndarray:
        """Optimized pattern generation using vectorized operations"""
        grid_spacing = shot_pitch * 1.0
        n_points = max(1, int(pattern_size / grid_spacing))
        
        # Vectorized coordinate generation
        indices = np.arange(n_points)
        half_size = (n_points - 1) * grid_spacing / 2.0
        
        # Create coordinate arrays
        x_coords = -half_size + indices * grid_spacing
        y_coords = -half_size + indices * grid_spacing
        
        # Use meshgrid for efficient 2D generation
        X, Y = np.meshgrid(x_coords, y_coords)
        Z = np.zeros_like(X)
        
        # Stack into points array efficiently
        points = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
        
        return points

    def _optimized_preallocated_pattern(self, pattern_size: int, shot_pitch: int) -> np.ndarray:
        """Optimized pattern with pre-allocated memory"""
        grid_spacing = shot_pitch * 1.0
        n_points = max(1, int(pattern_size / grid_spacing))
        total_points = n_points * n_points
        
        # Pre-allocate full array (simulates C++ reserve())
        points = np.empty((total_points, 3), dtype=np.float64)
        half_size = (n_points - 1) * grid_spacing / 2.0
        
        # Fill array efficiently
        idx = 0
        for i in range(n_points):
            x = -half_size + i * grid_spacing
            for j in range(n_points):
                y = -half_size + j * grid_spacing
                points[idx] = [x, y, 0.0]
                idx += 1
                
        return points

    def _optimized_parallel_pattern(self, pattern_size: int, shot_pitch: int) -> np.ndarray:
        """Optimized pattern using parallel generation (simulated)"""
        # For large patterns, simulate parallel generation
        grid_spacing = shot_pitch * 1.0
        n_points = max(1, int(pattern_size / grid_spacing))
        
        if n_points > 100:  # Only parallelize large patterns
            # Simulate parallel generation by chunking
            chunk_size = max(1, n_points // 4)  # 4 "threads"
            chunks = []
            
            for chunk_start in range(0, n_points, chunk_size):
                chunk_end = min(chunk_start + chunk_size, n_points)
                chunk_points = self._generate_pattern_chunk(
                    chunk_start, chunk_end, n_points, grid_spacing
                )
                chunks.append(chunk_points)
                
            return np.vstack(chunks)
        else:
            # Fall back to vectorized for small patterns
            return self._optimized_vectorized_pattern(pattern_size, shot_pitch)

    def _optimized_cached_pattern(self, pattern_size: int, shot_pitch: int) -> np.ndarray:
        """Optimized pattern with cached calculations"""
        # Cache frequently used values
        grid_spacing = shot_pitch * 1.0
        n_points = max(1, int(pattern_size / grid_spacing))
        half_size = (n_points - 1) * grid_spacing / 2.0
        
        # Pre-compute coordinate arrays (cache-friendly)
        x_coords = np.linspace(-half_size, half_size, n_points)
        y_coords = np.linspace(-half_size, half_size, n_points)
        
        # Efficient meshgrid and stacking
        X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
        points = np.column_stack([X.ravel(), Y.ravel(), np.zeros(n_points * n_points)])
        
        return points

    def _generate_pattern_chunk(self, start_i: int, end_i: int, n_points: int, grid_spacing: float) -> np.ndarray:
        """Generate a chunk of pattern points (simulates parallel worker)"""
        half_size = (n_points - 1) * grid_spacing / 2.0
        chunk_points = []
        
        for i in range(start_i, end_i):
            x = -half_size + i * grid_spacing
            for j in range(n_points):
                y = -half_size + j * grid_spacing
                chunk_points.append([x, y, 0.0])
                
        return np.array(chunk_points)

    def _time_pattern_generation(self, func, size: int, pitch: int) -> Tuple[float, np.ndarray]:
        """Time a pattern generation function"""
        start_time = time.time()
        points = func(size, pitch)
        end_time = time.time()
        return end_time - start_time, points

    def generate_cpp_optimizations(self) -> str:
        """Generate C++ optimization recommendations"""
        
        cpp_optimizations = """
// PatternGenerator.cc Performance Optimizations
// Based on profiling analysis and algorithmic improvements

#include "PatternGenerator.hh"
#include "G4SystemOfUnits.hh"
#include "G4PhysicalConstants.hh"
#include <cmath>
#include <sstream>
#include <algorithm>
#include <execution>  // C++17 parallel algorithms

// OPTIMIZATION 1: Memory Pool for Pattern Points
class PatternPointPool {
private:
    static constexpr size_t POOL_SIZE = 1000000;  // 1M points
    static thread_local std::vector<G4ThreeVector> point_pool;
    static thread_local size_t pool_index;
    
public:
    static std::vector<G4ThreeVector>& get_points(size_t count) {
        if (count > POOL_SIZE) {
            // Fallback for very large patterns
            thread_local std::vector<G4ThreeVector> large_pool;
            large_pool.clear();
            large_pool.reserve(count);
            return large_pool;
        }
        
        point_pool.clear();
        point_pool.reserve(count);
        return point_pool;
    }
};

// OPTIMIZATION 2: Vectorized Square Pattern Generation
void PatternGenerator::GenerateSquarePatternOptimized() {
    // Cache calculations outside loops
    const G4double gridSpacing = fShotPitch * fMachineGrid;
    const G4int nPoints = std::max(1, static_cast<G4int>(std::floor(fPatternSize / gridSpacing)));
    const size_t totalPoints = static_cast<size_t>(nPoints) * nPoints;
    
    // Use memory pool for better cache performance
    auto& points_ref = PatternPointPool::get_points(totalPoints);
    points_ref.reserve(totalPoints);
    
    // Pre-calculate coordinate offsets
    const G4double halfSize = (nPoints - 1) * gridSpacing / 2.0;
    const G4double baseX = fPatternCenter.x() - halfSize;
    const G4double baseY = fPatternCenter.y() - halfSize;
    const G4double z = fPatternCenter.z();
    
    // SIMD-friendly loop structure with better cache locality
    if (totalPoints > 10000) {
        // Parallel generation for large patterns
        std::vector<size_t> indices(totalPoints);
        std::iota(indices.begin(), indices.end(), 0);
        
        std::for_each(std::execution::par_unseq, indices.begin(), indices.end(),
            [&](size_t idx) {
                const G4int i = idx / nPoints;
                const G4int j = idx % nPoints;
                const G4double x = baseX + i * gridSpacing;
                const G4double y = baseY + j * gridSpacing;
                points_ref[idx] = G4ThreeVector(x, y, z);
            });
    } else {
        // Sequential optimized version for smaller patterns
        size_t idx = 0;
        for (G4int i = 0; i < nPoints; ++i) {
            const G4double x = baseX + i * gridSpacing;
            for (G4int j = 0; j < nPoints; ++j) {
                const G4double y = baseY + j * gridSpacing;
                points_ref[idx++] = G4ThreeVector(x, y, z);
            }
        }
    }
    
    // Move to member vector (avoids copy)
    fExposurePoints = std::move(points_ref);
}

// OPTIMIZATION 3: Cached Dwell Time Calculation
class DwellTimeCache {
private:
    struct CacheKey {
        G4double shotPitch;
        G4double machineGrid; 
        G4double beamCurrent;
        G4double dose;
        
        bool operator==(const CacheKey& other) const {
            return std::abs(shotPitch - other.shotPitch) < 1e-9 &&
                   std::abs(machineGrid - other.machineGrid) < 1e-9 &&
                   std::abs(beamCurrent - other.beamCurrent) < 1e-9 &&
                   std::abs(dose - other.dose) < 1e-9;
        }
    };
    
    struct CacheKeyHash {
        size_t operator()(const CacheKey& key) const {
            size_t h1 = std::hash<G4double>{}(key.shotPitch);
            size_t h2 = std::hash<G4double>{}(key.machineGrid);
            size_t h3 = std::hash<G4double>{}(key.beamCurrent);
            size_t h4 = std::hash<G4double>{}(key.dose);
            return h1 ^ (h2 << 1) ^ (h3 << 2) ^ (h4 << 3);
        }
    };
    
    static std::unordered_map<CacheKey, std::pair<G4double, G4double>, CacheKeyHash> cache;
    
public:
    static std::pair<G4double, G4double> get_dwell_time_and_frequency(
        G4double shotPitch, G4double machineGrid, G4double beamCurrent, G4double dose) {
        
        CacheKey key{shotPitch, machineGrid, beamCurrent, dose};
        auto it = cache.find(key);
        
        if (it != cache.end()) {
            return it->second;
        }
        
        // Calculate and cache
        const G4double exposureGrid = shotPitch * machineGrid / nm;
        const G4double gridSquared = exposureGrid * exposureGrid;
        G4double clockFrequency = (beamCurrent * 100000.0) / (dose * gridSquared);
        
        constexpr G4double MAX_CLOCK_FREQ = 50.0;
        if (clockFrequency > MAX_CLOCK_FREQ) {
            clockFrequency = MAX_CLOCK_FREQ;
        }
        
        const G4double dwellTime = 1.0 / clockFrequency;
        
        auto result = std::make_pair(dwellTime, clockFrequency);
        cache[key] = result;
        return result;
    }
};

// OPTIMIZATION 4: Template Specialization for Common Patterns
template<G4int ShotPitch>
void PatternGenerator::GenerateSquarePatternSpecialized() {
    static_assert(ShotPitch > 0 && ShotPitch <= 16, "Invalid shot pitch");
    
    // Compile-time optimizations for common shot pitch values
    constexpr G4double GRID_FACTOR = ShotPitch * 1.0;  // Assumes 1nm machine grid
    
    const G4int nPoints = std::max(1, static_cast<G4int>(std::floor(fPatternSize / GRID_FACTOR)));
    const size_t totalPoints = static_cast<size_t>(nPoints) * nPoints;
    
    fExposurePoints.clear();
    fExposurePoints.reserve(totalPoints);
    
    const G4double halfSize = (nPoints - 1) * GRID_FACTOR / 2.0;
    const G4double baseX = fPatternCenter.x() - halfSize;
    const G4double baseY = fPatternCenter.y() - halfSize;
    const G4double z = fPatternCenter.z();
    
    // Unrolled loops for small common patterns
    if constexpr (ShotPitch <= 4 && totalPoints <= 10000) {
        // Loop unrolling for very small patterns
        for (G4int i = 0; i < nPoints; ++i) {
            const G4double x = baseX + i * GRID_FACTOR;
            for (G4int j = 0; j < nPoints; j += 4) {  // Unroll inner loop by 4
                if (j < nPoints) fExposurePoints.emplace_back(x, baseY + j * GRID_FACTOR, z);
                if (j+1 < nPoints) fExposurePoints.emplace_back(x, baseY + (j+1) * GRID_FACTOR, z);
                if (j+2 < nPoints) fExposurePoints.emplace_back(x, baseY + (j+2) * GRID_FACTOR, z);
                if (j+3 < nPoints) fExposurePoints.emplace_back(x, baseY + (j+3) * GRID_FACTOR, z);
            }
        }
    } else {
        // Use optimized general version
        GenerateSquarePatternOptimized();
    }
}

// OPTIMIZATION 5: Branch Prediction Optimization
void PatternGenerator::GeneratePatternOptimized() {
    fExposurePoints.clear();
    CalculateDwellTimeOptimized();
    
    // Likely branch first for better prediction
    if ([[likely]] fPatternType == SQUARE) {
        // Use template specialization for common shot pitches
        switch (fShotPitch) {
            case 1: GenerateSquarePatternSpecialized<1>(); break;
            case 2: GenerateSquarePatternSpecialized<2>(); break;
            case 4: GenerateSquarePatternSpecialized<4>(); break;
            case 8: GenerateSquarePatternSpecialized<8>(); break;
            default: GenerateSquarePatternOptimized(); break;
        }
    } else if ([[likely]] fPatternType == SINGLE_SPOT) {
        fExposurePoints.reserve(1);
        fExposurePoints.emplace_back(fPatternCenter);
    } else if (fPatternType == LINE) {
        GenerateLinePatternOptimized();
    } else {
        GenerateCustomPatternOptimized();
    }
    
    // Reduced logging for performance
    if (G4VerboseLevel > 0) {
        G4cout << "Generated " << fExposurePoints.size() << " points, "
               << "dwell: " << fDwellTime << " μs\\n";
    }
}

// Memory optimization: Thread-local storage definitions
thread_local std::vector<G4ThreeVector> PatternPointPool::point_pool;
thread_local size_t PatternPointPool::pool_index = 0;
std::unordered_map<DwellTimeCache::CacheKey, std::pair<G4double, G4double>, 
                   DwellTimeCache::CacheKeyHash> DwellTimeCache::cache;
"""
        
        return cpp_optimizations

    def create_performance_report(self, results: List[PatternOptimizationResult]) -> str:
        """Create comprehensive performance optimization report"""
        
        report = []
        report.append("Pattern Generation Performance Optimization Report")
        report.append("=" * 60)
        report.append("")
        
        # Group results by technique
        by_technique = {}
        for result in results:
            if result.optimization_technique not in by_technique:
                by_technique[result.optimization_technique] = []
            by_technique[result.optimization_technique].append(result)
            
        # Summary statistics
        all_speedups = [r.speedup_factor for r in results]
        report.append(f"Overall Performance Improvements:")
        report.append(f"  Total optimizations tested: {len(results)}")
        report.append(f"  Average speedup: {np.mean(all_speedups):.2f}x")
        report.append(f"  Maximum speedup: {np.max(all_speedups):.2f}x")
        report.append(f"  Minimum speedup: {np.min(all_speedups):.2f}x")
        report.append("")
        
        # Detailed breakdown by technique
        for technique, technique_results in by_technique.items():
            speedups = [r.speedup_factor for r in technique_results]
            memory_savings = [r.memory_reduction_mb for r in technique_results]
            
            report.append(f"{technique.replace('_', ' ').title()} Optimization:")
            report.append(f"  Average speedup: {np.mean(speedups):.2f}x")
            report.append(f"  Best case speedup: {np.max(speedups):.2f}x")
            report.append(f"  Average memory reduction: {np.mean(memory_savings):.2f} MB")
            report.append(f"  Tests performed: {len(technique_results)}")
            
            # Performance by pattern size
            sizes = sorted(set(r.pattern_size for r in technique_results))
            report.append(f"  Performance by pattern size:")
            for size in sizes:
                size_results = [r for r in technique_results if r.pattern_size == size]
                avg_speedup = np.mean([r.speedup_factor for r in size_results])
                report.append(f"    {size} nm pattern: {avg_speedup:.2f}x speedup")
            report.append("")
            
        # Recommendations
        report.append("Implementation Recommendations:")
        report.append("-" * 30)
        
        best_techniques = sorted(
            [(technique, np.mean([r.speedup_factor for r in results])) 
             for technique, results in by_technique.items()],
            key=lambda x: x[1], reverse=True
        )
        
        for i, (technique, avg_speedup) in enumerate(best_techniques[:3], 1):
            report.append(f"{i}. {technique.replace('_', ' ').title()}: "
                         f"{avg_speedup:.2f}x average speedup")
            
            if technique == "vectorized_numpy":
                report.append("   - Implement SIMD vectorization in C++")
                report.append("   - Use Intel intrinsics or compiler auto-vectorization")
                
            elif technique == "preallocated_memory":
                report.append("   - Pre-allocate fExposurePoints vector with exact size")
                report.append("   - Use memory pools for repeated pattern generation")
                
            elif technique == "parallel_generation":
                report.append("   - Parallelize large pattern generation with OpenMP")
                report.append("   - Use C++17 parallel algorithms for cross-platform support")
                
            elif technique == "cached_calculations":
                report.append("   - Cache dwell time calculations")
                report.append("   - Pre-compute coordinate offsets outside loops")
                
        return "\n".join(report)

    def plot_performance_analysis(self, results: List[PatternOptimizationResult], output_dir: str = "."):
        """Generate performance visualization plots"""
        
        # Speedup by technique
        techniques = list(set(r.optimization_technique for r in results))
        avg_speedups = []
        
        for technique in techniques:
            technique_results = [r for r in results if r.optimization_technique == technique]
            avg_speedups.append(np.mean([r.speedup_factor for r in technique_results]))
            
        plt.figure(figsize=(12, 8))
        
        # Subplot 1: Average speedup by technique
        plt.subplot(2, 2, 1)
        bars = plt.bar(range(len(techniques)), avg_speedups)
        plt.xlabel('Optimization Technique')
        plt.ylabel('Average Speedup Factor')
        plt.title('Pattern Generation Optimization Results')
        plt.xticks(range(len(techniques)), [t.replace('_', '\n') for t in techniques], rotation=45)
        
        # Color bars by performance
        for i, bar in enumerate(bars):
            if avg_speedups[i] > 3:
                bar.set_color('green')
            elif avg_speedups[i] > 2:
                bar.set_color('orange')
            else:
                bar.set_color('red')
                
        # Subplot 2: Speedup vs pattern size
        plt.subplot(2, 2, 2)
        for technique in techniques:
            technique_results = [r for r in results if r.optimization_technique == technique]
            sizes = [r.pattern_size for r in technique_results]
            speedups = [r.speedup_factor for r in technique_results]
            plt.scatter(sizes, speedups, label=technique.replace('_', ' '), alpha=0.7)
            
        plt.xlabel('Pattern Size (nm)')
        plt.ylabel('Speedup Factor')
        plt.title('Speedup vs Pattern Size')
        plt.legend()
        plt.xscale('log')
        
        # Subplot 3: Memory reduction
        plt.subplot(2, 2, 3)
        memory_reductions = [np.mean([r.memory_reduction_mb for r in results 
                                    if r.optimization_technique == technique]) 
                           for technique in techniques]
        plt.bar(range(len(techniques)), memory_reductions)
        plt.xlabel('Optimization Technique')
        plt.ylabel('Average Memory Reduction (MB)')
        plt.title('Memory Usage Improvements')
        plt.xticks(range(len(techniques)), [t.replace('_', '\n') for t in techniques], rotation=45)
        
        # Subplot 4: Performance efficiency
        plt.subplot(2, 2, 4)
        for technique in techniques:
            technique_results = [r for r in results if r.optimization_technique == technique]
            original_times = [r.original_time for r in technique_results]
            optimized_times = [r.optimized_time for r in technique_results]
            plt.scatter(original_times, optimized_times, label=technique.replace('_', ' '), alpha=0.7)
            
        # Add diagonal line for reference
        max_time = max(max(r.original_time for r in results), 
                      max(r.optimized_time for r in results))
        plt.plot([0, max_time], [0, max_time], 'k--', alpha=0.5, label='No improvement')
        
        plt.xlabel('Original Time (seconds)')
        plt.ylabel('Optimized Time (seconds)')
        plt.title('Original vs Optimized Performance')
        plt.legend()
        plt.xscale('log')
        plt.yscale('log')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/pattern_optimization_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Performance analysis plots saved to {output_dir}/pattern_optimization_analysis.png")


def main():
    """Run pattern optimization analysis"""
    optimizer = PatternGeneratorOptimizer()
    
    # Analyze current implementation
    print("Analyzing current PatternGenerator implementation...")
    analysis = optimizer.analyze_current_implementation()
    
    print("\nPerformance Bottlenecks Identified:")
    for bottleneck in analysis["bottlenecks"]:
        print(f"- {bottleneck['location']}: {bottleneck['issue']} (Impact: {bottleneck['impact']})")
    
    # Run performance benchmarks
    print("\nRunning performance benchmarks...")
    pattern_sizes = [1000, 5000, 10000, 25000, 50000]  # nm
    shot_pitches = [1, 2, 4, 8]
    
    optimization_results = optimizer.benchmark_optimized_algorithms(pattern_sizes, shot_pitches)
    
    # Generate report
    report = optimizer.create_performance_report(optimization_results)
    print("\n" + report)
    
    # Save detailed results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Save optimization report
    report_file = f"pattern_optimization_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\nDetailed report saved to {report_file}")
    
    # Save C++ optimizations
    cpp_file = f"pattern_optimization_cpp_{timestamp}.cpp"
    cpp_code = optimizer.generate_cpp_optimizations()
    with open(cpp_file, 'w') as f:
        f.write(cpp_code)
    print(f"C++ optimization code saved to {cpp_file}")
    
    # Generate plots
    optimizer.plot_performance_analysis(optimization_results, ".")
    
    print(f"\nOptimization analysis complete. Found up to "
          f"{max(r.speedup_factor for r in optimization_results):.2f}x speedup potential.")


if __name__ == "__main__":
    main()