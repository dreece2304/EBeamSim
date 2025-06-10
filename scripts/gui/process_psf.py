import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import simpson
from scipy import stats

# === Load and Normalize ===
df = pd.read_csv("../DataOutput/ebl_psf_data.csv")
df.columns = ['radius_nm', 'energy']
df.sort_values('radius_nm', inplace=True)
radius_nm = df['radius_nm'].values
energy = df['energy'].values
area = simpson(energy * 2 * np.pi * radius_nm, radius_nm)
energy_norm = energy / area
df['energy_norm'] = energy_norm

# === Export BEAMER format ===
with open("../DataOutput/beamer_psf.dat", "w") as f:
    f.write(f"0.0 {energy_norm.max():.6g}\n")
    for r, e in zip(radius_nm * 1e-3, energy_norm):
        f.write(f"{r:.6f} {e:.6f}\n")

# === Log-Log PSF Plot ===
plt.figure(figsize=(10, 8))
plt.loglog(radius_nm, energy, 'b-', label='Energy Deposition')

# Power-law fit examples
for label, rmin, rmax, color in [('Near', 10, 100, 'r'), ('Far', 1000, 10000, 'g')]:
    mask = (radius_nm >= rmin) & (radius_nm <= rmax)
    if mask.sum() > 2:
        slope, intercept, *_ = stats.linregress(np.log10(radius_nm[mask]), np.log10(energy[mask]))
        r_fit = np.logspace(np.log10(rmin), np.log10(rmax), 50)
        e_fit = 10**intercept * r_fit**slope
        plt.loglog(r_fit, e_fit, f'{color}--', label=f'{label} field: r^{slope:.2f}')

plt.xlabel('Radius (nm)')
plt.ylabel('Energy Deposition (eV/nm²)')
plt.title('PSF - Log-Log Scale')
plt.grid(True, which="both", ls=':')
plt.legend()
plt.tight_layout()
plt.savefig("psf_loglog_plot.png", dpi=300)
plt.close()

# === 2D Kernel ===
grid_nm = 10000
res_nm = 5.0
x = np.arange(-grid_nm/2, grid_nm/2 + res_nm, res_nm)
y = np.arange(-grid_nm/2, grid_nm/2 + res_nm, res_nm)
xx, yy = np.meshgrid(x, y)
rr = np.sqrt(xx**2 + yy**2)
psf_2d = np.interp(rr.flatten(), radius_nm, energy_norm).reshape(rr.shape)
psf_2d /= np.sum(psf_2d)
np.save("../DataOutput/psf_kernel.npy", psf_2d)

print("✅ PSF export complete: beamer_psf.dat, psf_loglog_plot.png, psf_kernel.npy")
