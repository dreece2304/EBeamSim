#!/usr/bin/env python3
"""
EBL Electron Trajectory Animator
Creates animations of electron paths through resist and substrate
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for headless rendering
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle
from pathlib import Path
import subprocess
import re
import sys
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json


@dataclass
class TrajectoryPoint:
    x: float  # nm
    y: float  # nm
    z: float  # nm
    energy: float  # keV
    particle: str


@dataclass
class Trajectory:
    points: List[TrajectoryPoint]
    particle_type: str
    track_id: int


class ElectronAnimator:
    """Creates animations of electron trajectories in EBL simulation"""

    def __init__(self, resist_thickness: float = 100, resist_material: str = "Zincone",
                 beam_energy: float = 100, substrate_thickness: float = 500,
                 show_secondaries: bool = False):
        """
        Args:
            resist_thickness: Resist thickness in nm
            resist_material: Material name
            beam_energy: Beam energy in keV
            substrate_thickness: Substrate thickness to show in nm
            show_secondaries: Whether to show secondary electrons (not just primaries)
        """
        self.resist_thickness = resist_thickness
        self.resist_material = resist_material
        self.beam_energy = beam_energy
        self.substrate_thickness = substrate_thickness
        self.trajectories: List[Trajectory] = []
        self.use_real_data = False
        self.show_secondaries = show_secondaries

    def load_geant4_trajectories(self, json_file: str) -> bool:
        """Load trajectories from Geant4 JSON output"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            self.trajectories = []

            for event in data.get('events', []):
                tracks = event.get('tracks', {})
                for track_id, track_data in tracks.items():
                    points = []
                    particle = track_data.get('particle', 'e-')
                    raw_points = track_data.get('points', [])

                    for pt in raw_points:
                        if len(pt) >= 4:
                            points.append(TrajectoryPoint(
                                x=pt[0],
                                y=pt[1],
                                z=pt[2],
                                energy=pt[3],
                                particle=particle
                            ))

                    if points:
                        self.trajectories.append(Trajectory(
                            points=points,
                            particle_type=particle,
                            track_id=int(track_id)
                        ))

            self.use_real_data = len(self.trajectories) > 0
            print(f"Loaded {len(self.trajectories)} tracks from {json_file}")
            return self.use_real_data

        except Exception as e:
            print(f"Error loading trajectories: {e}")
            return False

    def generate_monte_carlo_trajectory(self, seed: int = None) -> Trajectory:
        """Generate a realistic Monte Carlo electron trajectory"""
        if seed is not None:
            np.random.seed(seed)

        points = []

        # Starting position - just above resist
        x, y, z = 0.0, 0.0, self.resist_thickness + 10
        energy = self.beam_energy

        # Direction (initially straight down)
        theta = 0.0  # angle from z-axis
        phi = np.random.uniform(0, 2 * np.pi)

        # Material-dependent scattering parameters
        # Effective Z weighted by mass fraction for metalcones (EG-based)
        # Zincone: 52% Zn (Z=30) + organics → Zeff ≈ 22
        # Alucone: 23% Al (Z=13) + organics → Zeff ≈ 9
        # Tincone: 50% Sn (Z=50) + organics → Zeff ≈ 30
        material_Z = {"Zincone": 22, "Alucone": 9, "Tincone": 30, "PMMA": 6, "HSQ": 14}
        Z = material_Z.get(self.resist_material, 14)

        # Higher Z = more scattering
        scatter_strength = 0.1 * (Z / 14) ** 0.5
        energy_loss_rate = 0.5 * (Z / 14) ** 0.3  # keV per nm

        step_size = 2.0  # nm per step

        while energy > 0.5 and z > -self.substrate_thickness:
            points.append(TrajectoryPoint(x, y, z, energy, "e-"))

            # Determine which material we're in
            if z > self.resist_thickness:
                # In vacuum - straight line
                in_material = False
            elif z > 0:
                # In resist
                in_material = True
                current_scatter = scatter_strength
                current_loss = energy_loss_rate
            else:
                # In substrate (silicon, Z=14)
                in_material = True
                current_scatter = 0.08
                current_loss = 0.4

            if in_material:
                # Random scattering - Rutherford-like angular distribution
                scatter_angle = np.random.exponential(current_scatter * (100 / energy) ** 0.5)
                scatter_angle = min(scatter_angle, np.pi / 2)

                # Update direction
                theta += scatter_angle * np.random.choice([-1, 1])
                theta = np.clip(theta, -np.pi/2, np.pi/2)
                phi += np.random.uniform(-0.5, 0.5)

                # Energy loss
                energy -= current_loss * step_size * np.random.uniform(0.8, 1.2)

            # Move in current direction
            dx = step_size * np.sin(theta) * np.cos(phi)
            dy = step_size * np.sin(theta) * np.sin(phi)
            dz = -step_size * np.cos(theta)  # negative because going down

            x += dx
            y += dy
            z += dz

        # Add final point
        points.append(TrajectoryPoint(x, y, z, max(0, energy), "e-"))

        return Trajectory(points=points, particle_type="e-", track_id=len(self.trajectories))

    def generate_trajectories(self, n_electrons: int = 10):
        """Generate multiple electron trajectories"""
        self.trajectories = []
        for i in range(n_electrons):
            traj = self.generate_monte_carlo_trajectory(seed=i * 42)
            self.trajectories.append(traj)

    def interpolate_trajectory(self, r_vals, z_vals, e_vals, n_points=200):
        """Interpolate trajectory for smooth animation based on path length"""
        if len(r_vals) < 2:
            return r_vals, z_vals, e_vals

        # Calculate cumulative path length
        path_lengths = [0]
        for i in range(1, len(r_vals)):
            dr = r_vals[i] - r_vals[i-1]
            dz = z_vals[i] - z_vals[i-1]
            path_lengths.append(path_lengths[-1] + np.sqrt(dr**2 + dz**2))

        total_length = path_lengths[-1]
        if total_length == 0:
            return r_vals, z_vals, e_vals

        # Interpolate uniformly along path
        uniform_lengths = np.linspace(0, total_length, n_points)
        interp_r = np.interp(uniform_lengths, path_lengths, r_vals)
        interp_z = np.interp(uniform_lengths, path_lengths, z_vals)
        interp_e = np.interp(uniform_lengths, path_lengths, e_vals)

        return list(interp_r), list(interp_z), list(interp_e)

    def create_dual_view_animation(self, output_file: str = "electron_animation.gif",
                                   fps: int = 30, duration: float = 8.0,
                                   loop: bool = False):
        """Create animation with both full view and zoomed resist region"""
        from matplotlib.collections import LineCollection

        if not self.trajectories:
            self.generate_trajectories(10)

        # Filter trajectories
        if self.use_real_data and not self.show_secondaries:
            trajs = [t for t in self.trajectories if t.track_id == 1]
            if not trajs:
                trajs = self.trajectories
            print(f"Showing {len(trajs)} primary electrons")
        else:
            trajs = self.trajectories
            if self.use_real_data:
                n_primary = len([t for t in self.trajectories if t.track_id == 1])
                print(f"Showing {n_primary} primary + {len(trajs) - n_primary} secondary electrons")

        # Prepare and interpolate trajectory data
        all_r, all_z, all_energy = [], [], []
        for traj in trajs:
            r_vals = [np.sqrt(p.x**2 + p.y**2) * np.sign(p.x + 0.001) for p in traj.points]
            z_vals = [p.z for p in traj.points]
            e_vals = [p.energy for p in traj.points]

            # Interpolate for smooth motion
            r_interp, z_interp, e_interp = self.interpolate_trajectory(r_vals, z_vals, e_vals, 200)
            all_r.append(r_interp)
            all_z.append(z_interp)
            all_energy.append(e_interp)

        # Calculate view bounds
        flat_r = [r for rs in all_r for r in rs]
        flat_z = [z for zs in all_z for z in zs]
        max_r = max(max(abs(r) for r in flat_r) * 1.1, 100)
        z_min = min(flat_z) * 1.1
        z_max = max(flat_z) * 1.1 + 20

        # Round to nice μm values for main view
        max_r = np.ceil(max_r / 1000) * 1000
        z_min = np.floor(z_min / 1000) * 1000

        # Create dual-panel figure
        fig = plt.figure(figsize=(14, 7), facecolor='#0a0a14')
        ax_main = fig.add_axes([0.05, 0.12, 0.55, 0.80])
        ax_zoom = fig.add_axes([0.65, 0.12, 0.32, 0.80])

        for ax in [ax_main, ax_zoom]:
            ax.set_facecolor('#0a0a14')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#333366')

        # Main view (full range, μm scale)
        ax_main.set_xlim(-max_r, max_r)
        ax_main.set_ylim(z_min, z_max)
        ax_main.set_xlabel('Lateral Position (μm)', color='white', fontsize=11)
        ax_main.set_ylabel('Depth (μm)', color='white', fontsize=11)
        ax_main.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        ax_main.set_title('Full Electron Range', color='white', fontsize=12, fontweight='bold')

        # Zoomed view (resist region, nm scale)
        zoom_lateral = 300  # nm
        zoom_depth = 500    # nm into substrate
        ax_zoom.set_xlim(-zoom_lateral, zoom_lateral)
        ax_zoom.set_ylim(-zoom_depth, self.resist_thickness + 50)
        ax_zoom.set_xlabel('Lateral Position (nm)', color='white', fontsize=11)
        ax_zoom.set_ylabel('Depth (nm)', color='white', fontsize=11)
        ax_zoom.set_title('Resist Region (Zoomed)', color='white', fontsize=12, fontweight='bold')

        # Draw geometry on both views
        for ax, mx in [(ax_main, max_r), (ax_zoom, zoom_lateral)]:
            y_bot = ax.get_ylim()[0]
            # Resist
            resist = Rectangle((-mx, 0), 2*mx, self.resist_thickness,
                              facecolor='#2090a0', alpha=0.4, edgecolor='#40c0d0', linewidth=2)
            ax.add_patch(resist)
            # Substrate
            substrate = Rectangle((-mx, y_bot), 2*mx, -y_bot,
                                 facecolor='#404050', alpha=0.6, edgecolor='#606080', linewidth=1)
            ax.add_patch(substrate)
            # Interface lines
            ax.axhline(y=0, color='#60a0b0', linestyle='--', alpha=0.5)
            ax.axhline(y=self.resist_thickness, color='#60a0b0', linestyle='--', alpha=0.5)

        # Labels
        ax_zoom.text(zoom_lateral - 10, self.resist_thickness / 2, self.resist_material,
                    color='#40c0d0', fontsize=10, ha='right', va='center', fontweight='bold')
        ax_zoom.text(zoom_lateral - 10, -zoom_depth / 2, 'Si Substrate',
                    color='#8080a0', fontsize=10, ha='right', va='center')

        # Energy colormap
        energy_cmap = plt.cm.plasma

        # Create line collections for both views
        lcs_main, lcs_zoom = [], []
        dots_main, dots_zoom = [], []

        for _ in trajs:
            lc_m = LineCollection([], cmap=energy_cmap, norm=plt.Normalize(0, self.beam_energy))
            lc_m.set_linewidth(1.5)
            ax_main.add_collection(lc_m)
            lcs_main.append(lc_m)
            dot_m, = ax_main.plot([], [], 'o', markersize=4)
            dots_main.append(dot_m)

            lc_z = LineCollection([], cmap=energy_cmap, norm=plt.Normalize(0, self.beam_energy))
            lc_z.set_linewidth(2)
            ax_zoom.add_collection(lc_z)
            lcs_zoom.append(lc_z)
            dot_z, = ax_zoom.plot([], [], 'o', markersize=6)
            dots_zoom.append(dot_z)

        # Colorbar
        sm = plt.cm.ScalarMappable(cmap=energy_cmap, norm=plt.Normalize(0, self.beam_energy))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax_zoom, shrink=0.6, pad=0.02)
        cbar.set_label('Energy (keV)', color='white', fontsize=10)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

        n_electrons = len(trajs)
        n_frames = int(fps * duration)

        # Timing parameters
        electron_duration = 0.65
        total_stagger = 0.30
        stagger = total_stagger / max(n_electrons - 1, 1)

        def init():
            for lc_m, lc_z, d_m, d_z in zip(lcs_main, lcs_zoom, dots_main, dots_zoom):
                lc_m.set_segments([])
                lc_z.set_segments([])
                d_m.set_data([], [])
                d_z.set_data([], [])
            return lcs_main + lcs_zoom + dots_main + dots_zoom

        def animate(frame):
            progress = frame / n_frames
            artists = []

            for i, (r_vals, z_vals, e_vals) in enumerate(zip(all_r, all_z, all_energy)):
                start_time = i * stagger
                ep = np.clip((progress - start_time) / electron_duration, 0, 1)
                n_pts = int(ep * len(r_vals))

                for lc, dot in [(lcs_main[i], dots_main[i]), (lcs_zoom[i], dots_zoom[i])]:
                    if n_pts > 1:
                        pts = np.array([r_vals[:n_pts], z_vals[:n_pts]]).T.reshape(-1, 1, 2)
                        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
                        lc.set_segments(segs)
                        lc.set_array(np.array(e_vals[:n_pts-1]))

                        cur_e = e_vals[n_pts-1]
                        dot.set_color(energy_cmap(cur_e / self.beam_energy))
                        dot.set_data([r_vals[n_pts-1]], [z_vals[n_pts-1]])
                    else:
                        lc.set_segments([])
                        dot.set_data([], [])

                    artists.extend([lc, dot])

            return artists

        anim = FuncAnimation(fig, animate, init_func=init, frames=n_frames,
                            interval=1000/fps, blit=True)

        print(f"Creating dual-view animation with {n_frames} frames...")

        # Save as GIF or MP4
        if output_file.endswith('.mp4'):
            from matplotlib.animation import FFMpegWriter
            writer = FFMpegWriter(fps=fps, metadata={'title': 'Electron Trajectories'})
            anim.save(output_file, writer=writer, dpi=100)
        else:
            writer = PillowWriter(fps=fps)
            # loop=0 means infinite loop, loop=1 means play once
            anim.save(output_file, writer=writer, dpi=100)

        print(f"Animation saved to: {output_file}")
        plt.close(fig)
        return output_file

    def create_dual_view_animation_gpu(self, output_file: str = "electron_animation.gif",
                                       fps: int = 45, duration: float = 6.0,
                                       fixed_energy_scale: Optional[float] = None,
                                       use_gpu: bool = True,
                                       interpolation_points: int = 400):
        """
        Create smooth dual-view animation with GPU acceleration.

        Features:
        - Left panel: Full electron range (μm scale)
        - Right panel: Zoomed resist region (nm scale)
        - Smooth path-length interpolation
        - GPU-accelerated encoding via NVENC
        - Fixed energy scale for consistent colorbars

        Args:
            output_file: Output filename (.gif or .mp4)
            fps: Frames per second (higher = smoother)
            duration: Animation duration in seconds (longer = slower motion)
            fixed_energy_scale: Max energy for colorbar (for consistent scaling)
            use_gpu: Use NVENC GPU acceleration
            interpolation_points: Points per trajectory for smooth motion
        """
        from matplotlib.collections import LineCollection

        if not self.trajectories:
            self.generate_trajectories(10)

        # Use fixed energy scale if provided, otherwise use beam energy
        max_energy_scale = fixed_energy_scale if fixed_energy_scale else self.beam_energy

        # Filter trajectories
        if self.use_real_data and not self.show_secondaries:
            trajs = [t for t in self.trajectories if t.track_id == 1]
            if not trajs:
                trajs = self.trajectories
            print(f"Animating {len(trajs)} primary electrons")
        else:
            trajs = self.trajectories
            if self.use_real_data:
                n_primary = len([t for t in self.trajectories if t.track_id == 1])
                print(f"Animating {n_primary} primary + {len(trajs) - n_primary} secondary electrons")

        # Prepare and interpolate trajectory data with more points for smoothness
        all_r, all_z, all_energy = [], [], []
        for traj in trajs:
            r_vals = [np.sqrt(p.x**2 + p.y**2) * np.sign(p.x + 0.001) for p in traj.points]
            z_vals = [p.z for p in traj.points]
            e_vals = [p.energy for p in traj.points]

            # Interpolate with more points for smoother motion
            r_interp, z_interp, e_interp = self.interpolate_trajectory(
                r_vals, z_vals, e_vals, interpolation_points
            )
            all_r.append(r_interp)
            all_z.append(z_interp)
            all_energy.append(e_interp)

        # FIXED view bounds for consistency across all GIFs
        # Main view: Fixed scale to show full 100 keV electron range (~50 μm)
        fixed_main_r = 50000  # nm = 50 μm lateral
        fixed_main_z_min = -55000  # nm = -55 μm (max depth for 100keV)
        fixed_main_z_max = 1000  # nm = 1 μm above surface

        # Create dual-panel figure
        fig = plt.figure(figsize=(14, 7), facecolor='#0a0a14')
        ax_main = fig.add_axes([0.05, 0.12, 0.55, 0.80])
        ax_zoom = fig.add_axes([0.65, 0.12, 0.32, 0.80])

        for ax in [ax_main, ax_zoom]:
            ax.set_facecolor('#0a0a14')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#333366')

        # Main view (full range, μm scale) - FIXED scale for all GIFs
        ax_main.set_xlim(-fixed_main_r, fixed_main_r)
        ax_main.set_ylim(fixed_main_z_min, fixed_main_z_max)
        ax_main.set_xlabel('Lateral Position (μm)', color='white', fontsize=11)
        ax_main.set_ylabel('Depth (μm)', color='white', fontsize=11)
        ax_main.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        ax_main.set_title('Full Electron Range', color='white', fontsize=12, fontweight='bold')

        # Zoomed view - FIXED scale based on energy for consistency
        # Low energy: tighter zoom to see detail in resist
        # High energy: wider zoom to see scattering
        if self.beam_energy <= 5:  # 1-5 keV
            zoom_lateral = 100  # nm
            zoom_depth = 150   # nm into substrate
        else:  # High energy (100 keV)
            zoom_lateral = 300  # nm
            zoom_depth = 400   # nm into substrate
        ax_zoom.set_xlim(-zoom_lateral, zoom_lateral)
        ax_zoom.set_ylim(-zoom_depth, self.resist_thickness + 30)
        ax_zoom.set_xlabel('Lateral Position (nm)', color='white', fontsize=11)
        ax_zoom.set_ylabel('Depth (nm)', color='white', fontsize=11)
        ax_zoom.set_title('Resist Region (Zoomed)', color='white', fontsize=12, fontweight='bold')

        # Draw geometry on both views
        for ax, mx in [(ax_main, fixed_main_r), (ax_zoom, zoom_lateral)]:
            y_bot = ax.get_ylim()[0]
            # Resist layer
            resist = Rectangle((-mx, 0), 2*mx, self.resist_thickness,
                              facecolor='#2090a0', alpha=0.4, edgecolor='#40c0d0', linewidth=2)
            ax.add_patch(resist)
            # Substrate
            substrate = Rectangle((-mx, y_bot), 2*mx, -y_bot,
                                 facecolor='#404050', alpha=0.6, edgecolor='#606080', linewidth=1)
            ax.add_patch(substrate)
            # Interface lines
            ax.axhline(y=0, color='#60a0b0', linestyle='--', alpha=0.5)
            ax.axhline(y=self.resist_thickness, color='#60a0b0', linestyle='--', alpha=0.5)

        # Labels on zoomed view
        ax_zoom.text(zoom_lateral - 10, self.resist_thickness / 2, self.resist_material,
                    color='#40c0d0', fontsize=10, ha='right', va='center', fontweight='bold')
        ax_zoom.text(zoom_lateral - 10, -zoom_depth / 2, 'Si Substrate',
                    color='#8080a0', fontsize=10, ha='right', va='center')

        # Energy colormap with FIXED scale
        energy_cmap = plt.cm.plasma
        energy_norm = plt.Normalize(0, max_energy_scale)

        # Create line collections for both views
        lcs_main, lcs_zoom = [], []
        dots_main, dots_zoom = [], []

        for _ in trajs:
            lc_m = LineCollection([], cmap=energy_cmap, norm=energy_norm)
            lc_m.set_linewidth(1.5)
            ax_main.add_collection(lc_m)
            lcs_main.append(lc_m)
            dot_m, = ax_main.plot([], [], 'o', markersize=4)
            dots_main.append(dot_m)

            lc_z = LineCollection([], cmap=energy_cmap, norm=energy_norm)
            lc_z.set_linewidth(2)
            ax_zoom.add_collection(lc_z)
            lcs_zoom.append(lc_z)
            dot_z, = ax_zoom.plot([], [], 'o', markersize=6)
            dots_zoom.append(dot_z)

        # Colorbar with fixed scale
        sm = plt.cm.ScalarMappable(cmap=energy_cmap, norm=energy_norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax_zoom, shrink=0.6, pad=0.02)
        cbar.set_label('Energy (keV)', color='white', fontsize=10)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

        n_electrons = len(trajs)
        n_frames = int(fps * duration)

        # Timing parameters - slower, smoother animation
        electron_duration = 0.75  # Each electron takes 75% of total time
        total_stagger = 0.20      # Start all electrons within first 20% of animation
        stagger = total_stagger / max(n_electrons - 1, 1)

        def init():
            for lc_m, lc_z, d_m, d_z in zip(lcs_main, lcs_zoom, dots_main, dots_zoom):
                lc_m.set_segments([])
                lc_z.set_segments([])
                d_m.set_data([], [])
                d_z.set_data([], [])
            return lcs_main + lcs_zoom + dots_main + dots_zoom

        def animate(frame):
            progress = frame / n_frames
            artists = []

            for i, (r_vals, z_vals, e_vals) in enumerate(zip(all_r, all_z, all_energy)):
                start_time = i * stagger
                ep = np.clip((progress - start_time) / electron_duration, 0, 1)

                # Use smooth easing for more natural motion
                # Slight ease-in-out
                ep_smooth = ep  # Linear for now, can add easing if desired

                n_pts = int(ep_smooth * len(r_vals))

                for lc, dot in [(lcs_main[i], dots_main[i]), (lcs_zoom[i], dots_zoom[i])]:
                    if n_pts > 1:
                        pts = np.array([r_vals[:n_pts], z_vals[:n_pts]]).T.reshape(-1, 1, 2)
                        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
                        lc.set_segments(segs)
                        lc.set_array(np.array(e_vals[:n_pts-1]))

                        cur_e = e_vals[n_pts-1]
                        dot.set_color(energy_cmap(cur_e / max_energy_scale))
                        dot.set_data([r_vals[n_pts-1]], [z_vals[n_pts-1]])
                    else:
                        lc.set_segments([])
                        dot.set_data([], [])

                    artists.extend([lc, dot])

            return artists

        anim = FuncAnimation(fig, animate, init_func=init, frames=n_frames,
                            interval=1000/fps, blit=True)

        print(f"Creating dual-view animation: {n_frames} frames @ {fps} fps ({duration}s)...")

        # GPU-accelerated saving
        if use_gpu and output_file.endswith('.gif'):
            has_nvenc = self._check_nvenc_support()

            with tempfile.TemporaryDirectory() as tmpdir:
                mp4_temp = Path(tmpdir) / "temp_video.mp4"

                if has_nvenc:
                    print("  Using NVIDIA NVENC GPU acceleration...")
                    from matplotlib.animation import FFMpegWriter
                    writer = FFMpegWriter(
                        fps=fps,
                        codec='h264_nvenc',
                        extra_args=['-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '19']
                    )
                    anim.save(str(mp4_temp), writer=writer, dpi=120)
                else:
                    print("  NVENC not available, using CPU encoding...")
                    from matplotlib.animation import FFMpegWriter
                    writer = FFMpegWriter(fps=fps, codec='libx264', extra_args=['-preset', 'fast'])
                    anim.save(str(mp4_temp), writer=writer, dpi=120)

                # Convert to high-quality GIF using ffmpeg with palette
                print("  Converting to GIF...")
                palette_path = Path(tmpdir) / "palette.png"

                # Generate optimal palette
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(mp4_temp),
                    '-vf', f'fps={fps},scale=1400:-1:flags=lanczos,palettegen=stats_mode=diff',
                    str(palette_path)
                ], capture_output=True)

                # Generate GIF with palette
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(mp4_temp), '-i', str(palette_path),
                    '-lavfi', f'fps={fps},scale=1400:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5',
                    '-loop', '0',
                    str(output_file)
                ], capture_output=True)

        elif output_file.endswith('.mp4'):
            has_nvenc = self._check_nvenc_support() if use_gpu else False
            if has_nvenc:
                print("  Using NVIDIA NVENC GPU acceleration for MP4...")
                from matplotlib.animation import FFMpegWriter
                writer = FFMpegWriter(
                    fps=fps,
                    codec='h264_nvenc',
                    extra_args=['-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '19']
                )
            else:
                from matplotlib.animation import FFMpegWriter
                writer = FFMpegWriter(fps=fps, codec='libx264')
            anim.save(output_file, writer=writer, dpi=120)
        else:
            print(f"  Creating animation with {n_frames} frames (PillowWriter)...")
            writer = PillowWriter(fps=fps)
            anim.save(output_file, writer=writer, dpi=120)

        print(f"  Saved: {output_file}")
        plt.close(fig)
        return output_file

    def create_animation(self, output_file: str = "electron_animation.gif",
                        fps: int = 30, duration: float = 5.0,
                        figsize: Tuple[int, int] = (10, 8)):
        """Create an animated GIF of electron trajectories"""

        if not self.trajectories:
            self.generate_trajectories(10)

        fig, ax = plt.subplots(figsize=figsize, facecolor='#0a0a14')
        ax.set_facecolor('#0a0a14')

        # Calculate view bounds from actual trajectory data
        if self.use_real_data and self.trajectories:
            all_x = [p.x for t in self.trajectories for p in t.points]
            all_y = [p.y for t in self.trajectories for p in t.points]
            all_z = [p.z for t in self.trajectories for p in t.points]

            # Calculate radial distances
            all_r = [np.sqrt(x**2 + y**2) for x, y in zip(all_x, all_y)]
            max_lateral = max(max(all_r) * 1.1, 100)  # At least 100nm, 10% margin
            z_min = min(all_z) * 1.1  # 10% margin below deepest point
            z_max = max(all_z) * 1.1 + 20  # 10% margin above highest + buffer

            # Round to nice values
            max_lateral = np.ceil(max_lateral / 1000) * 1000  # Round up to nearest μm
            z_min = np.floor(z_min / 1000) * 1000  # Round down to nearest μm
            print(f"Auto-scaled view: lateral ±{max_lateral/1000:.1f}μm, depth {z_min/1000:.1f}μm to {z_max:.0f}nm")
        else:
            max_lateral = 100  # nm
            z_min = -min(200, self.substrate_thickness)
            z_max = self.resist_thickness + 50

        ax.set_xlim(-max_lateral, max_lateral)
        ax.set_ylim(z_min, z_max)

        # Use μm for large scales
        use_microns = max_lateral > 500
        if use_microns:
            ax.set_xlabel('Lateral Position (μm)', color='white', fontsize=12)
            ax.set_ylabel('Depth (μm)', color='white', fontsize=12)
            # Convert tick labels to μm
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        else:
            ax.set_xlabel('Lateral Position (nm)', color='white', fontsize=12)
            ax.set_ylabel('Depth (nm)', color='white', fontsize=12)

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#333366')

        # Draw geometry (static)
        # Resist layer (thin at this scale but still shown)
        resist_rect = Rectangle((-max_lateral, 0), 2*max_lateral, self.resist_thickness,
                               facecolor='#2090a0', alpha=0.4, edgecolor='#40c0d0', linewidth=2)
        ax.add_patch(resist_rect)

        # Substrate (fills from z=0 down to z_min)
        substrate_rect = Rectangle((-max_lateral, z_min), 2*max_lateral, -z_min,
                                  facecolor='#404050', alpha=0.6, edgecolor='#606080', linewidth=2)
        ax.add_patch(substrate_rect)

        # Labels - position relative to view
        label_x = max_lateral * 0.95
        ax.text(label_x, self.resist_thickness / 2, self.resist_material,
               color='#40c0d0', fontsize=10, ha='right', va='center', fontweight='bold')
        ax.text(label_x, z_min / 2, 'Si Substrate',
               color='#8080a0', fontsize=10, ha='right', va='center')

        # Interface line
        ax.axhline(y=0, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=self.resist_thickness, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)

        # Title
        title = ax.set_title(f'{self.beam_energy} keV Electrons in {self.resist_thickness}nm {self.resist_material}',
                            color='white', fontsize=14, fontweight='bold', pad=10)

        # Filter trajectories based on show_secondaries setting
        if self.use_real_data and not self.show_secondaries:
            primary_trajectories = [t for t in self.trajectories if t.track_id == 1]
            if len(primary_trajectories) == 0:
                primary_trajectories = self.trajectories  # Fallback
            print(f"Showing {len(primary_trajectories)} primary electrons only")
        else:
            primary_trajectories = self.trajectories
            if self.use_real_data:
                n_primary = len([t for t in self.trajectories if t.track_id == 1])
                n_secondary = len(self.trajectories) - n_primary
                print(f"Showing {n_primary} primary + {n_secondary} secondary electrons")

        # Prepare trajectory data for animation
        # Use radial distance (sqrt(x^2 + y^2)) for 2D projection
        all_r = []
        all_z = []
        all_energy = []

        for traj in primary_trajectories:
            r_vals = [np.sqrt(p.x**2 + p.y**2) * np.sign(p.x + 0.001) for p in traj.points]
            z_vals = [p.z for p in traj.points]
            e_vals = [p.energy for p in traj.points]
            all_r.append(r_vals)
            all_z.append(z_vals)
            all_energy.append(e_vals)

        n_electrons = len(primary_trajectories)
        n_frames = int(fps * duration)

        # Energy colormap: high energy = bright yellow/white, low energy = dark red/purple
        energy_cmap = plt.cm.plasma

        # Create line collection and dot for each trajectory
        # We'll use LineCollection for energy-colored segments
        from matplotlib.collections import LineCollection

        line_collections = []
        dots = []

        for i in range(n_electrons):
            # Empty line collection - will be updated each frame
            lc = LineCollection([], cmap=energy_cmap, norm=plt.Normalize(0, self.beam_energy))
            lc.set_linewidth(2)
            ax.add_collection(lc)
            line_collections.append(lc)

            # Dot for current position
            dot, = ax.plot([], [], 'o', markersize=6)
            dots.append(dot)

        # Add colorbar for energy
        sm = plt.cm.ScalarMappable(cmap=energy_cmap, norm=plt.Normalize(0, self.beam_energy))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
        cbar.set_label('Energy (keV)', color='white', fontsize=10)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

        # Timing: consistent delay between electrons
        # Each electron takes 70% of total time, with staggered starts
        electron_duration = 0.7  # Fraction of total animation time for each electron
        total_stagger = 0.25  # Total time spent staggering all electrons
        stagger_per_electron = total_stagger / max(n_electrons - 1, 1)

        def init():
            for lc, dot in zip(line_collections, dots):
                lc.set_segments([])
                dot.set_data([], [])
            return line_collections + dots

        def animate(frame):
            progress = frame / n_frames
            artists = []

            for i, (lc, dot, r_vals, z_vals, e_vals) in enumerate(
                    zip(line_collections, dots, all_r, all_z, all_energy)):

                # Consistent stagger: each electron starts after a fixed delay
                start_time = i * stagger_per_electron
                electron_progress = (progress - start_time) / electron_duration
                electron_progress = np.clip(electron_progress, 0, 1)

                n_points = int(electron_progress * len(r_vals))

                if n_points > 1:
                    # Create line segments colored by energy
                    points = np.array([r_vals[:n_points], z_vals[:n_points]]).T.reshape(-1, 1, 2)
                    segments = np.concatenate([points[:-1], points[1:]], axis=1)
                    lc.set_segments(segments)
                    lc.set_array(np.array(e_vals[:n_points-1]))

                    # Color the dot by current energy
                    current_energy = e_vals[n_points-1]
                    dot_color = energy_cmap(current_energy / self.beam_energy)
                    dot.set_color(dot_color)
                    dot.set_data([r_vals[n_points-1]], [z_vals[n_points-1]])
                else:
                    lc.set_segments([])
                    dot.set_data([], [])

                artists.append(lc)
                artists.append(dot)

            return artists

        anim = FuncAnimation(fig, animate, init_func=init, frames=n_frames,
                            interval=1000/fps, blit=True)

        # Save animation
        print(f"Creating animation with {n_frames} frames...")
        writer = PillowWriter(fps=fps)
        anim.save(output_file, writer=writer, dpi=100)
        print(f"Animation saved to: {output_file}")

        plt.close(fig)
        return output_file

    def create_animation_gpu(self, output_file: str = "electron_animation.gif",
                             fps: int = 30, duration: float = 5.0,
                             figsize: Tuple[int, int] = (10, 8),
                             fixed_energy_scale: Optional[float] = None,
                             use_gpu: bool = True):
        """
        Create animation with GPU acceleration using NVENC.

        Args:
            output_file: Output filename (.gif or .mp4)
            fps: Frames per second
            duration: Animation duration in seconds
            figsize: Figure size in inches
            fixed_energy_scale: If set, use this as the max energy for colorbar (for consistent scaling)
            use_gpu: If True, attempt GPU-accelerated encoding via NVENC
        """
        from matplotlib.collections import LineCollection

        if not self.trajectories:
            self.generate_trajectories(10)

        # Use fixed energy scale if provided, otherwise use beam energy
        max_energy_scale = fixed_energy_scale if fixed_energy_scale else self.beam_energy

        fig, ax = plt.subplots(figsize=figsize, facecolor='#0a0a14')
        ax.set_facecolor('#0a0a14')

        # Calculate view bounds from actual trajectory data
        if self.use_real_data and self.trajectories:
            all_x = [p.x for t in self.trajectories for p in t.points]
            all_y = [p.y for t in self.trajectories for p in t.points]
            all_z = [p.z for t in self.trajectories for p in t.points]
            all_r = [np.sqrt(x**2 + y**2) for x, y in zip(all_x, all_y)]
            max_lateral = max(max(all_r) * 1.1, 100)
            z_min = min(all_z) * 1.1
            z_max = max(all_z) * 1.1 + 20
            max_lateral = np.ceil(max_lateral / 1000) * 1000
            z_min = np.floor(z_min / 1000) * 1000
        else:
            max_lateral = 100
            z_min = -min(200, self.substrate_thickness)
            z_max = self.resist_thickness + 50

        ax.set_xlim(-max_lateral, max_lateral)
        ax.set_ylim(z_min, z_max)

        use_microns = max_lateral > 500
        if use_microns:
            ax.set_xlabel('Lateral Position (μm)', color='white', fontsize=12)
            ax.set_ylabel('Depth (μm)', color='white', fontsize=12)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        else:
            ax.set_xlabel('Lateral Position (nm)', color='white', fontsize=12)
            ax.set_ylabel('Depth (nm)', color='white', fontsize=12)

        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#333366')

        # Draw geometry
        resist_rect = Rectangle((-max_lateral, 0), 2*max_lateral, self.resist_thickness,
                               facecolor='#2090a0', alpha=0.4, edgecolor='#40c0d0', linewidth=2)
        ax.add_patch(resist_rect)

        substrate_rect = Rectangle((-max_lateral, z_min), 2*max_lateral, -z_min,
                                  facecolor='#404050', alpha=0.6, edgecolor='#606080', linewidth=2)
        ax.add_patch(substrate_rect)

        label_x = max_lateral * 0.95
        ax.text(label_x, self.resist_thickness / 2, self.resist_material,
               color='#40c0d0', fontsize=10, ha='right', va='center', fontweight='bold')
        ax.text(label_x, z_min / 2, 'Si Substrate',
               color='#8080a0', fontsize=10, ha='right', va='center')

        ax.axhline(y=0, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=self.resist_thickness, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)

        # Title with energy
        ax.set_title(f'{self.beam_energy} keV Electrons in {self.resist_thickness}nm {self.resist_material}',
                    color='white', fontsize=14, fontweight='bold', pad=10)

        # Filter trajectories
        if self.use_real_data and not self.show_secondaries:
            primary_trajectories = [t for t in self.trajectories if t.track_id == 1]
            if not primary_trajectories:
                primary_trajectories = self.trajectories
        else:
            primary_trajectories = self.trajectories

        # Prepare trajectory data
        all_r, all_z_vals, all_energy = [], [], []
        for traj in primary_trajectories:
            r_vals = [np.sqrt(p.x**2 + p.y**2) * np.sign(p.x + 0.001) for p in traj.points]
            z_vals = [p.z for p in traj.points]
            e_vals = [p.energy for p in traj.points]
            all_r.append(r_vals)
            all_z_vals.append(z_vals)
            all_energy.append(e_vals)

        n_electrons = len(primary_trajectories)
        n_frames = int(fps * duration)

        # Energy colormap with FIXED scale
        energy_cmap = plt.cm.plasma
        energy_norm = plt.Normalize(0, max_energy_scale)

        line_collections = []
        dots = []

        for i in range(n_electrons):
            lc = LineCollection([], cmap=energy_cmap, norm=energy_norm)
            lc.set_linewidth(2)
            ax.add_collection(lc)
            line_collections.append(lc)
            dot, = ax.plot([], [], 'o', markersize=6)
            dots.append(dot)

        # Colorbar with fixed scale
        sm = plt.cm.ScalarMappable(cmap=energy_cmap, norm=energy_norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
        cbar.set_label('Energy (keV)', color='white', fontsize=10)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

        electron_duration = 0.7
        total_stagger = 0.25
        stagger_per_electron = total_stagger / max(n_electrons - 1, 1)

        def init():
            for lc, dot in zip(line_collections, dots):
                lc.set_segments([])
                dot.set_data([], [])
            return line_collections + dots

        def animate(frame):
            progress = frame / n_frames
            artists = []

            for i, (lc, dot, r_vals, z_vals, e_vals) in enumerate(
                    zip(line_collections, dots, all_r, all_z_vals, all_energy)):

                start_time = i * stagger_per_electron
                electron_progress = np.clip((progress - start_time) / electron_duration, 0, 1)
                n_points = int(electron_progress * len(r_vals))

                if n_points > 1:
                    points = np.array([r_vals[:n_points], z_vals[:n_points]]).T.reshape(-1, 1, 2)
                    segments = np.concatenate([points[:-1], points[1:]], axis=1)
                    lc.set_segments(segments)
                    lc.set_array(np.array(e_vals[:n_points-1]))

                    current_energy = e_vals[n_points-1]
                    dot.set_color(energy_cmap(current_energy / max_energy_scale))
                    dot.set_data([r_vals[n_points-1]], [z_vals[n_points-1]])
                else:
                    lc.set_segments([])
                    dot.set_data([], [])

                artists.extend([lc, dot])

            return artists

        anim = FuncAnimation(fig, animate, init_func=init, frames=n_frames,
                            interval=1000/fps, blit=True)

        # GPU-accelerated saving
        output_path = Path(output_file)

        if use_gpu and output_file.endswith('.gif'):
            # Save as MP4 first using GPU, then convert to GIF
            print(f"Creating GPU-accelerated animation with {n_frames} frames...")

            # Check for NVENC support
            has_nvenc = self._check_nvenc_support()

            with tempfile.TemporaryDirectory() as tmpdir:
                mp4_temp = Path(tmpdir) / "temp_video.mp4"

                if has_nvenc:
                    print("Using NVIDIA NVENC GPU acceleration...")
                    from matplotlib.animation import FFMpegWriter

                    # Use NVENC hardware encoder
                    writer = FFMpegWriter(
                        fps=fps,
                        codec='h264_nvenc',
                        extra_args=['-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '19']
                    )
                    anim.save(str(mp4_temp), writer=writer, dpi=100)
                else:
                    print("NVENC not available, using CPU encoding...")
                    from matplotlib.animation import FFMpegWriter
                    writer = FFMpegWriter(fps=fps, codec='libx264', extra_args=['-preset', 'fast'])
                    anim.save(str(mp4_temp), writer=writer, dpi=100)

                # Convert to GIF using ffmpeg with GPU-accelerated decoding
                print("Converting to GIF using ffmpeg...")
                palette_path = Path(tmpdir) / "palette.png"

                # Generate palette
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(mp4_temp),
                    '-vf', 'fps=30,scale=1000:-1:flags=lanczos,palettegen=stats_mode=diff',
                    str(palette_path)
                ], capture_output=True)

                # Generate GIF with palette
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(mp4_temp), '-i', str(palette_path),
                    '-lavfi', 'fps=30,scale=1000:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5',
                    '-loop', '0',
                    str(output_file)
                ], capture_output=True)

        elif output_file.endswith('.mp4'):
            # Direct MP4 output with GPU
            has_nvenc = self._check_nvenc_support() if use_gpu else False

            if has_nvenc:
                print("Using NVIDIA NVENC GPU acceleration for MP4...")
                from matplotlib.animation import FFMpegWriter
                writer = FFMpegWriter(
                    fps=fps,
                    codec='h264_nvenc',
                    extra_args=['-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '19']
                )
            else:
                print("Using CPU encoding for MP4...")
                from matplotlib.animation import FFMpegWriter
                writer = FFMpegWriter(fps=fps, codec='libx264')

            anim.save(output_file, writer=writer, dpi=100)
        else:
            # Fallback to Pillow for GIF
            print(f"Creating animation with {n_frames} frames (PillowWriter)...")
            writer = PillowWriter(fps=fps)
            anim.save(output_file, writer=writer, dpi=100)

        print(f"Animation saved to: {output_file}")
        plt.close(fig)
        return output_file

    def _check_nvenc_support(self) -> bool:
        """Check if NVIDIA NVENC is available"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True, text=True
            )
            return 'h264_nvenc' in result.stdout
        except Exception:
            return False


def batch_create_metalcone_animations(
    output_dir: str = ".",
    resist_thickness: float = 100,
    electrons: int = 15,
    fps: int = 30,
    duration: float = 5.0,
    use_gpu: bool = True
) -> List[str]:
    """
    Create animations for all metalcone resist types at 1kV and 100kV.
    Uses simple Monte Carlo trajectories (not Geant4).

    All animations use the same energy colorbar scale (100 keV max)
    for consistent comparison across energies.

    Args:
        output_dir: Directory to save animations
        resist_thickness: Resist thickness in nm
        electrons: Number of electrons per animation
        fps: Frames per second
        duration: Animation duration in seconds
        use_gpu: Use GPU acceleration if available

    Returns:
        List of created output file paths
    """
    # Metalcone resist types (metal-organic hybrid materials)
    metalcone_materials = [
        "Zincone",      # Zn-based MLD
        "Alucone",      # Al-based MLD
        "Tincone",      # Sn-based (treated as variant)
    ]

    energies_kv = [10, 100]  # 10 keV and 100 keV (realistic EBL range)

    # Use 100 keV as the fixed scale for all (so colorbars match)
    fixed_energy_scale = 100.0

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Check NVENC once
    animator_check = ElectronAnimator()
    has_nvenc = animator_check._check_nvenc_support()
    if has_nvenc:
        print("✓ NVIDIA NVENC GPU acceleration available")
    else:
        print("⚠ NVENC not available, using CPU encoding")

    total = len(metalcone_materials) * len(energies_kv)
    count = 0

    for material in metalcone_materials:
        for energy in energies_kv:
            count += 1
            print(f"\n{'='*60}")
            print(f"[{count}/{total}] Creating animation: {material} @ {energy} kV")
            print(f"{'='*60}")

            animator = ElectronAnimator(
                resist_thickness=resist_thickness,
                resist_material=material,
                beam_energy=energy,
                show_secondaries=False
            )

            # Generate Monte Carlo trajectories
            animator.generate_trajectories(electrons)

            # Output filename
            output_file = output_dir / f"electron_{material}_{energy}kV.gif"

            # Create animation with fixed energy scale
            animator.create_animation_gpu(
                output_file=str(output_file),
                fps=fps,
                duration=duration,
                fixed_energy_scale=fixed_energy_scale,
                use_gpu=use_gpu
            )

            created_files.append(str(output_file))

    print(f"\n{'='*60}")
    print(f"✓ Created {len(created_files)} animations:")
    for f in created_files:
        print(f"  - {f}")
    print(f"{'='*60}")

    return created_files


# Material definitions for Geant4 simulations
# Using Ethylene Glycol (EG) based chemistry for consistent comparison
# Chemistry: Metal precursor + EG → Metal-organic hybrid
#   - Al(III) + 1.5 EG → Al₂C₆H₁₂O₆ (23% Al by mass)
#   - Zn(II) + 1 EG → ZnC₂H₄O₂ (52% Zn by mass)
#   - Sn(IV) + 2 EG → SnC₄H₈O₄ (50% Sn by mass)
METALCONE_MATERIALS = {
    "Zincone": {
        "composition": "Zn:1,C:2,H:4,O:2",
        "density": 2.0,
        "description": "Zinc-based MLD (DEZ + EG) - ZnC₂H₄O₂, 52% Zn"
    },
    "Alucone": {
        "composition": "Al:2,C:6,H:12,O:6",
        "density": 1.5,
        "description": "Aluminum-based MLD (TMA + EG) - Al₂C₆H₁₂O₆, 23% Al"
    },
    "Tincone": {
        "composition": "Sn:1,C:4,H:8,O:4",
        "density": 2.5,
        "description": "Tin-based MLD (TDMASn + EG) - SnC₄H₈O₄, 50% Sn"
    }
}


def create_trajectory_macro(
    material_name: str,
    energy_kev: float,
    resist_thickness: float,
    n_electrons: int,
    output_json: str,
    macro_path: str
) -> str:
    """
    Create a Geant4 macro file for trajectory export.

    Args:
        material_name: Name of the material (Zincone, Alucone, Tincone)
        energy_kev: Beam energy in keV
        resist_thickness: Resist thickness in nm
        n_electrons: Number of electrons to simulate
        output_json: Path to output JSON file
        macro_path: Path to save the macro file

    Returns:
        Path to the created macro file
    """
    if material_name not in METALCONE_MATERIALS:
        raise ValueError(f"Unknown material: {material_name}")

    mat = METALCONE_MATERIALS[material_name]

    macro_content = f"""# Auto-generated macro for trajectory export
# Material: {material_name} - {mat['description']}
# Energy: {energy_kev} keV
# Generated by trajectory_animator.py

# ============================================================
# GEOMETRY SETUP
# ============================================================
/det/setResistComposition {mat['composition']}
/det/setResistDensity {mat['density']} g/cm3
/det/setResistThickness {resist_thickness} nm

# Initialize geometry
/run/initialize

# ============================================================
# BEAM CONFIGURATION
# ============================================================
/gun/particle e-
/gun/energy {energy_kev} keV
/gun/position 0 0 {resist_thickness + 50} nm
/gun/direction 0 0 -1
/gun/beamSize 0 nm

# ============================================================
# ENABLE TRAJECTORY RECORDING
# ============================================================
/ebl/trajectory/setFile {output_json}
/ebl/trajectory/enable true

# ============================================================
# RUN SIMULATION
# ============================================================
/run/beamOn {n_electrons}

# ============================================================
# WRITE TRAJECTORY DATA
# ============================================================
/ebl/trajectory/write
"""

    with open(macro_path, 'w') as f:
        f.write(macro_content)

    return macro_path


def run_geant4_simulation(macro_path: str, working_dir: str) -> bool:
    """
    Run Geant4 simulation with the given macro.

    Args:
        macro_path: Path to the macro file (absolute path)
        working_dir: Working directory for the simulation (where output goes)

    Returns:
        True if successful, False otherwise
    """
    # Find the ebl_sim executable
    script_dir = Path(__file__).parent
    exe_path = script_dir.parent.parent / "build" / "bin" / "ebl_sim"

    if not exe_path.exists():
        print(f"ERROR: ebl_sim not found at {exe_path}")
        return False

    # Set up environment
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/opt/geant4/lib:' + env.get('LD_LIBRARY_PATH', '')

    # Use absolute path for macro
    macro_abs = Path(macro_path).resolve()

    print(f"Running: {exe_path.name} -m {macro_abs.name}")
    print(f"  Working dir: {working_dir}")

    try:
        # Use single-threaded mode for trajectory recording (MT causes memory corruption)
        result = subprocess.run(
            [str(exe_path), '-t', '1', '-m', str(macro_abs)],
            cwd=working_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print output regardless of return code
        output_lines = result.stdout.strip().split('\n') if result.stdout else []
        stderr_lines = result.stderr.strip().split('\n') if result.stderr else []

        print(f"  ...{len(output_lines)} stdout lines, {len(stderr_lines)} stderr lines")

        # Show last few lines of output
        for line in output_lines[-8:]:
            if line.strip():
                print(f"  {line}")

        if result.returncode != 0:
            print(f"  Return code: {result.returncode}")
            # Show stderr for debugging
            for line in stderr_lines[-5:]:
                if line.strip():
                    print(f"  STDERR: {line}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Simulation timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def batch_create_geant4_animations(
    output_dir: str = ".",
    resist_thickness: float = 100,
    n_electrons: int = 10,
    fps: int = 45,
    duration: float = 6.0,
    use_gpu: bool = True,
    show_secondaries: bool = False
) -> List[str]:
    """
    Create animations for all metalcone resist types at 1kV and 100kV
    using actual Geant4 simulations.

    All animations use the same energy colorbar scale (100 keV max)
    for consistent comparison across energies.

    Args:
        output_dir: Directory to save animations
        resist_thickness: Resist thickness in nm
        n_electrons: Number of electrons per simulation
        fps: Frames per second
        duration: Animation duration in seconds
        use_gpu: Use GPU acceleration if available
        show_secondaries: Include secondary electrons in animation

    Returns:
        List of created output file paths
    """
    materials = list(METALCONE_MATERIALS.keys())
    energies_kev = [10, 100]  # 10 keV and 100 keV (realistic EBL range)

    # Use 100 keV as the fixed scale for all (so colorbars match)
    fixed_energy_scale = 100.0

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp directory for macros and JSON files
    macro_dir = output_dir / "macros"
    macro_dir.mkdir(exist_ok=True)

    json_dir = output_dir / "trajectories"
    json_dir.mkdir(exist_ok=True)

    created_files = []

    # Check NVENC once
    animator_check = ElectronAnimator()
    has_nvenc = animator_check._check_nvenc_support()
    if has_nvenc:
        print("✓ NVIDIA NVENC GPU acceleration available")
    else:
        print("⚠ NVENC not available, using CPU encoding")

    total = len(materials) * len(energies_kev)
    count = 0

    for material in materials:
        for energy in energies_kev:
            count += 1
            print(f"\n{'='*60}")
            print(f"[{count}/{total}] {material} @ {energy} keV (Geant4 simulation)")
            print(f"{'='*60}")

            # File paths
            json_file = json_dir / f"traj_{material}_{energy}keV.json"
            macro_file = macro_dir / f"traj_{material}_{energy}keV.mac"
            output_file = output_dir / f"electron_{material}_{energy}kV.gif"

            # Step 1: Create macro
            print(f"Creating macro: {macro_file.name}")
            create_trajectory_macro(
                material_name=material,
                energy_kev=energy,
                resist_thickness=resist_thickness,
                n_electrons=n_electrons,
                output_json=str(json_file.name),
                macro_path=str(macro_file)
            )

            # Step 2: Run Geant4 simulation
            print(f"Running Geant4 simulation...")
            success = run_geant4_simulation(
                macro_path=str(macro_file),
                working_dir=str(json_dir)
            )

            if not success:
                print(f"WARNING: Simulation failed for {material} @ {energy} keV, skipping...")
                continue

            # Step 3: Check JSON file exists
            if not json_file.exists():
                print(f"WARNING: Trajectory file not created: {json_file}")
                continue

            # Step 4: Create dual-view animation from Geant4 data
            print(f"Creating dual-view animation from Geant4 data...")
            animator = ElectronAnimator(
                resist_thickness=resist_thickness,
                resist_material=material,
                beam_energy=energy,
                show_secondaries=show_secondaries
            )

            if animator.load_geant4_trajectories(str(json_file)):
                # Use dual-view layout with smooth animation
                animator.create_dual_view_animation_gpu(
                    output_file=str(output_file),
                    fps=fps,
                    duration=duration,
                    fixed_energy_scale=fixed_energy_scale,
                    use_gpu=use_gpu,
                    interpolation_points=500  # More points for smoother motion
                )
                created_files.append(str(output_file))
            else:
                print(f"WARNING: Failed to load trajectories from {json_file}")

    print(f"\n{'='*60}")
    print(f"✓ Created {len(created_files)} animations from Geant4 data:")
    for f in created_files:
        print(f"  - {f}")
    print(f"{'='*60}")

    return created_files


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create electron trajectory animations')
    parser.add_argument('--material', '-m', default='Zincone',
                       choices=['Zincone', 'Alucone', 'Tincone', 'PMMA', 'HSQ'],
                       help='Resist material')
    parser.add_argument('--thickness', '-t', type=float, default=100,
                       help='Resist thickness in nm')
    parser.add_argument('--energy', '-e', type=float, default=100,
                       help='Beam energy in keV')
    parser.add_argument('--electrons', '-n', type=int, default=15,
                       help='Number of electrons to simulate')
    parser.add_argument('--output', '-o', default='electron_animation.gif',
                       help='Output filename')
    parser.add_argument('--duration', '-d', type=float, default=5.0,
                       help='Animation duration in seconds')
    parser.add_argument('--fps', type=int, default=30,
                       help='Frames per second')
    parser.add_argument('--geant4', '-g', type=str, default=None,
                       help='Use real Geant4 trajectory data from JSON file')
    parser.add_argument('--run-geant4', action='store_true',
                       help='Run Geant4 simulation first to generate trajectory data')
    parser.add_argument('--secondaries', '-s', action='store_true',
                       help='Show secondary electrons (not just primaries)')
    parser.add_argument('--euv', action='store_true',
                       help='Simulate EUV photons (92 eV) instead of electron beam')
    parser.add_argument('--dual-view', action='store_true',
                       help='Create dual-view animation (full range + zoomed resist)')
    # New GPU and batch options
    parser.add_argument('--gpu', action='store_true',
                       help='Use GPU acceleration (NVIDIA NVENC) for encoding')
    parser.add_argument('--batch-metalcones', action='store_true',
                       help='Create animations for all metalcone types at 1kV and 100kV (Monte Carlo)')
    parser.add_argument('--batch-geant4', action='store_true',
                       help='Create animations for all metalcone types at 1kV and 100kV (Geant4)')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for batch mode')
    parser.add_argument('--fixed-scale', type=float, default=None,
                       help='Fixed energy scale for colorbar (keV)')

    args = parser.parse_args()

    # Batch mode with Geant4: create all metalcone animations using real simulations
    if args.batch_geant4:
        print("="*60)
        print("BATCH MODE: Creating animations using GEANT4 simulations")
        print("Materials: Zincone, Alucone, Tincone")
        print("Energies: 1 kV and 100 kV")
        print("Fixed colorbar scale: 100 keV (for comparison)")
        print("="*60)

        batch_create_geant4_animations(
            output_dir=args.output_dir,
            resist_thickness=args.thickness,
            n_electrons=args.electrons,
            fps=args.fps,
            duration=args.duration,
            use_gpu=args.gpu,
            show_secondaries=args.secondaries
        )
        return

    # Batch mode (Monte Carlo): create all metalcone animations
    if args.batch_metalcones:
        print("="*60)
        print("BATCH MODE: Creating animations (Monte Carlo)")
        print("Materials: Zincone, Alucone, Tincone")
        print("Energies: 1 kV and 100 kV")
        print("Fixed colorbar scale: 100 keV (for comparison)")
        print("="*60)

        batch_create_metalcone_animations(
            output_dir=args.output_dir,
            resist_thickness=args.thickness,
            electrons=args.electrons,
            fps=args.fps,
            duration=args.duration,
            use_gpu=args.gpu
        )
        return

    # EUV mode uses 92 eV photons
    beam_energy = 0.092 if args.euv else args.energy  # 92 eV = 0.092 keV

    animator = ElectronAnimator(
        resist_thickness=args.thickness,
        resist_material=args.material,
        beam_energy=beam_energy,
        show_secondaries=args.secondaries
    )

    # Option 1: Run Geant4 simulation first
    if args.run_geant4:
        print("Running Geant4 simulation to generate trajectory data...")
        exe_path = Path(__file__).parent.parent.parent / "build" / "bin" / "ebl_sim"
        macro_path = Path(__file__).parent.parent.parent / "macros" / "trajectory_export.mac"

        if exe_path.exists() and macro_path.exists():
            env = os.environ.copy()
            env['LD_LIBRARY_PATH'] = '/opt/geant4/lib:' + env.get('LD_LIBRARY_PATH', '')

            result = subprocess.run(
                [str(exe_path), '-m', str(macro_path)],
                cwd=str(exe_path.parent),
                env=env,
                capture_output=True,
                text=True
            )
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

            # Load the generated data
            json_path = exe_path.parent / "trajectories.json"
            if json_path.exists():
                animator.load_geant4_trajectories(str(json_path))
            else:
                print("Warning: trajectories.json not found, using Monte Carlo")
        else:
            print(f"Warning: Could not find ebl_sim at {exe_path}")

    # Option 2: Load existing Geant4 data
    elif args.geant4:
        print(f"Loading Geant4 trajectory data from {args.geant4}...")
        if not animator.load_geant4_trajectories(args.geant4):
            print("Failed to load Geant4 data, falling back to Monte Carlo")

    # Option 3: Generate Monte Carlo trajectories
    if not animator.trajectories:
        print(f"Generating {args.electrons} Monte Carlo electron trajectories...")
        print(f"  Material: {args.material}")
        print(f"  Thickness: {args.thickness} nm")
        print(f"  Energy: {args.energy} keV")
        animator.generate_trajectories(args.electrons)

    # Create animation (dual-view, GPU-accelerated, or standard)
    if args.dual_view:
        output_path = animator.create_dual_view_animation(
            output_file=args.output,
            fps=args.fps,
            duration=args.duration
        )
    elif args.gpu or args.fixed_scale:
        # Use GPU-accelerated method (also supports fixed scale)
        output_path = animator.create_animation_gpu(
            output_file=args.output,
            fps=args.fps,
            duration=args.duration,
            fixed_energy_scale=args.fixed_scale,
            use_gpu=args.gpu
        )
    else:
        output_path = animator.create_animation(
            output_file=args.output,
            fps=args.fps,
            duration=args.duration
        )

    print(f"\nDone! Open {output_path} to view the animation.")


if __name__ == "__main__":
    main()
