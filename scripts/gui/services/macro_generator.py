"""
Geant4 macro generation service
"""

from typing import List, Dict, Any
from pathlib import Path
import textwrap

from ..models.simulation_model import SimulationModel


class MacroGeneratorService:
    """Service for generating Geant4 macro files"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent.parent.parent / "macros"
    
    def generate_macro(self, sim_model: SimulationModel, output_path: Path) -> str:
        """Generate complete macro file from simulation model"""
        
        macro_content = self._generate_header_comment(sim_model)
        macro_content += self._generate_initialization()
        macro_content += self._generate_detector_config(sim_model)
        macro_content += self._generate_physics_config(sim_model)
        macro_content += self._generate_beam_config(sim_model)
        macro_content += self._generate_output_config(sim_model, output_path)
        macro_content += self._generate_run_commands(sim_model)
        
        return macro_content
    
    def _generate_header_comment(self, sim_model: SimulationModel) -> str:
        """Generate header comment with simulation parameters"""
        return textwrap.dedent(f"""
            # EBL Simulation Macro
            # Generated automatically by EBL GUI
            # 
            # Simulation Parameters:
            # - Material: {sim_model.material.name}
            # - Beam Energy: {sim_model.beam.energy} keV
            # - Events: {sim_model.num_events}
            # - Physics: {sim_model.physics_list}
            #
            
        """)
    
    def _generate_initialization(self) -> str:
        """Generate initialization commands"""
        return textwrap.dedent("""
            # Initialize Geant4 kernel
            /run/initialize
            
        """)
    
    def _generate_detector_config(self, sim_model: SimulationModel) -> str:
        """Generate detector configuration commands"""
        material = sim_model.material
        
        return textwrap.dedent(f"""
            # Detector Configuration
            /det/setResistComposition "{material.composition}"
            /det/setResistThickness {material.thickness} nm
            /det/setResistDensity {material.density} g/cm3
            /det/update
            
        """)
    
    def _generate_physics_config(self, sim_model: SimulationModel) -> str:
        """Generate physics configuration commands"""
        commands = [
            "# Physics Configuration",
            f"/physics/setStepLimit {sim_model.step_limit} nm"
        ]
        
        if sim_model.enable_fluorescence:
            commands.append("/process/em/fluo true")
        
        if sim_model.enable_auger:
            commands.append("/process/em/auger true")
        
        if sim_model.enable_pixe:
            commands.append("/process/em/pixe true")
        
        commands.append("")
        return "\n".join(commands) + "\n"
    
    def _generate_beam_config(self, sim_model: SimulationModel) -> str:
        """Generate beam configuration commands"""
        beam = sim_model.beam
        
        return textwrap.dedent(f"""
            # Beam Configuration
            /gun/particle {beam.particle_type}
            /gun/energy {beam.energy} keV
            /gun/position {beam.position_x} {beam.position_y} {beam.position_z} nm
            /gun/direction {beam.direction_x} {beam.direction_y} {beam.direction_z}
            /gun/beamSize {beam.beam_size} nm
            
        """)
    
    def _generate_output_config(self, sim_model: SimulationModel, output_path: Path) -> str:
        """Generate output configuration commands"""
        output_dir = output_path.parent
        
        return textwrap.dedent(f"""
            # Output Configuration
            /output/setDirectory {output_dir}
            /output/setPrefix {sim_model.output_prefix}
            /output/setRadialBins {sim_model.radial_bins}
            /output/setDepthBins {sim_model.depth_bins}
            /output/setMaxRadius {sim_model.max_radius} nm
            /output/enableLogBinning {str(sim_model.log_binning).lower()}
            
        """)
    
    def _generate_run_commands(self, sim_model: SimulationModel) -> str:
        """Generate run commands"""
        return textwrap.dedent(f"""
            # Run Simulation
            /run/beamOn {sim_model.num_events}
            
            # Exit
            exit
        """)
    
    def save_macro(self, sim_model: SimulationModel, macro_path: Path, output_path: Path) -> None:
        """Generate and save macro file"""
        macro_content = self.generate_macro(sim_model, output_path)
        
        macro_path.parent.mkdir(parents=True, exist_ok=True)
        with open(macro_path, 'w') as f:
            f.write(macro_content)
    
    def load_template_macro(self, template_name: str) -> str:
        """Load a template macro file"""
        template_path = self.template_dir / f"{template_name}.mac"
        if template_path.exists():
            return template_path.read_text()
        return ""
    
    def get_available_templates(self) -> List[str]:
        """Get list of available macro templates"""
        if not self.template_dir.exists():
            return []
        
        templates = []
        for macro_file in self.template_dir.glob("**/*.mac"):
            rel_path = macro_file.relative_to(self.template_dir)
            templates.append(str(rel_path.with_suffix('')))
        
        return sorted(templates)