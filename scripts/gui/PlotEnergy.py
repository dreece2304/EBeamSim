import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('../DataOutput/ebl_psf_data.csv')
print(f"Loaded {len(df)} data points")

# Extract columns - handling potential header variations
if 'Radius(nm)' in df.columns:
    radius_nm = df['Radius(nm)'].values
    energy = df['EnergyDeposition(eV/nm^2)'].values
else:
    # Assume first column is radius, second is energy
    radius_nm = df.iloc[:, 0].values
    energy = df.iloc[:, 1].values

# Sort by radius to ensure proper plotting
sort_idx = np.argsort(radius_nm)
radius_nm = radius_nm[sort_idx]
energy = energy[sort_idx]

# Create the log-log plot
plt.figure(figsize=(10, 8))

# Main plot
plt.loglog(radius_nm, energy, 'b-', linewidth=1.5, label='Energy Deposition')

# Add grid
plt.grid(True, which="both", ls="-", alpha=0.2)
plt.grid(True, which="minor", ls=":", alpha=0.1)

# Labels and title
plt.xlabel('Radius (nm)', fontsize=12)
plt.ylabel('Energy Deposition (eV/nm²)', fontsize=12)
plt.title('Electron Beam PSF - Energy Deposition vs Radius\n(Log-Log Scale)', fontsize=14)

# Add some reference lines to help identify power law regions
# Find approximate power law in different regions
from scipy import stats

# Region 1: 10-100 nm
mask1 = (radius_nm >= 10) & (radius_nm <= 100)
if np.sum(mask1) > 2:
    slope1, intercept1, _, _, _ = stats.linregress(np.log10(radius_nm[mask1]), np.log10(energy[mask1]))
    r_fit1 = np.logspace(1, 2, 50)
    e_fit1 = 10**(intercept1) * r_fit1**slope1
    plt.loglog(r_fit1, e_fit1, 'r--', alpha=0.7, linewidth=1,
               label=f'Power law fit (10-100 nm): r^{slope1:.2f}')

# Region 2: 1000-10000 nm
mask2 = (radius_nm >= 1000) & (radius_nm <= 10000)
if np.sum(mask2) > 2:
    slope2, intercept2, _, _, _ = stats.linregress(np.log10(radius_nm[mask2]), np.log10(energy[mask2]))
    r_fit2 = np.logspace(3, 4, 50)
    e_fit2 = 10**(intercept2) * r_fit2**slope2
    plt.loglog(r_fit2, e_fit2, 'g--', alpha=0.7, linewidth=1,
               label=f'Power law fit (1-10 μm): r^{slope2:.2f}')

# Add annotations for key features
plt.axvline(x=100, color='gray', linestyle=':', alpha=0.5)
plt.axvline(x=1000, color='gray', linestyle=':', alpha=0.5)
plt.axvline(x=10000, color='gray', linestyle=':', alpha=0.5)

# Text annotations
plt.text(50, plt.ylim()[0]*10, 'Near field\n(< 100 nm)',
         ha='center', va='bottom', fontsize=10, alpha=0.7)
plt.text(500, plt.ylim()[0]*10, 'Transition\n(0.1-1 μm)',
         ha='center', va='bottom', fontsize=10, alpha=0.7)
plt.text(30000, plt.ylim()[0]*10, 'Far field\n(> 10 μm)',
         ha='center', va='bottom', fontsize=10, alpha=0.7)

# Set axis limits to show full range
plt.xlim(radius_nm[0]*0.8, radius_nm[-1]*1.2)
plt.ylim(energy[energy > 0].min()*0.5, energy.max()*2)

# Legend
plt.legend(loc='upper right', fontsize=10)

# Add statistics box
stats_text = f'Data Statistics:\n'
stats_text += f'Points: {len(radius_nm)}\n'
stats_text += f'Radius: {radius_nm[0]:.1f} - {radius_nm[-1]:.0f} nm\n'
stats_text += f'Energy: {energy.min():.2e} - {energy.max():.2e} eV/nm²\n'
stats_text += f'Dynamic range: {energy.max()/energy[energy>0].min():.1e}'

plt.text(0.02, 0.02, stats_text, transform=plt.gca().transAxes,
         fontsize=9, verticalalignment='bottom',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.savefig('psf_loglog_plot.png', dpi=300, bbox_inches='tight')
plt.show()

# Also create a version with normalized energy for comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Left plot: Original data
ax1.loglog(radius_nm, energy, 'b-', linewidth=1.5)
ax1.set_xlabel('Radius (nm)', fontsize=12)
ax1.set_ylabel('Energy Deposition (eV/nm²)', fontsize=12)
ax1.set_title('Original Energy Deposition', fontsize=14)
ax1.grid(True, which="both", ls="-", alpha=0.2)
ax1.grid(True, which="minor", ls=":", alpha=0.1)

# Right plot: Normalized data (as your code would produce)
# Calculate normalization using Simpson's rule
from scipy.integrate import simpson
area = simpson(energy * 2 * np.pi * radius_nm, radius_nm)
energy_norm = energy / area

ax2.loglog(radius_nm, energy_norm, 'r-', linewidth=1.5)
ax2.set_xlabel('Radius (nm)', fontsize=12)
ax2.set_ylabel('Normalized Energy Density', fontsize=12)
ax2.set_title(f'Normalized PSF (area = 1)\nNormalization factor: {area:.2e}', fontsize=14)
ax2.grid(True, which="both", ls="-", alpha=0.2)
ax2.grid(True, which="minor", ls=":", alpha=0.1)

# Match y-axis ranges for easier comparison
ax2.set_xlim(ax1.get_xlim())

plt.tight_layout()
plt.savefig('psf_comparison_plots.png', dpi=300, bbox_inches='tight')
plt.show()

# Print some key values
print(f"\nKey radius values:")
print(f"Radius at 50% of peak energy: {radius_nm[energy < 0.5*energy.max()][0]:.1f} nm")
print(f"Radius at 1% of peak energy: {radius_nm[energy < 0.01*energy.max()][0]:.1f} nm")
print(f"Radius at 0.01% of peak energy: {radius_nm[energy < 0.0001*energy.max()][0]:.1f} nm")

# Calculate energy fractions in different regions
ranges = [(1, 100), (100, 1000), (1000, 10000), (10000, 100000)]
print(f"\nEnergy distribution by radius range:")
for r_min, r_max in ranges:
    mask = (radius_nm >= r_min) & (radius_nm < r_max)
    if np.sum(mask) > 1:
        # Integrate energy in this range
        r_range = radius_nm[mask]
        e_range = energy[mask]
        integral = simpson(e_range * 2 * np.pi * r_range, r_range)
        fraction = integral / area * 100
        print(f"  {r_min:>6} - {r_max:>6} nm: {fraction:5.1f}%")