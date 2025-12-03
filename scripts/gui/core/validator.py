"""
Simulation Input Validation System
Validates all parameters before running simulations
"""

from pathlib import Path
from typing import Tuple, List, Optional
import os


class ValidationError:
    """Represents a validation error"""
    def __init__(self, field: str, message: str, severity: str = "error"):
        self.field = field
        self.message = message
        self.severity = severity  # "error" or "warning"

    def __str__(self):
        prefix = "❌ Error" if self.severity == "error" else "⚠️  Warning"
        return f"{prefix} [{self.field}]: {self.message}"


class SimulationValidator:
    """Validates simulation parameters before execution"""

    @staticmethod
    def validate_beam_parameters(energy: float, beam_size: float,
                                 pos_z: float, dir_z: float) -> List[ValidationError]:
        """
        Validate beam parameters

        Args:
            energy: Beam energy in keV
            beam_size: Beam size (FWHM) in nm
            pos_z: Z position in nm
            dir_z: Z direction component

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Energy validation
        if energy <= 0:
            errors.append(ValidationError(
                "Beam Energy",
                "Energy must be greater than 0 keV"
            ))
        elif energy < 10:
            errors.append(ValidationError(
                "Beam Energy",
                f"Energy {energy} keV is very low. Typical EBL uses 50-125 keV",
                "warning"
            ))
        elif energy > 300:
            errors.append(ValidationError(
                "Beam Energy",
                f"Energy {energy} keV is very high. Typical EBL uses 50-125 keV",
                "warning"
            ))

        # Beam size validation - 0nm (point source) is valid for PSF generation
        if beam_size < 0:
            errors.append(ValidationError(
                "Beam Size",
                "Beam size cannot be negative"
            ))
        elif beam_size == 0:
            # Point source is valid - BEAMER applies blur correction separately
            pass
        elif beam_size < 0.5:
            errors.append(ValidationError(
                "Beam Size",
                f"Beam size {beam_size} nm is extremely small. Use 0 nm for point source or typical range 2-10 nm",
                "warning"
            ))
        elif beam_size > 100:
            errors.append(ValidationError(
                "Beam Size",
                f"Beam size {beam_size} nm is very large. Typical range is 2-10 nm",
                "warning"
            ))

        # Position Z validation (beam starts above sample)
        if pos_z < 0:
            errors.append(ValidationError(
                "Beam Z Position",
                "Z position should be positive (beam starts above sample)"
            ))

        # Direction validation (should point downward for EBL)
        if dir_z >= 0:
            errors.append(ValidationError(
                "Beam Direction",
                "Z direction should be negative (pointing downward toward sample)",
                "warning"
            ))

        return errors

    @staticmethod
    def validate_material_parameters(composition: str, thickness: float,
                                     density: float) -> List[ValidationError]:
        """
        Validate material parameters

        Args:
            composition: Chemical composition
            thickness: Resist thickness in nm
            density: Material density in g/cm³

        Returns:
            List of validation errors
        """
        errors = []

        # Composition validation
        if not composition or not composition.strip():
            errors.append(ValidationError(
                "Material Composition",
                "Composition cannot be empty"
            ))

        # Thickness validation
        if thickness <= 0:
            errors.append(ValidationError(
                "Resist Thickness",
                "Thickness must be greater than 0 nm"
            ))
        elif thickness < 5:
            errors.append(ValidationError(
                "Resist Thickness",
                f"Thickness {thickness} nm is very thin. Typical range is 10-100 nm",
                "warning"
            ))
        elif thickness > 500:
            errors.append(ValidationError(
                "Resist Thickness",
                f"Thickness {thickness} nm is very thick. Typical range is 10-100 nm",
                "warning"
            ))

        # Density validation
        if density <= 0:
            errors.append(ValidationError(
                "Material Density",
                "Density must be greater than 0 g/cm³"
            ))
        elif density < 0.5:
            errors.append(ValidationError(
                "Material Density",
                f"Density {density} g/cm³ is very low. Typical range is 1.0-2.5 g/cm³",
                "warning"
            ))
        elif density > 5.0:
            errors.append(ValidationError(
                "Material Density",
                f"Density {density} g/cm³ is very high. Typical range is 1.0-2.5 g/cm³",
                "warning"
            ))

        return errors

    @staticmethod
    def validate_simulation_parameters(events: int, seed: int) -> List[ValidationError]:
        """
        Validate simulation parameters

        Args:
            events: Number of events to simulate
            seed: Random seed

        Returns:
            List of validation errors
        """
        errors = []

        # Events validation
        if events <= 0:
            errors.append(ValidationError(
                "Number of Events",
                "Number of events must be greater than 0"
            ))
        elif events < 1000:
            errors.append(ValidationError(
                "Number of Events",
                f"{events} events may have poor statistics. Consider at least 10,000 for testing",
                "warning"
            ))
        elif events > 10000000:  # 10M
            errors.append(ValidationError(
                "Number of Events",
                f"{events:,} events will take very long to simulate. Consider reducing for testing",
                "warning"
            ))

        # Seed validation (informational only)
        if seed == -1:
            # This is fine - means auto-generate
            pass
        elif seed < 0:
            errors.append(ValidationError(
                "Random Seed",
                "Random seed should be -1 (auto) or >= 0",
                "warning"
            ))

        return errors

    @staticmethod
    def validate_file_paths(executable_path: str, working_dir: str,
                           geant4_path: Optional[Path] = None) -> List[ValidationError]:
        """
        Validate file paths and directories

        Args:
            executable_path: Path to simulation executable
            working_dir: Working directory path
            geant4_path: Optional Geant4 installation path

        Returns:
            List of validation errors
        """
        errors = []

        # Executable validation
        if not executable_path:
            errors.append(ValidationError(
                "Executable Path",
                "No executable selected"
            ))
        else:
            exe_path = Path(executable_path)
            if not exe_path.exists():
                errors.append(ValidationError(
                    "Executable Path",
                    f"Executable not found: {executable_path}"
                ))
            elif not exe_path.is_file():
                errors.append(ValidationError(
                    "Executable Path",
                    f"Path is not a file: {executable_path}"
                ))
            elif not os.access(exe_path, os.X_OK):
                errors.append(ValidationError(
                    "Executable Path",
                    f"File is not executable: {executable_path}",
                    "warning"
                ))

        # Working directory validation
        if not working_dir:
            errors.append(ValidationError(
                "Working Directory",
                "No working directory specified"
            ))
        else:
            work_path = Path(working_dir)
            if not work_path.exists():
                errors.append(ValidationError(
                    "Working Directory",
                    f"Directory does not exist: {working_dir}"
                ))
            elif not work_path.is_dir():
                errors.append(ValidationError(
                    "Working Directory",
                    f"Path is not a directory: {working_dir}"
                ))
            elif not os.access(work_path, os.W_OK):
                errors.append(ValidationError(
                    "Working Directory",
                    f"Directory is not writable: {working_dir}"
                ))

        # Geant4 path validation
        if geant4_path is None:
            errors.append(ValidationError(
                "Geant4 Installation",
                "Geant4 path not configured. Simulation may fail.\n"
                "Please configure in Tools > Settings",
                "warning"
            ))

        return errors

    @classmethod
    def validate_all(cls, beam_params: dict, material_params: dict,
                     sim_params: dict, file_params: dict) -> Tuple[bool, List[ValidationError]]:
        """
        Validate all simulation parameters

        Args:
            beam_params: Dictionary with beam parameters (energy, beam_size, pos_z, dir_z)
            material_params: Dictionary with material parameters (composition, thickness, density)
            sim_params: Dictionary with simulation parameters (events, seed)
            file_params: Dictionary with file parameters (executable_path, working_dir, geant4_path)

        Returns:
            Tuple of (is_valid, list_of_errors)
            is_valid is True only if there are no errors (warnings are allowed)
        """
        all_errors = []

        # Validate each category
        all_errors.extend(cls.validate_beam_parameters(**beam_params))
        all_errors.extend(cls.validate_material_parameters(**material_params))
        all_errors.extend(cls.validate_simulation_parameters(**sim_params))
        all_errors.extend(cls.validate_file_paths(**file_params))

        # Check if there are any actual errors (not just warnings)
        has_errors = any(err.severity == "error" for err in all_errors)

        return (not has_errors, all_errors)

    @classmethod
    def format_validation_report(cls, errors: List[ValidationError]) -> str:
        """
        Format validation errors into a readable report

        Args:
            errors: List of validation errors

        Returns:
            Formatted string report
        """
        if not errors:
            return "✅ All parameters are valid!"

        # Separate errors and warnings
        actual_errors = [e for e in errors if e.severity == "error"]
        warnings = [e for e in errors if e.severity == "warning"]

        report_lines = []

        if actual_errors:
            report_lines.append("❌ ERRORS (must fix before running):")
            for err in actual_errors:
                report_lines.append(f"  • {err.field}: {err.message}")
            report_lines.append("")

        if warnings:
            report_lines.append("⚠️  WARNINGS (review recommended):")
            for warn in warnings:
                report_lines.append(f"  • {warn.field}: {warn.message}")

        return "\n".join(report_lines)
