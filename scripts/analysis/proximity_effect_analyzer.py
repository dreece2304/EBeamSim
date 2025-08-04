#!/usr/bin/env python3
"""
Proximity Effect Analysis Tool
Analyzes how resist thickness, dose, and pattern proximity affect exposure
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
from pathlib import Path
import subprocess
import json
from datetime import datetime
import os
import sys


class ProximityEffectAnalyzer:
    """Comprehensive analysis of proximity effects in e-beam lithography"""
    
    def __init__(self, ebl_executable, output_dir="proximity_analysis"):
        self.ebl_executable = Path(ebl_executable)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Standard parameters
        self.beam_energy = 100  # keV
        self.beam_current = 2.0  # nA
        
        # Resist parameters to study
        self.resist_thicknesses = [10, 20, 30, 50, 100, 200]  # nm
        self.doses = [100, 200, 300, 400, 500, 600]  # uC/cm^2
        
        # Pattern configurations
        self.pattern_configs = {
            'single_square': {
                'patterns': [{'type': 'square', 'size': 100, 'center': [0, 0]}],
                'field_size': 1000
            },
            'two_squares': {
                'patterns': [
                    {'type': 'square', 'size': 100, 'center': [-150, 0]},
                    {'type': 'square', 'size': 100, 'center': [150, 0]}
                ],
                'field_size': 1000
            },
            'line_array': {
                'patterns': [
                    {'type': 'line', 'size': 500, 'center': [0, -200]},
                    {'type': 'line', 'size': 500, 'center': [0, -100]},
                    {'type': 'line', 'size': 500, 'center': [0, 0]},
                    {'type': 'line', 'size': 500, 'center': [0, 100]},
                    {'type': 'line', 'size': 500, 'center': [0, 200]}
                ],
                'field_size': 1500
            },
            'dense_array': {
                'patterns': [],  # Will be generated
                'field_size': 2000
            }
        }
        
        # Generate dense array
        for i in range(-2, 3):
            for j in range(-2, 3):
                self.pattern_configs['dense_array']['patterns'].append({
                    'type': 'square',
                    'size': 100,
                    'center': [i * 200, j * 200]
                })
        
        # Resist response thresholds (example values)
        self.resist_thresholds = {
            'clearing_dose': 250,  # uC/cm^2 - dose to fully clear resist
            'crosslink_start': 50,  # uC/cm^2 - dose where crosslinking begins
            'crosslink_full': 150   # uC/cm^2 - dose for full crosslinking
        }
        
    def generate_macro(self, resist_thickness, dose, pattern_config, output_file):
        """Generate Geant4 macro for specific parameters"""
        macro_content = f"""# Proximity effect analysis macro
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Resist thickness: {resist_thickness} nm, Dose: {dose} uC/cm^2

/run/verbose 0
/event/verbose 0
/tracking/verbose 0

# Initialize
/run/initialize

# Material settings
/det/setResistThickness {resist_thickness} nm
/det/update

# Physics processes
/process/em/fluo 1
/process/em/auger 1

# Multiple pattern exposure
"""
        
        # Add each pattern
        for i, pattern in enumerate(pattern_config['patterns']):
            macro_content += f"""
# Pattern {i+1}
/pattern/enable true
/pattern/type {pattern['type']}
/pattern/size {pattern['size']} nm
/pattern/center {pattern['center'][0]} {pattern['center'][1]} 0 nm
/pattern/beamCurrent {self.beam_current} nA
/pattern/dose {dose}
/pattern/generate

# Run exposure for this pattern
/run/beamOn {self.calculate_events(pattern, dose)}
"""
        
        # Dose grid for entire field
        field_size = pattern_config['field_size']
        macro_content += f"""
# Initialize dose grid for analysis
/data/initDoseGrid 400 400 50 -{field_size/2} {field_size/2} -{field_size/2} {field_size/2} 0 {resist_thickness} nm
"""
        
        # Save macro
        with open(output_file, 'w') as f:
            f.write(macro_content)
            
        return output_file
        
    def calculate_events(self, pattern, dose):
        """Calculate number of events needed for pattern exposure"""
        # Simplified calculation - would need actual PatternGenerator logic
        if pattern['type'] == 'square':
            area = pattern['size'] ** 2  # nm^2
        elif pattern['type'] == 'line':
            area = pattern['size'] * 10  # Assume 10nm wide line
        else:
            area = 10000  # Default
            
        # Rough estimate of electrons needed
        shot_pitch = 4  # nm
        points = int(area / (shot_pitch ** 2))
        
        # From dose equation
        clock_freq = (self.beam_current * 1000 * 100) / (dose * shot_pitch ** 2)
        if clock_freq > 50:
            clock_freq = 50
            
        dwell_time = 1.0 / clock_freq  # microseconds
        electrons_per_point = int((self.beam_current * 1e-9 * dwell_time * 1e-6) / 1.602e-19)
        
        return points * electrons_per_point
        
    def run_simulation(self, params):
        """Run single simulation with given parameters"""
        thickness = params['thickness']
        dose = params['dose']
        pattern_name = params['pattern']
        
        # Create unique output name
        output_name = f"{pattern_name}_T{thickness}nm_D{dose}uC"
        macro_file = self.output_dir / f"{output_name}.mac"
        
        # Generate macro
        pattern_config = self.pattern_configs[pattern_name]
        self.generate_macro(thickness, dose, pattern_config, macro_file)
        
        # Run simulation
        print(f"Running: {output_name}")
        result = subprocess.run(
            [str(self.ebl_executable), str(macro_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error in {output_name}: {result.stderr}")
            return None
            
        # Return output file paths
        return {
            'name': output_name,
            'thickness': thickness,
            'dose': dose,
            'pattern': pattern_name,
            'dose_file': self.output_dir / f"pattern_dose_distribution_{output_name}.csv"
        }
        
    def analyze_edge_broadening(self, results):
        """Analyze edge broadening vs resist thickness"""
        broadening_data = []
        
        for result in results:
            if result and result['dose_file'].exists():
                # Load dose data
                df = pd.read_csv(result['dose_file'], comment='#')
                
                # Extract line profile through center
                center_y = 0
                tolerance = 5  # nm
                mask = (df['Y[nm]'].abs() < tolerance) & (df['Z[nm]'] < 5)
                profile = df[mask].sort_values('X[nm]')
                
                if len(profile) > 10:
                    # Find FWHM
                    max_dose = profile['Dose[uC/cm^2]'].max()
                    half_max = max_dose * 0.5
                    
                    above_half = profile[profile['Dose[uC/cm^2]'] > half_max]
                    if len(above_half) > 2:
                        fwhm = above_half['X[nm]'].max() - above_half['X[nm]'].min()
                        
                        # Calculate edge slope (10-90%)
                        dose_10 = max_dose * 0.1
                        dose_90 = max_dose * 0.9
                        edge_region = profile[
                            (profile['Dose[uC/cm^2]'] > dose_10) & 
                            (profile['Dose[uC/cm^2]'] < dose_90)
                        ]
                        if len(edge_region) > 2:
                            edge_width = edge_region['X[nm]'].max() - edge_region['X[nm]'].min()
                        else:
                            edge_width = np.nan
                            
                        broadening_data.append({
                            'thickness': result['thickness'],
                            'dose': result['dose'],
                            'pattern': result['pattern'],
                            'fwhm': fwhm,
                            'edge_width': edge_width,
                            'max_dose': max_dose
                        })
                        
        return pd.DataFrame(broadening_data)
        
    def analyze_proximity_dose(self, results):
        """Analyze dose in unexposed regions between patterns"""
        proximity_data = []
        
        for result in results:
            if result and result['dose_file'].exists():
                # Load dose data
                df = pd.read_csv(result['dose_file'], comment='#')
                
                # Sample dose at specific points between patterns
                if result['pattern'] == 'two_squares':
                    # Check dose at midpoint between squares
                    midpoint_mask = (
                        (df['X[nm]'].abs() < 10) & 
                        (df['Y[nm]'].abs() < 10) & 
                        (df['Z[nm]'] < 5)
                    )
                    midpoint_dose = df[midpoint_mask]['Dose[uC/cm^2]'].mean()
                    
                    proximity_data.append({
                        'thickness': result['thickness'],
                        'dose': result['dose'],
                        'pattern': result['pattern'],
                        'location': 'midpoint',
                        'proximity_dose': midpoint_dose,
                        'relative_dose': midpoint_dose / result['dose'] * 100
                    })
                    
                elif result['pattern'] == 'dense_array':
                    # Check dose at array center (unexposed region)
                    center_mask = (
                        (df['X[nm]'].abs() < 50) & 
                        (df['Y[nm]'].abs() < 50) & 
                        (df['Z[nm]'] < 5)
                    )
                    center_dose = df[center_mask]['Dose[uC/cm^2]'].mean()
                    
                    proximity_data.append({
                        'thickness': result['thickness'],
                        'dose': result['dose'],
                        'pattern': result['pattern'],
                        'location': 'array_center',
                        'proximity_dose': center_dose,
                        'relative_dose': center_dose / result['dose'] * 100
                    })
                    
        return pd.DataFrame(proximity_data)
        
    def plot_thickness_study(self, broadening_df):
        """Plot edge broadening vs resist thickness"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # FWHM vs thickness
        for dose in self.doses:
            data = broadening_df[broadening_df['dose'] == dose]
            if len(data) > 0:
                ax1.plot(data['thickness'], data['fwhm'], 'o-', label=f'{dose} uC/cm²')
                
        ax1.set_xlabel('Resist Thickness [nm]')
        ax1.set_ylabel('Pattern FWHM [nm]')
        ax1.set_title('Edge Broadening vs Resist Thickness')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Edge slope vs thickness
        for dose in self.doses:
            data = broadening_df[broadening_df['dose'] == dose]
            if len(data) > 0:
                ax2.plot(data['thickness'], data['edge_width'], 's-', label=f'{dose} uC/cm²')
                
        ax2.set_xlabel('Resist Thickness [nm]')
        ax2.set_ylabel('Edge Width (10-90%) [nm]')
        ax2.set_title('Edge Slope vs Resist Thickness')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
        
    def plot_proximity_analysis(self, proximity_df):
        """Plot proximity dose analysis"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Proximity dose vs thickness
        patterns = proximity_df['pattern'].unique()
        for pattern in patterns:
            data = proximity_df[proximity_df['pattern'] == pattern]
            if len(data) > 0:
                # Average over doses
                avg_data = data.groupby('thickness')['proximity_dose'].mean()
                ax1.plot(avg_data.index, avg_data.values, 'o-', label=pattern)
                
        # Add threshold lines
        ax1.axhline(y=self.resist_thresholds['crosslink_start'], 
                   color='yellow', linestyle='--', label='Crosslink start')
        ax1.axhline(y=self.resist_thresholds['crosslink_full'], 
                   color='orange', linestyle='--', label='Full crosslink')
        ax1.axhline(y=self.resist_thresholds['clearing_dose'], 
                   color='red', linestyle='--', label='Clearing dose')
                   
        ax1.set_xlabel('Resist Thickness [nm]')
        ax1.set_ylabel('Proximity Dose [uC/cm²]')
        ax1.set_title('Dose in Unexposed Regions')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Relative proximity dose
        for thickness in self.resist_thicknesses:
            data = proximity_df[proximity_df['thickness'] == thickness]
            if len(data) > 0:
                ax2.plot(data['dose'], data['relative_dose'], 'o-', 
                        label=f'{thickness} nm')
                
        ax2.set_xlabel('Nominal Dose [uC/cm²]')
        ax2.set_ylabel('Proximity Dose [% of nominal]')
        ax2.set_title('Relative Proximity Effect')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
        
    def create_dose_map_comparison(self, results, dose=300):
        """Create visual comparison of dose maps for different thicknesses"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        thickness_results = [r for r in results if r and r['dose'] == dose]
        thickness_results.sort(key=lambda x: x['thickness'])
        
        for i, result in enumerate(thickness_results[:6]):
            if result['dose_file'].exists():
                # Load and create 2D projection
                df = pd.read_csv(result['dose_file'], comment='#')
                
                # Create grid
                x_unique = np.sort(df['X[nm]'].unique())
                y_unique = np.sort(df['Y[nm]'].unique())
                
                # Subsample if too dense
                if len(x_unique) > 100:
                    x_unique = x_unique[::len(x_unique)//100]
                if len(y_unique) > 100:
                    y_unique = y_unique[::len(y_unique)//100]
                    
                X, Y = np.meshgrid(x_unique, y_unique)
                dose_grid = np.zeros_like(X)
                
                # Fill grid (simplified - would need proper interpolation)
                for xi, x in enumerate(x_unique):
                    for yi, y in enumerate(y_unique):
                        mask = (
                            (df['X[nm]'] >= x - 10) & (df['X[nm]'] < x + 10) &
                            (df['Y[nm]'] >= y - 10) & (df['Y[nm]'] < y + 10)
                        )
                        if mask.any():
                            dose_grid[yi, xi] = df[mask]['Dose[uC/cm^2]'].mean()
                            
                # Plot with log scale to show backscattering
                im = axes[i].pcolormesh(X, Y, dose_grid + 1e-3, 
                                       norm=plt.matplotlib.colors.LogNorm(vmin=1, vmax=dose),
                                       cmap='viridis')
                
                # Add contours at key thresholds
                if dose_grid.max() > 0:
                    axes[i].contour(X, Y, dose_grid, 
                                   levels=[self.resist_thresholds['crosslink_start'],
                                          self.resist_thresholds['crosslink_full'],
                                          self.resist_thresholds['clearing_dose']],
                                   colors=['yellow', 'orange', 'red'],
                                   linewidths=1)
                    
                axes[i].set_title(f'Thickness: {result["thickness"]} nm')
                axes[i].set_xlabel('X [nm]')
                axes[i].set_ylabel('Y [nm]')
                axes[i].set_aspect('equal')
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=axes[i])
                cbar.set_label('Dose [uC/cm²]')
                
        plt.suptitle(f'Dose Distribution Comparison at {dose} uC/cm² Nominal Dose')
        plt.tight_layout()
        return fig
        
    def run_complete_analysis(self):
        """Run complete proximity effect analysis"""
        print("Starting proximity effect analysis...")
        
        all_results = []
        
        # Run simulations for different parameters
        for thickness in self.resist_thicknesses:
            for dose in self.doses:
                for pattern_name in self.pattern_configs.keys():
                    params = {
                        'thickness': thickness,
                        'dose': dose,
                        'pattern': pattern_name
                    }
                    result = self.run_simulation(params)
                    if result:
                        all_results.append(result)
                        
        # Analyze results
        print("\nAnalyzing edge broadening...")
        broadening_df = self.analyze_edge_broadening(all_results)
        
        print("Analyzing proximity doses...")
        proximity_df = self.analyze_proximity_dose(all_results)
        
        # Save analysis results
        broadening_df.to_csv(self.output_dir / 'edge_broadening_analysis.csv', index=False)
        proximity_df.to_csv(self.output_dir / 'proximity_dose_analysis.csv', index=False)
        
        # Create plots
        print("\nGenerating plots...")
        
        # Thickness study
        fig1 = self.plot_thickness_study(broadening_df)
        fig1.savefig(self.output_dir / 'thickness_study.png', dpi=150)
        
        # Proximity analysis
        fig2 = self.plot_proximity_analysis(proximity_df)
        fig2.savefig(self.output_dir / 'proximity_analysis.png', dpi=150)
        
        # Dose map comparison
        fig3 = self.create_dose_map_comparison(all_results)
        fig3.savefig(self.output_dir / 'dose_map_comparison.png', dpi=150)
        
        print(f"\nAnalysis complete! Results saved to {self.output_dir}")
        
        # Generate summary report
        self.generate_report(broadening_df, proximity_df)
        
        return broadening_df, proximity_df
        
    def generate_report(self, broadening_df, proximity_df):
        """Generate analysis report"""
        report_path = self.output_dir / 'proximity_analysis_report.txt'
        
        with open(report_path, 'w') as f:
            f.write("PROXIMITY EFFECT ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("PARAMETERS STUDIED:\n")
            f.write(f"- Resist thicknesses: {self.resist_thicknesses} nm\n")
            f.write(f"- Doses: {self.doses} uC/cm²\n")
            f.write(f"- Beam energy: {self.beam_energy} keV\n")
            f.write(f"- Beam current: {self.beam_current} nA\n\n")
            
            f.write("KEY FINDINGS:\n\n")
            
            # Edge broadening trends
            f.write("1. Edge Broadening vs Thickness:\n")
            for dose in self.doses:
                data = broadening_df[broadening_df['dose'] == dose]
                if len(data) > 1:
                    # Linear fit to FWHM vs thickness
                    coeff = np.polyfit(data['thickness'], data['fwhm'], 1)
                    f.write(f"   - At {dose} uC/cm²: FWHM increases ~{coeff[0]:.2f} nm per nm of resist\n")
                    
            f.write("\n2. Proximity Dose in Unexposed Regions:\n")
            
            # Find critical conditions
            critical_conditions = []
            for _, row in proximity_df.iterrows():
                if row['proximity_dose'] > self.resist_thresholds['crosslink_start']:
                    critical_conditions.append(row)
                    
            if critical_conditions:
                f.write("   WARNING: Crosslinking threshold exceeded in:\n")
                for cond in critical_conditions[:5]:  # Show first 5
                    f.write(f"   - {cond['pattern']} at {cond['thickness']}nm, "
                           f"{cond['dose']} uC/cm²: {cond['proximity_dose']:.1f} uC/cm²\n")
                           
            # Recommendations
            f.write("\nRECOMMENDATIONS:\n")
            
            # Find optimal thickness
            min_broadening = broadening_df.groupby('thickness')['fwhm'].mean()
            optimal_thickness = min_broadening.idxmin()
            f.write(f"1. Optimal resist thickness for minimum broadening: {optimal_thickness} nm\n")
            
            # Safe dose range
            safe_doses = []
            for dose in self.doses:
                data = proximity_df[proximity_df['dose'] == dose]
                if data['proximity_dose'].max() < self.resist_thresholds['crosslink_start']:
                    safe_doses.append(dose)
                    
            if safe_doses:
                f.write(f"2. Safe dose range to avoid crosslinking: {min(safe_doses)}-{max(safe_doses)} uC/cm²\n")
            else:
                f.write("2. WARNING: All tested doses show risk of crosslinking in dense patterns\n")
                
        print(f"Report saved to: {report_path}")


def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python proximity_effect_analyzer.py <ebl_executable>")
        print("\nExample:")
        print("  python proximity_effect_analyzer.py /path/to/ebl_sim")
        sys.exit(1)
        
    ebl_executable = sys.argv[1]
    
    # Create analyzer
    analyzer = ProximityEffectAnalyzer(ebl_executable)
    
    # Run analysis
    analyzer.run_complete_analysis()
    
    # Show plots
    plt.show()


if __name__ == "__main__":
    main()