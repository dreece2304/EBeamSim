#!/usr/bin/env python3
"""
Enhanced PSF Visualization Generator for PhD Defense

Improvements over base version:
- Viridis color scheme throughout
- Dual-view: forward scattering detail + full backscatter range
- Log-log plots for power-law analysis
- Stopping power vs backscatter trade-off analysis
- Fixed 2D heatmaps with proper scaling
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend for saving figures
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re

# Use viridis-based colormaps
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 150

# Output directory
OUTPUT_DIR = Path(__file__).parent / "psf_analysis_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# PSF data directory
PSF_BASE = Path(__file__).parent / "psf_output" / "metalcones_corrected"

# Material properties with stopping power estimates
MATERIALS = {
    'Alucone_EG': {
        'name': 'Alucone (EG)', 'metal': 'Al', 'linker': 'EG',
        'formula': 'Al₂C₆H₁₂O₆', 'Z': 13, 'metal_fraction': 0.23,
        'density': 1.5, 'color': '#440154',  # viridis dark purple
        'stopping_power_rel': 1.15  # relative to pure carbon
    },
    'Zincone_EG': {
        'name': 'Zincone (EG)', 'metal': 'Zn', 'linker': 'EG',
        'formula': 'ZnC₂H₄O₂', 'Z': 30, 'metal_fraction': 0.52,
        'density': 2.0, 'color': '#31688e',  # viridis blue
        'stopping_power_rel': 1.45
    },
    'Tincone_EG': {
        'name': 'Tincone (EG)', 'metal': 'Sn', 'linker': 'EG',
        'formula': 'SnC₄H₈O₄', 'Z': 50, 'metal_fraction': 0.50,
        'density': 2.5, 'color': '#35b779',  # viridis green
        'stopping_power_rel': 1.55
    },
    'Alucone_BD': {
        'name': 'Alucone (BD)', 'metal': 'Al', 'linker': 'BD',
        'formula': 'Al₂C₁₂H₁₂O₆', 'Z': 13, 'metal_fraction': 0.176,
        'density': 1.4, 'color': '#443983',  # viridis purple
        'stopping_power_rel': 1.10,
        'linestyle': '--'
    },
    'Zincone_BD': {
        'name': 'Zincone (BD)', 'metal': 'Zn', 'linker': 'BD',
        'formula': 'ZnC₄H₄O₂', 'Z': 30, 'metal_fraction': 0.437,
        'density': 1.9, 'color': '#21918c',  # viridis teal
        'stopping_power_rel': 1.35,
        'linestyle': '--'
    },
    'Tincone_BD': {
        'name': 'Tincone (BD)', 'metal': 'Sn', 'linker': 'BD',
        'formula': 'SnC₈H₈O₄', 'Z': 50, 'metal_fraction': 0.414,
        'density': 2.4, 'color': '#90d743',  # viridis yellow-green
        'stopping_power_rel': 1.42,
        'linestyle': '--'
    }
}

# Viridis-based color palette for consistent styling
VIRIDIS_COLORS = plt.cm.viridis(np.linspace(0.1, 0.9, 6))


@dataclass
class PSFData:
    """Container for PSF data from a single material."""
    name: str
    radii: np.ndarray  # nm
    psf_values: np.ndarray  # normalized intensity
    psf_2d: Optional[np.ndarray] = None
    r_bins: Optional[np.ndarray] = None
    z_bins: Optional[np.ndarray] = None
    summary: Dict = field(default_factory=dict)


def load_psf_data(mat_key: str) -> Optional[PSFData]:
    """Load PSF data for a material."""
    mat_info = MATERIALS[mat_key]
    linker = mat_info['linker']
    mat_name = mat_key.split('_')[0]

    # Construct path - files are directly in EG/BD folders
    psf_dir = PSF_BASE / linker
    base_name = f"{mat_name}_{linker}_100keV"

    if not psf_dir.exists():
        print(f"  Warning: Directory not found: {psf_dir}")
        return None

    # Load radial PSF - file is psf_Materialname_Linker_100keV.csv
    radial_file = psf_dir / f"psf_{mat_name}_{linker}_100keV.csv"
    if not radial_file.exists():
        # Try alternate patterns
        radial_files = list(psf_dir.glob(f"psf_{mat_name}*.csv"))
        radial_files = [f for f in radial_files if '2d' not in f.name.lower()]
        if radial_files:
            radial_file = radial_files[0]
        else:
            print(f"  Warning: No PSF CSV found for {mat_name} in {psf_dir}")
            return None

    try:
        df = pd.read_csv(radial_file)
        # Handle different column naming conventions
        if 'Radius_nm' in df.columns:
            radii = df['Radius_nm'].values
            psf_values = df['PSF_normalized'].values
        elif 'Radius(nm)' in df.columns:
            radii = df['Radius(nm)'].values
            # Normalize energy deposition to get PSF
            energy_dep = df['EnergyDeposition(eV/nm^2)'].values
            # Normalize so max = 1
            psf_values = energy_dep / energy_dep.max() if energy_dep.max() > 0 else energy_dep
        else:
            print(f"  Warning: Unknown column format in {radial_file}")
            return None

        # Load summary if available
        summary = {}
        # Try different naming conventions
        summary_candidates = [
            psf_dir / f"summary_{mat_name}_{linker}_100keV.txt",
            psf_dir / f"psf_{mat_name}_{linker}_100keV_summary.txt",
        ]
        summary_file = None
        for candidate in summary_candidates:
            if candidate.exists():
                summary_file = candidate
                break

        if not summary_file:
            summary_files = list(psf_dir.glob(f"*{mat_name}*summary*.txt"))
            if summary_files:
                summary_file = summary_files[0]

        if summary_file and summary_file.exists():
            summary = parse_summary_file(summary_file)

        # Load 2D data if available
        psf_2d, r_bins, z_bins = None, None, None
        heatmap_file = psf_dir / f"psf2d_{mat_name}_{linker}_100keV.csv"
        if not heatmap_file.exists():
            heatmap_files = list(psf_dir.glob(f"psf2d_{mat_name}*.csv"))
            if heatmap_files:
                heatmap_file = heatmap_files[0]

        if heatmap_file.exists():
            try:
                df_2d = pd.read_csv(heatmap_file)
                if 'R_nm' in df_2d.columns and 'Z_nm' in df_2d.columns:
                    r_bins = df_2d['R_nm'].unique()
                    z_bins = df_2d['Z_nm'].unique()
                    psf_2d = df_2d.pivot(index='Z_nm', columns='R_nm', values='Energy_keV').values
            except Exception as e:
                print(f"  Warning: Could not load 2D data: {e}")

        return PSFData(
            name=mat_info['name'],
            radii=radii,
            psf_values=psf_values,
            psf_2d=psf_2d,
            r_bins=r_bins,
            z_bins=z_bins,
            summary=summary
        )

    except Exception as e:
        print(f"  Error loading {mat_key}: {e}")
        return None


def parse_summary_file(filepath: Path) -> Dict:
    """Parse summary file for key metrics."""
    summary = {}
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        patterns = {
            'total_events': r'Events:\s*(\d+)',
            'energy_in_resist': r'Resist fraction:\s*([\d.]+)%',
            'fwhm': r'FWHM:\s*([\d.]+)\s*nm',
            'alpha': r'Alpha:\s*([\d.]+)',
            'beta': r'Beta:\s*([\d.]+)',
            'eta': r'Eta:\s*([\d.]+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                summary[key] = float(match.group(1))

    except Exception as e:
        print(f"  Warning: Could not parse summary: {e}")

    return summary


def create_dual_view_psf(data: Dict[str, PSFData], save_path: Path):
    """Create dual-view PSF: forward scattering detail + full range.

    Log x-axis (radial distance), linear y-axis (energy deposition).
    Radial distance = lateral spread from beam center.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Use viridis colors
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(data)))

    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        ls = mat_info.get('linestyle', '-')
        color = colors[idx]
        label = mat_info['name']

        # Filter valid data (r > 0 for log scale on x)
        mask = psf_data.radii > 0

        # Left: Forward scattering detail (1-500 nm) - LOG x, LINEAR y
        mask_forward = (psf_data.radii > 0) & (psf_data.radii <= 500)
        axes[0].semilogx(psf_data.radii[mask_forward], psf_data.psf_values[mask_forward],
                        color=color, linestyle=ls, linewidth=2, label=label)

        # Right: Full range - LOG x, LINEAR y
        axes[1].semilogx(psf_data.radii[mask], psf_data.psf_values[mask],
                        color=color, linestyle=ls, linewidth=2, label=label)

    # Left plot formatting - forward scattering detail
    axes[0].set_xlabel('Lateral Distance from Beam (nm)')
    axes[0].set_ylabel('Energy Deposition (normalized)')
    axes[0].set_title('Forward Scattering Detail\n(Determines Resolution)')
    axes[0].set_xlim(0.1, 500)
    axes[0].set_ylim(0, None)
    axes[0].legend(loc='upper right', framealpha=0.9)
    axes[0].grid(True, which='both', alpha=0.3)

    # Right plot formatting - full range
    axes[1].set_xlabel('Lateral Distance from Beam (nm)')
    axes[1].set_ylabel('Energy Deposition (normalized)')
    axes[1].set_title('Full PSF Range\n(Shows Proximity Effect Tail)')
    axes[1].set_xlim(0.1, 15000)
    axes[1].set_ylim(0, None)
    axes[1].legend(loc='upper right', framealpha=0.9)
    axes[1].axvline(x=1000, color='red', linestyle=':', alpha=0.5)
    axes[1].text(2000, axes[1].get_ylim()[1]*0.8, 'Backscatter\ntail begins',
                fontsize=9, color='darkred', ha='left')
    axes[1].grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_stopping_power_analysis(data: Dict[str, PSFData], save_path: Path):
    """Create stopping power vs backscatter trade-off analysis."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Collect data points
    metals = []
    linkers = []
    stopping_powers = []
    energies = []
    metal_fractions = []
    z_values = []

    for mat_key, psf_data in data.items():
        mat_info = MATERIALS[mat_key]
        energy = psf_data.summary.get('energy_in_resist')
        if energy:
            metals.append(mat_info['metal'])
            linkers.append(mat_info['linker'])
            stopping_powers.append(mat_info['stopping_power_rel'])
            energies.append(energy)
            metal_fractions.append(mat_info['metal_fraction'] * 100)
            z_values.append(mat_info['Z'])

    # Convert to arrays
    stopping_powers = np.array(stopping_powers)
    energies = np.array(energies)
    metal_fractions = np.array(metal_fractions)
    z_values = np.array(z_values)

    # Color by metal type
    metal_colors = {'Al': '#440154', 'Zn': '#21918c', 'Sn': '#fde725'}
    colors = [metal_colors[m] for m in metals]
    markers = ['o' if l == 'EG' else 's' for l in linkers]

    # Plot 1: Stopping Power vs Energy in Resist
    ax1 = axes[0]
    for i in range(len(metals)):
        ax1.scatter(stopping_powers[i], energies[i], c=colors[i],
                   marker=markers[i], s=150, edgecolors='black', linewidth=1.5,
                   label=f"{metals[i]} ({linkers[i]})")

    # Add trend line
    z = np.polyfit(stopping_powers, energies, 1)
    p = np.poly1d(z)
    x_line = np.linspace(min(stopping_powers)-0.05, max(stopping_powers)+0.05, 100)
    ax1.plot(x_line, p(x_line), 'k--', alpha=0.5, linewidth=1)

    ax1.set_xlabel('Relative Stopping Power')
    ax1.set_ylabel('Energy in Resist (%)')
    ax1.set_title('Stopping Power vs Backscatter\n(The Trade-off)')
    ax1.legend(loc='upper left', fontsize=9)

    # Add annotation explaining the trend
    ax1.annotate('Lower stopping power\n→ deeper penetration\n→ MORE backscatter',
                xy=(1.12, 134), fontsize=9, ha='left',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    # Plot 2: Metal Fraction vs Energy (showing the paradox)
    ax2 = axes[1]
    for i in range(len(metals)):
        ax2.scatter(metal_fractions[i], energies[i], c=colors[i],
                   marker=markers[i], s=150, edgecolors='black', linewidth=1.5)

    # Connect EG-BD pairs with arrows
    for metal in ['Al', 'Zn', 'Sn']:
        eg_idx = [i for i, (m, l) in enumerate(zip(metals, linkers)) if m == metal and l == 'EG']
        bd_idx = [i for i, (m, l) in enumerate(zip(metals, linkers)) if m == metal and l == 'BD']
        if eg_idx and bd_idx:
            ax2.annotate('', xy=(metal_fractions[bd_idx[0]], energies[bd_idx[0]]),
                        xytext=(metal_fractions[eg_idx[0]], energies[eg_idx[0]]),
                        arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))

    ax2.set_xlabel('Metal Mass Fraction (%)')
    ax2.set_ylabel('Energy in Resist (%)')
    ax2.set_title('Metal Fraction vs Backscatter\n(The Paradox)')

    # Add paradox annotation
    ax2.annotate('Arrows show EG→BD\n(less metal, MORE backscatter\nfor Zn and Sn)',
                xy=(45, 128), fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.3))

    # Plot 3: Physical explanation diagram
    ax3 = axes[2]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.set_aspect('equal')
    ax3.axis('off')
    ax3.set_title('Physical Mechanism', fontsize=13, fontweight='bold')

    # Draw resist layers
    # High stopping power (left)
    rect1 = plt.Rectangle((0.5, 6), 4, 1.5, facecolor='#21918c', alpha=0.7, edgecolor='black')
    ax3.add_patch(rect1)
    ax3.text(2.5, 6.75, 'High Metal\n(High S.P.)', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    # Substrate
    rect1b = plt.Rectangle((0.5, 4), 4, 2, facecolor='gray', alpha=0.5, edgecolor='black')
    ax3.add_patch(rect1b)
    ax3.text(2.5, 5, 'Si Substrate', ha='center', va='center', fontsize=9)

    # Electron paths - high stopping power (stops in resist)
    ax3.annotate('', xy=(2.5, 6), xytext=(2.5, 8.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax3.plot([2.3, 2.7], [6.2, 6.2], 'r*', markersize=10)  # Energy deposition
    ax3.text(2.5, 8.7, 'e⁻', fontsize=11, ha='center')
    ax3.text(1, 6.2, 'Stops\nearly', fontsize=8, color='red')

    # Low stopping power (right)
    rect2 = plt.Rectangle((5.5, 6), 4, 1.5, facecolor='#90d743', alpha=0.7, edgecolor='black')
    ax3.add_patch(rect2)
    ax3.text(7.5, 6.75, 'Low Metal\n(Low S.P.)', ha='center', va='center', fontsize=9, fontweight='bold')

    # Substrate
    rect2b = plt.Rectangle((5.5, 4), 4, 2, facecolor='gray', alpha=0.5, edgecolor='black')
    ax3.add_patch(rect2b)
    ax3.text(7.5, 5, 'Si Substrate', ha='center', va='center', fontsize=9)

    # Electron paths - low stopping power (penetrates, backscatters)
    ax3.annotate('', xy=(7.5, 4.5), xytext=(7.5, 8.5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax3.annotate('', xy=(8.2, 7.8), xytext=(7.7, 4.8),
                arrowprops=dict(arrowstyle='->', color='orange', lw=2,
                               connectionstyle='arc3,rad=0.3'))
    ax3.text(7.5, 8.7, 'e⁻', fontsize=11, ha='center')
    ax3.text(9, 6.5, 'Backscatter\ndeposits\nenergy', fontsize=8, color='orange')
    ax3.plot([7.8, 8.0, 8.2], [6.8, 7.2, 6.5], 'o', color='orange', markersize=6)

    # Labels
    ax3.text(2.5, 3.5, 'Less backscatter', fontsize=10, ha='center', color='#21918c', fontweight='bold')
    ax3.text(7.5, 3.5, 'More backscatter', fontsize=10, ha='center', color='#90d743', fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_log_log_analysis(data: Dict[str, PSFData], save_path: Path):
    """Create log-log PSF plot for power-law analysis."""
    fig, ax = plt.subplots(figsize=(10, 8))

    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(data)))

    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        ls = mat_info.get('linestyle', '-')
        color = colors[idx]

        # Filter valid data
        mask = (psf_data.radii > 0) & (psf_data.psf_values > 0)
        r = psf_data.radii[mask]
        psf = psf_data.psf_values[mask]

        ax.loglog(r, psf, color=color, linestyle=ls, linewidth=2,
                 label=mat_info['name'])

    # Add reference slopes
    r_ref = np.logspace(2, 4, 100)
    ax.loglog(r_ref, 1e-1 * (r_ref/100)**(-2), 'k:', alpha=0.5, linewidth=1.5, label='r⁻² (Gaussian tail)')
    ax.loglog(r_ref, 5e-2 * (r_ref/100)**(-3), 'k--', alpha=0.5, linewidth=1.5, label='r⁻³ (screened)')

    # Mark regions
    ax.axvline(x=100, color='gray', linestyle=':', alpha=0.7)
    ax.axvline(x=1000, color='red', linestyle=':', alpha=0.7)
    ax.axvspan(0, 100, alpha=0.05, color='yellow')
    ax.axvspan(1000, 20000, alpha=0.05, color='red')

    ax.text(30, 1e-1, 'Resist\nLayer', fontsize=10, ha='center', color='olive')
    ax.text(5000, 1e-1, 'Proximity\nEffect\nZone', fontsize=10, ha='center', color='darkred')

    ax.set_xlabel('Radial Distance (nm)', fontsize=12)
    ax.set_ylabel('Normalized PSF (a.u.)', fontsize=12)
    ax.set_title('Log-Log PSF Analysis\nPower-Law Behavior of Scattering Tails', fontsize=14)
    ax.legend(loc='lower left', fontsize=10, ncol=2)
    ax.set_xlim(0.1, 20000)
    ax.set_ylim(1e-7, 2)
    ax.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_presentation_summary(data: Dict[str, PSFData], save_path: Path):
    """Create a single summary figure suitable for presentation slides."""
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(data)))

    # Panel A: Forward scattering (resolution zone) - LOG x, LINEAR y
    ax1 = fig.add_subplot(gs[0, 0])
    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        ls = mat_info.get('linestyle', '-')
        mask = (psf_data.radii > 0) & (psf_data.radii <= 500)
        ax1.semilogx(psf_data.radii[mask], psf_data.psf_values[mask],
                    color=colors[idx], linestyle=ls, linewidth=2)
    ax1.set_xlabel('Lateral Distance (nm)')
    ax1.set_ylabel('Energy Deposition')
    ax1.set_title('A) Forward Scattering\n(Resolution Zone)', fontweight='bold')
    ax1.set_xlim(0.1, 500)
    ax1.set_ylim(0, None)
    ax1.grid(True, which='both', alpha=0.3)

    # Panel B: Full PSF - LOG x, LINEAR y
    ax2 = fig.add_subplot(gs[0, 1])
    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        ls = mat_info.get('linestyle', '-')
        mask = psf_data.radii > 0
        ax2.semilogx(psf_data.radii[mask], psf_data.psf_values[mask],
                    color=colors[idx], linestyle=ls, linewidth=2,
                    label=mat_info['name'])
    ax2.set_xlabel('Lateral Distance (nm)')
    ax2.set_ylabel('Energy Deposition')
    ax2.set_title('B) Full PSF Range', fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8, ncol=2)
    ax2.set_xlim(0.1, 15000)
    ax2.set_ylim(0, None)
    ax2.grid(True, which='both', alpha=0.3)

    # Panel C: Energy deposition bar chart
    ax3 = fig.add_subplot(gs[0, 2])
    mat_names = []
    energies = []
    bar_colors = []
    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        energy = psf_data.summary.get('energy_in_resist')
        if energy:
            mat_names.append(mat_info['name'].replace(' ', '\n'))
            energies.append(energy)
            bar_colors.append(colors[idx])

    bars = ax3.bar(mat_names, energies, color=bar_colors, edgecolor='black')
    ax3.axhline(y=100, color='red', linestyle='--', linewidth=1.5, label='100% (no backscatter)')
    ax3.set_ylabel('Energy in Resist (%)')
    ax3.set_title('C) Backscatter Contribution\n(>100% = backscatter)', fontweight='bold')
    ax3.set_ylim(125, 140)

    # Add value labels on bars
    for bar, val in zip(bars, energies):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

    # Panel D: Metal Z vs Energy
    ax4 = fig.add_subplot(gs[1, 0])
    z_vals = []
    e_vals = []
    c_vals = []
    m_vals = []
    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        energy = psf_data.summary.get('energy_in_resist')
        if energy:
            z_vals.append(mat_info['Z'])
            e_vals.append(energy)
            c_vals.append(colors[idx])
            m_vals.append('o' if mat_info['linker'] == 'EG' else 's')

    for z, e, c, m in zip(z_vals, e_vals, c_vals, m_vals):
        ax4.scatter(z, e, c=[c], marker=m, s=150, edgecolors='black', linewidth=1.5)

    ax4.set_xlabel('Metal Atomic Number (Z)')
    ax4.set_ylabel('Energy in Resist (%)')
    ax4.set_title('D) Atomic Number Effect\n(○ EG, □ BD)', fontweight='bold')

    # Panel E: Stopping power explanation
    ax5 = fig.add_subplot(gs[1, 1])
    mf_vals = []
    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        energy = psf_data.summary.get('energy_in_resist')
        if energy:
            mf_vals.append(mat_info['metal_fraction'] * 100)

    for mf, e, c, m in zip(mf_vals, e_vals, c_vals, m_vals):
        ax5.scatter(mf, e, c=[c], marker=m, s=150, edgecolors='black', linewidth=1.5)

    ax5.set_xlabel('Metal Mass Fraction (%)')
    ax5.set_ylabel('Energy in Resist (%)')
    ax5.set_title('E) The Stopping Power Paradox\n(Lower metal → MORE backscatter)', fontweight='bold')

    # Add connecting arrows for BD paradox
    ax5.annotate('BD variants have\nless metal but\nmore backscatter!',
                xy=(42, 134), fontsize=9, ha='center',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    # Panel F: Key findings text
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    findings_text = """
Key Findings:

1. Tincone shows highest backscatter
   (133-135%) due to high-Z tin

2. BD linker paradox: Lower metal
   content → MORE backscatter
   (for Zn and Sn)

3. Physics: Lower stopping power
   allows deeper penetration →
   more substrate backscatter

4. Design implication: Optimal
   resist balances sensitivity
   vs. proximity effect
"""
    ax6.text(0.1, 0.9, findings_text, transform=ax6.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    ax6.set_title('F) Summary', fontweight='bold')

    plt.suptitle('PSF Analysis: Metalcone Resists at 100 keV\n100 nm resist on Si substrate',
                fontsize=14, fontweight='bold', y=0.98)

    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_viridis_overlay(data: Dict[str, PSFData], save_path: Path):
    """Create clean viridis-colored PSF overlay. Log x-axis, linear y-axis."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Use viridis colormap
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(data)))

    for idx, (mat_key, psf_data) in enumerate(data.items()):
        mat_info = MATERIALS[mat_key]
        ls = mat_info.get('linestyle', '-')
        lw = 2.5 if mat_info['linker'] == 'EG' else 2

        # Filter valid data for log scale on x
        mask = psf_data.radii > 0
        ax.semilogx(psf_data.radii[mask], psf_data.psf_values[mask],
                   color=colors[idx], linestyle=ls, linewidth=lw,
                   label=mat_info['name'])

    ax.set_xlabel('Lateral Distance from Beam Center (nm)', fontsize=13)
    ax.set_ylabel('Energy Deposition (normalized)', fontsize=13)
    ax.set_title('Point Spread Functions: Metalcone Resists at 100 keV\n(Solid = EG linker, Dashed = BD linker)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
    ax.set_xlim(0.1, 15000)
    ax.set_ylim(0, None)
    ax.grid(True, which='both', alpha=0.3)

    # Add region annotations
    ax.axvline(x=1000, color='red', linestyle=':', alpha=0.5)
    ax.text(1500, ax.get_ylim()[1]*0.7, 'Backscatter tail\n(Proximity effect)',
           fontsize=10, ha='left', color='darkred')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_metal_comparison_viridis(data: Dict[str, PSFData], save_path: Path):
    """Create metal series comparison. Log x-axis, linear y-axis."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    metals = ['Al', 'Zn', 'Sn']
    metal_colors = {
        'Al': ('#440154', '#7e4e90'),  # dark/light purple
        'Zn': ('#21918c', '#5ec962'),  # teal/green
        'Sn': ('#fde725', '#b5de2b')   # yellow/lime
    }

    for ax, metal in zip(axes, metals):
        for mat_key, psf_data in data.items():
            mat_info = MATERIALS[mat_key]
            if mat_info['metal'] != metal:
                continue

            color = metal_colors[metal][0 if mat_info['linker'] == 'EG' else 1]
            ls = '-' if mat_info['linker'] == 'EG' else '--'

            # Filter valid data for log scale on x
            mask = psf_data.radii > 0
            ax.semilogx(psf_data.radii[mask], psf_data.psf_values[mask],
                       color=color, linestyle=ls, linewidth=2.5,
                       label=f"{mat_info['linker']} ({mat_info['metal_fraction']*100:.0f}% {metal})")

        ax.set_xlabel('Lateral Distance (nm)')
        ax.set_ylabel('Energy Deposition (norm.)')
        # Get Z value for this metal
        metal_to_material = {'Al': 'Alucone_EG', 'Zn': 'Zincone_EG', 'Sn': 'Tincone_EG'}
        z_val = MATERIALS[metal_to_material[metal]]['Z']
        ax.set_title(f'{metal}-based Metalcones\n(Z = {z_val})',
                    fontweight='bold')
        ax.legend(loc='upper right')
        ax.set_xlim(0.1, 15000)
        ax.set_ylim(0, None)
        ax.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def generate_all_enhanced():
    """Generate all enhanced visualizations."""
    print("=" * 60)
    print("Enhanced PSF Visualization Generator")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}\n")

    # Load data
    print("--- Loading PSF Data ---")
    data = {}
    for mat_key in MATERIALS.keys():
        psf_data = load_psf_data(mat_key)
        if psf_data:
            data[mat_key] = psf_data
            print(f"✓ Loaded {mat_key}: {len(psf_data.radii)} points")

    if not data:
        print("ERROR: No PSF data found!")
        return

    print(f"\nLoaded {len(data)} materials\n")
    print("--- Generating Enhanced Visualizations ---\n")

    # Generate all figures
    print("1. Dual-view PSF (forward + full range)...")
    create_dual_view_psf(data, OUTPUT_DIR / "psf_dual_view.png")

    print("2. Stopping power vs backscatter analysis...")
    create_stopping_power_analysis(data, OUTPUT_DIR / "stopping_power_analysis.png")

    print("3. Log-log power-law analysis...")
    create_log_log_analysis(data, OUTPUT_DIR / "psf_log_log.png")

    print("4. Presentation summary figure...")
    create_presentation_summary(data, OUTPUT_DIR / "presentation_summary.png")

    print("5. Viridis PSF overlay...")
    create_viridis_overlay(data, OUTPUT_DIR / "psf_viridis_overlay.png")

    print("6. Metal series comparison...")
    create_metal_comparison_viridis(data, OUTPUT_DIR / "psf_metal_series_viridis.png")

    print("\n" + "=" * 60)
    print("Enhanced visualization generation complete!")
    print(f"Output saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    generate_all_enhanced()
