#!/usr/bin/env python3
"""
EBL Trajectory to Blender Exporter
==================================

Converts Geant4 trajectory JSON files to Blender-compatible Python scripts
for GPU-accelerated ray-traced rendering of electron beam trajectories.

Features:
- 3D electron paths with energy-based coloring
- Metalcone resist layer visualization (translucent)
- Silicon substrate with metallic shader
- GPU rendering via OptiX (RTX 4070)
- Animated camera orbit
- High-quality emissive materials for electrons

Usage:
    python ebl_to_blender.py trajectory.json [options]

Options:
    -o, --output    Output .blend filename (default: ebl_scene.blend)
    -t, --thickness Resist thickness in nm (default: 100)
    -e, --energy    Beam energy in keV for colorbar (default: 100)
    -m, --material  Resist material name (default: Metalcone)
    -f, --frames    Animation frames (default: 300)
    --scale         Scale factor for coordinates (default: 1.0)

Then in Blender (Windows):
    File > Open > output.blend
    Render > Render Animation (Ctrl+F12 for animation, F12 for single frame)

The script creates:
    - Primary electron tracks (plasma colormap by energy)
    - Secondary electrons (optional, orange)
    - Metalcone resist layer (translucent teal)
    - Silicon substrate (metallic gray)
    - Animated camera path
    - Professional lighting setup
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math


def energy_to_color(energy_keV: float, max_energy: float = 100.0) -> Tuple[float, float, float]:
    """
    Convert energy to plasma colormap color (like matplotlib).

    High energy = bright yellow/white
    Low energy = dark purple/blue
    """
    # Normalize energy
    t = min(max(energy_keV / max_energy, 0.0), 1.0)

    # Plasma colormap approximation
    # From dark purple (0) to yellow (1)
    if t < 0.25:
        r = 0.05 + t * 2
        g = 0.02 + t * 0.4
        b = 0.5 + t * 0.8
    elif t < 0.5:
        r = 0.55 + (t - 0.25) * 1.8
        g = 0.12 + (t - 0.25) * 0.8
        b = 0.7 - (t - 0.25) * 0.4
    elif t < 0.75:
        r = 1.0
        g = 0.32 + (t - 0.5) * 1.6
        b = 0.6 - (t - 0.5) * 1.6
    else:
        r = 1.0
        g = 0.72 + (t - 0.75) * 1.1
        b = 0.2 - (t - 0.75) * 0.6

    return (min(r, 1.0), min(g, 1.0), max(b, 0.0))


def generate_blender_script(trajectory_data: dict,
                            resist_thickness: float = 100.0,
                            beam_energy: float = 100.0,
                            material_name: str = "Metalcone",
                            animation_frames: int = 300,
                            output_blend: str = "ebl_scene.blend",
                            scale: float = 1.0,
                            show_secondaries: bool = False) -> str:
    """Generate a Blender Python script from trajectory data."""

    events = trajectory_data.get('events', [])
    if not events:
        print("No events found in trajectory data")
        return ""

    # Use first event for visualization
    event = events[0]
    tracks = event.get('tracks', {})

    # Collect track data
    track_list = []
    max_time = 0
    min_z = 0
    max_z = resist_thickness
    max_r = 0

    for track_id, track in tracks.items():
        particle = track.get('particle', 'unknown')
        parent_id = track.get('parent_id', 0)
        points = track.get('points', [])

        if not points:
            continue

        # Skip secondaries if not requested
        if not show_secondaries and int(track_id) != 1:
            continue

        # Extract coordinates
        coords = []
        for pt in points:
            x, y, z = pt[0] * scale, pt[1] * scale, pt[2] * scale
            energy = pt[3] if len(pt) > 3 else beam_energy
            time = pt[4] if len(pt) > 4 else len(coords) * 0.01
            coords.append((x, y, z, energy, time))
            max_time = max(max_time, time)
            min_z = min(min_z, z)
            max_z = max(max_z, z)
            max_r = max(max_r, abs(x), abs(y))

        # Classify track
        is_primary = int(track_id) == 1

        track_list.append({
            'id': track_id,
            'coords': coords,
            'is_primary': is_primary,
            'particle': particle
        })

    if not track_list:
        print("No tracks to visualize")
        return ""

    # Calculate scene bounds
    substrate_depth = abs(min_z) + 100  # Extra padding
    lateral_extent = max(max_r * 1.2, 500)  # At least 500nm

    # Camera distance based on scene size
    camera_distance = max(substrate_depth, lateral_extent) * 2

    # Generate Blender Python script
    script = f'''# Auto-generated Blender script for EBL trajectory visualization
# Run this script inside Blender: Scripting > Open > Run Script
# Or: blender --background --python this_script.py

import bpy
import math
from mathutils import Vector

print("=" * 60)
print("EBL Trajectory Visualization - Blender Scene Generator")
print("=" * 60)

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Delete all existing materials
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# ============================================================
# SCENE SETTINGS
# ============================================================
RESIST_THICKNESS = {resist_thickness}
BEAM_ENERGY = {beam_energy}
SUBSTRATE_DEPTH = {substrate_depth}
LATERAL_EXTENT = {lateral_extent}
CAMERA_DISTANCE = {camera_distance}
TOTAL_FRAMES = {animation_frames}
MAX_TIME = {max_time if max_time > 0 else 1.0}
MATERIAL_NAME = "{material_name}"

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = TOTAL_FRAMES
bpy.context.scene.render.fps = 30

# ============================================================
# GPU RENDERING SETUP (OptiX for RTX GPUs)
# ============================================================
bpy.context.scene.render.engine = 'CYCLES'

# Try to enable OptiX GPU rendering
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()

    # Enable all GPU devices
    for device in prefs.devices:
        if device.type == 'OPTIX':
            device.use = True
            print(f"Enabled GPU: {{device.name}}")

    bpy.context.scene.cycles.device = 'GPU'
    print("GPU rendering enabled via OptiX")
except Exception as e:
    print(f"GPU setup note: {{e}}")
    print("Falling back to CPU rendering")

# Render quality settings
bpy.context.scene.cycles.samples = 256
bpy.context.scene.cycles.use_denoising = True

# ============================================================
# MATERIAL DEFINITIONS
# ============================================================

def create_emission_material(name: str, color: tuple, strength: float = 10.0):
    """Create glowing emission material for electrons."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*color, 1.0)
    emission.inputs['Strength'].default_value = strength

    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat


def create_glass_material(name: str, color: tuple, transmission: float = 0.9):
    """Create glass-like material for resist."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    principled = nodes.new('ShaderNodeBsdfPrincipled')

    principled.inputs['Base Color'].default_value = (*color, 1.0)
    principled.inputs['Transmission Weight'].default_value = transmission
    principled.inputs['Roughness'].default_value = 0.1
    principled.inputs['IOR'].default_value = 1.5

    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    mat.blend_method = 'BLEND'
    mat.shadow_method = 'HASHED'

    return mat


def create_metallic_material(name: str, color: tuple, metallic: float = 0.9):
    """Create metallic material for substrate."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    principled = nodes.new('ShaderNodeBsdfPrincipled')

    principled.inputs['Base Color'].default_value = (*color, 1.0)
    principled.inputs['Metallic'].default_value = metallic
    principled.inputs['Roughness'].default_value = 0.3

    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    return mat


# Create materials
mat_resist = create_glass_material(
    "Resist_" + MATERIAL_NAME,
    (0.2, 0.7, 0.8),  # Teal color for metalcone
    transmission=0.85
)

mat_substrate = create_metallic_material(
    "Substrate_Silicon",
    (0.35, 0.35, 0.4),  # Gray silicon
    metallic=0.7
)

# Energy-based electron materials (plasma colormap)
electron_materials = {{}}
for i in range(11):
    energy_frac = i / 10.0
    # Plasma colormap approximation
    if energy_frac < 0.25:
        r, g, b = 0.05 + energy_frac * 2, 0.02 + energy_frac * 0.4, 0.5 + energy_frac * 0.8
    elif energy_frac < 0.5:
        r, g, b = 0.55 + (energy_frac - 0.25) * 1.8, 0.12 + (energy_frac - 0.25) * 0.8, 0.7 - (energy_frac - 0.25) * 0.4
    elif energy_frac < 0.75:
        r, g, b = 1.0, 0.32 + (energy_frac - 0.5) * 1.6, 0.6 - (energy_frac - 0.5) * 1.6
    else:
        r, g, b = 1.0, 0.72 + (energy_frac - 0.75) * 1.1, max(0.2 - (energy_frac - 0.75) * 0.6, 0)

    r, g, b = min(r, 1.0), min(g, 1.0), max(b, 0.0)

    mat_name = f"Electron_Energy_{{i}}"
    electron_materials[i] = create_emission_material(mat_name, (r, g, b), strength=8.0)

# Secondary electron material
mat_secondary = create_emission_material("Secondary_Electron", (1.0, 0.4, 0.2), strength=5.0)

# ============================================================
# GEOMETRY CREATION
# ============================================================

# Create resist layer
bpy.ops.mesh.primitive_cube_add(size=1)
resist = bpy.context.object
resist.name = "Resist_Layer"
resist.scale = (LATERAL_EXTENT, LATERAL_EXTENT, RESIST_THICKNESS / 2)
resist.location = (0, 0, RESIST_THICKNESS / 2)
resist.data.materials.append(mat_resist)

# Create substrate
bpy.ops.mesh.primitive_cube_add(size=1)
substrate = bpy.context.object
substrate.name = "Silicon_Substrate"
substrate.scale = (LATERAL_EXTENT * 1.2, LATERAL_EXTENT * 1.2, SUBSTRATE_DEPTH / 2)
substrate.location = (0, 0, -SUBSTRATE_DEPTH / 2)
substrate.data.materials.append(mat_substrate)

# ============================================================
# TRACK DATA
# ============================================================
tracks = {repr(track_list)}

# ============================================================
# CREATE ELECTRON TRACKS
# ============================================================

def get_energy_material(energy_keV: float, is_primary: bool):
    """Get material based on energy."""
    if not is_primary:
        return mat_secondary

    # Map energy to material index (0-10)
    idx = min(int((energy_keV / BEAM_ENERGY) * 10), 10)
    return electron_materials.get(idx, electron_materials[5])


def create_track_curve(track_data: dict, track_idx: int):
    """Create a Bezier curve for an electron track."""
    coords = track_data['coords']
    is_primary = track_data['is_primary']

    if len(coords) < 2:
        return None

    # Create curve object
    curve = bpy.data.curves.new(f"Track_{{track_idx}}", 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = 1.0 if is_primary else 0.5  # Thicker primary track
    curve.bevel_resolution = 4

    # Create spline
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(coords) - 1)

    # Set control points
    avg_energy = 0
    for i, (x, y, z, energy, time) in enumerate(coords):
        pt = spline.bezier_points[i]
        pt.co = (x, y, z)
        pt.handle_type = 'AUTO'
        avg_energy += energy

    avg_energy /= len(coords)

    # Create object
    obj = bpy.data.objects.new(f"Track_{{track_idx}}", curve)
    bpy.context.collection.objects.link(obj)

    # Assign material based on average energy
    mat = get_energy_material(avg_energy, is_primary)
    obj.data.materials.append(mat)

    # Animate track appearance based on time
    if coords:
        start_time = coords[0][4]
        start_frame = max(1, int((start_time / MAX_TIME) * TOTAL_FRAMES * 0.8))

        # Hide before start time
        obj.hide_render = True
        obj.hide_viewport = True
        obj.keyframe_insert('hide_render', frame=1)
        obj.keyframe_insert('hide_viewport', frame=1)

        # Appear at start time
        obj.hide_render = False
        obj.hide_viewport = False
        obj.keyframe_insert('hide_render', frame=start_frame)
        obj.keyframe_insert('hide_viewport', frame=start_frame)

    return obj


# Create all tracks
print(f"Creating {{len(tracks)}} electron tracks...")
for idx, track in enumerate(tracks):
    create_track_curve(track, idx)

# ============================================================
# CAMERA SETUP
# ============================================================

# Calculate camera position for good view
cam_x = CAMERA_DISTANCE * 0.7
cam_y = -CAMERA_DISTANCE * 0.7
cam_z = CAMERA_DISTANCE * 0.4

bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
camera = bpy.context.object
camera.name = "Main_Camera"
bpy.context.scene.camera = camera

# Point camera at center of resist
look_at = Vector((0, 0, RESIST_THICKNESS / 2))
direction = look_at - camera.location
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

# Camera orbit animation
camera.animation_data_create()

# Start position
camera.keyframe_insert('location', frame=1)
camera.keyframe_insert('rotation_euler', frame=1)

# End position (rotated 90 degrees)
camera.location = (cam_y * -1, cam_x, cam_z)
direction = look_at - camera.location
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()
camera.keyframe_insert('location', frame=TOTAL_FRAMES)
camera.keyframe_insert('rotation_euler', frame=TOTAL_FRAMES)

# ============================================================
# LIGHTING SETUP
# ============================================================

# Key light (sun)
bpy.ops.object.light_add(type='SUN', location=(100, 100, 200))
sun = bpy.context.object
sun.name = "Key_Light"
sun.data.energy = 3.0
sun.data.angle = math.radians(5)
sun.rotation_euler = (math.radians(45), math.radians(30), 0)

# Fill light (area)
bpy.ops.object.light_add(type='AREA', location=(-80, -80, 100))
fill = bpy.context.object
fill.name = "Fill_Light"
fill.data.energy = 800
fill.data.size = 50

# Rim light
bpy.ops.object.light_add(type='AREA', location=(0, 150, 50))
rim = bpy.context.object
rim.name = "Rim_Light"
rim.data.energy = 400
rim.data.size = 30

# ============================================================
# WORLD BACKGROUND
# ============================================================
world = bpy.data.worlds.new("Dark_Background")
bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs['Color'].default_value = (0.02, 0.02, 0.05, 1)  # Very dark blue

# ============================================================
# RENDER SETTINGS
# ============================================================
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.film_transparent = False

# Output settings for MP4
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.context.scene.render.ffmpeg.format = 'MPEG4'
bpy.context.scene.render.ffmpeg.codec = 'H264'
bpy.context.scene.render.ffmpeg.constant_rate_factor = 'HIGH'
bpy.context.scene.render.filepath = "//ebl_render"

# ============================================================
# SAVE BLEND FILE
# ============================================================
output_path = bpy.path.abspath("//") + "{output_blend}"
bpy.ops.wm.save_as_mainfile(filepath=output_path)

print("=" * 60)
print("Blender scene created successfully!")
print(f"Tracks: {{len(tracks)}}")
print(f"Resist: {{RESIST_THICKNESS}} nm {material_name}")
print(f"Beam energy: {{BEAM_ENERGY}} keV")
print(f"Output: {{output_path}}")
print("=" * 60)
print("")
print("To render:")
print("  - Single frame: Press F12")
print("  - Animation: Press Ctrl+F12")
print("  - Output will be saved to the blend file directory")
'''

    return script


def main():
    parser = argparse.ArgumentParser(
        description='Convert EBL trajectories to Blender scene',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python ebl_to_blender.py traj_Zincone_100keV.json
    python ebl_to_blender.py traj.json -o zincone_scene.blend -m Zincone
    python ebl_to_blender.py traj.json --thickness 100 --energy 100 --frames 300

Then in Blender:
    File > Open > output.blend
    Press F12 for single frame, Ctrl+F12 for animation
'''
    )

    parser.add_argument('input', help='Input trajectory JSON file')
    parser.add_argument('-o', '--output', default='ebl_scene.blend',
                        help='Output .blend filename (default: ebl_scene.blend)')
    parser.add_argument('-t', '--thickness', type=float, default=100.0,
                        help='Resist thickness in nm (default: 100)')
    parser.add_argument('-e', '--energy', type=float, default=100.0,
                        help='Beam energy in keV for color scale (default: 100)')
    parser.add_argument('-m', '--material', default='Metalcone',
                        help='Resist material name (default: Metalcone)')
    parser.add_argument('-f', '--frames', type=int, default=300,
                        help='Animation frame count (default: 300)')
    parser.add_argument('--scale', type=float, default=1.0,
                        help='Scale factor for coordinates (default: 1.0)')
    parser.add_argument('--secondaries', action='store_true',
                        help='Include secondary electrons (default: primary only)')

    args = parser.parse_args()

    # Load trajectory data
    print(f"Loading trajectory data from {args.input}...")
    try:
        with open(args.input, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # Generate Blender script
    script = generate_blender_script(
        data,
        resist_thickness=args.thickness,
        beam_energy=args.energy,
        material_name=args.material,
        animation_frames=args.frames,
        output_blend=args.output,
        scale=args.scale,
        show_secondaries=args.secondaries
    )

    if not script:
        print("Failed to generate script")
        return

    # Save as Python script
    script_path = Path(args.input).stem + '_blender.py'
    with open(script_path, 'w') as f:
        f.write(script)

    print(f"\nBlender script saved to: {script_path}")
    print("\n" + "=" * 50)
    print("To use:")
    print("=" * 50)
    print("  1. Open Blender on Windows")
    print("  2. Go to: Scripting workspace")
    print("  3. Click: Open > select the .py file")
    print("  4. Click: Run Script")
    print("")
    print("Or from command line:")
    print(f"  blender --background --python {script_path}")
    print("")
    print(f"The script will create: {args.output}")
    print("=" * 50)


if __name__ == '__main__':
    main()
