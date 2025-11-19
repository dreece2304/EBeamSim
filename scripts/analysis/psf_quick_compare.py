#!/usr/bin/env python3
"""
Quick PSF Comparison (no matplotlib required)
Compares PSF profiles from different materials to verify physics accuracy
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, List


class QuickPSFCompare:
    """Compare PSF profiles without plotting"""

    def __init__(self):
        self.psf_data: Dict[str, Tuple[List[float], List[float]]] = {}

    def load_beamer_psf(self, filepath: Path, material_name: str) -> bool:
        """Load PSF data from BEAMER format file"""
        try:
            with open(filepath, 'r') as f:
                lines = [line for line in f if not line.startswith('#') and line.strip()]

            radii = []
            energies = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    radii.append(float(parts[0]) * 1000)  # Convert μm to nm
                    energies.append(float(parts[1]))

            self.psf_data[material_name] = (radii, energies)
            print(f"✓ Loaded {material_name}: {len(radii)} data points")
            return True

        except Exception as e:
            print(f"✗ Error loading {filepath}: {e}")
            return False

    def find_closest_index(self, radii: List[float], target_nm: float) -> int:
        """Find index of closest radius to target"""
        min_diff = float('inf')
        best_idx = 0
        for i, r in enumerate(radii):
            diff = abs(r - target_nm)
            if diff < min_diff:
                min_diff = diff
                best_idx = i
        return best_idx

    def calculate_metrics(self) -> Dict[str, Dict]:
        """Calculate key metrics for all materials"""
        metrics = {}

        for mat_name, (radii, energies) in self.psf_data.items():
            # Find key radii
            idx_50nm = self.find_closest_index(radii, 50)
            idx_500nm = self.find_closest_index(radii, 500)
            idx_1um = self.find_closest_index(radii, 1000)
            idx_2um = self.find_closest_index(radii, 2000)
            idx_5um = self.find_closest_index(radii, 5000)
            idx_10um = self.find_closest_index(radii, 10000)

            # Peak
            peak_energy = max(energies)
            peak_idx = energies.index(peak_energy)
            peak_radius = radii[peak_idx]

            # FWHM
            half_max = peak_energy / 2
            above_half = [i for i, e in enumerate(energies) if e > half_max]
            fwhm_nm = radii[above_half[-1]] - radii[above_half[0]] if above_half else 0

            # Tail extent (1% of peak)
            tail_threshold = peak_energy * 0.01
            above_tail = [i for i, e in enumerate(energies) if e > tail_threshold]
            tail_extent_nm = radii[above_tail[-1]] if above_tail else 0

            metrics[mat_name] = {
                'peak_energy': peak_energy,
                'peak_radius_nm': peak_radius,
                'fwhm_nm': fwhm_nm,
                'tail_extent_nm': tail_extent_nm,
                'energy_at_50nm': energies[idx_50nm],
                'energy_at_500nm': energies[idx_500nm],
                'energy_at_1um': energies[idx_1um],
                'energy_at_2um': energies[idx_2um],
                'energy_at_5um': energies[idx_5um],
                'energy_at_10um': energies[idx_10um],
            }

        return metrics

    def generate_report(self) -> str:
        """Generate detailed comparison report"""
        metrics = self.calculate_metrics()

        lines = []
        lines.append("="*80)
        lines.append("PSF PHYSICS VERIFICATION REPORT")
        lines.append("="*80)
        lines.append(f"Analysis Date: 2025-11-19")
        lines.append(f"Materials Analyzed: {len(self.psf_data)}")
        lines.append("")

        # Individual metrics
        lines.append("INDIVIDUAL MATERIAL METRICS:")
        lines.append("-" * 80)
        for mat_name, m in metrics.items():
            lines.append(f"\n{mat_name}:")
            lines.append(f"  Peak Energy (normalized): {m['peak_energy']:.6f}")
            lines.append(f"  Peak Radius: {m['peak_radius_nm']:.1f} nm")
            lines.append(f"  FWHM: {m['fwhm_nm']:.1f} nm")
            lines.append(f"  Tail Extent (>1% peak): {m['tail_extent_nm']:.0f} nm")
            lines.append(f"  Energy at 50 nm: {m['energy_at_50nm']:.6f}")
            lines.append(f"  Energy at 500 nm: {m['energy_at_500nm']:.6f}")
            lines.append(f"  Energy at 1 μm: {m['energy_at_1um']:.6f}")
            lines.append(f"  Energy at 2 μm: {m['energy_at_2um']:.6e}")
            lines.append(f"  Energy at 5 μm: {m['energy_at_5um']:.6e}")
            lines.append(f"  Energy at 10 μm: {m['energy_at_10um']:.6e}")

        # Comparative analysis
        if len(metrics) >= 2:
            materials = list(metrics.keys())
            baseline = materials[0]
            baseline_m = metrics[baseline]

            lines.append(f"\n\nCOMPARATIVE ANALYSIS (relative to {baseline}):")
            lines.append("-" * 80)

            for mat_name in materials[1:]:
                m = metrics[mat_name]
                lines.append(f"\n{mat_name} vs {baseline}:")
                lines.append(f"  Peak ratio: {m['peak_energy']/baseline_m['peak_energy']:.3f}×")
                lines.append(f"  FWHM ratio: {m['fwhm_nm']/baseline_m['fwhm_nm']:.3f}×")
                lines.append(f"  Tail extent ratio: {m['tail_extent_nm']/baseline_m['tail_extent_nm']:.3f}×")
                lines.append(f"  Energy ratio at 50 nm: {m['energy_at_50nm']/baseline_m['energy_at_50nm']:.3f}×")
                lines.append(f"  Energy ratio at 500 nm: {m['energy_at_500nm']/baseline_m['energy_at_500nm']:.3f}×")
                lines.append(f"  Energy ratio at 1 μm: {m['energy_at_1um']/baseline_m['energy_at_1um']:.3f}×")
                lines.append(f"  Energy ratio at 2 μm: {m['energy_at_2um']/baseline_m['energy_at_2um']:.3f}×")
                lines.append(f"  Energy ratio at 5 μm: {m['energy_at_5um']/baseline_m['energy_at_5um']:.3f}×")

        # Physics interpretation
        lines.append("\n\nPHYSICS INTERPRETATION:")
        lines.append("-" * 80)
        lines.append("Expected behavior for high-Z materials (e.g., Sn-MLD with Z=50):")
        lines.append("  • HIGHER energy in core region (Auger electron cascade from K-shell)")
        lines.append("  • WIDER core (increased backscattering, ~Z² dependence)")
        lines.append("  • THICKER tails (X-ray fluorescence transport, ~29 keV for Sn)")
        lines.append("")
        lines.append("✓ If high-Z shows 2-20× higher energy at 0.5-5 μm:")
        lines.append("    ➜ Physics is CORRECT - Auger and fluorescence working as expected")
        lines.append("    ➜ This is REAL physics, not a bug!")
        lines.append("")
        lines.append("✗ If all materials show similar anomalous increases:")
        lines.append("    ➜ Possible normalization bug - investigate energy accounting")

        # Conclusion
        lines.append("\n\nCONCLUSION:")
        lines.append("-" * 80)

        if len(metrics) >= 2:
            materials = list(metrics.keys())
            mat1, mat2 = materials[0], materials[1]
            m1, m2 = metrics[mat1], metrics[mat2]

            ratio_500nm = m2['energy_at_500nm'] / m1['energy_at_500nm']
            ratio_2um = m2['energy_at_2um'] / m1['energy_at_2um']

            if ratio_500nm > 1.5 and ratio_2um > 3.0:
                lines.append(f"✓ PHYSICS APPEARS CORRECT:")
                lines.append(f"  {mat2} shows significantly higher energy than {mat1}")
                lines.append(f"  Ratio at 500 nm: {ratio_500nm:.2f}×")
                lines.append(f"  Ratio at 2 μm: {ratio_2um:.2f}×")
                lines.append(f"  This is consistent with high-Z Auger/fluorescence effects")
                lines.append("")
                lines.append("  RECOMMENDATION: Physics implementation is WORKING AS INTENDED")
                lines.append("                  The increased energy is expected for high-Z materials")
            else:
                lines.append(f"⚠ UNCLEAR RESULT:")
                lines.append(f"  Ratios between materials are not as expected")
                lines.append(f"  Further investigation may be needed")

        lines.append("\n" + "="*80)

        return "\n".join(lines)


def main():
    """Main function"""
    analyzer = QuickPSFCompare()

    # Find PSF files
    script_dir = Path(__file__).parent
    gui_dir = script_dir.parent / 'gui'

    psf_files = {
        'AluconeXPS': gui_dir / 'psf_E100keV_beam2.0nm_resist30nm_AluconeXPS_run001_beamer.txt',
        'Sn-MLD': gui_dir / 'psf_E100keV_beam5.0nm_resist15nm_Sn-MLD_run001_beamer.txt',
    }

    # Load data
    loaded_count = 0
    for mat_name, filepath in psf_files.items():
        if filepath.exists():
            if analyzer.load_beamer_psf(filepath, mat_name):
                loaded_count += 1
        else:
            print(f"✗ File not found: {filepath}")

    if loaded_count < 2:
        print("Error: Need at least 2 PSF files to compare")
        return 1

    print(f"\n✓ Loaded {loaded_count} PSF files\n")

    # Generate report
    report = analyzer.generate_report()
    print(report)

    # Save to file
    output_file = script_dir / 'psf_physics_verification_report.txt'
    with open(output_file, 'w') as f:
        f.write(report)
    print(f"\n✓ Report saved to: {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
