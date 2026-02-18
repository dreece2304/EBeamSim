#!/usr/bin/env python3
"""
Publication-Quality PSF Figure for PhD Defense

Creates a clean, modern, aesthetically pleasing PSF visualization
using a single material dataset.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe
from pathlib import Path

# Output
OUTPUT_DIR = Path(__file__).parent / "psf_analysis_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Load data
PSF_FILE = Path(__file__).parent / "psf_output/metalcones_corrected/EG/psf_Tincone_EG_100keV.csv"


def create_gradient_line(ax, x, y, cmap='viridis', linewidth=3):
    """Create a line with color gradient based on y-value."""
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Normalize y for color mapping
    norm = plt.Normalize(y.min(), y.max())
    lc = LineCollection(segments, cmap=cmap, norm=norm, linewidth=linewidth)
    lc.set_array(y)
    return ax.add_collection(lc)


def create_modern_psf_dark():
    """Create dark-themed modern PSF figure."""
    # Load data
    df = pd.read_csv(PSF_FILE)
    r = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values

    # Normalize
    energy_norm = energy / energy.max()

    # Dark theme
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 8))

    # Set background
    fig.patch.set_facecolor('#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    # Create custom colormap (cyan to magenta)
    colors_cmap = ['#00ffff', '#00ff88', '#88ff00', '#ffff00', '#ff8800', '#ff0088']
    cmap = LinearSegmentedColormap.from_list('energy', colors_cmap)

    # Plot with gradient
    mask = r > 0
    r_plot = r[mask]
    e_plot = energy_norm[mask]

    # Main line with glow effect
    ax.semilogx(r_plot, e_plot, color='#00ffff', linewidth=3, alpha=0.9,
                path_effects=[pe.withStroke(linewidth=8, foreground='#00ffff', alpha=0.3)])

    # Fill under curve with gradient
    ax.fill_between(r_plot, 0, e_plot, alpha=0.15, color='#00ffff')

    # Subtle grid
    ax.grid(True, which='major', alpha=0.15, color='white', linestyle='-')
    ax.grid(True, which='minor', alpha=0.05, color='white', linestyle='-')

    # Labels with modern font
    ax.set_xlabel('Lateral Distance from Beam (nm)', fontsize=14, color='white', fontweight='light')
    ax.set_ylabel('Energy Deposition (normalized)', fontsize=14, color='white', fontweight='light')

    # Title
    ax.set_title('Point Spread Function\nTincone MLD Resist | 100 keV',
                fontsize=18, color='white', fontweight='light', pad=20)

    # Axis styling
    ax.set_xlim(0.1, 15000)
    ax.set_ylim(0, 1.05)
    ax.tick_params(colors='white', labelsize=11)
    for spine in ax.spines.values():
        spine.set_color('#333333')

    # Add subtle annotations
    ax.axvline(x=100, color='#ff6600', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(120, 0.85, 'Resist\nThickness', fontsize=10, color='#ff6600', alpha=0.8)

    ax.axvline(x=1000, color='#ff0066', linestyle='--', alpha=0.4, linewidth=1.5)
    ax.text(1200, 0.6, 'Proximity\nEffect Zone', fontsize=10, color='#ff0066', alpha=0.8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'psf_modern_dark.png', dpi=300, facecolor='#0a0a0a',
                bbox_inches='tight', pad_inches=0.3)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'psf_modern_dark.png'}")


def create_modern_psf_light():
    """Create light-themed clean PSF figure with log-log axes, viridis colors, full border."""
    from scipy.signal import savgol_filter

    # Load data
    df = pd.read_csv(PSF_FILE)
    r = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values
    energy_norm = energy / energy.max()

    # Filter valid data
    mask = (r > 0) & (energy_norm > 0)
    r_raw = r[mask]
    e_raw = energy_norm[mask]

    # Sort by radius (required for smoothing)
    sort_idx = np.argsort(r_raw)
    r_sorted = r_raw[sort_idx]
    e_sorted = e_raw[sort_idx]

    # Apply mild Savitzky-Golay smoothing to reduce noise while preserving features
    # Use smaller window for gentler smoothing
    window = min(11, len(e_sorted) // 10 * 2 + 1)  # Small window for gentle smoothing
    window = max(5, window)  # Minimum 5 points
    if len(e_sorted) >= window:
        e_smooth = savgol_filter(e_sorted, window_length=window, polyorder=2)
        # Ensure no negative values after smoothing
        e_smooth = np.maximum(e_smooth, e_sorted.min() * 0.1)
    else:
        e_smooth = e_sorted

    # Conservative extrapolation for log-log scale: extend to 0.1nm
    # Use logarithmic spacing and hold at peak value
    r_extrap = np.logspace(-1, np.log10(r_sorted[0] * 0.95), 10)  # 0.1nm to just below data start
    e_extrap = np.full_like(r_extrap, e_smooth[0])  # Hold at peak value

    # Combine extrapolated + smoothed data
    r_plot = np.concatenate([r_extrap, r_sorted])
    e_plot = np.concatenate([e_extrap, e_smooth])

    # Light theme with clean styling
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 12,
        'axes.linewidth': 1.2,
    })

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Create gradient colored line using viridis
    points = np.array([np.log10(r_plot), np.log10(e_plot)]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    from matplotlib.collections import LineCollection
    norm = plt.Normalize(np.log10(e_plot).min(), np.log10(e_plot).max())
    lc = LineCollection(segments, cmap='viridis', norm=norm, linewidth=3)
    lc.set_array(np.log10(e_plot[:-1]))

    # Plot on log-log scale
    ax.set_xscale('log')
    ax.set_yscale('log')

    # Add the gradient line
    ax.add_collection(lc)

    # Plot main line with viridis color based on energy
    ax.plot(r_plot, e_plot, color=plt.cm.viridis(0.7), linewidth=2.5, solid_capstyle='round')

    # Viridis gradient fill - color based on ENERGY VALUE (high=yellow, low=purple)
    # Normalize energy to 0-1 for colormap
    e_log = np.log10(e_plot)
    e_norm = (e_log - e_log.min()) / (e_log.max() - e_log.min())

    # Set fill baseline to be just below the minimum energy value
    fill_baseline = e_plot.min() * 0.8  # Slightly below data minimum

    # Fill with color gradient based on energy at each point
    for i in range(len(r_plot) - 1):
        # Color based on average energy in this segment
        avg_e_norm = (e_norm[i] + e_norm[i+1]) / 2
        color = plt.cm.viridis(avg_e_norm)  # high energy = yellow, low = purple
        ax.fill_between(r_plot[i:i+2], fill_baseline, e_plot[i:i+2],
                       alpha=0.25, color=color, linewidth=0)

    # Grid
    ax.grid(True, which='major', alpha=0.3, color='#888888', linestyle='-', linewidth=0.5)
    ax.grid(True, which='minor', alpha=0.15, color='#aaaaaa', linestyle='-', linewidth=0.3)
    ax.set_axisbelow(True)

    # Clean labels
    ax.set_xlabel('Lateral Distance from Beam (nm)', fontsize=14, color='#222222')
    ax.set_ylabel('Energy Deposition (normalized)', fontsize=14, color='#222222')

    # Elegant title
    ax.set_title('Point Spread Function — Tincone MLD Resist at 100 keV',
                fontsize=16, color='#111111', fontweight='medium', pad=15)

    # Set axis limits
    # x: start near data minimum for log scale
    # y: use larger non-negligible minimum (e.g., 1e-4) to avoid excessive dynamic range
    ax.set_xlim(r_plot.min() * 0.8, 20000)
    y_min = max(1e-4, e_plot.min() * 0.7)  # At least 1e-4 or slightly below data minimum
    ax.set_ylim(y_min, 2)

    # Full border with all spines visible
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#333333')
        spine.set_linewidth(1.2)

    # Inward tick marks on all sides
    ax.tick_params(axis='both', which='both', direction='in',
                   top=True, right=True, bottom=True, left=True,
                   colors='#333333', labelsize=11, length=6, width=1)
    ax.tick_params(axis='both', which='minor', length=3, width=0.8)

    # Add colorbar for reference
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
    cbar.set_label('Normalized Energy', fontsize=11)
    cbar.ax.tick_params(direction='in', length=4)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'psf_modern_light.png', dpi=300, facecolor='white',
                bbox_inches='tight', pad_inches=0.2)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'psf_modern_light.png'}")


def create_infographic_psf():
    """Create an infographic-style PSF with physical context."""
    df = pd.read_csv(PSF_FILE)
    r = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values
    energy_norm = energy / energy.max()

    fig = plt.figure(figsize=(14, 9))

    # Main PSF plot (larger)
    ax_main = fig.add_axes([0.08, 0.12, 0.6, 0.75])

    # Schematic inset (top right)
    ax_inset = fig.add_axes([0.72, 0.55, 0.25, 0.35])

    # Stats box (bottom right)
    ax_stats = fig.add_axes([0.72, 0.12, 0.25, 0.35])

    # === Main PSF Plot ===
    ax_main.set_facecolor('#f8f9fa')

    mask = r > 0
    r_plot = r[mask]
    e_plot = energy_norm[mask]

    # Gradient fill using multiple fills
    n_fills = 50
    for i in range(n_fills):
        alpha = 0.3 * (1 - i/n_fills)
        y_lower = e_plot * (i/n_fills)
        y_upper = e_plot * ((i+1)/n_fills)
        color = plt.cm.viridis(1 - i/n_fills)
        ax_main.fill_between(r_plot, y_lower, y_upper, alpha=alpha, color=color, linewidth=0)

    # Main line
    ax_main.semilogx(r_plot, e_plot, color='#2c3e50', linewidth=2.5)

    ax_main.set_xlabel('Lateral Distance from Beam Center (nm)', fontsize=13)
    ax_main.set_ylabel('Energy Deposition (normalized)', fontsize=13)
    ax_main.set_xlim(0.1, 15000)
    ax_main.set_ylim(0, 1.05)
    ax_main.grid(True, alpha=0.2, which='both')

    # Region annotations with arrows
    ax_main.annotate('Resolution\nLimit', xy=(10, 0.7), xytext=(3, 0.5),
                    fontsize=10, color='#27ae60', ha='center',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', lw=1.5))

    ax_main.annotate('Backscatter\nTail', xy=(3000, 0.05), xytext=(6000, 0.25),
                    fontsize=10, color='#c0392b', ha='center',
                    arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.5))

    for spine in ['top', 'right']:
        ax_main.spines[spine].set_visible(False)

    # === Schematic Inset ===
    ax_inset.set_xlim(-50, 50)
    ax_inset.set_ylim(-120, 20)
    ax_inset.set_aspect('equal')
    ax_inset.axis('off')
    ax_inset.set_title('Physical Model', fontsize=11, fontweight='bold', pad=5)

    # Draw resist layer
    resist = FancyBboxPatch((-40, -100), 80, 100, boxstyle="round,pad=0.02",
                           facecolor='#f1c40f', edgecolor='#d68910', alpha=0.7, linewidth=2)
    ax_inset.add_patch(resist)
    ax_inset.text(0, -50, 'Resist\n(100 nm)', ha='center', va='center', fontsize=9, fontweight='bold')

    # Draw substrate
    substrate = FancyBboxPatch((-45, -180), 90, 80, boxstyle="square",
                              facecolor='#95a5a6', edgecolor='#7f8c8d', alpha=0.8, linewidth=2)
    ax_inset.add_patch(substrate)
    ax_inset.text(0, -140, 'Si\nSubstrate', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    # Electron beam
    ax_inset.annotate('', xy=(0, -5), xytext=(0, 15),
                     arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=3))
    ax_inset.text(0, 18, 'e⁻ beam', ha='center', fontsize=9, color='#e74c3c', fontweight='bold')

    # Scatter paths
    for angle, color in [(30, '#3498db'), (-25, '#3498db'), (50, '#9b59b6'), (-45, '#9b59b6')]:
        dx = 30 * np.sin(np.radians(angle))
        dy = -40 * np.cos(np.radians(angle))
        ax_inset.annotate('', xy=(dx, dy-20), xytext=(0, -10),
                         arrowprops=dict(arrowstyle='->', color=color, lw=1, alpha=0.6,
                                       connectionstyle=f'arc3,rad={0.2 if angle > 0 else -0.2}'))

    # Backscatter
    ax_inset.annotate('', xy=(25, -30), xytext=(15, -110),
                     arrowprops=dict(arrowstyle='->', color='#e67e22', lw=1.5,
                                   connectionstyle='arc3,rad=0.3'))
    ax_inset.text(35, -70, 'Back-\nscatter', fontsize=8, color='#e67e22')

    # === Stats Box ===
    ax_stats.axis('off')
    ax_stats.set_xlim(0, 1)
    ax_stats.set_ylim(0, 1)

    stats_text = """Material: Tincone (EG)
Formula: SnC₄H₈O₄
Metal: Sn (Z=50)
Metal fraction: 50%
Density: 2.5 g/cm³

Beam Energy: 100 keV
Resist: 100 nm
Substrate: Silicon

Backscatter: 133.2%"""

    ax_stats.text(0.1, 0.95, 'Simulation Parameters', fontsize=11, fontweight='bold',
                 transform=ax_stats.transAxes, va='top')
    ax_stats.text(0.1, 0.82, stats_text, fontsize=9, transform=ax_stats.transAxes,
                 va='top', family='monospace',
                 bbox=dict(boxstyle='round', facecolor='#ecf0f1', edgecolor='#bdc3c7', alpha=0.8))

    # Main title
    fig.suptitle('Point Spread Function Analysis', fontsize=18, fontweight='bold', y=0.97)

    plt.savefig(OUTPUT_DIR / 'psf_infographic.png', dpi=300, facecolor='white',
                bbox_inches='tight', pad_inches=0.2)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'psf_infographic.png'}")


def create_minimal_psf():
    """Ultra-minimal, elegant PSF figure."""
    df = pd.read_csv(PSF_FILE)
    r = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values
    energy_norm = energy / energy.max()

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    mask = r > 0
    r_plot = r[mask]
    e_plot = energy_norm[mask]

    # Single elegant line
    ax.semilogx(r_plot, e_plot, color='#2c3e50', linewidth=2)

    # Very subtle fill
    ax.fill_between(r_plot, 0, e_plot, alpha=0.1, color='#3498db')

    # Minimal styling
    ax.set_xlim(0.1, 15000)
    ax.set_ylim(0, 1.05)

    # Remove all spines except bottom and left
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#dddddd')
    ax.spines['left'].set_color('#dddddd')

    # Minimal labels
    ax.set_xlabel('r (nm)', fontsize=12, color='#666666')
    ax.set_ylabel('E(r) / E₀', fontsize=12, color='#666666')

    ax.tick_params(colors='#999999', labelsize=10)

    # No grid, no title - ultra clean

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'psf_minimal.png', dpi=300, facecolor='white',
                bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'psf_minimal.png'}")


def create_gradient_background_psf():
    """PSF with beautiful gradient background."""
    df = pd.read_csv(PSF_FILE)
    r = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values
    energy_norm = energy / energy.max()

    fig, ax = plt.subplots(figsize=(12, 8))

    # Create gradient background
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    gradient = np.vstack([gradient] * 256)

    # Custom gradient colormap (dark blue to dark purple)
    colors = ['#1a1a2e', '#16213e', '#1a1a2e']
    bg_cmap = LinearSegmentedColormap.from_list('bg', colors)

    ax.imshow(gradient, aspect='auto', cmap=bg_cmap, extent=[0.1, 15000, 0, 1.05],
              alpha=0.9, zorder=0)

    mask = r > 0
    r_plot = r[mask]
    e_plot = energy_norm[mask]

    # Glowing line effect
    for lw, alpha in [(12, 0.1), (8, 0.15), (5, 0.3), (2.5, 1.0)]:
        ax.semilogx(r_plot, e_plot, color='#00d4ff', linewidth=lw, alpha=alpha)

    # Gradient fill
    ax.fill_between(r_plot, 0, e_plot, alpha=0.15, color='#00d4ff')

    ax.set_xlim(0.1, 15000)
    ax.set_ylim(0, 1.05)
    ax.set_xscale('log')

    # Style
    ax.set_xlabel('Lateral Distance (nm)', fontsize=13, color='white')
    ax.set_ylabel('Energy Deposition', fontsize=13, color='white')
    ax.set_title('Point Spread Function — Tincone at 100 keV',
                fontsize=16, color='white', fontweight='light', pad=15)

    ax.tick_params(colors='white', labelsize=11)
    ax.grid(True, alpha=0.1, color='white', which='both')

    for spine in ax.spines.values():
        spine.set_color('#333355')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'psf_gradient_bg.png', dpi=300, facecolor='#1a1a2e',
                bbox_inches='tight', pad_inches=0.2)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'psf_gradient_bg.png'}")


if __name__ == "__main__":
    print("=" * 60)
    print("Creating Presentation-Quality PSF Figures")
    print("=" * 60)
    print()

    print("1. Dark theme (neon style)...")
    create_modern_psf_dark()

    print("2. Light theme (clean professional)...")
    create_modern_psf_light()

    print("3. Infographic style (with schematic)...")
    create_infographic_psf()

    print("4. Minimal style (ultra-clean)...")
    create_minimal_psf()

    print("5. Gradient background (dramatic)...")
    create_gradient_background_psf()

    print()
    print("=" * 60)
    print("All presentation figures generated!")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)
