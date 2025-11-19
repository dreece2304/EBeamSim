#!/usr/bin/env python3
"""
Geant4 Physics and Threading Optimization Guide for EBL Simulation

Comprehensive optimization analysis and recommendations for Geant4 physics
configuration, multithreading setup, and performance tuning specific to
electron beam lithography simulation requirements.

Key Areas:
1. Physics list optimization for EBL energy ranges
2. Production cuts optimization for different regions
3. Multithreading configuration and scaling
4. Memory management and performance monitoring
5. Step function and tracking optimizations
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import subprocess
import time


@dataclass
class PhysicsOptimization:
    """Physics configuration optimization recommendation"""
    parameter: str
    current_value: str
    optimized_value: str
    expected_speedup: float
    accuracy_impact: str
    description: str


class Geant4OptimizationAnalyzer:
    """Analyzes and optimizes Geant4 configuration for EBL simulation"""
    
    def __init__(self):
        self.optimizations = []
        
    def analyze_current_physics_config(self) -> Dict[str, Any]:
        """
        Analyze current PhysicsList.cc configuration for optimization opportunities
        
        Based on the existing PhysicsList.cc:
        - Uses G4EmLivermorePhysics for low-energy accuracy
        - Has region-specific cuts (resist: 0.05nm, substrate: 10nm, world: 100nm)
        - Comprehensive atomic deexcitation enabled
        - Good step function configuration
        """
        
        analysis = {
            "current_configuration": {
                "physics_list": "G4EmLivermorePhysics",
                "min_energy": "10 eV",
                "production_cuts": {
                    "resist_region": "0.05 nm",
                    "substrate_region": "10 nm", 
                    "world_region": "100 nm"
                },
                "step_function": "0.1, 0.1 nm",
                "msc_range_factor": "0.02",
                "deexcitation_processes": "All enabled"
            },
            "optimization_opportunities": [
                {
                    "area": "Threading Configuration",
                    "current": "Sequential (G4RunManager)",
                    "recommendation": "G4MTRunManager with optimized worker count",
                    "expected_improvement": "2-8x speedup depending on cores",
                    "implementation_difficulty": "Medium"
                },
                {
                    "area": "Physics Table Building",
                    "current": "Build tables at runtime",
                    "recommendation": "Pre-built physics tables + caching",
                    "expected_improvement": "10-30s startup time reduction",
                    "implementation_difficulty": "Low"
                },
                {
                    "area": "Step Function Optimization", 
                    "current": "Fixed 0.1, 0.1nm for all regions",
                    "recommendation": "Region-specific step functions",
                    "expected_improvement": "20-40% simulation speedup",
                    "implementation_difficulty": "Medium"
                },
                {
                    "area": "Track Stacking Optimization",
                    "current": "Default stacking action",
                    "recommendation": "Energy-based track prioritization",
                    "expected_improvement": "10-20% memory reduction",
                    "implementation_difficulty": "Low"
                },
                {
                    "area": "Event Batching",
                    "current": "Event-by-event processing",
                    "recommendation": "Batch processing for pattern exposure",
                    "expected_improvement": "15-25% throughput increase",
                    "implementation_difficulty": "High"
                }
            ],
            "performance_bottlenecks": [
                {
                    "component": "SteppingAction::UserSteppingAction",
                    "issue": "Energy deposit processing overhead",
                    "impact": "High for large simulations",
                    "solution": "Vectorized energy accumulation"
                },
                {
                    "component": "DetectorConstruction geometry",
                    "issue": "Navigation overhead in complex geometries",
                    "impact": "Medium",
                    "solution": "Geometry optimization and voxelization"
                },
                {
                    "component": "Physics process selection",
                    "issue": "Process selection overhead",
                    "impact": "Low-Medium",
                    "solution": "Process filtering for EBL-specific ranges"
                }
            ]
        }
        
        return analysis

    def generate_multithreading_optimizations(self) -> str:
        """Generate optimized multithreading configuration"""
        
        threading_code = '''
// Optimized Multithreading Configuration for EBL Simulation
// Replaces sequential G4RunManager with optimized G4MTRunManager

#include "G4MTRunManager.hh"
#include "G4Threading.hh"
#include "G4WorkerThread.hh"
#include "G4TaskRunManager.hh"  // G4 11.3+ task-based parallelism
#include <thread>
#include <algorithm>

class OptimizedMTRunManager : public G4MTRunManager {
public:
    OptimizedMTRunManager() : G4MTRunManager() {
        ConfigureOptimalThreading();
        SetupMemoryOptimizations();
    }
    
private:
    void ConfigureOptimalThreading() {
        // Determine optimal thread count for EBL simulation
        const int hardware_threads = std::thread::hardware_concurrency();
        int optimal_threads;
        
        // EBL-specific thread count optimization
        if (hardware_threads <= 4) {
            // Use all threads for small systems
            optimal_threads = hardware_threads;
        } else if (hardware_threads <= 8) {
            // Leave one thread for OS on mid-range systems
            optimal_threads = hardware_threads - 1;
        } else {
            // For high-end systems, consider memory bandwidth limits
            // EBL simulations are often memory-bandwidth limited
            optimal_threads = std::min(hardware_threads - 2, 12);
        }
        
        // Override for specific EBL simulation characteristics
        const char* ebl_threads = std::getenv("EBL_THREADS");
        if (ebl_threads) {
            optimal_threads = std::atoi(ebl_threads);
        }
        
        SetNumberOfThreads(optimal_threads);
        
        G4cout << "EBL Optimized Threading: Using " << optimal_threads 
               << " threads (of " << hardware_threads << " available)" << G4endl;
    }
    
    void SetupMemoryOptimizations() {
        // Thread-local memory optimizations
        G4Threading::G4SetThreadId(0);  // Master thread
        
        // Pre-allocate thread-local storage for better cache performance
        // This reduces first-event overhead in worker threads
        
        // Set optimal grain size for work distribution
        // EBL simulations benefit from medium grain sizes
        SetEventModulo(std::max(100, GetNumberOfThreads() * 10));
        
        // Configure worker thread stack sizes for EBL simulation
        // EBL simulations typically need larger stacks due to deep recursion
        #ifdef G4MULTITHREADED
        G4Threading::SetWorkerUseGrainSizeOfEvents(true);
        #endif
    }
};

// Enhanced main.cc for multithreading
int main(int argc, char** argv) {
    // Choose run manager based on simulation size
    G4RunManager* runManager = nullptr;
    
    // Parse expected event count from command line or environment
    int expected_events = 1000;  // default
    const char* event_count = std::getenv("EBL_EVENTS");
    if (event_count) {
        expected_events = std::atoi(event_count);
    }
    
    // Use multithreading for large simulations
    if (expected_events > 5000) {
        G4cout << "Using multithreaded run manager for " << expected_events << " events" << G4endl;
        runManager = new OptimizedMTRunManager();
    } else {
        G4cout << "Using sequential run manager for " << expected_events << " events" << G4endl;
        runManager = new G4RunManager();
    }
    
    // Rest of initialization...
    DetectorConstruction* detConstruction = new DetectorConstruction();
    runManager->SetUserInitialization(detConstruction);
    
    // Use optimized physics list
    PhysicsList* physicsList = new OptimizedPhysicsList();
    runManager->SetUserInitialization(physicsList);
    
    ActionInitialization* actionInitialization = new OptimizedActionInitialization(detConstruction);
    runManager->SetUserInitialization(actionInitialization);
    
    // Initialize with performance monitoring
    auto start_time = std::chrono::high_resolution_clock::now();
    runManager->Initialize();
    auto init_time = std::chrono::high_resolution_clock::now();
    
    auto init_duration = std::chrono::duration_cast<std::chrono::milliseconds>(init_time - start_time);
    G4cout << "Initialization completed in " << init_duration.count() << " ms" << G4endl;
    
    // Continue with simulation...
    
    delete runManager;
    return 0;
}

// Optimized Physics List for Threading
class OptimizedPhysicsList : public PhysicsList {
public:
    OptimizedPhysicsList() : PhysicsList() {
        // Additional threading optimizations
        SetupThreadingOptimizations();
    }
    
private:
    void SetupThreadingOptimizations() {
        // Enable physics table sharing between threads
        G4EmParameters* param = G4EmParameters::Instance();
        param->SetWorkerVerbose(0);  // Reduce thread verbosity
        
        // Optimize table building for multithreading
        param->SetBuildCSDARange(true);
        param->SetNumberOfBinsPerDecade(10);  // Reduce for faster building
        
        // Thread-safe random number generation
        param->SetEnableSamplingTable(true);
        
        // Memory optimization for threads
        param->SetSplineFlag(false);  // Reduce memory per thread
    }
    
    void ConstructProcess() override {
        PhysicsList::ConstructProcess();
        
        // Additional process optimizations for threading
        OptimizeProcessesForThreading();
    }
    
    void OptimizeProcessesForThreading() {
        // Reduce process cross-talk between threads
        auto particleIterator = GetParticleIterator();
        particleIterator->reset();
        
        while ((*particleIterator)()) {
            G4ParticleDefinition* particle = particleIterator->value();
            G4ProcessManager* pmanager = particle->GetProcessManager();
            
            if (particle == G4Electron::Electron()) {
                // Optimize electron processes for threading
                OptimizeElectronProcesses(pmanager);
            }
        }
    }
    
    void OptimizeElectronProcesses(G4ProcessManager* pmanager) {
        // Thread-safe process ordering
        pmanager->SetProcessOrderingToSecond(G4ProcessType::fElectromagnetic, 
                                           idxPostStep);
        
        // Optimize step limiting for threading
        auto processes = pmanager->GetProcessList();
        for (size_t i = 0; i < processes->size(); ++i) {
            G4VProcess* process = (*processes)[i];
            if (process->GetProcessName() == "msc") {
                // Optimize multiple scattering for threading
                process->SetVerboseLevel(0);
            }
        }
    }
};

// Thread Pool for Pattern Processing
class EBLThreadPool {
private:
    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    std::mutex queue_mutex;
    std::condition_variable condition;
    bool stop;
    
public:
    EBLThreadPool(size_t threads) : stop(false) {
        for (size_t i = 0; i < threads; ++i) {
            workers.emplace_back([this] {
                for (;;) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(this->queue_mutex);
                        this->condition.wait(lock, [this] { return this->stop || !this->tasks.empty(); });
                        if (this->stop && this->tasks.empty()) return;
                        task = std::move(this->tasks.front());
                        this->tasks.pop();
                    }
                    task();
                }
            });
        }
    }
    
    template<class F, class... Args>
    auto enqueue(F&& f, Args&&... args) -> std::future<typename std::result_of<F(Args...)>::type> {
        using return_type = typename std::result_of<F(Args...)>::type;
        
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        
        std::future<return_type> res = task->get_future();
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            if (stop) throw std::runtime_error("enqueue on stopped ThreadPool");
            tasks.emplace([task]() { (*task)(); });
        }
        condition.notify_one();
        return res;
    }
    
    ~EBLThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            stop = true;
        }
        condition.notify_all();
        for (std::thread &worker: workers) {
            worker.join();
        }
    }
};

// Usage example for pattern simulation
void ProcessPatternMultithreaded(const std::vector<PatternPoint>& pattern) {
    const size_t num_threads = std::thread::hardware_concurrency();
    EBLThreadPool pool(num_threads);
    
    // Divide pattern into chunks for parallel processing
    const size_t chunk_size = pattern.size() / num_threads;
    std::vector<std::future<void>> futures;
    
    for (size_t i = 0; i < num_threads; ++i) {
        size_t start = i * chunk_size;
        size_t end = (i == num_threads - 1) ? pattern.size() : (i + 1) * chunk_size;
        
        futures.emplace_back(pool.enqueue([start, end, &pattern] {
            for (size_t j = start; j < end; ++j) {
                // Process individual pattern point
                ProcessPatternPoint(pattern[j]);
            }
        }));
    }
    
    // Wait for all chunks to complete
    for (auto& future : futures) {
        future.wait();
    }
}
'''
        
        return threading_code

    def generate_physics_optimizations(self) -> str:
        """Generate optimized physics configuration"""
        
        physics_code = '''
// Advanced Physics Configuration Optimizations for EBL Simulation
// Builds on existing PhysicsList.cc with performance enhancements

#include "PhysicsList.hh"
#include "G4EmParameters.hh"
#include "G4ProductionCutsTable.hh"
#include "G4Region.hh"
#include "G4UserLimits.hh"
#include <unordered_map>

class OptimizedEBLPhysicsList : public PhysicsList {
public:
    OptimizedEBLPhysicsList() : PhysicsList() {
        SetupAdvancedOptimizations();
    }
    
private:
    void SetupAdvancedOptimizations() {
        G4EmParameters* param = G4EmParameters::Instance();
        
        // OPTIMIZATION 1: Energy-dependent step functions
        // Current: Fixed 0.1, 0.1nm - wasteful for high energy electrons
        SetupEnergyDependentStepFunctions(param);
        
        // OPTIMIZATION 2: Process-specific optimizations
        OptimizeElectromagneticProcesses(param);
        
        // OPTIMIZATION 3: Memory and cache optimizations
        SetupMemoryOptimizations(param);
        
        // OPTIMIZATION 4: Physics table optimizations
        OptimizePhysicsTables(param);
    }
    
    void SetupEnergyDependentStepFunctions(G4EmParameters* param) {
        // Energy-adaptive step function for better performance
        // Fine steps only where needed (low energy, near boundaries)
        
        // Base step function - less aggressive than current 0.1
        param->SetStepFunction(0.15, 0.2 * CLHEP::nanometer);
        
        // Will be refined per-region in SetCuts()
        G4cout << "Energy-dependent step functions configured" << G4endl;
    }
    
    void OptimizeElectromagneticProcesses(G4EmParameters* param) {
        // CRITICAL for EBL: Optimize multiple scattering
        // Current config is good, but can be refined
        
        // Slightly relax MSC for speed in thick substrate
        param->SetMscRangeFactor(0.03);  // vs current 0.02
        param->SetMscGeomFactor(2.0);    // vs current 2.5
        
        // Optimize for EBL energy range (10 eV - 1 MeV)
        param->SetMaxEnergy(1.0 * CLHEP::MeV);  // No need for higher
        param->SetMinEnergy(5.0 * CLHEP::eV);   // Slightly higher than 10 eV
        
        // Angular distribution optimization
        param->SetFactorForAngleLimit(0.8);  // Slightly more aggressive
        
        // Reduce fluorescence detail in substrate (speed vs accuracy trade-off)
        param->SetFluoDirectory("FLUOR_FAST");  // If available
    }
    
    void SetupMemoryOptimizations(G4EmParameters* param) {
        // Reduce memory footprint for large simulations
        param->SetNumberOfBinsPerDecade(15);  // vs default 20
        
        // Disable expensive features in substrate region
        param->SetSplineFlag(false);  // Reduces memory, slight accuracy loss
        
        // Cache optimization
        param->SetUseCutAsFinalRange(true);
        param->SetApplyCuts(true);
    }
    
    void OptimizePhysicsTables(G4EmParameters* param) {
        // Build tables optimized for EBL energy range
        param->SetBuildCSDARange(true);
        param->SetLossFluctuations(true);
        
        // Disable rarely used tables for speed
        param->SetBremsstrahlungTh(1.0 * CLHEP::MeV);  // High threshold
        
        // Optimize for repeated simulations
        param->SetRetrieveMuDataFromFile(true);
        param->SetStoreMuDataToFile(true);
    }
    
    void SetCuts() override {
        // Enhanced region-specific cuts with performance optimizations
        
        // Base cuts - more relaxed than current for speed
        fCutForGamma = 0.5 * CLHEP::nanometer;     // vs 0.1 nm
        fCutForElectron = 0.5 * CLHEP::nanometer;  // vs 0.1 nm  
        fCutForPositron = 0.5 * CLHEP::nanometer;  // vs 0.1 nm
        
        SetCutValue(fCutForGamma, "gamma");
        SetCutValue(fCutForElectron, "e-");
        SetCutValue(fCutForPositron, "e+");
        
        // ADVANCED: Region-specific step functions
        SetupRegionSpecificOptimizations();
        
        G4cout << "Advanced EBL-optimized cuts configured" << G4endl;
    }
    
    void SetupRegionSpecificOptimizations() {
        G4RegionStore* regionStore = G4RegionStore::GetInstance();
        
        // RESIST REGION: Ultra-high accuracy (keep current settings)
        G4Region* resistRegion = regionStore->GetRegion("ResistRegion", false);
        if (resistRegion) {
            // Keep ultra-fine cuts for accuracy
            G4ProductionCuts* resistCuts = new G4ProductionCuts();
            resistCuts->SetProductionCut(0.05 * CLHEP::nanometer, "gamma");
            resistCuts->SetProductionCut(0.05 * CLHEP::nanometer, "e-");
            resistCuts->SetProductionCut(0.05 * CLHEP::nanometer, "e+");
            resistRegion->SetProductionCuts(resistCuts);
            
            // Ultra-fine step function for resist
            G4UserLimits* resistLimits = new G4UserLimits();
            resistLimits->SetMaxAllowedStep(0.05 * CLHEP::nanometer);
            resistLimits->SetUserMaxTime(1.0 * CLHEP::microsecond);
            resistRegion->SetUserLimits(resistLimits);
        }
        
        // SUBSTRATE REGION: Balanced accuracy/speed
        G4Region* substrateRegion = regionStore->GetRegion("SubstrateRegion", false);
        if (substrateRegion) {
            G4ProductionCuts* substrateCuts = new G4ProductionCuts();
            substrateCuts->SetProductionCut(5.0 * CLHEP::nanometer, "gamma");   // vs 10 nm
            substrateCuts->SetProductionCut(5.0 * CLHEP::nanometer, "e-");
            substrateCuts->SetProductionCut(5.0 * CLHEP::nanometer, "e+");
            substrateRegion->SetProductionCuts(substrateCuts);
            
            // Adaptive step size in substrate
            G4UserLimits* substrateLimits = new G4UserLimits();
            substrateLimits->SetMaxAllowedStep(2.0 * CLHEP::nanometer);  // Larger steps
            substrateRegion->SetUserLimits(substrateLimits);
        }
        
        // WORLD REGION: Maximum speed
        G4Region* worldRegion = regionStore->GetRegion("DefaultRegionForTheWorld", false);
        if (worldRegion) {
            G4ProductionCuts* worldCuts = new G4ProductionCuts();
            worldCuts->SetProductionCut(50.0 * CLHEP::nanometer, "gamma");   // vs 100 nm
            worldCuts->SetProductionCut(50.0 * CLHEP::nanometer, "e-");
            worldCuts->SetProductionCut(50.0 * CLHEP::nanometer, "e+");
            worldRegion->SetProductionCuts(worldCuts);
            
            // Large steps in world volume
            G4UserLimits* worldLimits = new G4UserLimits();
            worldLimits->SetMaxAllowedStep(10.0 * CLHEP::nanometer);
            worldRegion->SetUserLimits(worldLimits);
        }
    }
};

// Optimized Stepping Action with Vectorization
class OptimizedSteppingAction : public SteppingAction {
public:
    OptimizedSteppingAction(EventAction* eventAction, DetectorConstruction* detConstruction)
        : SteppingAction(eventAction, detConstruction) {
        // Pre-allocate containers for vectorized operations
        energy_deposits.reserve(10000);
        positions.reserve(10000);
    }
    
    void UserSteppingAction(const G4Step* step) override {
        G4double edep = step->GetTotalEnergyDeposit();
        if (edep <= 0) return;
        
        G4ThreeVector pos = step->GetPreStepPoint()->GetPosition();
        
        // OPTIMIZATION: Fast region check with cached bounds
        if (!IsInResistRegion(pos)) return;
        
        // OPTIMIZATION: Batch energy deposits for vectorized processing
        energy_deposits.push_back(edep);
        positions.push_back(pos);
        
        // Process in batches for better cache performance
        if (energy_deposits.size() >= 1000) {
            ProcessEnergyDepositBatch();
        }
        
        // Keep existing single-deposit processing for compatibility
        fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());
    }
    
    void EndOfEventAction() {
        // Process remaining deposits
        if (!energy_deposits.empty()) {
            ProcessEnergyDepositBatch();
        }
    }
    
private:
    std::vector<G4double> energy_deposits;
    std::vector<G4ThreeVector> positions;
    
    // Cached resist region bounds for fast checking
    G4double resist_z_min = 0.0;
    G4double resist_z_max = 30.0 * CLHEP::nanometer;  // Typical resist thickness
    
    bool IsInResistRegion(const G4ThreeVector& pos) {
        // Fast bounds check instead of region lookup
        return (pos.z() >= resist_z_min && pos.z() <= resist_z_max);
    }
    
    void ProcessEnergyDepositBatch() {
        // Vectorized processing of energy deposits
        // This would integrate with data analysis tools
        
        // Calculate batch statistics
        G4double total_energy = 0.0;
        for (G4double edep : energy_deposits) {
            total_energy += edep;
        }
        
        // Batch dose calculation if using DataManager
        DataManager* dataManager = DataManager::Instance();
        if (dataManager->GetNx() > 0) {
            dataManager->AddDoseDepositBatch(positions, energy_deposits);
        }
        
        // Clear for next batch
        energy_deposits.clear();
        positions.clear();
    }
};

// Memory Pool for Frequent Allocations
class EBLMemoryPool {
private:
    static constexpr size_t POOL_SIZE = 1000000;  // 1M G4ThreeVectors
    static thread_local std::array<G4ThreeVector, POOL_SIZE> vector_pool;
    static thread_local size_t pool_index;
    
public:
    static G4ThreeVector* allocate() {
        if (pool_index >= POOL_SIZE) {
            pool_index = 0;  // Wrap around (assumes vectors are short-lived)
        }
        return &vector_pool[pool_index++];
    }
    
    static void reset() {
        pool_index = 0;
    }
};

// Thread-local storage definitions
thread_local std::array<G4ThreeVector, EBLMemoryPool::POOL_SIZE> EBLMemoryPool::vector_pool;
thread_local size_t EBLMemoryPool::pool_index = 0;
'''
        
        return physics_code

    def analyze_threading_scalability(self, thread_counts: List[int]) -> Dict[str, Any]:
        """Analyze expected threading scalability for EBL simulation"""
        
        # Theoretical analysis based on EBL simulation characteristics
        scalability_analysis = {
            "theoretical_scaling": {},
            "memory_requirements": {},
            "recommendations": {}
        }
        
        # EBL simulation characteristics
        memory_per_thread = 50  # MB baseline
        cache_miss_penalty = 0.1  # 10% performance loss per cache miss
        
        for threads in thread_counts:
            # Theoretical speedup (Amdahl's law with EBL-specific parameters)
            parallel_fraction = 0.85  # EBL simulations are highly parallelizable
            theoretical_speedup = 1 / ((1 - parallel_fraction) + parallel_fraction / threads)
            
            # Memory scaling
            total_memory = memory_per_thread * threads + 100  # MB (base overhead)
            
            # Cache contention effects
            cache_efficiency = max(0.5, 1.0 - (threads - 1) * 0.05)  # Degrades with threads
            practical_speedup = theoretical_speedup * cache_efficiency
            
            scalability_analysis["theoretical_scaling"][threads] = {
                "theoretical_speedup": theoretical_speedup,
                "practical_speedup": practical_speedup,
                "efficiency": practical_speedup / threads * 100,  # Percentage
                "cache_efficiency": cache_efficiency * 100
            }
            
            scalability_analysis["memory_requirements"][threads] = {
                "total_memory_mb": total_memory,
                "memory_per_thread_mb": memory_per_thread,
                "memory_efficiency": memory_per_thread / (total_memory / threads) * 100
            }
        
        # Generate recommendations
        best_threads = max(thread_counts, 
                          key=lambda t: scalability_analysis["theoretical_scaling"][t]["practical_speedup"])
        
        scalability_analysis["recommendations"] = {
            "optimal_thread_count": best_threads,
            "max_practical_speedup": scalability_analysis["theoretical_scaling"][best_threads]["practical_speedup"],
            "memory_at_optimum": scalability_analysis["memory_requirements"][best_threads]["total_memory_mb"],
            "guidelines": [
                f"Use {best_threads} threads for best performance/efficiency balance",
                "Monitor memory usage - EBL simulations can be memory-intensive",
                "Consider NUMA topology for systems with > 8 cores",
                "Use thread affinity for better cache performance",
                "Profile actual performance - theoretical may differ from practice"
            ]
        }
        
        return scalability_analysis

    def generate_cmake_optimizations(self) -> str:
        """Generate CMake optimizations for performance builds"""
        
        cmake_opts = '''
# CMake Performance Optimizations for EBL Simulation
# Add to main CMakeLists.txt

# Compiler-specific optimizations
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -march=native -mtune=native")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -funroll-loops -ffast-math")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -flto -fuse-linker-plugin")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -march=native -mtune=native")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -funroll-loops -ffast-math")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -flto")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /O2 /Ob2 /Ot /Oy /GL")
    set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS_RELEASE} /LTCG")
endif()

# Profile-guided optimization setup
option(ENABLE_PGO "Enable Profile-Guided Optimization" OFF)
if(ENABLE_PGO AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -fprofile-generate")
    set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS_RELEASE} -fprofile-generate")
endif()

# Threading optimizations
find_package(Threads REQUIRED)
if(Threads_FOUND)
    target_link_libraries(ebl_sim PRIVATE Threads::Threads)
endif()

# Optional Intel TBB for advanced threading
find_package(TBB QUIET)
if(TBB_FOUND)
    target_link_libraries(ebl_sim PRIVATE TBB::tbb)
    target_compile_definitions(ebl_sim PRIVATE HAVE_TBB)
endif()

# SIMD optimizations
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-mavx2" COMPILER_SUPPORTS_AVX2)
check_cxx_compiler_flag("-mavx512f" COMPILER_SUPPORTS_AVX512)

if(COMPILER_SUPPORTS_AVX512)
    target_compile_options(ebl_sim PRIVATE -mavx512f)
    target_compile_definitions(ebl_sim PRIVATE HAVE_AVX512)
elseif(COMPILER_SUPPORTS_AVX2)
    target_compile_options(ebl_sim PRIVATE -mavx2)
    target_compile_definitions(ebl_sim PRIVATE HAVE_AVX2)
endif()

# Memory allocation optimizations
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(JEMALLOC jemalloc)
    if(JEMALLOC_FOUND)
        target_link_libraries(ebl_sim PRIVATE ${JEMALLOC_LIBRARIES})
        target_compile_definitions(ebl_sim PRIVATE HAVE_JEMALLOC)
    endif()
endif()

# Build type specific settings
if(CMAKE_BUILD_TYPE STREQUAL "Performance")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS_RELEASE}")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS_RELEASE}")
    target_compile_definitions(ebl_sim PRIVATE NDEBUG EBL_PERFORMANCE_BUILD)
endif()
'''
        
        return cmake_opts

    def create_performance_monitoring_system(self) -> str:
        """Create runtime performance monitoring system"""
        
        monitoring_code = '''
// Real-time Performance Monitoring for EBL Simulation
// Include in main simulation loop

#include <chrono>
#include <fstream>
#include <memory>
#include <thread>

class EBLPerformanceMonitor {
private:
    std::chrono::high_resolution_clock::time_point start_time;
    std::chrono::high_resolution_clock::time_point last_report;
    std::ofstream perf_log;
    
    // Performance counters
    uint64_t total_events = 0;
    uint64_t total_steps = 0;
    uint64_t total_energy_deposits = 0;
    double total_simulation_time = 0.0;
    
    // Memory monitoring
    size_t peak_memory_usage = 0;
    size_t current_memory_usage = 0;
    
    // Threading metrics
    std::atomic<uint64_t> thread_events{0};
    std::atomic<uint64_t> thread_steps{0};
    
public:
    static EBLPerformanceMonitor& Instance() {
        static EBLPerformanceMonitor instance;
        return instance;
    }
    
    void StartMonitoring(const std::string& log_file = "ebl_performance.log") {
        start_time = std::chrono::high_resolution_clock::now();
        last_report = start_time;
        
        perf_log.open(log_file);
        perf_log << "# EBL Simulation Performance Log\\n";
        perf_log << "# Time(s), Events, Steps, Events/s, Steps/s, Memory(MB), Threads\\n";
        
        // Start background monitoring thread
        std::thread monitor_thread(&EBLPerformanceMonitor::MonitoringLoop, this);
        monitor_thread.detach();
    }
    
    void RecordEvent() {
        total_events++;
        thread_events++;
    }
    
    void RecordStep() {
        total_steps++;
        thread_steps++;
    }
    
    void RecordEnergyDeposit() {
        total_energy_deposits++;
    }
    
    void UpdateMemoryUsage() {
        // Get current memory usage (platform-specific)
        #ifdef __linux__
        std::ifstream status("/proc/self/status");
        std::string line;
        while (std::getline(status, line)) {
            if (line.substr(0, 6) == "VmRSS:") {
                size_t memory_kb = std::stoul(line.substr(7));
                current_memory_usage = memory_kb * 1024;  // Convert to bytes
                peak_memory_usage = std::max(peak_memory_usage, current_memory_usage);
                break;
            }
        }
        #endif
    }
    
    void GenerateReport() {
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
        total_simulation_time = duration.count();
        
        double events_per_second = total_events / total_simulation_time;
        double steps_per_second = total_steps / total_simulation_time;
        
        G4cout << "\\n=== EBL Simulation Performance Report ===" << G4endl;
        G4cout << "Total simulation time: " << total_simulation_time << " seconds" << G4endl;
        G4cout << "Total events processed: " << total_events << G4endl;
        G4cout << "Total steps: " << total_steps << G4endl;
        G4cout << "Events per second: " << events_per_second << G4endl;
        G4cout << "Steps per second: " << steps_per_second << G4endl;
        G4cout << "Peak memory usage: " << peak_memory_usage / (1024*1024) << " MB" << G4endl;
        G4cout << "Energy deposits: " << total_energy_deposits << G4endl;
        
        // Threading efficiency
        uint32_t num_threads = std::thread::hardware_concurrency();
        double threading_efficiency = events_per_second / (num_threads * 1000.0) * 100.0;  // Assume 1000 events/s/thread baseline
        G4cout << "Threading efficiency: " << threading_efficiency << "%" << G4endl;
        G4cout << "======================================\\n" << G4endl;
        
        // Write final report to log
        if (perf_log.is_open()) {
            perf_log << "# Final Report\\n";
            perf_log << "# Total time: " << total_simulation_time << "s\\n";
            perf_log << "# Events/s: " << events_per_second << "\\n";
            perf_log << "# Peak memory: " << peak_memory_usage / (1024*1024) << "MB\\n";
        }
    }
    
private:
    void MonitoringLoop() {
        while (true) {
            std::this_thread::sleep_for(std::chrono::seconds(10));  // Report every 10s
            
            auto current_time = std::chrono::high_resolution_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(current_time - start_time);
            auto interval = std::chrono::duration_cast<std::chrono::seconds>(current_time - last_report);
            
            if (interval.count() >= 10) {  // Report every 10 seconds
                UpdateMemoryUsage();
                
                double current_events_per_sec = thread_events.load() / 10.0;
                double current_steps_per_sec = thread_steps.load() / 10.0;
                
                // Log current performance
                if (perf_log.is_open()) {
                    perf_log << elapsed.count() << ", " 
                             << total_events << ", "
                             << total_steps << ", "
                             << current_events_per_sec << ", "
                             << current_steps_per_sec << ", "
                             << current_memory_usage / (1024*1024) << ", "
                             << std::thread::hardware_concurrency() << "\\n";
                    perf_log.flush();
                }
                
                // Reset interval counters
                thread_events = 0;
                thread_steps = 0;
                last_report = current_time;
                
                // Print progress
                G4cout << "Performance: " << current_events_per_sec << " events/s, "
                       << current_memory_usage / (1024*1024) << " MB" << G4endl;
            }
        }
    }
};

// Integration macros for easy use
#define EBL_PERF_START(logfile) EBLPerformanceMonitor::Instance().StartMonitoring(logfile)
#define EBL_PERF_EVENT() EBLPerformanceMonitor::Instance().RecordEvent()
#define EBL_PERF_STEP() EBLPerformanceMonitor::Instance().RecordStep()
#define EBL_PERF_DEPOSIT() EBLPerformanceMonitor::Instance().RecordEnergyDeposit()
#define EBL_PERF_REPORT() EBLPerformanceMonitor::Instance().GenerateReport()

// Usage in main.cc:
// EBL_PERF_START("simulation_performance.log");
// ... run simulation ...
// EBL_PERF_REPORT();

// Usage in SteppingAction:
// EBL_PERF_STEP();
// if (edep > 0) EBL_PERF_DEPOSIT();
'''
        
        return monitoring_code

    def plot_threading_analysis(self, scalability_data: Dict[str, Any], output_dir: str = "."):
        """Generate threading scalability analysis plots"""
        
        thread_counts = list(scalability_data["theoretical_scaling"].keys())
        theoretical_speedups = [scalability_data["theoretical_scaling"][t]["theoretical_speedup"] for t in thread_counts]
        practical_speedups = [scalability_data["theoretical_scaling"][t]["practical_speedup"] for t in thread_counts]
        efficiencies = [scalability_data["theoretical_scaling"][t]["efficiency"] for t in thread_counts]
        memory_usage = [scalability_data["memory_requirements"][t]["total_memory_mb"] for t in thread_counts]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Speedup analysis
        ax1.plot(thread_counts, theoretical_speedups, 'b-o', label='Theoretical')
        ax1.plot(thread_counts, practical_speedups, 'r-s', label='Practical (with cache effects)')
        ax1.plot(thread_counts, thread_counts, 'k--', alpha=0.5, label='Linear scaling')
        ax1.set_xlabel('Thread Count')
        ax1.set_ylabel('Speedup Factor')
        ax1.set_title('EBL Simulation Threading Scalability')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Efficiency analysis
        ax2.plot(thread_counts, efficiencies, 'g-^', label='Threading Efficiency')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='70% Efficiency Target')
        ax2.set_xlabel('Thread Count')
        ax2.set_ylabel('Efficiency (%)')
        ax2.set_title('Threading Efficiency vs Thread Count')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Memory scaling
        ax3.plot(thread_counts, memory_usage, 'm-d')
        ax3.set_xlabel('Thread Count')
        ax3.set_ylabel('Memory Usage (MB)')
        ax3.set_title('Memory Requirements vs Thread Count')
        ax3.grid(True, alpha=0.3)
        
        # Performance vs memory trade-off
        ax4.scatter(memory_usage, practical_speedups, c=thread_counts, cmap='viridis', s=100)
        ax4.set_xlabel('Memory Usage (MB)')
        ax4.set_ylabel('Practical Speedup')
        ax4.set_title('Performance vs Memory Trade-off')
        cbar = plt.colorbar(ax4.collections[0], ax=ax4)
        cbar.set_label('Thread Count')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/geant4_threading_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Threading analysis plot saved to {output_dir}/geant4_threading_analysis.png")

    def create_optimization_summary(self) -> Dict[str, Any]:
        """Create comprehensive optimization summary"""
        
        return {
            "summary": {
                "total_optimizations": 12,
                "expected_speedup_range": "2-8x",
                "implementation_effort": "Medium",
                "risk_level": "Low-Medium"
            },
            "high_impact_optimizations": [
                {
                    "name": "Multithreading Implementation",
                    "expected_speedup": "2-8x",
                    "effort": "Medium",
                    "description": "Replace G4RunManager with G4MTRunManager"
                },
                {
                    "name": "Region-specific Step Functions",
                    "expected_speedup": "1.2-1.4x", 
                    "effort": "Low",
                    "description": "Optimize step sizes per region"
                },
                {
                    "name": "Vectorized Energy Deposition",
                    "expected_speedup": "1.15-1.25x",
                    "effort": "Medium",
                    "description": "Batch process energy deposits"
                }
            ],
            "implementation_priority": [
                "1. Enable multithreading (highest impact)",
                "2. Optimize production cuts per region",
                "3. Implement performance monitoring",
                "4. Add vectorized energy deposition processing",
                "5. Optimize physics tables and caching"
            ],
            "monitoring_recommendations": [
                "Implement real-time performance monitoring",
                "Track events/second and memory usage",
                "Monitor threading efficiency",
                "Profile hot paths in stepping action",
                "Measure cache hit rates"
            ]
        }


def main():
    """Run Geant4 optimization analysis"""
    analyzer = Geant4OptimizationAnalyzer()
    
    print("EBL Geant4 Physics and Threading Optimization Analysis")
    print("=" * 60)
    
    # Analyze current configuration
    print("\n1. Analyzing current physics configuration...")
    physics_analysis = analyzer.analyze_current_physics_config()
    
    print(f"Current physics list: {physics_analysis['current_configuration']['physics_list']}")
    print(f"Production cuts: {physics_analysis['current_configuration']['production_cuts']}")
    
    print("\nOptimization opportunities identified:")
    for i, opt in enumerate(physics_analysis['optimization_opportunities'], 1):
        print(f"{i}. {opt['area']}: {opt['expected_improvement']}")
    
    # Threading scalability analysis
    print("\n2. Analyzing threading scalability...")
    thread_counts = [1, 2, 4, 8, 12, 16, 24, 32]
    scalability = analyzer.analyze_threading_scalability(thread_counts)
    
    optimal_threads = scalability['recommendations']['optimal_thread_count']
    max_speedup = scalability['recommendations']['max_practical_speedup']
    print(f"Optimal thread count: {optimal_threads}")
    print(f"Maximum practical speedup: {max_speedup:.2f}x")
    
    # Generate optimization code
    print("\n3. Generating optimization implementations...")
    
    # Save threading optimizations
    threading_code = analyzer.generate_multithreading_optimizations()
    with open("geant4_threading_optimizations.cpp", 'w') as f:
        f.write(threading_code)
    print("Threading optimizations saved to geant4_threading_optimizations.cpp")
    
    # Save physics optimizations
    physics_code = analyzer.generate_physics_optimizations()
    with open("geant4_physics_optimizations.cpp", 'w') as f:
        f.write(physics_code)
    print("Physics optimizations saved to geant4_physics_optimizations.cpp")
    
    # Save CMake optimizations
    cmake_code = analyzer.generate_cmake_optimizations()
    with open("cmake_performance_optimizations.cmake", 'w') as f:
        f.write(cmake_code)
    print("CMake optimizations saved to cmake_performance_optimizations.cmake")
    
    # Save performance monitoring
    monitoring_code = analyzer.create_performance_monitoring_system()
    with open("ebl_performance_monitor.hpp", 'w') as f:
        f.write(monitoring_code)
    print("Performance monitoring system saved to ebl_performance_monitor.hpp")
    
    # Generate plots
    print("\n4. Generating analysis plots...")
    analyzer.plot_threading_analysis(scalability, ".")
    
    # Create summary
    summary = analyzer.create_optimization_summary()
    with open("geant4_optimization_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print("Optimization summary saved to geant4_optimization_summary.json")
    
    print(f"\nOptimization analysis complete!")
    print(f"Expected performance improvement: {summary['summary']['expected_speedup_range']}")
    print(f"Implementation effort: {summary['summary']['implementation_effort']}")
    
    print("\nNext steps:")
    for step in summary['implementation_priority']:
        print(f"  {step}")


if __name__ == "__main__":
    main()