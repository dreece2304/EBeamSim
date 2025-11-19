#!/usr/bin/env python3
"""
EBL Physics Parameter Optimizer

Automated optimization of Geant4 physics parameters for EBL applications.
Uses multi-objective optimization to balance accuracy and performance.

Optimization targets:
1. Electron range accuracy (vs Grün model)
2. Backscatter coefficient accuracy (vs literature)
3. Forward scatter width accuracy
4. Simulation performance (speed)
5. Memory usage

Optimized parameters:
- Production cuts (region-specific)
- Multiple scattering parameters
- Step function parameters
- Energy thresholds
- Physics model selection

Author: EBL Physics Optimization Team
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import subprocess
import json
import time
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from scipy.optimize import minimize, differential_evolution
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OptimizationParameter:
    """Definition of an optimization parameter"""
    name: str
    min_value: float
    max_value: float
    default_value: float
    unit: str = ""
    description: str = ""
    importance: float = 1.0  # Weight in optimization
    
@dataclass
class OptimizationResult:
    """Result of a single optimization run"""
    parameters: Dict[str, float]
    accuracy_score: float
    performance_score: float  # Events per second
    memory_score: float       # Peak memory in MB
    combined_score: float
    validation_results: Dict = field(default_factory=dict)
    execution_time: float = 0.0

class EBLPhysicsOptimizer:
    """Multi-objective physics parameter optimizer for EBL"""
    
    def __init__(self, ebl_executable: str, work_dir: str = "optimization"):
        self.ebl_executable = Path(ebl_executable)
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
        # Optimization parameters
        self.parameters = self._define_optimization_parameters()
        
        # Reference data for accuracy scoring
        self.reference_data = self._load_reference_data()
        
        # Optimization settings
        self.max_evaluations = 100
        self.population_size = 20
        self.accuracy_weight = 0.6    # Weight for accuracy in combined score
        self.performance_weight = 0.3 # Weight for performance
        self.memory_weight = 0.1      # Weight for memory usage
        
        # Results storage
        self.optimization_history: List[OptimizationResult] = []
        self.best_result: Optional[OptimizationResult] = None
        
        # Surrogate model for expensive evaluations
        self.use_surrogate = True
        self.surrogate_model = None
        self.surrogate_data = []
        
    def _define_optimization_parameters(self) -> Dict[str, OptimizationParameter]:
        """Define the physics parameters to optimize"""
        return {
            'resist_cut': OptimizationParameter(
                name='resist_cut',
                min_value=0.005,  # 0.005 nm
                max_value=1.0,    # 1.0 nm
                default_value=0.05,
                unit='nm',
                description='Production cut in resist region',
                importance=2.0
            ),
            'substrate_cut': OptimizationParameter(
                name='substrate_cut',
                min_value=0.5,    # 0.5 nm
                max_value=20.0,   # 20 nm
                default_value=5.0,
                unit='nm',
                description='Production cut in substrate region',
                importance=1.5
            ),
            'msc_range_factor': OptimizationParameter(
                name='msc_range_factor',
                min_value=0.005,
                max_value=0.2,
                default_value=0.02,
                unit='',
                description='MSC range factor for step limitation',
                importance=2.0
            ),
            'msc_geom_factor': OptimizationParameter(
                name='msc_geom_factor',
                min_value=1.0,
                max_value=5.0,
                default_value=2.5,
                unit='',
                description='MSC geometry factor',
                importance=1.5
            ),
            'step_function_dRoverR': OptimizationParameter(
                name='step_function_dRoverR',
                min_value=0.01,
                max_value=0.3,
                default_value=0.1,
                unit='',
                description='Maximum relative energy loss per step',
                importance=2.0
            ),
            'step_function_final_range': OptimizationParameter(
                name='step_function_final_range',
                min_value=0.01,   # 0.01 nm
                max_value=2.0,    # 2.0 nm
                default_value=0.1,
                unit='nm',
                description='Final range for step function',
                importance=1.8
            ),
            'min_tracking_energy': OptimizationParameter(
                name='min_tracking_energy',
                min_value=5.0,    # 5 eV
                max_value=50.0,   # 50 eV
                default_value=10.0,
                unit='eV',
                description='Minimum tracking energy',
                importance=1.5
            ),
            'linear_loss_limit': OptimizationParameter(
                name='linear_loss_limit',
                min_value=0.001,
                max_value=0.1,
                default_value=0.01,
                unit='',
                description='Linear loss limit for fluctuations',
                importance=1.0
            )
        }
    
    def _load_reference_data(self) -> Dict:
        """Load reference data for accuracy evaluation"""
        return {
            'electron_ranges_pmma': {  # Grün model ranges in PMMA (nm)
                20: 3.2, 50: 15.8, 100: 50.0, 200: 154, 300: 294
            },
            'backscatter_si': {  # Joy & Luo backscatter coefficients for Si
                50: 0.14, 100: 0.16, 200: 0.17, 300: 0.18
            },
            'forward_scatter_hsq': {  # Forward scatter widths in HSQ (nm)
                50: 0.8, 100: 0.5, 200: 0.3, 300: 0.25
            }
        }
    
    def generate_macro(self, parameters: Dict[str, float], test_type: str = "validation") -> str:
        """Generate Geant4 macro with optimized parameters"""
        macro_content = f"""
# Auto-generated optimization macro
/run/verbose 0
/event/verbose 0
/tracking/verbose 0

# Set optimized physics parameters
/process/em/fluo true
/process/em/auger true
/process/em/pixe true
/process/em/deexcitationIgnoreCut true

# Production cuts
/run/setCut {parameters.get('substrate_cut', 5.0)} nm
/run/setCutForAGivenParticle e- {parameters.get('resist_cut', 0.05)} nm
/run/setCutForAGivenParticle e+ {parameters.get('resist_cut', 0.05)} nm
/run/setCutForAGivenParticle gamma {parameters.get('resist_cut', 0.05)} nm

/run/initialize

# Configure detector for PMMA on Si
/det/setResistComposition "C:5,H:8,O:2"
/det/setResistThickness 100 nm
/det/setResistDensity 1.18 g/cm3
/det/update

# Set beam parameters
/gun/particle e-
/gun/position 0 0 100 nm
/gun/direction 0 0 -1
/gun/beamSize 0.1 nm

# Run validation tests
"""
        
        if test_type == "validation":
            # Quick validation run
            macro_content += """
/analysis/setFileName optimization_test
/gun/energy 100 keV
/run/beamOn 1000
"""
        elif test_type == "comprehensive":
            # Comprehensive test for final evaluation
            energies = [50, 100, 200, 300]
            for energy in energies:
                macro_content += f"""
/analysis/setFileName opt_test_{energy}keV
/gun/energy {energy} keV
/run/beamOn 5000
"""
        
        return macro_content
    
    def run_simulation(self, parameters: Dict[str, float], test_type: str = "validation") -> Dict:
        """Run simulation with given parameters and return metrics"""
        # Create temporary directory for this run
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Generate macro
            macro_content = self.generate_macro(parameters, test_type)
            macro_file = temp_path / "optimization.mac"
            with open(macro_file, 'w') as f:
                f.write(macro_content)
            
            # Run simulation and measure performance
            start_time = time.time()
            try:
                result = subprocess.run([
                    str(self.ebl_executable),
                    str(macro_file)
                ], capture_output=True, text=True, cwd=temp_path, timeout=300)
                
                execution_time = time.time() - start_time
                
                if result.returncode != 0:
                    logger.warning(f"Simulation failed: {result.stderr}")
                    return self._create_failed_metrics(execution_time)
                
                # Parse results
                return self._parse_simulation_results(temp_path, execution_time, test_type)
                
            except subprocess.TimeoutExpired:
                logger.warning("Simulation timed out")
                return self._create_failed_metrics(300.0)
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                return self._create_failed_metrics(time.time() - start_time)
    
    def _parse_simulation_results(self, output_dir: Path, execution_time: float, test_type: str) -> Dict:
        """Parse simulation output and calculate metrics"""
        metrics = {
            'execution_time': execution_time,
            'performance_score': 0.0,
            'accuracy_score': 0.0,
            'memory_score': 0.0,
            'validation_results': {}
        }
        
        # Performance score (events per second)
        if test_type == "validation":
            events = 1000
        else:
            events = 5000 * 4  # 4 energies
        
        if execution_time > 0:
            metrics['performance_score'] = events / execution_time
        
        # Memory score (mock - would need actual memory monitoring)
        metrics['memory_score'] = max(0, 1000 - execution_time * 10)  # Simple model
        
        # Accuracy score from validation results
        accuracy_score = 0.0
        validation_count = 0
        
        # Look for output files
        for csv_file in output_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file)
                if not df.empty:
                    # Extract energy from filename
                    filename = csv_file.stem
                    if 'keV' in filename:
                        energy_str = filename.split('_')[-1].replace('keV', '')
                        try:
                            energy = int(energy_str)
                            
                            # Calculate specific metrics based on energy
                            if test_type == "comprehensive":
                                score = self._calculate_accuracy_score(df, energy)
                                accuracy_score += score
                                validation_count += 1
                                metrics['validation_results'][f'{energy}keV'] = score
                        except ValueError:
                            continue
                            
            except Exception as e:
                logger.warning(f"Error parsing {csv_file}: {e}")
        
        if validation_count > 0:
            metrics['accuracy_score'] = accuracy_score / validation_count
        
        return metrics
    
    def _calculate_accuracy_score(self, df: pd.DataFrame, energy: int) -> float:
        """Calculate accuracy score for specific energy"""
        score = 0.0
        
        if 'radius_nm' not in df.columns or 'energy_deposit' not in df.columns:
            return 0.0
        
        # Calculate electron range and compare to reference
        if energy in self.reference_data['electron_ranges_pmma']:
            if 'z_nm' in df.columns:
                # Calculate practical range (90% energy deposition depth)
                cumulative_energy = df.groupby('z_nm')['energy_deposit'].sum().cumsum()
                total_energy = cumulative_energy.iloc[-1]
                if total_energy > 0:
                    range_90_idx = (cumulative_energy <= 0.9 * total_energy).sum() - 1
                    if range_90_idx >= 0 and range_90_idx < len(cumulative_energy):
                        measured_range = cumulative_energy.index[range_90_idx]
                        reference_range = self.reference_data['electron_ranges_pmma'][energy]
                        
                        # Calculate relative error
                        rel_error = abs(measured_range - reference_range) / reference_range
                        range_score = max(0, 1.0 - rel_error)  # Score decreases with error
                        score += range_score * 0.5  # Weight: 50%
        
        # Calculate forward scatter width
        if energy in self.reference_data['forward_scatter_hsq']:
            # Simple radial spread calculation
            radial_data = df.groupby('radius_nm')['energy_deposit'].sum()
            if len(radial_data) > 0:
                # Calculate weighted standard deviation as scatter width approximation
                total_energy = radial_data.sum()
                if total_energy > 0:
                    weighted_mean = (radial_data.index * radial_data).sum() / total_energy
                    weighted_var = ((radial_data.index - weighted_mean)**2 * radial_data).sum() / total_energy
                    measured_width = np.sqrt(weighted_var)
                    
                    reference_width = self.reference_data['forward_scatter_hsq'][energy]
                    rel_error = abs(measured_width - reference_width) / reference_width
                    scatter_score = max(0, 1.0 - rel_error)
                    score += scatter_score * 0.3  # Weight: 30%
        
        # Backscatter coefficient calculation
        if energy in self.reference_data['backscatter_si'] and 'z_nm' in df.columns:
            backscattered_energy = df[df['z_nm'] > 0]['energy_deposit'].sum()
            total_energy = df['energy_deposit'].sum()
            if total_energy > 0:
                measured_backscatter = backscattered_energy / total_energy
                reference_backscatter = self.reference_data['backscatter_si'][energy]
                rel_error = abs(measured_backscatter - reference_backscatter) / reference_backscatter
                backscatter_score = max(0, 1.0 - rel_error)
                score += backscatter_score * 0.2  # Weight: 20%
        
        return score
    
    def _create_failed_metrics(self, execution_time: float) -> Dict:
        """Create metrics for failed simulation"""
        return {
            'execution_time': execution_time,
            'performance_score': 0.0,
            'accuracy_score': 0.0,
            'memory_score': 0.0,
            'validation_results': {}
        }
    
    def objective_function(self, param_values: np.ndarray) -> float:
        """Objective function for optimization (to be minimized)"""
        # Convert parameter values to dictionary
        parameters = {}
        param_names = list(self.parameters.keys())
        for i, value in enumerate(param_values):
            parameters[param_names[i]] = value
        
        # Run simulation
        metrics = self.run_simulation(parameters, "validation")
        
        # Calculate combined score (higher is better, so we negate for minimization)
        combined_score = (
            self.accuracy_weight * metrics['accuracy_score'] +
            self.performance_weight * min(1.0, metrics['performance_score'] / 100.0) +  # Normalize performance
            self.memory_weight * min(1.0, metrics['memory_score'] / 1000.0)   # Normalize memory
        )
        
        # Store result
        result = OptimizationResult(
            parameters=parameters,
            accuracy_score=metrics['accuracy_score'],
            performance_score=metrics['performance_score'],
            memory_score=metrics['memory_score'],
            combined_score=combined_score,
            validation_results=metrics['validation_results'],
            execution_time=metrics['execution_time']
        )
        
        self.optimization_history.append(result)
        
        # Update best result
        if self.best_result is None or combined_score > self.best_result.combined_score:
            self.best_result = result
            logger.info(f"New best result: {combined_score:.3f} (accuracy: {metrics['accuracy_score']:.3f}, "
                       f"performance: {metrics['performance_score']:.1f} events/s)")
        
        return -combined_score  # Negate because we're minimizing
    
    def optimize_parameters(self) -> OptimizationResult:
        """Run parameter optimization"""
        logger.info("Starting physics parameter optimization...")
        
        # Prepare bounds for optimization
        bounds = []
        param_names = []
        for name, param in self.parameters.items():
            bounds.append((param.min_value, param.max_value))
            param_names.append(name)
        
        logger.info(f"Optimizing {len(param_names)} parameters: {param_names}")
        
        # Use differential evolution for global optimization
        result = differential_evolution(
            self.objective_function,
            bounds,
            maxiter=self.max_evaluations // self.population_size,
            popsize=self.population_size,
            seed=42,
            disp=True,
            workers=1  # Sequential for now due to file I/O
        )
        
        logger.info(f"Optimization completed. Best score: {-result.fun:.3f}")
        
        # Final comprehensive evaluation of best parameters
        if self.best_result:
            logger.info("Running comprehensive validation of best parameters...")
            comprehensive_metrics = self.run_simulation(
                self.best_result.parameters, "comprehensive"
            )
            
            # Update best result with comprehensive metrics
            self.best_result.validation_results.update(comprehensive_metrics['validation_results'])
            
        return self.best_result
    
    def save_optimization_results(self, filename: str = "optimization_results.json"):
        """Save optimization results to file"""
        results_data = {
            'best_parameters': self.best_result.parameters if self.best_result else {},
            'best_scores': {
                'combined': self.best_result.combined_score if self.best_result else 0,
                'accuracy': self.best_result.accuracy_score if self.best_result else 0,
                'performance': self.best_result.performance_score if self.best_result else 0,
                'memory': self.best_result.memory_score if self.best_result else 0
            },
            'optimization_history': [
                {
                    'parameters': result.parameters,
                    'combined_score': result.combined_score,
                    'accuracy_score': result.accuracy_score,
                    'performance_score': result.performance_score,
                    'memory_score': result.memory_score,
                    'execution_time': result.execution_time
                }
                for result in self.optimization_history
            ],
            'parameter_definitions': {
                name: {
                    'min_value': param.min_value,
                    'max_value': param.max_value,
                    'default_value': param.default_value,
                    'unit': param.unit,
                    'description': param.description
                }
                for name, param in self.parameters.items()
            }
        }
        
        output_file = self.work_dir / filename
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"Optimization results saved to {output_file}")
    
    def plot_optimization_progress(self):
        """Plot optimization progress"""
        if not self.optimization_history:
            logger.warning("No optimization history to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        iterations = range(len(self.optimization_history))
        combined_scores = [r.combined_score for r in self.optimization_history]
        accuracy_scores = [r.accuracy_score for r in self.optimization_history]
        performance_scores = [r.performance_score for r in self.optimization_history]
        memory_scores = [r.memory_score for r in self.optimization_history]
        
        # Combined score
        axes[0, 0].plot(iterations, combined_scores, 'b-o', alpha=0.7)
        axes[0, 0].set_xlabel('Iteration')
        axes[0, 0].set_ylabel('Combined Score')
        axes[0, 0].set_title('Optimization Progress')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Accuracy score
        axes[0, 1].plot(iterations, accuracy_scores, 'g-o', alpha=0.7)
        axes[0, 1].set_xlabel('Iteration')
        axes[0, 1].set_ylabel('Accuracy Score')
        axes[0, 1].set_title('Physics Accuracy')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Performance score
        axes[1, 0].plot(iterations, performance_scores, 'r-o', alpha=0.7)
        axes[1, 0].set_xlabel('Iteration')
        axes[1, 0].set_ylabel('Performance (events/s)')
        axes[1, 0].set_title('Simulation Performance')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Memory score
        axes[1, 1].plot(iterations, memory_scores, 'm-o', alpha=0.7)
        axes[1, 1].set_xlabel('Iteration')
        axes[1, 1].set_ylabel('Memory Score')
        axes[1, 1].set_title('Memory Usage')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.work_dir / 'optimization_progress.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_optimized_macro(self, output_file: str = "optimized_physics.mac"):
        """Generate macro with optimized parameters"""
        if not self.best_result:
            logger.error("No optimization results available")
            return
        
        params = self.best_result.parameters
        
        macro_content = f"""# Optimized EBL Physics Parameters
# Generated by EBL Physics Optimizer
# Combined Score: {self.best_result.combined_score:.3f}
# Accuracy Score: {self.best_result.accuracy_score:.3f}

# Production cuts (optimized)
/run/setCut {params.get('substrate_cut', 5.0)} nm
/run/setCutForAGivenParticle e- {params.get('resist_cut', 0.05)} nm
/run/setCutForAGivenParticle e+ {params.get('resist_cut', 0.05)} nm
/run/setCutForAGivenParticle gamma {params.get('resist_cut', 0.05)} nm

# Enable all EM processes
/process/em/fluo true
/process/em/auger true
/process/em/pixe true
/process/em/deexcitationIgnoreCut true

# MSC parameters (optimized)
# Note: These would need to be implemented in physics messenger
# /process/em/mscRangeFactor {params.get('msc_range_factor', 0.02)}
# /process/em/mscGeomFactor {params.get('msc_geom_factor', 2.5)}

# Step function parameters (optimized)
# /process/em/stepFunction {params.get('step_function_dRoverR', 0.1)} {params.get('step_function_final_range', 0.1)} nm

# Energy thresholds (optimized)
# /process/em/minEnergy {params.get('min_tracking_energy', 10.0)} eV

/run/initialize
"""
        
        output_path = self.work_dir / output_file
        with open(output_path, 'w') as f:
            f.write(macro_content)
        
        logger.info(f"Optimized macro saved to {output_path}")

def main():
    """Main optimization script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EBL Physics Parameter Optimizer')
    parser.add_argument('executable', help='Path to EBL simulation executable')
    parser.add_argument('--work-dir', default='optimization', help='Working directory')
    parser.add_argument('--max-eval', type=int, default=100, help='Maximum evaluations')
    parser.add_argument('--population', type=int, default=20, help='Population size')
    
    args = parser.parse_args()
    
    # Create optimizer
    optimizer = EBLPhysicsOptimizer(args.executable, args.work_dir)
    optimizer.max_evaluations = args.max_eval
    optimizer.population_size = args.population
    
    print("EBL Physics Parameter Optimizer")
    print("==============================")
    print(f"Executable: {args.executable}")
    print(f"Work directory: {args.work_dir}")
    print(f"Max evaluations: {args.max_eval}")
    
    # Run optimization
    try:
        best_result = optimizer.optimize_parameters()
        
        if best_result:
            print(f"\nOptimization Results:")
            print(f"Combined Score: {best_result.combined_score:.3f}")
            print(f"Accuracy Score: {best_result.accuracy_score:.3f}")
            print(f"Performance: {best_result.performance_score:.1f} events/s")
            print(f"Memory Score: {best_result.memory_score:.1f}")
            
            print(f"\nOptimal Parameters:")
            for name, value in best_result.parameters.items():
                param = optimizer.parameters[name]
                print(f"  {name}: {value:.4f} {param.unit} ({param.description})")
            
            # Save results
            optimizer.save_optimization_results()
            optimizer.plot_optimization_progress()
            optimizer.generate_optimized_macro()
            
        else:
            print("Optimization failed - no valid results obtained")
            
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user")
        if optimizer.optimization_history:
            optimizer.save_optimization_results("partial_optimization_results.json")
            print("Partial results saved")
    
    except Exception as e:
        print(f"Optimization failed: {e}")
        raise

if __name__ == "__main__":
    main()