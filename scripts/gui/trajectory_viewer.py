#!/usr/bin/env python3
"""
Interactive Electron Trajectory Viewer
Play/pause controls, zoom, and smooth interpolated motion
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
from matplotlib.widgets import Button, Slider
from pathlib import Path
import json
from dataclasses import dataclass
from typing import List
import sys


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


class InteractiveTrajectoryViewer:
    """Interactive viewer for electron trajectories with play/pause controls"""

    def __init__(self, json_file: str, resist_thickness: float = 100,
                 beam_energy: float = 100, show_secondaries: bool = False):
        self.resist_thickness = resist_thickness
        self.beam_energy = beam_energy
        self.show_secondaries = show_secondaries
        self.trajectories = []
        self.playing = False
        self.current_frame = 0
        self.total_frames = 300
        self.timer = None

        # Load data
        self.load_trajectories(json_file)

        # Interpolate trajectories for smooth animation
        self.interpolate_trajectories()

    def load_trajectories(self, json_file: str):
        """Load trajectories from Geant4 JSON output"""
        with open(json_file, 'r') as f:
            data = json.load(f)

        for event in data.get('events', []):
            tracks = event.get('tracks', {})
            for track_id, track_data in tracks.items():
                points = []
                particle = track_data.get('particle', 'e-')
                raw_points = track_data.get('points', [])

                for pt in raw_points:
                    if len(pt) >= 4:
                        points.append(TrajectoryPoint(
                            x=pt[0], y=pt[1], z=pt[2],
                            energy=pt[3], particle=particle
                        ))

                if points:
                    self.trajectories.append(Trajectory(
                        points=points,
                        particle_type=particle,
                        track_id=int(track_id)
                    ))

        print(f"Loaded {len(self.trajectories)} tracks")

    def interpolate_trajectories(self):
        """Interpolate trajectories for smooth animation"""
        # Filter to primaries only if not showing secondaries
        if not self.show_secondaries:
            trajs = [t for t in self.trajectories if t.track_id == 1]
        else:
            trajs = self.trajectories

        self.interp_data = []
        n_interp_points = 200  # Interpolate each trajectory to this many points

        for traj in trajs:
            if len(traj.points) < 2:
                continue

            # Calculate path length for each segment
            r_vals = [np.sqrt(p.x**2 + p.y**2) * np.sign(p.x + 0.001) for p in traj.points]
            z_vals = [p.z for p in traj.points]
            e_vals = [p.energy for p in traj.points]

            # Cumulative path length
            path_lengths = [0]
            for i in range(1, len(r_vals)):
                dr = r_vals[i] - r_vals[i-1]
                dz = z_vals[i] - z_vals[i-1]
                path_lengths.append(path_lengths[-1] + np.sqrt(dr**2 + dz**2))

            total_length = path_lengths[-1]
            if total_length == 0:
                continue

            # Interpolate uniformly along path length
            uniform_lengths = np.linspace(0, total_length, n_interp_points)
            interp_r = np.interp(uniform_lengths, path_lengths, r_vals)
            interp_z = np.interp(uniform_lengths, path_lengths, z_vals)
            interp_e = np.interp(uniform_lengths, path_lengths, e_vals)

            self.interp_data.append({
                'r': interp_r,
                'z': interp_z,
                'energy': interp_e,
                'track_id': traj.track_id
            })

        print(f"Interpolated {len(self.interp_data)} trajectories")

    def setup_figure(self):
        """Create the figure with two views and controls"""
        self.fig = plt.figure(figsize=(14, 8), facecolor='#0a0a14')

        # Main view (full range)
        self.ax_main = self.fig.add_axes([0.05, 0.15, 0.55, 0.75])
        self.ax_main.set_facecolor('#0a0a14')

        # Zoomed view (resist region)
        self.ax_zoom = self.fig.add_axes([0.65, 0.15, 0.30, 0.75])
        self.ax_zoom.set_facecolor('#0a0a14')

        # Calculate view bounds from data
        all_r = np.concatenate([d['r'] for d in self.interp_data])
        all_z = np.concatenate([d['z'] for d in self.interp_data])

        max_r = max(np.abs(all_r).max() * 1.1, 100)
        z_min = min(all_z.min() * 1.1, -200)
        z_max = max(all_z.max() * 1.1, self.resist_thickness + 50)

        # Main view setup
        self.ax_main.set_xlim(-max_r, max_r)
        self.ax_main.set_ylim(z_min, z_max)
        self.ax_main.set_xlabel('Lateral Position (μm)', color='white', fontsize=11)
        self.ax_main.set_ylabel('Depth (μm)', color='white', fontsize=11)
        self.ax_main.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        self.ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}'))
        self.ax_main.tick_params(colors='white')
        self.ax_main.set_title('Full View', color='white', fontsize=12)

        # Zoomed view setup (focus on resist ± some substrate)
        zoom_depth = 500  # nm into substrate
        self.ax_zoom.set_xlim(-200, 200)
        self.ax_zoom.set_ylim(-zoom_depth, self.resist_thickness + 50)
        self.ax_zoom.set_xlabel('Lateral Position (nm)', color='white', fontsize=11)
        self.ax_zoom.set_ylabel('Depth (nm)', color='white', fontsize=11)
        self.ax_zoom.tick_params(colors='white')
        self.ax_zoom.set_title('Resist Region (Zoomed)', color='white', fontsize=12)

        # Draw geometry on both axes
        for ax, max_x in [(self.ax_main, max_r), (self.ax_zoom, 200)]:
            # Resist
            resist = Rectangle((-max_x, 0), 2*max_x, self.resist_thickness,
                             facecolor='#2090a0', alpha=0.4, edgecolor='#40c0d0', linewidth=2)
            ax.add_patch(resist)

            # Substrate
            y_min = ax.get_ylim()[0]
            substrate = Rectangle((-max_x, y_min), 2*max_x, -y_min,
                                 facecolor='#404050', alpha=0.6, edgecolor='#606080', linewidth=1)
            ax.add_patch(substrate)

            # Interface lines
            ax.axhline(y=0, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(y=self.resist_thickness, color='#60a0b0', linestyle='--', alpha=0.5, linewidth=1)

            for spine in ax.spines.values():
                spine.set_color('#333366')

        # Labels
        self.ax_zoom.text(190, self.resist_thickness/2, 'Resist', color='#40c0d0',
                         fontsize=10, ha='right', va='center', fontweight='bold')

        # Energy colormap
        self.energy_cmap = plt.cm.plasma

        # Create line collections for each trajectory (on both axes)
        self.line_collections_main = []
        self.line_collections_zoom = []
        self.dots_main = []
        self.dots_zoom = []

        for _ in self.interp_data:
            # Main view
            lc_main = LineCollection([], cmap=self.energy_cmap,
                                    norm=plt.Normalize(0, self.beam_energy))
            lc_main.set_linewidth(1.5)
            self.ax_main.add_collection(lc_main)
            self.line_collections_main.append(lc_main)

            dot_main, = self.ax_main.plot([], [], 'o', markersize=4)
            self.dots_main.append(dot_main)

            # Zoom view
            lc_zoom = LineCollection([], cmap=self.energy_cmap,
                                    norm=plt.Normalize(0, self.beam_energy))
            lc_zoom.set_linewidth(2)
            self.ax_zoom.add_collection(lc_zoom)
            self.line_collections_zoom.append(lc_zoom)

            dot_zoom, = self.ax_zoom.plot([], [], 'o', markersize=6)
            self.dots_zoom.append(dot_zoom)

        # Colorbar
        sm = plt.cm.ScalarMappable(cmap=self.energy_cmap,
                                   norm=plt.Normalize(0, self.beam_energy))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=self.ax_zoom, shrink=0.5, pad=0.02)
        cbar.set_label('Energy (keV)', color='white', fontsize=9)
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

        # Controls
        ax_play = self.fig.add_axes([0.05, 0.02, 0.08, 0.04])
        ax_reset = self.fig.add_axes([0.15, 0.02, 0.08, 0.04])
        ax_slider = self.fig.add_axes([0.30, 0.02, 0.60, 0.03])

        self.btn_play = Button(ax_play, 'Play', color='#2090a0', hovercolor='#40c0d0')
        self.btn_play.label.set_color('white')
        self.btn_play.on_clicked(self.toggle_play)

        self.btn_reset = Button(ax_reset, 'Reset', color='#606080', hovercolor='#8080a0')
        self.btn_reset.label.set_color('white')
        self.btn_reset.on_clicked(self.reset)

        self.slider = Slider(ax_slider, 'Frame', 0, self.total_frames-1,
                            valinit=0, valstep=1, color='#2090a0')
        self.slider.label.set_color('white')
        self.slider.valtext.set_color('white')
        self.slider.on_changed(self.on_slider_change)

    def update_frame(self, frame):
        """Update visualization for given frame"""
        self.current_frame = frame
        progress = frame / self.total_frames

        n_electrons = len(self.interp_data)
        stagger = 0.3 / max(n_electrons - 1, 1)
        duration = 0.65

        for i, data in enumerate(self.interp_data):
            start_time = i * stagger
            electron_progress = np.clip((progress - start_time) / duration, 0, 1)

            r_vals = data['r']
            z_vals = data['z']
            e_vals = data['energy']

            n_points = int(electron_progress * len(r_vals))

            # Update both main and zoom views
            for lc, dot in [(self.line_collections_main[i], self.dots_main[i]),
                           (self.line_collections_zoom[i], self.dots_zoom[i])]:
                if n_points > 1:
                    points = np.array([r_vals[:n_points], z_vals[:n_points]]).T.reshape(-1, 1, 2)
                    segments = np.concatenate([points[:-1], points[1:]], axis=1)
                    lc.set_segments(segments)
                    lc.set_array(np.array(e_vals[:n_points-1]))

                    current_energy = e_vals[n_points-1]
                    dot_color = self.energy_cmap(current_energy / self.beam_energy)
                    dot.set_color(dot_color)
                    dot.set_data([r_vals[n_points-1]], [z_vals[n_points-1]])
                else:
                    lc.set_segments([])
                    dot.set_data([], [])

        self.fig.canvas.draw_idle()

    def toggle_play(self, event=None):
        """Toggle play/pause"""
        self.playing = not self.playing
        self.btn_play.label.set_text('Pause' if self.playing else 'Play')

        if self.playing:
            self.animate()

    def animate(self):
        """Animation loop"""
        if not self.playing:
            return

        self.current_frame += 1
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
            self.playing = False
            self.btn_play.label.set_text('Play')
            self.fig.canvas.draw_idle()
            return

        self.slider.set_val(self.current_frame)
        self.update_frame(self.current_frame)

        # Schedule next frame (30 fps = 33ms)
        self.timer = self.fig.canvas.new_timer(interval=33)
        self.timer.add_callback(self.animate)
        self.timer.single_shot = True
        self.timer.start()

    def reset(self, event=None):
        """Reset to beginning"""
        self.playing = False
        self.btn_play.label.set_text('Play')
        self.current_frame = 0
        self.slider.set_val(0)
        self.update_frame(0)

    def on_slider_change(self, val):
        """Handle slider change"""
        if not self.playing:
            self.update_frame(int(val))

    def show(self):
        """Display the viewer"""
        self.setup_figure()
        self.update_frame(0)
        plt.show()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Interactive electron trajectory viewer')
    parser.add_argument('json_file', help='Geant4 trajectory JSON file')
    parser.add_argument('--thickness', '-t', type=float, default=100,
                       help='Resist thickness in nm')
    parser.add_argument('--energy', '-e', type=float, default=100,
                       help='Beam energy in keV')
    parser.add_argument('--secondaries', '-s', action='store_true',
                       help='Show secondary electrons')

    args = parser.parse_args()

    viewer = InteractiveTrajectoryViewer(
        args.json_file,
        resist_thickness=args.thickness,
        beam_energy=args.energy,
        show_secondaries=args.secondaries
    )
    viewer.show()


if __name__ == "__main__":
    main()
