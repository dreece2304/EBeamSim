#!/usr/bin/env python3
"""
PSF Physics Verification Tool
Compares PSF profiles from different materials to verify physics accuracy
Author: Claude Code Physics Verification Suite
Date: 2025-11-19
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple, List
import json


class PSFAnalyzer:
    """Analyze and compare PSF profiles from different materials"""

    def __init__(self):
        self.psf_data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self.material_info: Dict[str, Dict] = {}

    def load_beamer_psf(self, filepath: Path, material_name: str) -> bool:
        """Load PSF data from BEAMER format file"""
        try:
            # Read file, skip comment lines
            with open(filepath, 'r') as f:
                lines = [line for line in f if not line.startswith('#') and line.strip()]

            # Parse data
            radii = []
            energies = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    radii.append(float(parts[0]))
                    energies.append(float(parts[1]))

            radii = np.array(radii) * 1000  # Convert μm to nm
            energies = np.array(energies)

            self.psf_data[material_name] = (radii, energies)

            # Extract material info from filename
            stem = filepath.stem
            self.material_info[material_name] = {
                'filename': filepath.name,
                'peak_energy': np.max(energies),
                'peak_radius_nm': radii[np.argmax(energies)],
                'total_integrated': np.trapz(energies * 2 * np.pi * radii / 1000, radii / 1000)  # Integrate in μm
            }

            print(f"✓ Loaded {material_name}: {len(radii)} data points")
            return True

        except Exception as e:
            print(f"✗ Error loading {filepath}: {e}")
            return False

    def calculate_metrics(self) -> Dict[str, Dict]:
        """Calculate comparison metrics for all materials"""
        metrics = {}

        for mat_name, (radii, energies) in self.psf_data.items():
            # Find key radii
            r_50nm = np.argmin(np.abs(radii - 50))
            r_500nm = np.argmin(np.abs(radii - 500))
            r_2um = np.argmin(np.abs(radii - 2000))
            r_10um = np.argmin(np.abs(radii - 10000))

            # Calculate full width at half maximum (FWHM)
            half_max = np.max(energies) / 2
            above_half = energies > half_max
            if np.any(above_half):
                fwhm_indices = np.where(above_half)[0]
                fwhm_nm = radii[fwhm_indices[-1]] - radii[fwhm_indices[0]]
            else:
                fwhm_nm = 0

            # Calculate tail extent (where energy drops below 1% of peak)
            tail_threshold = np.max(energies) * 0.01
            tail_indices = np.where(energies > tail_threshold)[0]
            tail_extent_nm = radii[tail_indices[-1]] if len(tail_indices) > 0 else 0

            metrics[mat_name] = {
                'peak_energy': np.max(energies),
                'peak_radius_nm': radii[np.argmax(energies)],
                'fwhm_nm': fwhm_nm,
                'tail_extent_nm': tail_extent_nm,
                'energy_at_50nm': energies[r_50nm],
                'energy_at_500nm': energies[r_500nm],
                'energy_at_2um': energies[r_2um],
                'energy_at_10um': energies[r_10um],
                'integrated_energy': np.trapz(energies * 2 * np.pi * radii / 1000, radii / 1000)
            }

        return metrics

    def compare_materials(self, baseline_material: str) -> Dict[str, Dict]:
        """Compare all materials to baseline"""
        metrics = self.calculate_metrics()

        if baseline_material not in metrics:
            print(f"Warning: Baseline material '{baseline_material}' not found")
            return {}

        baseline = metrics[baseline_material]
        comparisons = {}

        for mat_name, mat_metrics in metrics.items():
            if mat_name == baseline_material:
                continue

            comparisons[mat_name] = {
                'peak_ratio': mat_metrics['peak_energy'] / baseline['peak_energy'],
                'fwhm_ratio': mat_metrics['fwhm_nm'] / baseline['fwhm_nm'] if baseline['fwhm_nm'] > 0 else 0,
                'tail_ratio': mat_metrics['tail_extent_nm'] / baseline['tail_extent_nm'],
                'energy_ratio_50nm': mat_metrics['energy_at_50nm'] / baseline['energy_at_50nm'],
                'energy_ratio_500nm': mat_metrics['energy_at_500nm'] / baseline['energy_at_500nm'],
                'energy_ratio_2um': mat_metrics['energy_at_2um'] / baseline['energy_at_2um'],
                'energy_ratio_10um': mat_metrics['energy_at_10um'] / baseline['energy_at_10um'],
                'integrated_ratio': mat_metrics['integrated_energy'] / baseline['integrated_energy']
            }

        return comparisons

    def plot_comparison(self, output_path: Path = None, log_scale: bool = True):
        """Create comprehensive comparison plots"""
        if len(self.psf_data) == 0:
            print("No PSF data loaded")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle('PSF Physics Verification: Material Comparison', fontsize=16, fontweight='bold')

        # Define colors for materials
        colors = {'AluconeXPS': 'blue', 'Sn-MLD': 'red', 'PMMA': 'green', 'HSQ': 'orange'}

        # Plot 1: Full PSF comparison (linear scale)
        ax1 = axes[0, 0]
        for mat_name, (radii, energies) in self.psf_data.items():
            color = colors.get(mat_name, 'black')
            ax1.plot(radii / 1000, energies, label=mat_name, linewidth=2, color=color, alpha=0.7)
        ax1.set_xlabel('Radius (μm)', fontsize=12)
        ax1.set_ylabel('Normalized Energy Deposition', fontsize=12)
        ax1.set_title('PSF Comparison - Linear Scale', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 10)

        # Plot 2: Core region detail (0-1 μm)
        ax2 = axes[0, 1]
        for mat_name, (radii, energies) in self.psf_data.items():
            color = colors.get(mat_name, 'black')
            mask = radii < 1000
            ax2.plot(radii[mask], energies[mask], label=mat_name, linewidth=2, color=color, alpha=0.7)
        ax2.set_xlabel('Radius (nm)', fontsize=12)
        ax2.set_ylabel('Normalized Energy Deposition', fontsize=12)
        ax2.set_title('Core Region Detail (0-1 μm)', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)

        # Plot 3: Log scale PSF (showing tails)
        ax3 = axes[1, 0]
        for mat_name, (radii, energies) in self.psf_data.items():
            color = colors.get(mat_name, 'black')
            # Filter out zeros for log scale
            mask = energies > 0
            ax3.loglog(radii[mask] / 1000, energies[mask], label=mat_name, linewidth=2, color=color, alpha=0.7)
        ax3.set_xlabel('Radius (μm)', fontsize=12)
        ax3.set_ylabel('Normalized Energy Deposition (log)', fontsize=12)
        ax3.set_title('PSF Comparison - Log Scale (Tail Analysis)', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, which='both', alpha=0.3)

        # Plot 4: Ratio plot (relative to first material)
        ax4 = axes[1, 1]
        materials = list(self.psf_data.keys())
        if len(materials) >= 2:
            baseline_mat = materials[0]
            baseline_radii, baseline_energies = self.psf_data[baseline_mat]

            for mat_name in materials[1:]:
                radii, energies = self.psf_data[mat_name]
                # Interpolate to baseline radii for comparison
                energies_interp = np.interp(baseline_radii, radii, energies)
                ratio = energies_interp / (baseline_energies + 1e-20)  # Avoid division by zero
                color = colors.get(mat_name, 'black')
                ax4.semilogx(baseline_radii / 1000, ratio, label=f'{mat_name}/{baseline_mat}',
                           linewidth=2, color=color, alpha=0.7)

            ax4.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5, label='Baseline')
            ax4.set_xlabel('Radius (μm)', fontsize=12)
            ax4.set_ylabel(f'Energy Ratio (relative to {baseline_mat})', fontsize=12)
            ax4.set_title('Material Ratio Analysis', fontsize=14, fontweight='bold')
            ax4.legend(fontsize=10)
            ax4.grid(True, alpha=0.3)
            ax4.set_ylim(0, 5)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved comparison plot to {output_path}")

        plt.savefig('psf_physics_verification.png', dpi=300, bbox_inches='tight')
        print("✓ Saved plot as psf_physics_verification.png")

        # Don't show in headless environment
        # plt.show()
        plt.close()

    def generate_report(self, output_path: Path = None) -> str:
        """Generate detailed text report"""
        metrics = self.calculate_metrics()

        report = []
        report.append("="*80)
        report.append("PSF PHYSICS VERIFICATION REPORT")
        report.append("="*80)
        report.append(f"Analysis Date: 2025-11-19")
        report.append(f"Materials Analyzed: {len(self.psf_data)}")
        report.append("")

        # Individual material metrics
        report.append("INDIVIDUAL MATERIAL METRICS:")
        report.append("-" * 80)
        for mat_name, mat_metrics in metrics.items():
            report.append(f"\n{mat_name}:")
            report.append(f"  Peak Energy: {mat_metrics['peak_energy']:.6f}")
            report.append(f"  Peak Radius: {mat_metrics['peak_radius_nm']:.2f} nm")
            report.append(f"  FWHM: {mat_metrics['fwhm_nm']:.2f} nm")
            report.append(f"  Tail Extent (>1% peak): {mat_metrics['tail_extent_nm']:.0f} nm")
            report.append(f"  Energy at 50 nm: {mat_metrics['energy_at_50nm']:.6f}")
            report.append(f"  Energy at 500 nm: {mat_metrics['energy_at_500nm']:.6f}")
            report.append(f"  Energy at 2 μm: {mat_metrics['energy_at_2um']:.6e}")
            report.append(f"  Energy at 10 μm: {mat_metrics['energy_at_10um']:.6e}")
            report.append(f"  Integrated Energy: {mat_metrics['integrated_energy']:.6f}")

        # Comparative analysis
        if len(metrics) >= 2:
            materials = list(metrics.keys())
            baseline = materials[0]
            comparisons = self.compare_materials(baseline)

            report.append(f"\n\nCOMPARATIVE ANALYSIS (relative to {baseline}):")
            report.append("-" * 80)

            for mat_name, comp in comparisons.items():
                report.append(f"\n{mat_name} vs {baseline}:")
                report.append(f"  Peak ratio: {comp['peak_ratio']:.3f}×")
                report.append(f"  FWHM ratio: {comp['fwhm_ratio']:.3f}×")
                report.append(f"  Tail extent ratio: {comp['tail_ratio']:.3f}×")
                report.append(f"  Energy ratio at 50 nm: {comp['energy_ratio_50nm']:.3f}×")
                report.append(f"  Energy ratio at 500 nm: {comp['energy_ratio_500nm']:.3f}×")
                report.append(f"  Energy ratio at 2 μm: {comp['energy_ratio_2um']:.3f}×")
                report.append(f"  Energy ratio at 10 μm: {comp['energy_ratio_10um']:.3f}×")
                report.append(f"  Integrated energy ratio: {comp['integrated_ratio']:.3f}×")

        # Physics interpretation
        report.append("\n\nPHYSICS INTERPRETATION:")
        report.append("-" * 80)
        report.append("Expected behavior for high-Z materials (Sn-MLD):")
        report.append("  • HIGHER energy in core region (Auger electron cascade)")
        report.append("  • WIDER core (increased backscattering, Z² dependence)")
        report.append("  • THICKER tails (X-ray fluorescence transport)")
        report.append("")
        report.append("If high-Z shows 2-20× higher energy at 0.5-5 μm:")
        report.append("  ➜ Physics is CORRECT - Auger and fluorescence working as expected")
        report.append("")
        report.append("If all materials show similar anomalous increases:")
        report.append("  ➜ Possible normalization bug - investigate energy accounting")

        report.append("\n" + "="*80)

        report_text = "\n".join(report)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
            print(f"✓ Saved report to {output_path}")

        return report_text


def main():
    """Main analysis function"""
    analyzer = PSFAnalyzer()

    # Find PSF files
    script_dir = Path(__file__).parent
    gui_dir = script_dir.parent / 'gui'

    # Load available PSF files
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

    print(f"\n✓ Loaded {loaded_count} PSF files")

    # Generate analysis
    print("\nGenerating analysis...")
    analyzer.plot_comparison()
    report = analyzer.generate_report(script_dir / 'psf_physics_verification_report.txt')

    print("\n" + report)

    return 0


if __name__ == '__main__':
    exit(main())
