#!/usr/bin/env python3
"""
EBL Physics Validation Analyzer

Compares Geant4 Monte Carlo simulation results with:
1. Analytical models (Grün, Bethe-Bloch, etc.)
2. Experimental literature data
3. Established physics benchmarks

Validates:
- Electron ranges and straggling
- Backscatter coefficients
- Forward scatter distributions
- Energy deposition profiles
- Secondary electron generation
- Proximity effect parameters

Author: EBL Physics Validation Team
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import json
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.optimize import curve_fit
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Literature data and analytical models
class LiteratureData:
    """Reference data from literature for validation"""
    
    # Grün model electron ranges in PMMA (nm)
    GRUN_RANGES_PMMA = {
        20: 3.2, 50: 15.8, 100: 50.0, 
        200: 154, 300: 294, 500: 678
    }
    
    # Backscatter coefficients from Joy & Luo (1989)
    BACKSCATTER_SI = {
        20: 0.11, 50: 0.14, 100: 0.16, 
        200: 0.17, 300: 0.18, 500: 0.19
    }
    
    BACKSCATTER_GAAS = {
        20: 0.32, 50: 0.35, 100: 0.37, 
        200: 0.38, 300: 0.39, 500: 0.40
    }
    
    # Forward scatter widths (Gaussian σ) from Kratschmer & Rishton (1986)
    FORWARD_SCATTER_HSQ = {
        20: 1.5, 50: 0.8, 100: 0.5, 
        200: 0.3, 300: 0.25, 500: 0.18
    }
    
    # Proximity effect parameters (typical values)
    PROXIMITY_PARAMS = {
        'PMMA_Si': {'alpha': 0.8, 'beta_um': 5.0, 'eta': 0.7},
        'HSQ_Si': {'alpha': 0.9, 'beta_um': 3.5, 'eta': 0.6},
        'ARP_Si': {'alpha': 0.85, 'beta_um': 4.2, 'eta': 0.65}
    }

@dataclass
class ValidationResult:
    """Container for validation test results"""
    test_name: str
    measured_value: float
    reference_value: float
    relative_error: float
    absolute_error: float
    tolerance: float
    passed: bool
    confidence_interval: Tuple[float, float] = None
    notes: str = ""

class PhysicsValidationAnalyzer:
    """Comprehensive physics validation analyzer"""
    
    def __init__(self, data_directory: str = "output"):
        self.data_dir = Path(data_directory)
        self.results: List[ValidationResult] = []
        self.tolerance_strict = 0.05  # 5% for critical parameters
        self.tolerance_normal = 0.10  # 10% for typical parameters
        self.tolerance_loose = 0.20   # 20% for approximate parameters
        
        # Material properties database
        self.materials = {
            'PMMA': {'density': 1.18, 'composition': 'C5H8O2'},
            'HSQ': {'density': 1.4, 'composition': 'H8Si8O12'},
            'Si': {'density': 2.33, 'composition': 'Si'},
            'GaAs': {'density': 5.32, 'composition': 'GaAs'},
            'ARP': {'density': 1.25, 'composition': 'C3H4O'}
        }
        
    def load_simulation_data(self, filename: str) -> pd.DataFrame:
        """Load PSF data from simulation output"""
        try:
            file_path = self.data_dir / filename
            if file_path.suffix == '.csv':
                return pd.read_csv(file_path)
            elif file_path.suffix == '.txt':
                # Parse BEAMER format or custom format
                return self._parse_custom_format(file_path)
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
            return pd.DataFrame()
    
    def _parse_custom_format(self, file_path: Path) -> pd.DataFrame:
        """Parse custom PSF format files"""
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        radius = float(parts[0])
                        energy = float(parts[1])
                        data.append({'radius_nm': radius, 'energy_deposit': energy})
        return pd.DataFrame(data)
    
    def validate_electron_ranges(self) -> List[ValidationResult]:
        """Validate electron ranges against Grün model"""
        print("Validating electron ranges against Grün model...")
        range_results = []
        
        for energy in [20, 50, 100, 200, 300]:
            filename = f"range_validation_{energy}keV.csv"
            df = self.load_simulation_data(filename)
            
            if df.empty:
                continue
                
            # Calculate practical range (90% energy deposition)
            if 'z_nm' in df.columns and 'energy_deposit' in df.columns:
                cumulative_energy = df.groupby('z_nm')['energy_deposit'].sum().cumsum()
                total_energy = cumulative_energy.iloc[-1]
                range_90 = cumulative_energy[cumulative_energy <= 0.9 * total_energy].index[-1]
                
                reference = LiteratureData.GRUN_RANGES_PMMA.get(energy)
                if reference:
                    result = self._create_validation_result(
                        f"Range_{energy}keV", range_90, reference, 
                        self.tolerance_strict, "Grün model comparison"
                    )
                    range_results.append(result)
        
        return range_results
    
    def validate_backscatter_coefficients(self) -> List[ValidationResult]:
        """Validate backscatter coefficients"""
        print("Validating backscatter coefficients...")
        backscatter_results = []
        
        # Silicon validation
        for energy in [20, 50, 100, 200, 300]:
            filename = f"backscatter_Si_{energy}keV.csv"
            df = self.load_simulation_data(filename)
            
            if df.empty:
                continue
                
            # Calculate backscatter coefficient
            if 'radius_nm' in df.columns and 'energy_deposit' in df.columns:
                # Electrons that exit the top surface
                backscattered = df[df['z_nm'] > 0]['energy_deposit'].sum()
                total_incident = df['energy_deposit'].sum()
                eta_measured = backscattered / total_incident if total_incident > 0 else 0
                
                reference = LiteratureData.BACKSCATTER_SI.get(energy)
                if reference:
                    result = self._create_validation_result(
                        f"Backscatter_Si_{energy}keV", eta_measured, reference,
                        self.tolerance_normal, "Joy & Luo (1989)"
                    )
                    backscatter_results.append(result)
        
        # GaAs validation
        for energy in [100, 200, 300]:
            filename = f"backscatter_GaAs_{energy}keV.csv"
            df = self.load_simulation_data(filename)
            
            if df.empty:
                continue
                
            if 'radius_nm' in df.columns and 'energy_deposit' in df.columns:
                backscattered = df[df['z_nm'] > 0]['energy_deposit'].sum()
                total_incident = df['energy_deposit'].sum()
                eta_measured = backscattered / total_incident if total_incident > 0 else 0
                
                reference = LiteratureData.BACKSCATTER_GAAS.get(energy)
                if reference:
                    result = self._create_validation_result(
                        f"Backscatter_GaAs_{energy}keV", eta_measured, reference,
                        self.tolerance_normal, "Joy & Luo (1989)"
                    )
                    backscatter_results.append(result)
        
        return backscatter_results
    
    def validate_forward_scatter(self) -> List[ValidationResult]:
        """Validate forward scatter distributions"""
        print("Validating forward scatter distributions...")
        forward_results = []
        
        for energy in [20, 50, 100, 200, 300]:
            filename = f"forward_scatter_HSQ_{energy}keV.csv"
            df = self.load_simulation_data(filename)
            
            if df.empty:
                continue
            
            if 'radius_nm' in df.columns and 'energy_deposit' in df.columns:
                # Fit Gaussian to radial distribution
                sigma_measured = self._fit_gaussian_width(df)
                
                reference = LiteratureData.FORWARD_SCATTER_HSQ.get(energy)
                if reference and sigma_measured > 0:
                    result = self._create_validation_result(
                        f"ForwardScatter_HSQ_{energy}keV", sigma_measured, reference,
                        self.tolerance_normal, "Kratschmer & Rishton (1986)"
                    )
                    forward_results.append(result)
        
        return forward_results
    
    def validate_proximity_parameters(self) -> List[ValidationResult]:
        """Extract and validate proximity effect parameters"""
        print("Validating proximity effect parameters...")
        proximity_results = []
        
        systems = ['PMMA_Si', 'HSQ_Si']
        for system in systems:
            filename = f"proximity_{system}_100keV.csv"
            df = self.load_simulation_data(filename)
            
            if df.empty:
                continue
            
            # Fit proximity function: f(r) = (1/(1+η)) * [1 + η*exp(-r/β)]
            params = self._extract_proximity_parameters(df)
            if params:
                ref_params = LiteratureData.PROXIMITY_PARAMS.get(system, {})
                
                for param_name, measured_val in params.items():
                    ref_val = ref_params.get(param_name)
                    if ref_val:
                        result = self._create_validation_result(
                            f"Proximity_{param_name}_{system}", measured_val, ref_val,
                            self.tolerance_loose, "Typical literature values"
                        )
                        proximity_results.append(result)
        
        return proximity_results
    
    def _fit_gaussian_width(self, df: pd.DataFrame) -> float:
        """Fit Gaussian to radial energy distribution and extract width"""
        try:
            # Create radial bins
            r_bins = np.linspace(0, df['radius_nm'].max(), 100)
            energy_profile = np.zeros_like(r_bins)
            
            for i, r in enumerate(r_bins[:-1]):
                mask = (df['radius_nm'] >= r) & (df['radius_nm'] < r_bins[i+1])
                energy_profile[i] = df[mask]['energy_deposit'].sum()
            
            # Fit Gaussian: A * exp(-(r**2)/(2*sigma**2))
            def gaussian(r, A, sigma):
                return A * np.exp(-(r**2)/(2*sigma**2))
            
            # Initial guess
            p0 = [energy_profile.max(), 1.0]
            
            # Fit only the central portion
            fit_mask = r_bins < 5 * np.std(r_bins)
            popt, _ = curve_fit(gaussian, r_bins[fit_mask], energy_profile[fit_mask], 
                              p0=p0, maxfev=1000)
            
            return abs(popt[1])  # Return sigma
            
        except Exception as e:
            print(f"Gaussian fitting failed: {e}")
            return 0.0
    
    def _extract_proximity_parameters(self, df: pd.DataFrame) -> Optional[Dict]:
        """Extract proximity effect parameters from PSF data"""
        try:
            if 'radius_nm' not in df.columns:
                return None
            
            # Group by radius and sum energy
            radial_profile = df.groupby('radius_nm')['energy_deposit'].sum().reset_index()
            radial_profile = radial_profile.sort_values('radius_nm')
            
            r = radial_profile['radius_nm'].values
            energy = radial_profile['energy_deposit'].values
            
            # Normalize
            energy_norm = energy / energy.max()
            
            # Fit proximity function: f(r) = (1/(1+η)) * [1 + η*exp(-r/β)]
            def proximity_func(r, eta, beta):
                return (1/(1+eta)) * (1 + eta * np.exp(-r/beta))
            
            # Initial guess
            p0 = [0.7, 5.0]  # eta, beta (in micrometers)
            
            # Convert r to micrometers for fitting
            r_um = r / 1000.0
            
            popt, _ = curve_fit(proximity_func, r_um, energy_norm, 
                              p0=p0, maxfev=2000, bounds=([0.1, 0.5], [2.0, 20.0]))
            
            eta, beta = popt
            alpha = 1.0 / (1.0 + eta)
            
            return {
                'alpha': alpha,
                'beta_um': beta,
                'eta': eta
            }
            
        except Exception as e:
            print(f"Proximity parameter extraction failed: {e}")
            return None
    
    def _create_validation_result(self, test_name: str, measured: float, 
                                reference: float, tolerance: float, 
                                notes: str = "") -> ValidationResult:
        """Create a validation result object"""
        abs_error = abs(measured - reference)
        rel_error = abs_error / reference if reference != 0 else float('inf')
        passed = rel_error <= tolerance
        
        return ValidationResult(
            test_name=test_name,
            measured_value=measured,
            reference_value=reference,
            relative_error=rel_error,
            absolute_error=abs_error,
            tolerance=tolerance,
            passed=passed,
            notes=notes
        )
    
    def run_comprehensive_validation(self) -> Dict:
        """Run all validation tests"""
        print("Starting comprehensive physics validation...")
        
        all_results = []
        
        # Run individual validation tests
        all_results.extend(self.validate_electron_ranges())
        all_results.extend(self.validate_backscatter_coefficients())
        all_results.extend(self.validate_forward_scatter())
        all_results.extend(self.validate_proximity_parameters())
        
        # Store results
        self.results = all_results
        
        # Generate summary
        summary = self._generate_summary()
        
        return summary
    
    def _generate_summary(self) -> Dict:
        """Generate validation summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'results': self.results
        }
        
        return summary
    
    def generate_validation_report(self, output_file: str = "physics_validation_report.html"):
        """Generate comprehensive HTML validation report"""
        html_content = self._create_html_report()
        
        report_path = self.data_dir / output_file
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        print(f"Validation report saved to: {report_path}")
    
    def _create_html_report(self) -> str:
        """Create HTML validation report"""
        summary = self._generate_summary()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>EBL Physics Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .pass {{ color: green; font-weight: bold; }}
                .fail {{ color: red; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .tolerance-strict {{ background-color: #ffeeee; }}
                .tolerance-normal {{ background-color: #fff7ee; }}
                .tolerance-loose {{ background-color: #eeffee; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>EBL Physics Validation Report</h1>
                <p>Comprehensive validation of Geant4 physics models against literature data</p>
                <p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>Validation Summary</h2>
                <p>Total Tests: {summary['total_tests']}</p>
                <p class="pass">Passed: {summary['passed_tests']}</p>
                <p class="fail">Failed: {summary['failed_tests']}</p>
                <p>Pass Rate: {summary['pass_rate']:.1%}</p>
            </div>
            
            <h2>Detailed Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Measured</th>
                    <th>Reference</th>
                    <th>Rel. Error</th>
                    <th>Tolerance</th>
                    <th>Status</th>
                    <th>Notes</th>
                </tr>
        """
        
        for result in self.results:
            status_class = "pass" if result.passed else "fail"
            tolerance_class = ("tolerance-strict" if result.tolerance <= 0.05 
                             else "tolerance-normal" if result.tolerance <= 0.10 
                             else "tolerance-loose")
            
            html += f"""
                <tr class="{tolerance_class}">
                    <td>{result.test_name}</td>
                    <td>{result.measured_value:.3f}</td>
                    <td>{result.reference_value:.3f}</td>
                    <td>{result.relative_error:.2%}</td>
                    <td>{result.tolerance:.1%}</td>
                    <td class="{status_class}">{'PASS' if result.passed else 'FAIL'}</td>
                    <td>{result.notes}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Validation Criteria</h2>
            <ul>
                <li><span class="tolerance-strict">Strict (5%)</span>: Critical parameters like electron ranges</li>
                <li><span class="tolerance-normal">Normal (10%)</span>: Important parameters like backscatter coefficients</li>
                <li><span class="tolerance-loose">Loose (20%)</span>: Approximate parameters like proximity effects</li>
            </ul>
            
        </body>
        </html>
        """
        
        return html
    
    def plot_validation_results(self):
        """Create validation plots"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Range validation
        self._plot_ranges(axes[0, 0])
        
        # Plot 2: Backscatter validation  
        self._plot_backscatter(axes[0, 1])
        
        # Plot 3: Forward scatter validation
        self._plot_forward_scatter(axes[1, 0])
        
        # Plot 4: Overall validation status
        self._plot_validation_summary(axes[1, 1])
        
        plt.tight_layout()
        plt.savefig(self.data_dir / 'validation_plots.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def _plot_ranges(self, ax):
        """Plot electron range validation"""
        range_results = [r for r in self.results if 'Range_' in r.test_name]
        
        if not range_results:
            ax.text(0.5, 0.5, 'No range data', ha='center', va='center')
            ax.set_title('Electron Range Validation')
            return
        
        energies = [int(r.test_name.split('_')[1].replace('keV', '')) for r in range_results]
        measured = [r.measured_value for r in range_results]
        reference = [r.reference_value for r in range_results]
        
        ax.loglog(energies, measured, 'bo-', label='Simulated')
        ax.loglog(energies, reference, 'rs-', label='Grün Model')
        ax.set_xlabel('Energy (keV)')
        ax.set_ylabel('Range (nm)')
        ax.set_title('Electron Range Validation')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_backscatter(self, ax):
        """Plot backscatter coefficient validation"""
        backscatter_results = [r for r in self.results if 'Backscatter_' in r.test_name]
        
        if not backscatter_results:
            ax.text(0.5, 0.5, 'No backscatter data', ha='center', va='center')
            ax.set_title('Backscatter Validation')
            return
        
        # Separate Si and GaAs results
        si_results = [r for r in backscatter_results if 'Si_' in r.test_name]
        gaas_results = [r for r in backscatter_results if 'GaAs_' in r.test_name]
        
        if si_results:
            si_energies = [int(r.test_name.split('_')[2].replace('keV', '')) for r in si_results]
            si_measured = [r.measured_value for r in si_results]
            si_reference = [r.reference_value for r in si_results]
            ax.plot(si_energies, si_measured, 'bo-', label='Si (Simulated)')
            ax.plot(si_energies, si_reference, 'b--', label='Si (Literature)')
        
        if gaas_results:
            gaas_energies = [int(r.test_name.split('_')[2].replace('keV', '')) for r in gaas_results]
            gaas_measured = [r.measured_value for r in gaas_results]
            gaas_reference = [r.reference_value for r in gaas_results]
            ax.plot(gaas_energies, gaas_measured, 'ro-', label='GaAs (Simulated)')
            ax.plot(gaas_energies, gaas_reference, 'r--', label='GaAs (Literature)')
        
        ax.set_xlabel('Energy (keV)')
        ax.set_ylabel('Backscatter Coefficient')
        ax.set_title('Backscatter Validation')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_forward_scatter(self, ax):
        """Plot forward scatter validation"""
        forward_results = [r for r in self.results if 'ForwardScatter_' in r.test_name]
        
        if not forward_results:
            ax.text(0.5, 0.5, 'No forward scatter data', ha='center', va='center')
            ax.set_title('Forward Scatter Validation')
            return
        
        energies = [int(r.test_name.split('_')[2].replace('keV', '')) for r in forward_results]
        measured = [r.measured_value for r in forward_results]
        reference = [r.reference_value for r in forward_results]
        
        ax.loglog(energies, measured, 'go-', label='Simulated')
        ax.loglog(energies, reference, 'ms-', label='Literature')
        ax.set_xlabel('Energy (keV)')
        ax.set_ylabel('Forward Scatter σ (nm)')
        ax.set_title('Forward Scatter Validation')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_validation_summary(self, ax):
        """Plot validation summary"""
        categories = ['Range', 'Backscatter', 'Forward Scatter', 'Proximity']
        pass_counts = []
        total_counts = []
        
        for category in categories:
            category_results = [r for r in self.results if category.replace(' ', '') in r.test_name]
            passed = sum(1 for r in category_results if r.passed)
            total = len(category_results)
            pass_counts.append(passed)
            total_counts.append(total)
        
        pass_rates = [p/t if t > 0 else 0 for p, t in zip(pass_counts, total_counts)]
        
        colors = ['green' if rate >= 0.8 else 'orange' if rate >= 0.6 else 'red' 
                 for rate in pass_rates]
        
        bars = ax.bar(categories, pass_rates, color=colors, alpha=0.7)
        ax.set_ylabel('Pass Rate')
        ax.set_title('Validation Summary by Category')
        ax.set_ylim(0, 1.1)
        
        # Add pass rate labels on bars
        for bar, rate in zip(bars, pass_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{rate:.1%}', ha='center', va='bottom')

def main():
    """Main validation script"""
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "output"
    
    analyzer = PhysicsValidationAnalyzer(data_dir)
    
    print("EBL Physics Validation Analyzer")
    print("==============================")
    
    # Run comprehensive validation
    summary = analyzer.run_comprehensive_validation()
    
    # Print summary
    print(f"\nValidation Results:")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    
    # Generate report
    analyzer.generate_validation_report()
    
    # Create plots
    analyzer.plot_validation_results()
    
    # Print detailed results
    print("\nDetailed Results:")
    print("-" * 80)
    for result in analyzer.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.test_name:30s} {result.measured_value:8.3f} vs {result.reference_value:8.3f} "
              f"({result.relative_error:6.1%}) [{status}]")

if __name__ == "__main__":
    main()