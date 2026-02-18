#!/usr/bin/env python3
"""
Blender Trajectory Export for EBL Simulations

Exports electron trajectory data to formats Blender can import:
1. JSON with trajectory data + materials for Blender Python scripting
2. OBJ mesh export with vertex colors encoded as UV coordinates
3. Direct Blender Python script generator

Usage in Blender:
  1. File > Import > Run Python script (trajectory_blender_import.py)
  OR
  2. Load the JSON and use the provided Blender addon

Author: EBL Simulation Project
"""

import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import colorsys


@dataclass
class BlenderTrajectory:
    """Trajectory data formatted for Blender import."""
    points: List[List[float]]  # [[x, y, z], ...]
    energies: List[float]      # [keV, ...]
    colors: List[List[float]]  # [[r, g, b], ...] normalized 0-1
    track_id: int
    particle: str
    path_length: float


@dataclass
class BlenderScene:
    """Complete scene data for Blender."""
    trajectories: List[BlenderTrajectory]
    resist_thickness: float  # nm
    resist_material: str
    substrate_depth: float   # nm
    beam_energy: float       # keV
    scale_factor: float      # nm to Blender units
    colormap: str            # "plasma", "viridis", etc.


def energy_to_rgb(energy: float, max_energy: float, colormap: str = "plasma") -> Tuple[float, float, float]:
    """Convert energy value to RGB color using a colormap."""
    import matplotlib.pyplot as plt

    # Normalize energy
    norm_e = np.clip(energy / max_energy, 0, 1)

    # Get colormap
    cmap = plt.cm.get_cmap(colormap)
    rgba = cmap(norm_e)

    return (rgba[0], rgba[1], rgba[2])


class BlenderExporter:
    """Export trajectory data for Blender rendering."""

    def __init__(self, resist_thickness: float = 100, beam_energy: float = 100,
                 scale_factor: float = 0.001):
        """
        Args:
            resist_thickness: Resist thickness in nm
            beam_energy: Beam energy in keV
            scale_factor: Convert nm to Blender units (0.001 = 1nm = 0.001 BU)
        """
        self.resist_thickness = resist_thickness
        self.beam_energy = beam_energy
        self.scale_factor = scale_factor
        self.trajectories: List[BlenderTrajectory] = []
        self.resist_material = "Resist"

    def load_geant4_json(self, json_file: str) -> bool:
        """Load trajectory data from Geant4 JSON output."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            self.trajectories = []

            for event in data.get('events', []):
                tracks = event.get('tracks', {})

                for track_id, track_data in tracks.items():
                    raw_points = track_data.get('points', [])
                    particle = track_data.get('particle', 'e-')

                    if len(raw_points) < 2:
                        continue

                    points = []
                    energies = []
                    colors = []
                    path_length = 0

                    for i, pt in enumerate(raw_points):
                        if len(pt) >= 4:
                            x, y, z, e = pt[0], pt[1], pt[2], pt[3]

                            # Scale coordinates
                            scaled_point = [
                                x * self.scale_factor,
                                y * self.scale_factor,
                                z * self.scale_factor
                            ]
                            points.append(scaled_point)
                            energies.append(e)

                            # Calculate color
                            rgb = energy_to_rgb(e, self.beam_energy, "plasma")
                            colors.append(list(rgb))

                            # Calculate path length
                            if i > 0:
                                prev = raw_points[i-1]
                                dx = pt[0] - prev[0]
                                dy = pt[1] - prev[1]
                                dz = pt[2] - prev[2]
                                path_length += np.sqrt(dx**2 + dy**2 + dz**2)

                    if points:
                        traj = BlenderTrajectory(
                            points=points,
                            energies=energies,
                            colors=colors,
                            track_id=int(track_id),
                            particle=particle,
                            path_length=path_length * self.scale_factor
                        )
                        self.trajectories.append(traj)

            print(f"Loaded {len(self.trajectories)} trajectories from {json_file}")
            return True

        except Exception as e:
            print(f"Error loading JSON: {e}")
            return False

    def export_blender_json(self, output_file: str) -> str:
        """Export complete scene data as JSON for Blender import."""
        # Calculate substrate depth from trajectory data
        all_z = []
        for traj in self.trajectories:
            all_z.extend([p[2] for p in traj.points])

        substrate_depth = abs(min(all_z)) if all_z else 500 * self.scale_factor

        scene = BlenderScene(
            trajectories=[asdict(t) for t in self.trajectories],
            resist_thickness=self.resist_thickness * self.scale_factor,
            resist_material=self.resist_material,
            substrate_depth=substrate_depth,
            beam_energy=self.beam_energy,
            scale_factor=self.scale_factor,
            colormap="plasma"
        )

        with open(output_file, 'w') as f:
            json.dump(asdict(scene), f, indent=2)

        print(f"Exported Blender JSON: {output_file}")
        return output_file

    def generate_blender_script(self, output_file: str, json_filename: str) -> str:
        """Generate a Python script that can be run directly in Blender.

        Args:
            output_file: Path to write the Python script
            json_filename: Just the filename (not full path) of the JSON data file
        """

        script = f'''"""
Blender Import Script for EBL Electron Trajectories

Run this script in Blender's Text Editor or via:
  blender --python trajectory_blender_import.py

Generated for: {self.resist_material} at {self.beam_energy} keV

Features:
- Organized collections (Geometry, Trajectories, Lights, Camera)
- Enhanced materials with volumetric glow effects
- Pre-configured render settings for EEVEE and Cycles
- Ready to render immediately after import
"""

import bpy
import bmesh
import json
import math
from mathutils import Vector

# === CONFIGURATION ===
JSON_FILE = r"C:\\Users\\dreec\\OneDrive - UW\\Desktop\\blender_export\\{json_filename}"
TUBE_RADIUS = 0.003  # Trajectory tube radius in Blender units
TUBE_RESOLUTION = 8   # Segments around tube
ANIMATE = True        # Create animation
ANIMATION_FRAMES = 180  # Total animation frames
FPS = 30
USE_EEVEE = True      # True for fast renders, False for Cycles quality

# === SCENE ORGANIZATION ===
def setup_collections():
    """Create organized collection structure."""
    # Get or create main collection
    scene_col = bpy.context.scene.collection

    # Create sub-collections
    collections = {{}}
    for name in ["Geometry", "Trajectories", "Lights", "Camera"]:
        col = bpy.data.collections.get(f"EBL_{{name}}")
        if col is None:
            col = bpy.data.collections.new(f"EBL_{{name}}")
            scene_col.children.link(col)
        collections[name] = col

    return collections

def link_to_collection(obj, collection_name, collections):
    """Link object to specific collection and unlink from others."""
    # Unlink from all collections first
    for col in obj.users_collection:
        col.objects.unlink(obj)
    # Link to target collection
    collections[collection_name].objects.link(obj)

# === CLEAR EXISTING ===
def clear_scene():
    """Remove existing trajectory objects and collections."""
    # Remove objects
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Trajectory_") or obj.name.startswith("EBL_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Remove old collections
    for col in list(bpy.data.collections):
        if col.name.startswith("EBL_"):
            bpy.data.collections.remove(col)

# === ENHANCED MATERIALS ===
def create_energy_material(name, color):
    """Create an emission material with volumetric glow effect."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Emission shader with high strength for bloom
    emission = nodes.new(type='ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*color, 1.0)
    emission.inputs['Strength'].default_value = 8.0  # High for EEVEE bloom
    emission.location = (0, 0)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    # Enable backface culling for performance
    mat.use_backface_culling = True

    return mat

def create_resist_material():
    """Create glass-like resist material with refraction."""
    mat = bpy.data.materials.new(name="EBL_Resist_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Glass-like principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.1, 0.7, 0.8, 1.0)  # Cyan tint
    bsdf.inputs['Alpha'].default_value = 0.25  # Semi-transparent
    bsdf.inputs['Roughness'].default_value = 0.05  # Very smooth/glossy
    bsdf.inputs['IOR'].default_value = 1.45  # Glass-like refraction
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    bsdf.location = (0, 0)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Transparency settings
    mat.blend_method = 'BLEND'
    mat.shadow_method = 'HASHED'
    mat.use_screen_refraction = True

    return mat

def create_substrate_material():
    """Create brushed silicon substrate material."""
    mat = bpy.data.materials.new(name="EBL_Substrate_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Brushed metal look
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.25, 0.25, 0.3, 1.0)  # Dark gray-blue
    bsdf.inputs['Metallic'].default_value = 0.9  # Highly metallic
    bsdf.inputs['Roughness'].default_value = 0.35  # Slightly brushed
    bsdf.inputs['Specular IOR Level'].default_value = 0.8
    bsdf.location = (0, 0)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat

# === RENDER SETTINGS ===
def setup_render_settings():
    """Configure render settings for optimal quality/speed."""
    scene = bpy.context.scene

    # Animation settings
    scene.frame_start = 1
    scene.frame_end = ANIMATION_FRAMES
    scene.render.fps = FPS

    # Output settings
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    # Output format - MP4 video
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'

    if USE_EEVEE:
        # EEVEE settings (fast, good for preview)
        scene.render.engine = 'BLENDER_EEVEE_NEXT'

        # Enable bloom for glow effects
        scene.eevee.use_bloom = True
        scene.eevee.bloom_threshold = 0.5
        scene.eevee.bloom_intensity = 0.3
        scene.eevee.bloom_radius = 6.0

        # Screen space reflections
        scene.eevee.use_ssr = True
        scene.eevee.use_ssr_refraction = True

        # Ambient occlusion
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 0.2

        # Samples
        scene.eevee.taa_render_samples = 64
        scene.eevee.taa_samples = 16

        print("  Render: EEVEE (fast) with bloom enabled")
    else:
        # Cycles settings (high quality)
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'GPU'
        scene.cycles.samples = 256
        scene.cycles.use_denoising = True

        print("  Render: Cycles (quality) with GPU acceleration")

    # Color management
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'

    print(f"  Output: 1920x1080 @ {{FPS}}fps, {{ANIMATION_FRAMES}} frames")

# === CREATE GEOMETRY ===
def create_trajectory_curve(points, colors, name, radius=0.003, collections=None):
    """Create a curve object from trajectory points with vertex colors."""

    # Create curve data
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = TUBE_RESOLUTION

    # Create spline
    spline = curve_data.splines.new(type='POLY')
    spline.points.add(len(points) - 1)

    for i, (pt, color) in enumerate(zip(points, colors)):
        spline.points[i].co = (*pt, 1.0)  # x, y, z, w

    # Create object
    curve_obj = bpy.data.objects.new(name, curve_data)

    # Link to Trajectories collection
    if collections:
        collections["Trajectories"].objects.link(curve_obj)
    else:
        bpy.context.collection.objects.link(curve_obj)

    # Apply average color as material (weighted toward start for energy-based color)
    # Use first 30% of points for color (high energy region)
    n_color_pts = max(1, len(colors) // 3)
    avg_color = [sum(c[i] for c in colors[:n_color_pts])/n_color_pts for i in range(3)]
    mat = create_energy_material(f"Mat_{{name}}", avg_color)
    curve_obj.data.materials.append(mat)

    return curve_obj

def create_resist_box(thickness, size=1.0, collections=None):
    """Create resist layer geometry."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    resist = bpy.context.active_object
    resist.name = "EBL_Resist"
    resist.scale = (size, size, thickness / 2)
    resist.location = (0, 0, thickness / 2)

    mat = create_resist_material()
    resist.data.materials.append(mat)

    # Link to Geometry collection
    if collections:
        link_to_collection(resist, "Geometry", collections)

    return resist

def create_substrate(depth, size=1.0, collections=None):
    """Create substrate geometry."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    substrate = bpy.context.active_object
    substrate.name = "EBL_Substrate"
    substrate.scale = (size, size, depth / 2)
    substrate.location = (0, 0, -depth / 2)

    mat = create_substrate_material()
    substrate.data.materials.append(mat)

    # Link to Geometry collection
    if collections:
        link_to_collection(substrate, "Geometry", collections)

    return substrate

def create_lighting(view_distance, collections=None):
    """Create 3-point lighting setup."""
    lights = []

    # Key light (main light, warm)
    bpy.ops.object.light_add(type='AREA', location=(view_distance, -view_distance, view_distance * 0.8))
    key = bpy.context.active_object
    key.name = "EBL_Key_Light"
    key.data.energy = 500
    key.data.size = view_distance * 0.5
    key.data.color = (1.0, 0.95, 0.9)  # Warm white
    key.rotation_euler = (math.radians(45), 0, math.radians(45))
    lights.append(key)

    # Fill light (softer, cooler)
    bpy.ops.object.light_add(type='AREA', location=(-view_distance * 0.7, -view_distance * 0.5, view_distance * 0.4))
    fill = bpy.context.active_object
    fill.name = "EBL_Fill_Light"
    fill.data.energy = 200
    fill.data.size = view_distance * 0.8
    fill.data.color = (0.9, 0.95, 1.0)  # Cool white
    fill.rotation_euler = (math.radians(60), 0, math.radians(-30))
    lights.append(fill)

    # Rim light (backlight for edge definition)
    bpy.ops.object.light_add(type='AREA', location=(0, view_distance * 0.8, view_distance * 0.3))
    rim = bpy.context.active_object
    rim.name = "EBL_Rim_Light"
    rim.data.energy = 300
    rim.data.size = view_distance * 0.3
    rim.data.color = (0.8, 0.9, 1.0)  # Slightly blue
    rim.rotation_euler = (math.radians(120), 0, math.radians(180))
    lights.append(rim)

    # Link to Lights collection
    if collections:
        for light in lights:
            link_to_collection(light, "Lights", collections)

    return lights

# === ANIMATION ===
def animate_trajectory(curve_obj, start_frame, end_frame):
    """Animate trajectory growth using bevel factor."""
    curve_obj.data.bevel_factor_end = 0.0
    curve_obj.data.keyframe_insert(data_path="bevel_factor_end", frame=start_frame)

    curve_obj.data.bevel_factor_end = 1.0
    curve_obj.data.keyframe_insert(data_path="bevel_factor_end", frame=end_frame)

    # Set interpolation to linear for constant speed
    fcurve = curve_obj.data.animation_data.action.fcurves[0]
    for kf in fcurve.keyframe_points:
        kf.interpolation = 'LINEAR'

# === MAIN IMPORT ===
def import_trajectories(json_file):
    """Import all trajectory data from JSON."""
    print("=" * 50)
    print("EBL Trajectory Import for Blender")
    print("=" * 50)

    with open(json_file, 'r') as f:
        data = json.load(f)

    # Clear existing and setup collections
    clear_scene()
    collections = setup_collections()
    print("  Created collection structure")

    # Create geometry
    resist_thickness = data.get('resist_thickness', 0.1)
    substrate_depth = data.get('substrate_depth', 0.5)
    size = max(substrate_depth * 2, 1.0)

    resist = create_resist_box(resist_thickness, size, collections)
    substrate = create_substrate(substrate_depth, size, collections)
    print(f"  Geometry: resist={{resist_thickness*1000:.0f}}nm, substrate={{substrate_depth*1000:.0f}}nm")

    # Create trajectories
    trajectories = data.get('trajectories', [])
    curve_objects = []

    for i, traj in enumerate(trajectories):
        points = traj['points']
        colors = traj['colors']
        track_id = traj.get('track_id', i)

        name = f"Trajectory_{{track_id:03d}}"
        curve = create_trajectory_curve(points, colors, name, TUBE_RADIUS, collections)
        curve_objects.append(curve)

    print(f"  Created {{len(curve_objects)}} trajectory curves")

    # Animation
    if ANIMATE and curve_objects:
        # Stagger trajectory animations
        n_traj = len(curve_objects)
        frames_per_traj = int(ANIMATION_FRAMES * 0.8 / max(n_traj, 1))

        for i, curve in enumerate(curve_objects):
            start = int(i * frames_per_traj * 0.3) + 1
            end = start + frames_per_traj
            animate_trajectory(curve, start, min(end, ANIMATION_FRAMES))

        print(f"  Animation: {{ANIMATION_FRAMES}} frames with staggered growth")

    # Setup camera and lighting
    cam = setup_camera(substrate_depth, collections)
    lights = create_lighting(substrate_depth, collections)
    print(f"  Added camera and 3-point lighting")

    # Configure render settings
    setup_render_settings()

    # Delete default objects if they exist
    for name in ["Cube", "Light", "Camera"]:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    print("=" * 50)
    print("Import complete! Ready to render.")
    print("  - Press F12 for single frame")
    print("  - Press Ctrl+F12 for animation")
    print("=" * 50)

def setup_camera(view_distance, collections=None):
    """Setup camera for good view of scene."""
    cam_data = bpy.data.cameras.new(name="EBL_Camera")
    cam_data.lens = 50  # Standard lens
    cam_data.clip_start = 0.001
    cam_data.clip_end = 1000

    cam_obj = bpy.data.objects.new("EBL_Camera", cam_data)

    # Link to Camera collection
    if collections:
        collections["Camera"].objects.link(cam_obj)
    else:
        bpy.context.collection.objects.link(cam_obj)

    # Position camera for good view
    cam_obj.location = (view_distance * 1.2, -view_distance * 1.5, view_distance * 0.6)
    cam_obj.rotation_euler = (math.radians(65), 0, math.radians(40))

    bpy.context.scene.camera = cam_obj
    return cam_obj

# === RUN ===
if __name__ == "__main__":
    import_trajectories(JSON_FILE)
'''

        with open(output_file, 'w') as f:
            f.write(script)

        print(f"Generated Blender script: {output_file}")
        return output_file


def export_all_trajectories():
    """Export all trajectory files for Blender."""
    traj_dir = Path(__file__).parent / "metalcone_animations_final" / "trajectories"
    output_dir = Path(__file__).parent / "metalcone_animations_final" / "blender_export"
    output_dir.mkdir(exist_ok=True)

    materials = {
        "Alucone": 1.5,
        "Zincone": 2.0,
        "Tincone": 2.5,
    }

    energies = [10, 100]

    print("=" * 70)
    print("Exporting Trajectory Data for Blender")
    print("=" * 70)
    print()

    exported = []

    for material, density in materials.items():
        for energy in energies:
            json_file = traj_dir / f"traj_{material}_{energy}keV.json"

            if not json_file.exists():
                print(f"SKIP: {json_file.name} not found")
                continue

            print(f"\n>>> {material} at {energy} keV")

            exporter = BlenderExporter(
                resist_thickness=100,
                beam_energy=energy,
                scale_factor=0.001  # 1nm = 0.001 Blender units
            )
            exporter.resist_material = material

            if exporter.load_geant4_json(str(json_file)):
                # Export JSON for Blender
                blender_json = output_dir / f"blender_{material}_{energy}keV.json"
                exporter.export_blender_json(str(blender_json))

                # Generate Blender import script (use just filename for portability)
                blender_script = output_dir / f"import_{material}_{energy}keV.py"
                exporter.generate_blender_script(str(blender_script), blender_json.name)

                exported.append((blender_json, blender_script))

    print()
    print("=" * 70)
    print(f"Exported {len(exported)} trajectory datasets for Blender")
    print("=" * 70)
    print()
    print("To import in Blender:")
    print("  1. Open Blender")
    print("  2. Go to Scripting workspace")
    print("  3. Open one of the import_*.py scripts")
    print("  4. Click 'Run Script'")
    print()
    print("Output files:")
    for json_f, script_f in exported:
        print(f"  {json_f.name}")
        print(f"  {script_f.name}")

    return exported


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export trajectories for Blender")
    parser.add_argument("--json", type=str, help="Single JSON file to export")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--all", action="store_true", help="Export all trajectory files")
    args = parser.parse_args()

    if args.all or not args.json:
        export_all_trajectories()
    elif args.json:
        output_dir = Path(args.output) if args.output else Path(args.json).parent

        exporter = BlenderExporter()
        if exporter.load_geant4_json(args.json):
            base_name = Path(args.json).stem
            json_filename = f"blender_{base_name}.json"
            exporter.export_blender_json(str(output_dir / json_filename))
            exporter.generate_blender_script(
                str(output_dir / f"import_{base_name}.py"),
                json_filename  # Just the filename for portability
            )


if __name__ == "__main__":
    main()
