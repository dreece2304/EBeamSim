# Physics Review Findings and Corrections

## Summary of Issues Found

### 1. ✅ FIXED: Beam Current Unit Conversion Error
**Location:** `/src/beam/src/PatternGenerator.cc`
**Issue:** Beam current was passed in nA but the dose calculation formula expected pA
**Fix Applied:** Added conversion factor of 1000.0 when calling `CalculateClockFrequency`

### 2. ❌ PSF Normalization Error
**Location:** `/scripts/gui/ebl_gui.py` (line 4323-4336)
**Issue:** The PSF calculation has incorrect normalization
**Current Code:**
```python
def calculate_psf(self, r, alpha, beta, sigma_f, sigma_b):
    forward = alpha * np.exp(-r**2 / (2 * sigma_f_um**2))
    backscatter = beta * np.exp(-r**2 / (2 * sigma_b**2))
    norm_f = 1 / (2 * np.pi * sigma_f_um**2)
    norm_b = 1 / (2 * np.pi * sigma_b**2)
    return forward * norm_f + backscatter * norm_b
```
**Problem:** The normalization is applied AFTER multiplying by alpha/beta, but alpha and beta should BE the normalized amplitudes.

**Correct Physics:**
```python
def calculate_psf(self, r, alpha, beta, sigma_f, sigma_b):
    # Two-Gaussian PSF model where alpha + beta = 1 for energy conservation
    sigma_f_um = sigma_f / 1000.0  # Convert nm to μm
    
    # Properly normalized Gaussians
    forward = (alpha / (2 * np.pi * sigma_f_um**2)) * np.exp(-r**2 / (2 * sigma_f_um**2))
    backscatter = (beta / (2 * np.pi * sigma_b**2)) * np.exp(-r**2 / (2 * sigma_b**2))
    
    return forward + backscatter
```

### 3. ❌ Proximity Correction Algorithm Issues
**Location:** `/scripts/gui/ebl_gui.py` (line 4583-4633)
**Issues:**
- The PSF is not properly normalized (integrates to alpha+beta instead of 1)
- The correction should use deconvolution, not simple ratio adjustment
- Missing exposure grid spacing in dose calculations

### 4. ✅ Energy Deposition Collection is Correct
**Location:** `/src/actions/src/EventAction.cc`
- Correctly collects ALL energy deposits (not just resist)
- Properly calculates radial distance from beam axis
- Uses appropriate binning for PSF analysis

### 5. ❌ Dose Unit Consistency
**Issue:** Mixed units throughout the code
- C++ uses μC/cm² for dose
- Dwell time is in microseconds
- Need to ensure consistent unit conversion for dose per area

### 6. ❌ Missing Physical Constants
**Location:** `/src/common/include/JEOLParameters.hh`
**Missing:**
- Electron charge (1.602e-19 C)
- Proper conversion factors documented

## Recommended Fixes

### Fix 1: PSF Model Correction
The PSF should satisfy:
∫∫ PSF(r) * 2πr dr = 1 (energy conservation)

For the two-Gaussian model:
- α + β should equal 1.0 (or very close)
- Each Gaussian should be properly normalized

### Fix 2: Dose Calculation Verification
Dose = (Beam Current × Dwell Time) / (Exposure Area)

Where:
- Beam Current in Amperes (not pA or nA)
- Dwell Time in seconds
- Area in cm²
- Result in C/cm² (then convert to μC/cm²)

### Fix 3: Proximity Correction Algorithm
Should use iterative deconvolution:
1. Start with target pattern T
2. Calculate effective dose E = Pattern ⊗ PSF
3. Update: Pattern_new = Pattern_old × (T / E)
4. Iterate until convergence

### Fix 4: Physical Parameter Ranges
Typical values for 100 keV on Silicon:
- α (forward/total ratio): 0.2-0.4
- β (backscatter/total ratio): 0.6-0.8
- σf (forward range): 10-50 nm
- σb (backscatter range): 5-15 μm
- η = α/β: 0.3-0.7

## Critical Physics Principles

1. **Energy Conservation:** Total deposited energy must equal beam energy × number of electrons
2. **Dose Definition:** Charge per unit area (C/cm²)
3. **PSF Normalization:** Must integrate to 1 over all space
4. **Proximity Effect:** Caused by electron scattering, depends on:
   - Beam energy
   - Resist material (Z, density)
   - Substrate material (Z, density)
   - Resist thickness

## Validation Tests Needed

1. **PSF Integration Test:** Verify ∫∫ PSF(r) * 2πr dr ≈ 1.0
2. **Dose Conservation Test:** Total dose in = Total dose out
3. **Monte Carlo Validation:** Compare PSF with simulation results
4. **Known Pattern Test:** Compare with published proximity effect data

## References

1. "Proximity effect in electron-beam lithography" - T. H. P. Chang, J. Vac. Sci. Technol. 12, 1271 (1975)
2. "Monte Carlo simulation of the electron-solid interaction" - D. C. Joy, Scanning Microscopy 1995
3. JEOL JBX-6300FS Technical Manual
4. "Electron-beam lithography" - M. A. McCord and M. J. Rooks, SPIE Handbook (2000)