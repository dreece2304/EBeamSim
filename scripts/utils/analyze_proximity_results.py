#!/usr/bin/env python3
"""
analyze_proximity_results.py

Analyzes proximity effect simulation results from pattern scanning runs.
Extracts PSF parameters and compares corrected vs uncorrected patterns.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from pathlib import Path
import sys

def two_gaussian_psf(r, alpha, beta, sigma_f, sigma_b):
    """Two-Gaussian PSF model"""
    # Convert sigmas from nm to same units as r
    term1 = alpha / (2 * np.pi * sigma_f**2) * np.exp(-r**2 / (2 * sigma_f**2))
    term2 = beta / (2 * np.pi * sigma_b**2) * np.exp(-r**2 / (2 * sigma_b**2))
    return term1 + term2

def extract_psf_parameters(psf_file):
    """Extract PSF parameters from simulation data"""
    print(f"\nAnalyzing: {psf_file}")
    
    # Load PSF data
    df = pd.read_csv(psf_file, comment='#')
    
    # Get radius and energy density columns
    r = df.iloc[:, 0].values  # radius in nm
    energy_density = df.iloc[:, 2].values  # energy per area
    
    # Filter out zero values and normalize
    mask = energy_density > 0
    r = r[mask]
    energy_density = energy_density[mask]
    
    if len(r) < 10:
        print("Warning: Too few data points for fitting")
        return None
    
    # Normalize to peak value
    energy_density = energy_density / np.max(energy_density)
    
    # Initial parameter guesses
    # alpha = forward scatter amplitude (typically ~1)
    # beta = backscatter amplitude (typically 2-5)
    # sigma_f = forward scatter range in nm (typically 10-50 nm)
    # sigma_b = backscatter range in nm (typically 1000-10000 nm)
    p0 = [1.0, 3.0, 30.0, 5000.0]
    
    # Bounds for parameters
    bounds = ([0.1, 0.1, 5.0, 100.0],      # Lower bounds
              [10.0, 20.0, 200.0, 50000.0])  # Upper bounds
    
    try:
        # Fit the two-Gaussian model
        popt, pcov = curve_fit(two_gaussian_psf, r, energy_density, 
                              p0=p0, bounds=bounds, maxfev=5000)
        
        alpha, beta, sigma_f, sigma_b = popt
        
        # Calculate goodness of fit
        fit_values = two_gaussian_psf(r, *popt)
        residuals = energy_density - fit_values
        r_squared = 1 - (np.sum(residuals**2) / np.sum((energy_density - np.mean(energy_density))**2))
        
        print(f"Fitted PSF parameters:")
        print(f"  α (forward ratio): {alpha:.3f}")
        print(f"  β (backscatter ratio): {beta:.3f}")
        print(f"  σf (forward range): {sigma_f:.1f} nm")
        print(f"  σb (backscatter range): {sigma_b/1000:.1f} μm")
        print(f"  R² fit quality: {r_squared:.4f}")
        
        return {
            'alpha': alpha,
            'beta': beta,
            'sigma_f': sigma_f,
            'sigma_b': sigma_b,
            'r_squared': r_squared,
            'radius': r,
            'psf_data': energy_density,
            'fit_data': fit_values
        }
        
    except Exception as e:
        print(f"Error fitting PSF: {e}")
        return None

def plot_psf_comparison(results_dict, output_file='psf_comparison.png'):
    """Plot PSF data and fits for multiple results"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    
    for i, (name, result) in enumerate(results_dict.items()):
        if result is None:
            continue
            
        color = colors[i % len(colors)]
        
        # Linear scale plot
        ax1.semilogy(result['radius'], result['psf_data'], 'o', 
                    color=color, alpha=0.5, markersize=3, label=f'{name} (data)')
        ax1.semilogy(result['radius'], result['fit_data'], '-', 
                    color=color, linewidth=2, label=f'{name} (fit)')
        
        # Log-log scale plot
        ax2.loglog(result['radius'], result['psf_data'], 'o', 
                  color=color, alpha=0.5, markersize=3)
        ax2.loglog(result['radius'], result['fit_data'], '-', 
                  color=color, linewidth=2)
    
    # Format linear plot
    ax1.set_xlabel('Radius (nm)')
    ax1.set_ylabel('Normalized PSF')
    ax1.set_title('PSF Comparison - Linear Scale')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8)
    ax1.set_xlim(0, 1000)
    ax1.set_ylim(1e-6, 2)
    
    # Format log-log plot
    ax2.set_xlabel('Radius (nm)')
    ax2.set_ylabel('Normalized PSF')
    ax2.set_title('PSF Comparison - Log Scale')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(10, 50000)
    ax2.set_ylim(1e-6, 2)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")
    plt.close()

def calculate_proximity_metrics(result):
    """Calculate useful proximity effect metrics"""
    if result is None:
        return
    
    print("\nProximity Effect Metrics:")
    
    # Energy containment radii
    r = result['radius']
    psf = result['psf_data']
    
    # Calculate cumulative energy
    from scipy.integrate import cumtrapz
    cumulative = cumtrapz(psf * 2 * np.pi * r, r, initial=0)
    cumulative = cumulative / cumulative[-1]  # Normalize
    
    # Find containment radii
    for fraction in [0.5, 0.9, 0.95, 0.99]:
        idx = np.argmax(cumulative >= fraction)
        if idx > 0:
            print(f"  R({fraction*100:.0f}%): {r[idx]:.1f} nm ({r[idx]/1000:.2f} μm)")
    
    # Ratio of forward to backscatter
    eta = result['alpha'] / result['beta']
    print(f"\n  η (alpha/beta ratio): {eta:.3f}")
    
    # Effective range for proximity correction
    # This is where backscatter becomes dominant
    r_transition = result['sigma_f'] * np.sqrt(2 * np.log(result['alpha']/result['beta']))
    print(f"  Transition radius: {r_transition:.1f} nm")
    
    # Recommended minimum pattern spacing
    min_spacing = 3 * result['sigma_b'] / 1000  # Convert to μm
    print(f"  Recommended min spacing: {min_spacing:.1f} μm")

def main():
    # Default output directory
    output_dir = Path("cmake-build-release/bin/output")
    
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    
    print(f"Looking for PSF files in: {output_dir}")
    
    # Find PSF files
    psf_files = list(output_dir.glob("psf_pattern_*.csv"))
    
    if not psf_files:
        print("No PSF pattern files found!")
        print("Run the test_proximity_pattern.mac macro first.")
        return
    
    # Analyze each PSF file
    results = {}
    for psf_file in sorted(psf_files):
        name = psf_file.stem.replace("psf_pattern_", "")
        result = extract_psf_parameters(psf_file)
        if result:
            results[name] = result
            calculate_proximity_metrics(result)
    
    # Create comparison plot
    if results:
        plot_psf_comparison(results, output_dir / "psf_comparison.png")
        
        # Save parameters to file for GUI import
        params_file = output_dir / "psf_parameters.txt"
        with open(params_file, 'w') as f:
            f.write("# PSF Parameters extracted from simulation\n")
            f.write("# Use these values in the Pattern Visualization tab\n\n")
            
            for name, result in results.items():
                f.write(f"[{name}]\n")
                f.write(f"alpha = {result['alpha']:.3f}\n")
                f.write(f"beta = {result['beta']:.3f}\n")
                f.write(f"sigma_f = {result['sigma_f']:.1f} nm\n")
                f.write(f"sigma_b = {result['sigma_b']/1000:.1f} μm\n")
                f.write(f"r_squared = {result['r_squared']:.4f}\n\n")
        
        print(f"\nParameters saved to: {params_file}")
        print("\nYou can now:")
        print("1. Copy these parameters to the GUI's Pattern Visualization tab")
        print("2. Use 'Load PSF from Simulation' button to auto-import")
        print("3. Compare corrected vs uncorrected patterns")

if __name__ == "__main__":
    main()