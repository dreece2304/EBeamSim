#!/usr/bin/env python3
"""
Resist Exposure Model Validation Framework

Comprehensive validation of resist exposure models against experimental data:

1. Resist Models:
   - Positive tone resists (PMMA, HSQ, ARP series)
   - Negative tone resists (ma-N series, SU-8)
   - Chemically amplified resists (CAR)
   - Multi-layer resist systems

2. Exposure Response:
   - Dose-response curves
   - Contrast measurements
   - Resolution limits
   - Line edge roughness (LER)

3. Material Properties:
   - Absorption coefficients
   - Quantum yield
   - Chain scission/crosslinking
   - Development rates

4. Process Validation:
   - Pre-exposure bake effects
   - Post-exposure bake effects
   - Development kinetics
   - Pattern collapse phenomena

Author: EBL Resist Modeling Team
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field
from scipy import optimize, integrate, interpolate
from scipy.special import erf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResistProperties:
    """Physical and chemical properties of resist materials"""
    name: str
    type: str  # "positive", "negative", "CAR"
    molecular_weight: float  # g/mol
    density: float  # g/cm³
    absorption_coefficient: float  # cm⁻¹ at exposure wavelength
    quantum_yield: float  # Number of events per absorbed photon/electron
    contrast: float  # γ (gamma) - steepness of dose response
    sensitivity: float  # D₀ - characteristic dose (μC/cm²)
    
    # Development parameters
    dev_rate_max: float  # Maximum development rate (nm/s)
    dev_rate_min: float  # Minimum development rate (nm/s)
    dev_selectivity: float  # Selectivity ratio
    
    # Optional parameters
    glass_transition_temp: Optional[float] = None  # °C
    etch_resistance: Optional[float] = None  # Relative to reference
    adhesion_promoter: Optional[str] = None
    
    @classmethod
    def create_pmma(cls) -> 'ResistProperties':
        """Create PMMA resist properties"""
        return cls(
            name="PMMA",
            type="positive",
            molecular_weight=100000,
            density=1.18,
            absorption_coefficient=0.1,
            quantum_yield=1.5,
            contrast=2.2,
            sensitivity=250,
            dev_rate_max=50,
            dev_rate_min=0.1,
            dev_selectivity=100,
            glass_transition_temp=105
        )
    
    @classmethod
    def create_hsq(cls) -> 'ResistProperties':
        """Create HSQ resist properties"""
        return cls(
            name="HSQ",
            type="negative",
            molecular_weight=43,  # Monomer unit
            density=1.4,
            absorption_coefficient=0.05,
            quantum_yield=0.8,
            contrast=1.8,
            sensitivity=800,
            dev_rate_max=20,
            dev_rate_min=0.05,
            dev_selectivity=400,
            glass_transition_temp=450
        )

@dataclass
class ExposureConditions:
    """Exposure and processing conditions"""
    beam_energy: float  # keV
    beam_current: float  # nA
    dose: float  # μC/cm²
    
    # Processing conditions
    peb_temperature: Optional[float] = None  # Post-exposure bake °C
    peb_time: Optional[float] = None  # Post-exposure bake time (s)
    dev_temperature: float = 20  # Development temperature °C
    dev_time: float = 60  # Development time (s)
    developer: str = "MIBK:IPA 1:3"  # Developer solution

@dataclass
class ExperimentalData:
    """Experimental validation data"""
    dose_series: np.ndarray  # Dose values (μC/cm²)
    thickness_remaining: np.ndarray  # Remaining thickness (fraction)
    line_width: np.ndarray  # Measured line widths (nm)
    target_width: np.ndarray  # Target line widths (nm)
    ler_3sigma: Optional[np.ndarray] = None  # Line edge roughness (nm)
    resolution_limit: Optional[float] = None  # Minimum resolvable feature (nm)
    
    @classmethod
    def load_from_csv(cls, filename: str) -> 'ExperimentalData':
        """Load experimental data from CSV file"""
        df = pd.read_csv(filename)
        
        return cls(
            dose_series=df['dose'].values,
            thickness_remaining=df['thickness_remaining'].values,
            line_width=df.get('line_width', np.zeros_like(df['dose'])).values,
            target_width=df.get('target_width', np.zeros_like(df['dose'])).values,
            ler_3sigma=df.get('ler_3sigma', None),
            resolution_limit=df.get('resolution_limit', [None])[0]
        )

class ResistModel:
    """Base class for resist exposure models"""
    
    def __init__(self, properties: ResistProperties):
        self.properties = properties
    
    def exposure_response(self, dose: np.ndarray) -> np.ndarray:
        """Calculate resist response to exposure dose"""
        raise NotImplementedError("Subclasses must implement exposure_response")
    
    def development_rate(self, exposure_level: np.ndarray) -> np.ndarray:
        """Calculate development rate as function of exposure level"""
        raise NotImplementedError("Subclasses must implement development_rate")
    
    def final_thickness(self, dose: np.ndarray, dev_time: float = 60) -> np.ndarray:
        """Calculate final resist thickness after development"""
        exposure = self.exposure_response(dose)
        dev_rate = self.development_rate(exposure)
        
        # Simple development model
        thickness_removed = dev_rate * dev_time
        thickness_remaining = np.maximum(0, 1.0 - thickness_removed)
        
        return thickness_remaining

class PositiveResistModel(ResistModel):
    """Model for positive-tone resists (PMMA, etc.)"""
    
    def exposure_response(self, dose: np.ndarray) -> np.ndarray:
        """
        Positive resist exposure response
        Uses modified sigmoidal model with quantum yield
        """
        D0 = self.properties.sensitivity
        gamma = self.properties.contrast
        quantum_yield = self.properties.quantum_yield
        
        # Effective dose considering quantum efficiency
        effective_dose = dose * quantum_yield
        
        # Sigmoidal response
        response = 1.0 / (1.0 + np.exp(-gamma * np.log(effective_dose / D0)))
        
        return response
    
    def development_rate(self, exposure_level: np.ndarray) -> np.ndarray:
        """
        Development rate for positive resist
        Higher exposure → higher development rate
        """
        rate_max = self.properties.dev_rate_max
        rate_min = self.properties.dev_rate_min
        
        # Exponential relationship between exposure and development rate
        rate = rate_min + (rate_max - rate_min) * exposure_level
        
        return rate

class NegativeResistModel(ResistModel):
    """Model for negative-tone resists (HSQ, ma-N, etc.)"""
    
    def exposure_response(self, dose: np.ndarray) -> np.ndarray:
        """
        Negative resist exposure response
        Crosslinking increases with dose
        """
        D0 = self.properties.sensitivity
        gamma = self.properties.contrast
        quantum_yield = self.properties.quantum_yield
        
        effective_dose = dose * quantum_yield
        
        # Crosslinking probability
        crosslink_density = 1.0 - np.exp(-effective_dose / D0)
        
        # Apply contrast
        response = crosslink_density ** (1.0 / gamma)
        
        return response
    
    def development_rate(self, exposure_level: np.ndarray) -> np.ndarray:
        """
        Development rate for negative resist
        Higher crosslinking → lower development rate
        """
        rate_max = self.properties.dev_rate_max
        rate_min = self.properties.dev_rate_min
        
        # Inverse relationship for negative resist
        rate = rate_max - (rate_max - rate_min) * exposure_level
        
        return np.maximum(rate, rate_min)

class CAResistModel(ResistModel):
    """Model for Chemically Amplified Resists"""
    
    def __init__(self, properties: ResistProperties, pag_concentration: float = 0.05):
        super().__init__(properties)
        self.pag_concentration = pag_concentration  # Photo-acid generator concentration
        self.amplification_factor = 100  # Chemical amplification factor
    
    def exposure_response(self, dose: np.ndarray, peb_temp: float = 110, 
                         peb_time: float = 90) -> np.ndarray:
        """
        CAR exposure response including acid generation and amplification
        """
        # Initial acid generation
        acid_generation_efficiency = self.properties.quantum_yield
        initial_acid = dose * acid_generation_efficiency * self.pag_concentration
        
        # Thermal amplification during PEB
        # Arrhenius model for reaction rate
        activation_energy = 50000  # J/mol (typical value)
        gas_constant = 8.314  # J/(mol·K)
        
        rate_constant = np.exp(-activation_energy / (gas_constant * (peb_temp + 273.15)))
        amplification = 1 + self.amplification_factor * rate_constant * peb_time
        
        final_acid = initial_acid * amplification
        
        # Resist response to acid concentration
        D0 = self.properties.sensitivity
        gamma = self.properties.contrast
        
        response = 1.0 / (1.0 + (D0 / final_acid) ** gamma)
        
        return response
    
    def development_rate(self, exposure_level: np.ndarray) -> np.ndarray:
        """Development rate for CAR (typically positive-tone behavior)"""
        rate_max = self.properties.dev_rate_max
        rate_min = self.properties.dev_rate_min
        
        rate = rate_min + (rate_max - rate_min) * exposure_level
        
        return rate

class ResistModelValidator:
    """Comprehensive resist model validation framework"""
    
    def __init__(self):
        self.models: Dict[str, ResistModel] = {}
        self.experimental_data: Dict[str, ExperimentalData] = {}
        self.validation_results: Dict = {}
    
    def add_model(self, name: str, model: ResistModel):
        """Add resist model to validation suite"""
        self.models[name] = model
        logger.info(f"Added resist model: {name}")
    
    def add_experimental_data(self, name: str, data: ExperimentalData):
        """Add experimental validation data"""
        self.experimental_data[name] = data
        logger.info(f"Added experimental data: {name}")
    
    def validate_dose_response(self, model_name: str, data_name: str) -> Dict:
        """Validate model dose response against experimental data"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        if data_name not in self.experimental_data:
            raise ValueError(f"Experimental data {data_name} not found")
        
        model = self.models[model_name]
        exp_data = self.experimental_data[data_name]
        
        # Calculate model predictions
        predicted_thickness = model.final_thickness(exp_data.dose_series)
        
        # Calculate metrics
        mse = np.mean((predicted_thickness - exp_data.thickness_remaining)**2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(predicted_thickness - exp_data.thickness_remaining))
        
        # R-squared
        ss_res = np.sum((exp_data.thickness_remaining - predicted_thickness)**2)
        ss_tot = np.sum((exp_data.thickness_remaining - np.mean(exp_data.thickness_remaining))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Sensitivity analysis
        d10_exp = self._find_dose_at_thickness(exp_data.dose_series, 
                                              exp_data.thickness_remaining, 0.1)
        d50_exp = self._find_dose_at_thickness(exp_data.dose_series, 
                                              exp_data.thickness_remaining, 0.5)
        
        dose_range = np.linspace(exp_data.dose_series.min(), 
                               exp_data.dose_series.max(), 1000)
        thickness_range = model.final_thickness(dose_range)
        
        d10_model = self._find_dose_at_thickness(dose_range, thickness_range, 0.1)
        d50_model = self._find_dose_at_thickness(dose_range, thickness_range, 0.5)
        
        # Calculate contrast from experimental data
        if d10_exp and d50_exp and d10_model and d50_model:
            contrast_exp = 1.0 / np.log10(d10_exp / d50_exp) if d10_exp != d50_exp else 0
            contrast_model = 1.0 / np.log10(d10_model / d50_model) if d10_model != d50_model else 0
            contrast_error = abs(contrast_model - contrast_exp) / contrast_exp if contrast_exp > 0 else 0
        else:
            contrast_exp = contrast_model = contrast_error = 0
        
        results = {
            'model_name': model_name,
            'data_name': data_name,
            'rmse': rmse,
            'mae': mae,
            'r_squared': r_squared,
            'contrast_experimental': contrast_exp,
            'contrast_model': contrast_model,
            'contrast_error': contrast_error,
            'sensitivity_d50_exp': d50_exp,
            'sensitivity_d50_model': d50_model,
            'predicted_thickness': predicted_thickness,
            'experimental_thickness': exp_data.thickness_remaining
        }
        
        return results
    
    def _find_dose_at_thickness(self, dose_array: np.ndarray, 
                               thickness_array: np.ndarray, 
                               target_thickness: float) -> Optional[float]:
        """Find dose that gives target remaining thickness"""
        try:
            # Interpolate to find dose
            interp_func = interpolate.interp1d(thickness_array, dose_array, 
                                             kind='linear', bounds_error=False)
            dose = interp_func(target_thickness)
            return float(dose) if not np.isnan(dose) else None
        except:
            return None
    
    def validate_line_width_bias(self, model_name: str, data_name: str) -> Dict:
        """Validate line width bias predictions"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        if data_name not in self.experimental_data:
            raise ValueError(f"Experimental data {data_name} not found")
        
        model = self.models[model_name]
        exp_data = self.experimental_data[data_name]
        
        # Calculate bias (measured - target)
        exp_bias = exp_data.line_width - exp_data.target_width
        
        # Simple bias model based on proximity effects and resist response
        # This is a simplified model - in practice would need more sophisticated approach
        predicted_bias = np.zeros_like(exp_bias)  # Placeholder
        
        # Calculate metrics
        bias_error = np.mean(np.abs(predicted_bias - exp_bias))
        
        results = {
            'model_name': model_name,
            'data_name': data_name,
            'experimental_bias': exp_bias,
            'predicted_bias': predicted_bias,
            'bias_error': bias_error
        }
        
        return results
    
    def parameter_optimization(self, model_name: str, data_name: str, 
                             parameters_to_fit: List[str] = None) -> Dict:
        """Optimize model parameters to fit experimental data"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        if data_name not in self.experimental_data:
            raise ValueError(f"Experimental data {data_name} not found")
        
        model = self.models[model_name]
        exp_data = self.experimental_data[data_name]
        
        if parameters_to_fit is None:
            parameters_to_fit = ['sensitivity', 'contrast']
        
        # Get initial parameter values
        initial_params = []
        param_names = []
        bounds = []
        
        for param in parameters_to_fit:
            if hasattr(model.properties, param):
                initial_params.append(getattr(model.properties, param))
                param_names.append(param)
                
                # Set reasonable bounds
                if param == 'sensitivity':
                    bounds.append((10, 2000))  # μC/cm²
                elif param == 'contrast':
                    bounds.append((0.5, 10))
                elif param == 'quantum_yield':
                    bounds.append((0.1, 5.0))
                else:
                    current_val = getattr(model.properties, param)
                    bounds.append((current_val * 0.1, current_val * 10))
        
        def objective(params):
            """Objective function for optimization"""
            # Update model parameters
            for i, param_name in enumerate(param_names):
                setattr(model.properties, param_name, params[i])
            
            # Calculate prediction
            predicted = model.final_thickness(exp_data.dose_series)
            
            # Return RMSE
            return np.sqrt(np.mean((predicted - exp_data.thickness_remaining)**2))
        
        # Optimize parameters
        result = optimize.minimize(objective, initial_params, 
                                 method='L-BFGS-B', bounds=bounds)
        
        # Update model with optimized parameters
        optimized_params = {}
        for i, param_name in enumerate(param_names):
            optimized_value = result.x[i]
            setattr(model.properties, param_name, optimized_value)
            optimized_params[param_name] = optimized_value
        
        # Calculate final metrics
        final_prediction = model.final_thickness(exp_data.dose_series)
        final_rmse = np.sqrt(np.mean((final_prediction - exp_data.thickness_remaining)**2))
        
        results = {
            'model_name': model_name,
            'data_name': data_name,
            'optimized_parameters': optimized_params,
            'initial_rmse': objective(initial_params),
            'final_rmse': final_rmse,
            'optimization_success': result.success,
            'optimization_message': result.message
        }
        
        return results
    
    def comprehensive_validation(self) -> Dict:
        """Run comprehensive validation across all models and datasets"""
        results = {
            'dose_response_validation': {},
            'line_width_validation': {},
            'parameter_optimization': {}
        }
        
        for model_name in self.models:
            for data_name in self.experimental_data:
                # Dose response validation
                try:
                    dose_results = self.validate_dose_response(model_name, data_name)
                    results['dose_response_validation'][f"{model_name}_{data_name}"] = dose_results
                except Exception as e:
                    logger.error(f"Dose response validation failed for {model_name} vs {data_name}: {e}")
                
                # Line width validation
                try:
                    lw_results = self.validate_line_width_bias(model_name, data_name)
                    results['line_width_validation'][f"{model_name}_{data_name}"] = lw_results
                except Exception as e:
                    logger.error(f"Line width validation failed for {model_name} vs {data_name}: {e}")
                
                # Parameter optimization
                try:
                    opt_results = self.parameter_optimization(model_name, data_name)
                    results['parameter_optimization'][f"{model_name}_{data_name}"] = opt_results
                except Exception as e:
                    logger.error(f"Parameter optimization failed for {model_name} vs {data_name}: {e}")
        
        return results
    
    def plot_dose_response_comparison(self, model_name: str, data_name: str, 
                                    save_path: Optional[Path] = None):
        """Plot dose response comparison between model and experiment"""
        if model_name not in self.models or data_name not in self.experimental_data:
            raise ValueError("Invalid model or data name")
        
        model = self.models[model_name]
        exp_data = self.experimental_data[data_name]
        
        # Calculate model predictions
        dose_range = np.logspace(np.log10(max(exp_data.dose_series.min(), 1)), 
                               np.log10(exp_data.dose_series.max()), 1000)
        predicted_thickness = model.final_thickness(dose_range)
        
        # Create plot
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Linear scale plot
        axes[0].plot(dose_range, predicted_thickness, 'b-', linewidth=2, 
                    label=f'{model_name} Model')
        axes[0].plot(exp_data.dose_series, exp_data.thickness_remaining, 
                    'ro', markersize=6, label='Experimental Data')
        axes[0].set_xlabel('Dose (μC/cm²)')
        axes[0].set_ylabel('Remaining Thickness (fraction)')
        axes[0].set_title(f'{model_name} vs {data_name} - Linear Scale')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        
        # Log scale plot
        axes[1].semilogx(dose_range, predicted_thickness, 'b-', linewidth=2, 
                        label=f'{model_name} Model')
        axes[1].semilogx(exp_data.dose_series, exp_data.thickness_remaining, 
                        'ro', markersize=6, label='Experimental Data')
        axes[1].set_xlabel('Dose (μC/cm²)')
        axes[1].set_ylabel('Remaining Thickness (fraction)')
        axes[1].set_title(f'{model_name} vs {data_name} - Log Scale')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Dose response plot saved to {save_path}")
        
        plt.show()
    
    def export_validation_report(self, output_file: str = "resist_validation_report.html"):
        """Export comprehensive validation report"""
        results = self.comprehensive_validation()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resist Model Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                .good {{ color: green; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
                .poor {{ color: red; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Resist Model Validation Report</h1>
                <p>Comprehensive validation of resist exposure models against experimental data</p>
                <p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h2>Models Under Test</h2>
                <ul>
        """
        
        for name, model in self.models.items():
            html_content += f"<li><strong>{name}</strong>: {model.properties.type.title()} tone, {model.properties.name}</li>"
        
        html_content += """
                </ul>
            </div>
            
            <div class="section">
                <h2>Dose Response Validation</h2>
                <table>
                    <tr>
                        <th>Model</th>
                        <th>Dataset</th>
                        <th>RMSE</th>
                        <th>R²</th>
                        <th>Contrast Error</th>
                        <th>Quality</th>
                    </tr>
        """
        
        for key, result in results['dose_response_validation'].items():
            rmse = result['rmse']
            r_squared = result['r_squared']
            contrast_error = result['contrast_error']
            
            # Quality assessment
            if rmse < 0.05 and r_squared > 0.95 and contrast_error < 0.1:
                quality = '<span class="good">Excellent</span>'
            elif rmse < 0.1 and r_squared > 0.9 and contrast_error < 0.2:
                quality = '<span class="warning">Good</span>'
            else:
                quality = '<span class="poor">Poor</span>'
            
            html_content += f"""
                    <tr>
                        <td>{result['model_name']}</td>
                        <td>{result['data_name']}</td>
                        <td>{rmse:.4f}</td>
                        <td>{r_squared:.4f}</td>
                        <td>{contrast_error:.4f}</td>
                        <td>{quality}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Parameter Optimization Results</h2>
                <table>
                    <tr>
                        <th>Model</th>
                        <th>Dataset</th>
                        <th>Initial RMSE</th>
                        <th>Final RMSE</th>
                        <th>Improvement</th>
                        <th>Optimized Parameters</th>
                    </tr>
        """
        
        for key, result in results['parameter_optimization'].items():
            initial_rmse = result['initial_rmse']
            final_rmse = result['final_rmse']
            improvement = (initial_rmse - final_rmse) / initial_rmse * 100
            
            param_str = ", ".join([f"{k}={v:.3f}" for k, v in result['optimized_parameters'].items()])
            
            html_content += f"""
                    <tr>
                        <td>{result['model_name']}</td>
                        <td>{result['data_name']}</td>
                        <td>{initial_rmse:.4f}</td>
                        <td>{final_rmse:.4f}</td>
                        <td>{improvement:.1f}%</td>
                        <td>{param_str}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    <li>Models with RMSE < 0.05 and R² > 0.95 are considered excellent for predictive use</li>
                    <li>Contrast errors > 20% indicate need for model refinement</li>
                    <li>Parameter optimization can significantly improve model accuracy</li>
                    <li>Consider additional experimental data for poorly performing models</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Validation report exported to {output_file}")

def create_synthetic_experimental_data() -> ExperimentalData:
    """Create synthetic experimental data for demonstration"""
    # Synthetic dose series
    dose_series = np.logspace(1, 3, 20)  # 10 to 1000 μC/cm²
    
    # Synthetic thickness response (positive tone resist)
    sensitivity = 200
    contrast = 2.5
    
    thickness_remaining = 1.0 / (1.0 + (dose_series / sensitivity) ** contrast)
    
    # Add some noise
    noise = np.random.normal(0, 0.02, len(thickness_remaining))
    thickness_remaining += noise
    thickness_remaining = np.clip(thickness_remaining, 0, 1)
    
    # Synthetic line width data
    target_widths = np.full_like(dose_series, 100)  # 100 nm target
    line_widths = target_widths + np.random.normal(0, 5, len(dose_series))  # +/- 5nm variation
    
    return ExperimentalData(
        dose_series=dose_series,
        thickness_remaining=thickness_remaining,
        line_width=line_widths,
        target_width=target_widths
    )

def main():
    """Main demonstration of resist model validation"""
    print("EBL Resist Model Validation Framework Demo")
    print("=" * 45)
    
    # Create validator
    validator = ResistModelValidator()
    
    # Add resist models
    pmma_properties = ResistProperties.create_pmma()
    hsq_properties = ResistProperties.create_hsq()
    
    pmma_model = PositiveResistModel(pmma_properties)
    hsq_model = NegativeResistModel(hsq_properties)
    
    validator.add_model("PMMA_Positive", pmma_model)
    validator.add_model("HSQ_Negative", hsq_model)
    
    print("Added resist models: PMMA (positive), HSQ (negative)")
    
    # Add synthetic experimental data
    exp_data = create_synthetic_experimental_data()
    validator.add_experimental_data("Synthetic_Data", exp_data)
    
    print("Added synthetic experimental data")
    
    # Run validation
    print("\nRunning dose response validation...")
    pmma_results = validator.validate_dose_response("PMMA_Positive", "Synthetic_Data")
    hsq_results = validator.validate_dose_response("HSQ_Negative", "Synthetic_Data")
    
    print(f"PMMA Model:")
    print(f"  RMSE: {pmma_results['rmse']:.4f}")
    print(f"  R²: {pmma_results['r_squared']:.4f}")
    print(f"  Contrast error: {pmma_results['contrast_error']:.4f}")
    
    print(f"HSQ Model:")
    print(f"  RMSE: {hsq_results['rmse']:.4f}")
    print(f"  R²: {hsq_results['r_squared']:.4f}")
    print(f"  Contrast error: {hsq_results['contrast_error']:.4f}")
    
    # Parameter optimization
    print("\nRunning parameter optimization...")
    opt_results = validator.parameter_optimization("PMMA_Positive", "Synthetic_Data")
    
    print(f"Parameter optimization results:")
    print(f"  Initial RMSE: {opt_results['initial_rmse']:.4f}")
    print(f"  Final RMSE: {opt_results['final_rmse']:.4f}")
    print(f"  Improvement: {((opt_results['initial_rmse'] - opt_results['final_rmse']) / opt_results['initial_rmse'] * 100):.1f}%")
    print(f"  Optimized parameters: {opt_results['optimized_parameters']}")
    
    # Create visualizations
    print("\nGenerating dose response plots...")
    validator.plot_dose_response_comparison("PMMA_Positive", "Synthetic_Data", 
                                          Path("pmma_dose_response.png"))
    validator.plot_dose_response_comparison("HSQ_Negative", "Synthetic_Data", 
                                          Path("hsq_dose_response.png"))
    
    # Export validation report
    print("\nExporting validation report...")
    validator.export_validation_report("resist_validation_report.html")
    
    print("\nResist model validation complete!")
    print("Check generated files: dose response plots and HTML report")

if __name__ == "__main__":
    main()