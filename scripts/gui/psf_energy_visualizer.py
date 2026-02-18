#!/usr/bin/env python3
"""
PSF Energy Profile Visualizer

Creates 1D, 2D, and 3D visualizations of energy deposition profiles
through resist layers from PSF simulation data.

All profiles are normalized for comparison across different materials.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
from typing import Optional, Tuple, List
import argparse


class PSFEnergyVisualizer:
    """Visualize PSF energy deposition profiles in 1D, 2D, and 3D"""

    def __init__(self, material: str = "Unknown", energy_kev: float = 100.0):
        """
        Args:
            material: Material name for labeling
            energy_kev: Beam energy in keV
        """
        self.material = material
        self.energy_kev = energy_kev
        self.data_1d = None
        self.data_2d = None
        self.resist_thickness = 100.0  # nm, default

    def load_psf_1d(self, csv_path: str) -> bool:
        """Load 1D radial PSF data"""
        try:
            self.data_1d = pd.read_csv(csv_path)
            # Expected columns: radius_nm, energy_keV/nm (or similar)
            print(f"Loaded 1D PSF: {csv_path}")
            print(f"  Columns: {list(self.data_1d.columns)}")
            print(f"  Shape: {self.data_1d.shape}")
            return True
        except Exception as e:
            print(f"Error loading 1D PSF: {e}")
            return False

    def load_psf_2d(self, csv_path: str) -> bool:
        """Load 2D (r, z) PSF data"""
        try:
            self.data_2d = pd.read_csv(csv_path)
            # Expected columns: radius_nm, depth_nm, energy_keV/nm3
            print(f"Loaded 2D PSF: {csv_path}")
            print(f"  Columns: {list(self.data_2d.columns)}")
            print(f"  Shape: {self.data_2d.shape}")
            return True
        except Exception as e:
            print(f"Error loading 2D PSF: {e}")
            return False

    def normalize_data(self, data: np.ndarray, method: str = "max") -> np.ndarray:
        """
        Normalize energy data for comparison

        Args:
            data: Energy data array
            method: 'max' (0-1), 'sum' (integrate to 1), or 'log' (log scale)
        """
        if method == "max":
            max_val = np.max(data)
            return data / max_val if max_val > 0 else data
        elif method == "sum":
            total = np.sum(data)
            return data / total if total > 0 else data
        elif method == "log":
            # Log scale with floor
            data_safe = np.maximum(data, 1e-10)
            return np.log10(data_safe)
        return data

    def plot_1d_radial(self, output_file: Optional[str] = None,
                       normalize: bool = True,
                       log_scale: bool = False) -> plt.Figure:
        """
        Create 1D radial energy profile plot

        Shows energy deposition vs. radial distance from beam center.
        """
        if self.data_1d is None:
            raise ValueError("No 1D data loaded. Call load_psf_1d first.")

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')

        # Determine column names (handle various formats)
        radius_col = None
        energy_col = None
        for col in self.data_1d.columns:
            if 'radius' in col.lower() or col.lower() == 'r':
                radius_col = col
            elif 'energy' in col.lower() or 'dose' in col.lower() or 'psf' in col.lower():
                energy_col = col

        if radius_col is None:
            radius_col = self.data_1d.columns[0]
        if energy_col is None:
            energy_col = self.data_1d.columns[1]

        r = self.data_1d[radius_col].values
        energy = self.data_1d[energy_col].values

        if normalize:
            energy = self.normalize_data(energy, "max")
            ylabel = "Normalized Energy Deposition"
        else:
            ylabel = "Energy Deposition (keV/nm)"

        if log_scale:
            ax.semilogy(r, energy, 'b-', linewidth=2, label=self.material)
        else:
            ax.plot(r, energy, 'b-', linewidth=2, label=self.material)

        ax.set_xlabel('Radial Distance (nm)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(f'1D Radial PSF - {self.material} @ {self.energy_kev:.0f} keV',
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Add resist region indicator
        ax.axvline(x=0, color='r', linestyle='--', alpha=0.5, label='Beam center')

        plt.tight_layout()

        if output_file:
            fig.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Saved 1D plot: {output_file}")

        return fig

    def plot_2d_contour(self, output_file: Optional[str] = None,
                        normalize: bool = True,
                        log_scale: bool = True) -> plt.Figure:
        """
        Create 2D contour plot of energy deposition (r vs z)

        Shows energy deposition as a function of radial distance and depth.
        """
        if self.data_2d is None:
            raise ValueError("No 2D data loaded. Call load_psf_2d first.")

        fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')

        # Get column names
        r_col = None
        z_col = None
        e_col = None

        for col in self.data_2d.columns:
            col_lower = col.lower()
            if 'radius' in col_lower or col_lower == 'r':
                r_col = col
            elif 'depth' in col_lower or col_lower == 'z':
                z_col = col
            elif 'energy' in col_lower or 'dose' in col_lower:
                e_col = col

        if r_col is None:
            r_col = self.data_2d.columns[0]
        if z_col is None:
            z_col = self.data_2d.columns[1]
        if e_col is None:
            e_col = self.data_2d.columns[2]

        # Create 2D grid from data
        r_unique = np.sort(self.data_2d[r_col].unique())
        z_unique = np.sort(self.data_2d[z_col].unique())

        # Pivot to create 2D array
        pivot_df = self.data_2d.pivot_table(index=z_col, columns=r_col, values=e_col, aggfunc='mean')
        energy_2d = pivot_df.values
        R, Z = np.meshgrid(r_unique, z_unique)

        if normalize:
            energy_2d = self.normalize_data(energy_2d, "max")

        if log_scale:
            energy_2d = np.log10(np.maximum(energy_2d, 1e-10))
            cbar_label = "log10(Normalized Energy)"
        else:
            cbar_label = "Normalized Energy Deposition"

        # Create contour plot
        levels = 50
        contour = ax.contourf(R, Z, energy_2d, levels=levels, cmap='plasma')
        cbar = plt.colorbar(contour, ax=ax, shrink=0.8)
        cbar.set_label(cbar_label, fontsize=11)

        # Mark resist boundaries
        ax.axhline(y=0, color='cyan', linestyle='--', linewidth=2, alpha=0.7, label='Resist surface')
        ax.axhline(y=self.resist_thickness, color='cyan', linestyle='--', linewidth=2, alpha=0.7, label='Substrate')

        ax.set_xlabel('Radial Distance (nm)', fontsize=12)
        ax.set_ylabel('Depth (nm)', fontsize=12)
        ax.set_title(f'2D PSF Energy Profile - {self.material} @ {self.energy_kev:.0f} keV',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')

        # Invert y-axis to show depth increasing downward
        ax.invert_yaxis()

        plt.tight_layout()

        if output_file:
            fig.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Saved 2D plot: {output_file}")

        return fig

    def plot_3d_surface(self, output_file: Optional[str] = None,
                        normalize: bool = True,
                        view_angle: Tuple[float, float] = (30, 45)) -> plt.Figure:
        """
        Create 3D surface plot of energy deposition

        Shows energy as z-height over the r-z plane.
        """
        if self.data_2d is None:
            raise ValueError("No 2D data loaded. Call load_psf_2d first.")

        fig = plt.figure(figsize=(12, 9), facecolor='white')
        ax = fig.add_subplot(111, projection='3d')

        # Get column names
        r_col = self.data_2d.columns[0]
        z_col = self.data_2d.columns[1]
        e_col = self.data_2d.columns[2]

        for col in self.data_2d.columns:
            col_lower = col.lower()
            if 'radius' in col_lower or col_lower == 'r':
                r_col = col
            elif 'depth' in col_lower or col_lower == 'z':
                z_col = col
            elif 'energy' in col_lower or 'dose' in col_lower:
                e_col = col

        # Create 2D grid
        r_unique = np.sort(self.data_2d[r_col].unique())
        z_unique = np.sort(self.data_2d[z_col].unique())

        pivot_df = self.data_2d.pivot_table(index=z_col, columns=r_col, values=e_col, aggfunc='mean')
        energy_2d = pivot_df.values
        R, Z = np.meshgrid(r_unique, z_unique)

        if normalize:
            energy_2d = self.normalize_data(energy_2d, "max")

        # Create 3D surface
        surf = ax.plot_surface(R, Z, energy_2d, cmap='plasma',
                               edgecolor='none', alpha=0.9)

        cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
        cbar.set_label('Normalized Energy', fontsize=11)

        ax.set_xlabel('Radial Distance (nm)', fontsize=11)
        ax.set_ylabel('Depth (nm)', fontsize=11)
        ax.set_zlabel('Energy Deposition', fontsize=11)
        ax.set_title(f'3D PSF Energy Surface - {self.material} @ {self.energy_kev:.0f} keV',
                    fontsize=14, fontweight='bold')

        ax.view_init(elev=view_angle[0], azim=view_angle[1])

        if output_file:
            fig.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Saved 3D plot: {output_file}")

        return fig

    def plot_depth_profile(self, output_file: Optional[str] = None,
                          normalize: bool = True) -> plt.Figure:
        """
        Create 1D depth profile (integrated over radius)

        Shows energy deposition as a function of depth through the resist.
        """
        if self.data_2d is None:
            raise ValueError("No 2D data loaded. Call load_psf_2d first.")

        fig, ax = plt.subplots(figsize=(8, 10), facecolor='white')

        # Get column names
        z_col = None
        e_col = None

        for col in self.data_2d.columns:
            col_lower = col.lower()
            if 'depth' in col_lower or col_lower == 'z':
                z_col = col
            elif 'energy' in col_lower or 'dose' in col_lower:
                e_col = col

        if z_col is None:
            z_col = self.data_2d.columns[1]
        if e_col is None:
            e_col = self.data_2d.columns[2]

        # Integrate energy over radius at each depth
        depth_profile = self.data_2d.groupby(z_col)[e_col].sum()
        depths = depth_profile.index.values
        energy = depth_profile.values

        if normalize:
            energy = self.normalize_data(energy, "max")
            xlabel = "Normalized Energy Deposition"
        else:
            xlabel = "Energy Deposition (keV/nm)"

        # Plot horizontally (depth on y-axis)
        ax.plot(energy, depths, 'b-', linewidth=2.5, label=self.material)
        ax.fill_betweenx(depths, 0, energy, alpha=0.3)

        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel('Depth (nm)', fontsize=12)
        ax.set_title(f'Depth Profile - {self.material} @ {self.energy_kev:.0f} keV',
                    fontsize=14, fontweight='bold')

        # Mark resist boundaries
        ax.axhline(y=0, color='cyan', linestyle='--', linewidth=2, alpha=0.7)
        ax.axhline(y=self.resist_thickness, color='cyan', linestyle='--', linewidth=2, alpha=0.7)
        ax.text(ax.get_xlim()[1] * 0.95, self.resist_thickness / 2, self.material,
               ha='right', va='center', fontsize=11, fontweight='bold', color='blue')
        ax.text(ax.get_xlim()[1] * 0.95, self.resist_thickness + 50, 'Substrate',
               ha='right', va='center', fontsize=11, color='gray')

        ax.invert_yaxis()  # Depth increases downward
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()

        if output_file:
            fig.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Saved depth profile: {output_file}")

        return fig

    def create_all_plots(self, output_dir: str) -> List[str]:
        """Create all visualization types and save to output directory"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        base_name = f"{self.material}_{int(self.energy_kev)}keV"

        if self.data_1d is not None:
            f1 = str(output_dir / f"{base_name}_1d_radial.png")
            self.plot_1d_radial(f1)
            created_files.append(f1)
            plt.close()

        if self.data_2d is not None:
            # 2D contour
            f2 = str(output_dir / f"{base_name}_2d_contour.png")
            self.plot_2d_contour(f2)
            created_files.append(f2)
            plt.close()

            # 3D surface
            f3 = str(output_dir / f"{base_name}_3d_surface.png")
            self.plot_3d_surface(f3)
            created_files.append(f3)
            plt.close()

            # Depth profile
            f4 = str(output_dir / f"{base_name}_depth_profile.png")
            self.plot_depth_profile(f4)
            created_files.append(f4)
            plt.close()

        return created_files


def compare_materials(psf_data: dict, output_file: Optional[str] = None,
                     normalize: bool = True) -> plt.Figure:
    """
    Compare 1D PSF profiles from multiple materials

    Args:
        psf_data: Dict of {material_name: (radius_array, energy_array)}
        output_file: Optional output filename
        normalize: Whether to normalize each profile
    """
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')

    colors = plt.cm.Set1(np.linspace(0, 1, len(psf_data)))

    for i, (material, (r, energy)) in enumerate(psf_data.items()):
        if normalize:
            energy = energy / np.max(energy) if np.max(energy) > 0 else energy

        ax.semilogy(r, energy, linewidth=2, color=colors[i], label=material)

    ax.set_xlabel('Radial Distance (nm)', fontsize=12)
    ax.set_ylabel('Normalized Energy Deposition', fontsize=12)
    ax.set_title('PSF Comparison - 100 keV Metalcone Resists', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=11)

    plt.tight_layout()

    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved comparison plot: {output_file}")

    return fig


def visualize_psf_results(psf_dir: str, output_dir: str):
    """
    Visualize all PSF results in a directory

    Args:
        psf_dir: Directory containing PSF CSV files
        output_dir: Directory to save visualization plots
    """
    psf_dir = Path(psf_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find PSF files
    psf_files = list(psf_dir.glob("psf_*.csv"))
    psf2d_files = list(psf_dir.glob("psf2d_*.csv"))

    print(f"Found {len(psf_files)} 1D PSF files, {len(psf2d_files)} 2D PSF files")

    all_1d_data = {}

    for psf_file in psf_files:
        # Parse material and energy from filename
        # Expected format: psf_Material_EnergykeV.csv
        parts = psf_file.stem.split('_')
        if len(parts) >= 3:
            material = parts[1]
            energy_str = parts[2].replace('keV', '')
            try:
                energy = float(energy_str)
            except:
                energy = 100.0
        else:
            material = "Unknown"
            energy = 100.0

        vis = PSFEnergyVisualizer(material=material, energy_kev=energy)

        # Load 1D data
        if vis.load_psf_1d(str(psf_file)):
            # Store for comparison
            r_col = vis.data_1d.columns[0]
            e_col = vis.data_1d.columns[1]
            all_1d_data[material] = (vis.data_1d[r_col].values, vis.data_1d[e_col].values)

        # Check for corresponding 2D file
        psf2d_file = psf_dir / f"psf2d_{material}_{int(energy)}keV.csv"
        if psf2d_file.exists():
            vis.load_psf_2d(str(psf2d_file))

        # Create all plots
        material_output = output_dir / material
        vis.create_all_plots(str(material_output))

    # Create comparison plot if we have multiple materials
    if len(all_1d_data) > 1:
        compare_materials(all_1d_data, str(output_dir / "comparison_all_materials.png"))
        plt.close()

    print(f"\nVisualization complete! Output saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Visualize PSF energy profiles')
    parser.add_argument('--psf-dir', '-d', default='./psf_output',
                       help='Directory containing PSF CSV files')
    parser.add_argument('--output-dir', '-o', default='./psf_visualizations',
                       help='Output directory for plots')
    parser.add_argument('--single', '-s', type=str, default=None,
                       help='Visualize a single PSF file (1D CSV)')
    parser.add_argument('--single-2d', type=str, default=None,
                       help='2D PSF file to accompany single 1D file')
    parser.add_argument('--material', '-m', default='Unknown',
                       help='Material name for single file mode')
    parser.add_argument('--energy', '-e', type=float, default=100.0,
                       help='Beam energy in keV')

    args = parser.parse_args()

    if args.single:
        # Single file mode
        vis = PSFEnergyVisualizer(material=args.material, energy_kev=args.energy)
        vis.load_psf_1d(args.single)
        if args.single_2d:
            vis.load_psf_2d(args.single_2d)
        vis.create_all_plots(args.output_dir)
    else:
        # Batch mode - process all files in directory
        visualize_psf_results(args.psf_dir, args.output_dir)


if __name__ == "__main__":
    main()
