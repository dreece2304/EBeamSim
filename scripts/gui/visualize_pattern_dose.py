#!/usr/bin/env python3
"""
Pattern Dose Visualization Tool
Visualizes dose distribution from pattern exposure simulations
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
from pathlib import Path
import sys
from scipy.ndimage import gaussian_filter


class PatternDoseVisualizer:
    def __init__(self, dose_file, dose_2d_file=None):
        """Initialize with dose distribution files"""
        self.dose_file = dose_file
        self.dose_2d_file = dose_2d_file
        self.data_3d = None
        self.data_2d = None
        
    def load_data(self):
        """Load dose distribution data"""
        print(f"Loading 3D dose data from: {self.dose_file}")
        
        # Load 3D data
        try:
            self.data_3d = pd.read_csv(self.dose_file, comment='#')
            print(f"Loaded {len(self.data_3d)} data points")
            
            # Check columns
            expected_cols = ['X[nm]', 'Y[nm]', 'Z[nm]', 'Energy[keV]', 'Dose[uC/cm^2]']
            if not all(col in self.data_3d.columns for col in expected_cols):
                print(f"Warning: Expected columns {expected_cols}, got {list(self.data_3d.columns)}")
        except Exception as e:
            print(f"Error loading 3D data: {e}")
            return False
            
        # Load 2D data if available
        if self.dose_2d_file and Path(self.dose_2d_file).exists():
            try:
                self.data_2d = pd.read_csv(self.dose_2d_file, comment='#')
                print(f"Loaded 2D projection data")
            except Exception as e:
                print(f"Warning: Could not load 2D data: {e}")
                
        return True
        
    def create_2d_grid(self, z_slice=None):
        """Create 2D grid from 3D data for a specific Z slice"""
        if self.data_3d is None:
            return None, None, None
            
        # Filter for specific Z slice if requested
        if z_slice is not None:
            z_values = self.data_3d['Z[nm]'].unique()
            closest_z = z_values[np.argmin(np.abs(z_values - z_slice))]
            data = self.data_3d[self.data_3d['Z[nm]'] == closest_z].copy()
            print(f"Using Z slice at {closest_z:.1f} nm")
        else:
            # Use 2D projection data if available
            if self.data_2d is not None:
                data = self.data_2d.copy()
            else:
                # Sum over all Z
                data = self.data_3d.groupby(['X[nm]', 'Y[nm]'])[['Energy[keV]', 'Dose[uC/cm^2]']].sum().reset_index()
                
        # Get unique coordinates
        x_unique = np.sort(data['X[nm]'].unique())
        y_unique = np.sort(data['Y[nm]'].unique())
        
        # Create meshgrid
        X, Y = np.meshgrid(x_unique, y_unique)
        
        # Create dose grid
        dose_grid = np.zeros_like(X)
        
        for i, y in enumerate(y_unique):
            for j, x in enumerate(x_unique):
                mask = (data['X[nm]'] == x) & (data['Y[nm]'] == y)
                if mask.any():
                    dose_grid[i, j] = data.loc[mask, 'Dose[uC/cm^2]'].iloc[0]
                    
        return X, Y, dose_grid
        
    def plot_2d_dose(self, ax=None, z_slice=None, colormap='viridis', log_scale=False):
        """Plot 2D dose distribution"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
            
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
            return ax
            
        # Apply log scale if requested
        if log_scale and dose.max() > 0:
            dose_plot = np.log10(dose + 1e-10)  # Add small value to avoid log(0)
            label = 'log10(Dose) [uC/cm^2]'
        else:
            dose_plot = dose
            label = 'Dose [uC/cm^2]'
            
        # Create heatmap
        im = ax.pcolormesh(X, Y, dose_plot, cmap=colormap, shading='auto')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(label)
        
        # Labels and title
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        
        if z_slice is not None:
            ax.set_title(f'Dose Distribution at Z = {z_slice:.1f} nm')
        else:
            ax.set_title('Integrated Dose Distribution (XY projection)')
            
        ax.set_aspect('equal')
        
        # Add pattern statistics
        if dose.max() > 0:
            stats_text = f'Max: {dose.max():.1f} uC/cm^2\nMin: {dose.min():.1f} uC/cm^2'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        return ax
        
    def plot_line_profiles(self, ax=None):
        """Plot line profiles through the center"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
            
        X, Y, dose = self.create_2d_grid()
        
        if dose is None:
            return ax
            
        # Get center indices
        center_y = len(Y) // 2
        center_x = len(X[0]) // 2
        
        # Extract line profiles
        x_profile = dose[center_y, :]
        y_profile = dose[:, center_x]
        
        # Plot profiles
        ax.plot(X[0, :], x_profile, 'b-', label='X profile (Y=0)', linewidth=2)
        ax.plot(Y[:, 0], y_profile, 'r-', label='Y profile (X=0)', linewidth=2)
        
        ax.set_xlabel('Position [nm]')
        ax.set_ylabel('Dose [uC/cm^2]')
        ax.set_title('Dose Line Profiles Through Pattern Center')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return ax
        
    def plot_3d_surface(self, ax=None, z_slice=None):
        """Plot 3D surface of dose distribution"""
        if ax is None:
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            return ax
            
        # Downsample for 3D plot if needed
        step = max(1, len(X) // 50)
        X_down = X[::step, ::step]
        Y_down = Y[::step, ::step]
        dose_down = dose[::step, ::step]
        
        # Create surface plot
        surf = ax.plot_surface(X_down, Y_down, dose_down, cmap='viridis', 
                              edgecolor='none', alpha=0.8)
        
        # Add colorbar
        plt.colorbar(surf, ax=ax, label='Dose [uC/cm^2]', shrink=0.5)
        
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_zlabel('Dose [uC/cm^2]')
        ax.set_title('3D Dose Distribution')
        
        return ax
        
    def plot_contour(self, ax=None, z_slice=None, levels=20):
        """Plot contour map of dose distribution"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
            
        X, Y, dose = self.create_2d_grid(z_slice)
        
        if dose is None:
            return ax
            
        # Apply slight smoothing for better contours
        dose_smooth = gaussian_filter(dose, sigma=0.5)
        
        # Create filled contour plot
        contourf = ax.contourf(X, Y, dose_smooth, levels=levels, cmap='viridis', alpha=0.7)
        
        # Add contour lines
        contour = ax.contour(X, Y, dose_smooth, levels=levels, colors='black', 
                            alpha=0.4, linewidths=0.5)
        
        # Label every other contour
        ax.clabel(contour, contour.levels[::2], inline=True, fontsize=8, fmt='%.0f')
        
        # Colorbar
        cbar = plt.colorbar(contourf, ax=ax)
        cbar.set_label('Dose [uC/cm^2]')
        
        ax.set_xlabel('X [nm]')
        ax.set_ylabel('Y [nm]')
        ax.set_title('Dose Distribution Contours')
        ax.set_aspect('equal')
        
        return ax
        
    def create_interactive_viewer(self):
        """Create interactive viewer with multiple plot types"""
        fig = plt.figure(figsize=(12, 8))
        
        # Main plot area
        ax_main = plt.subplot2grid((3, 3), (0, 0), colspan=2, rowspan=2)
        
        # Controls area
        ax_controls = plt.subplot2grid((3, 3), (2, 0), colspan=3)
        ax_controls.axis('off')
        
        # Radio buttons for plot type
        ax_radio = plt.subplot2grid((3, 3), (0, 2), rowspan=2)
        radio = RadioButtons(ax_radio, ('2D Heatmap', 'Contour', 'Line Profiles'))
        
        # Get Z range
        z_values = self.data_3d['Z[nm]'].unique() if self.data_3d is not None else [0]
        z_min, z_max = z_values.min(), z_values.max()
        
        # Z-slice slider
        if z_max > z_min:
            ax_z_slider = plt.axes([0.2, 0.02, 0.5, 0.03])
            z_slider = Slider(ax_z_slider, 'Z [nm]', z_min, z_max, 
                             valinit=(z_min + z_max)/2, valstep=z_values[1]-z_values[0])
        else:
            z_slider = None
            
        # Update function
        def update(val=None):
            ax_main.clear()
            
            plot_type = radio.value_selected
            z_slice = z_slider.val if z_slider else None
            
            if plot_type == '2D Heatmap':
                self.plot_2d_dose(ax_main, z_slice=z_slice)
            elif plot_type == 'Contour':
                self.plot_contour(ax_main, z_slice=z_slice)
            elif plot_type == 'Line Profiles':
                self.plot_line_profiles(ax_main)
                
            plt.draw()
            
        # Connect events
        radio.on_clicked(update)
        if z_slider:
            z_slider.on_changed(update)
            
        # Initial plot
        update()
        
        plt.tight_layout()
        return fig


def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python visualize_pattern_dose.py <dose_file.csv> [dose_2d_file.csv]")
        print("\nExample:")
        print("  python visualize_pattern_dose.py pattern_dose_distribution.csv pattern_dose_2d.csv")
        sys.exit(1)
        
    dose_file = sys.argv[1]
    dose_2d_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create visualizer
    viz = PatternDoseVisualizer(dose_file, dose_2d_file)
    
    # Load data
    if not viz.load_data():
        print("Failed to load data")
        sys.exit(1)
        
    # Create interactive viewer
    fig = viz.create_interactive_viewer()
    
    # Also create static plots
    fig2, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    viz.plot_2d_dose(axes[0, 0])
    viz.plot_contour(axes[0, 1])
    viz.plot_line_profiles(axes[1, 0])
    viz.plot_3d_surface(axes[1, 1])
    
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()