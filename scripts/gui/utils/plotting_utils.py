"""
Plotting utilities for EBL simulation GUI
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm
import matplotlib.cm as cm
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd


class PlottingUtils:
    """Utility functions for plotting and visualization"""
    
    @staticmethod
    def setup_matplotlib_style():
        """Set up consistent matplotlib styling"""
        plt.style.use('default')
        plt.rcParams.update({
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 14,
            'lines.linewidth': 1.5,
            'axes.grid': True,
            'grid.alpha': 0.3
        })
    
    @staticmethod
    def create_psf_plot(
        radius: np.ndarray, 
        intensity: np.ndarray,
        scale: str = 'log',
        title: str = "PSF Profile"
    ) -> Figure:
        """Create 1D PSF profile plot"""
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        if scale == 'log':
            ax.loglog(radius, intensity, 'b-', linewidth=2)
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Intensity (log scale)')
        elif scale == 'semilog':
            ax.semilogy(radius, intensity, 'b-', linewidth=2)
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Intensity (log scale)')
        else:
            ax.plot(radius, intensity, 'b-', linewidth=2)
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Intensity')
        
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        
        return fig
    
    @staticmethod
    def create_2d_psf_plot(
        radius: np.ndarray,
        depth: np.ndarray, 
        intensity: np.ndarray,
        plot_type: str = 'heatmap',
        title: str = "2D PSF"
    ) -> Figure:
        """Create 2D PSF visualization"""
        fig = Figure(figsize=(10, 8))
        
        if plot_type == 'heatmap':
            ax = fig.add_subplot(111)
            
            # Create regular grid for plotting
            radius_grid, depth_grid, intensity_grid = PlottingUtils._create_regular_grid(
                radius, depth, intensity
            )
            
            im = ax.pcolormesh(
                radius_grid, depth_grid, intensity_grid,
                cmap='viridis', norm=LogNorm(vmin=intensity_grid[intensity_grid > 0].min())
            )
            
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Depth (nm)')
            ax.set_title(title)
            
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Intensity')
            
        elif plot_type == 'contour':
            ax = fig.add_subplot(111)
            
            radius_grid, depth_grid, intensity_grid = PlottingUtils._create_regular_grid(
                radius, depth, intensity
            )
            
            levels = np.logspace(
                np.log10(intensity_grid[intensity_grid > 0].min()),
                np.log10(intensity_grid.max()),
                20
            )
            
            cs = ax.contour(radius_grid, depth_grid, intensity_grid, levels=levels, cmap='viridis')
            ax.clabel(cs, inline=True, fontsize=8)
            
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Depth (nm)')
            ax.set_title(title)
        
        elif plot_type == '3d':
            ax = fig.add_subplot(111, projection='3d')
            
            # Subsample for 3D plot performance
            step = max(1, len(radius) // 1000)
            r_sub = radius[::step]
            d_sub = depth[::step]
            i_sub = intensity[::step]
            
            ax.scatter(r_sub, d_sub, i_sub, c=i_sub, cmap='viridis', s=1)
            
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Depth (nm)')
            ax.set_zlabel('Intensity')
            ax.set_title(title)
        
        fig.tight_layout()
        return fig
    
    @staticmethod
    def _create_regular_grid(
        radius: np.ndarray, 
        depth: np.ndarray, 
        intensity: np.ndarray,
        grid_size: Tuple[int, int] = (100, 100)
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Create regular grid from scattered data"""
        from scipy.interpolate import griddata
        
        # Create regular grid
        r_min, r_max = radius.min(), radius.max()
        d_min, d_max = depth.min(), depth.max()
        
        r_grid = np.linspace(r_min, r_max, grid_size[0])
        d_grid = np.linspace(d_min, d_max, grid_size[1])
        
        R_grid, D_grid = np.meshgrid(r_grid, d_grid)
        
        # Interpolate intensity onto regular grid
        points = np.column_stack((radius, depth))
        I_grid = griddata(points, intensity, (R_grid, D_grid), method='linear', fill_value=0)
        
        return R_grid, D_grid, I_grid
    
    @staticmethod
    def create_comparison_plot(
        datasets: List[Dict[str, Any]], 
        scale: str = 'log'
    ) -> Figure:
        """Create comparison plot of multiple PSF datasets"""
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        
        for i, dataset in enumerate(datasets):
            radius = dataset['radius']
            intensity = dataset['intensity']
            label = dataset.get('label', f'Dataset {i+1}')
            color = colors[i % len(colors)]
            
            if scale == 'log':
                ax.loglog(radius, intensity, color=color, label=label, linewidth=2)
            elif scale == 'semilog':
                ax.semilogy(radius, intensity, color=color, label=label, linewidth=2)
            else:
                ax.plot(radius, intensity, color=color, label=label, linewidth=2)
        
        ax.set_xlabel('Radius (nm)')
        ax.set_ylabel('Intensity')
        ax.set_title('PSF Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        fig.tight_layout()
        return fig
    
    @staticmethod
    def create_cross_section_plot(
        radius: np.ndarray,
        depth: np.ndarray,
        intensity: np.ndarray,
        cross_section_type: str = 'radial',
        position: float = 0.0
    ) -> Figure:
        """Create cross-section plot from 2D data"""
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        df = pd.DataFrame({
            'radius': radius,
            'depth': depth,
            'intensity': intensity
        })
        
        if cross_section_type == 'radial':
            # Cross-section at specific depth
            tolerance = (depth.max() - depth.min()) * 0.05
            mask = np.abs(df['depth'] - position) <= tolerance
            subset = df[mask].sort_values('radius')
            
            ax.plot(subset['radius'], subset['intensity'], 'b-', linewidth=2)
            ax.set_xlabel('Radius (nm)')
            ax.set_ylabel('Intensity')
            ax.set_title(f'Radial Cross-section at Depth = {position:.1f} nm')
            
        elif cross_section_type == 'depth':
            # Cross-section at specific radius
            tolerance = (radius.max() - radius.min()) * 0.05
            mask = np.abs(df['radius'] - position) <= tolerance
            subset = df[mask].sort_values('depth')
            
            ax.plot(subset['depth'], subset['intensity'], 'r-', linewidth=2)
            ax.set_xlabel('Depth (nm)')
            ax.set_ylabel('Intensity')
            ax.set_title(f'Depth Cross-section at Radius = {position:.1f} nm')
        
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig
    
    @staticmethod
    def apply_colormap(values: np.ndarray, colormap: str = 'viridis') -> np.ndarray:
        """Apply colormap to values"""
        cmap = cm.get_cmap(colormap)
        normalized = (values - values.min()) / (values.max() - values.min())
        return cmap(normalized)
    
    @staticmethod
    def export_plot(fig: Figure, output_path: str, dpi: int = 300, format: str = 'png'):
        """Export plot to file"""
        fig.savefig(output_path, dpi=dpi, format=format, bbox_inches='tight')
    
    @staticmethod
    def get_available_colormaps() -> List[str]:
        """Get list of available colormaps"""
        return [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis',
            'jet', 'hot', 'cool', 'spring', 'summer', 'autumn', 'winter',
            'Greys', 'Blues', 'Reds', 'Greens', 'Oranges', 'Purples'
        ]
    
    @staticmethod
    def get_plot_statistics(radius: np.ndarray, intensity: np.ndarray) -> Dict[str, float]:
        """Calculate plot statistics"""
        valid_mask = (intensity > 0) & np.isfinite(intensity)
        valid_radius = radius[valid_mask]
        valid_intensity = intensity[valid_mask]
        
        if len(valid_intensity) == 0:
            return {}
        
        # Calculate FWHM (Full Width Half Maximum)
        max_intensity = valid_intensity.max()
        half_max = max_intensity / 2.0
        
        fwhm_mask = valid_intensity >= half_max
        if np.any(fwhm_mask):
            fwhm_radius = valid_radius[fwhm_mask]
            fwhm = fwhm_radius.max() - fwhm_radius.min()
        else:
            fwhm = 0.0
        
        return {
            'max_intensity': max_intensity,
            'max_radius': valid_radius.max(),
            'fwhm': fwhm,
            'total_energy': np.trapz(valid_intensity, valid_radius),
            'mean_radius': np.average(valid_radius, weights=valid_intensity),
            'num_points': len(valid_intensity)
        }