"""
Geant4 Installation Detection and Path Management
Automatically detects Geant4 installation across different platforms
"""

import os
import platform
from pathlib import Path
from typing import Optional, List, Tuple


class Geant4PathDetector:
    """Detects and validates Geant4 installation paths"""

    # Common environment variables that point to Geant4
    ENV_VARS = [
        'G4INSTALL',
        'GEANT4_INSTALL_DIR',
        'GEANT4_DIR',
        'G4_INSTALL',
        'GEANT4_HOME',
    ]

    # Common installation paths by platform
    COMMON_PATHS = {
        'Windows': [
            r'C:\Geant4\ProgramFiles',
            r'C:\Program Files\Geant4',
            r'C:\Program Files (x86)\Geant4',
        ],
        'Linux': [
            '/usr/local/geant4',
            '/opt/geant4',
            '/usr/share/geant4',
            str(Path.home() / 'geant4'),
        ],
        'Darwin': [  # macOS
            '/usr/local/geant4',
            '/opt/geant4',
            '/opt/local/geant4',
            str(Path.home() / 'geant4'),
        ],
    }

    def __init__(self):
        self.platform = platform.system()

    def detect_geant4_path(self) -> Optional[Path]:
        """
        Automatically detect Geant4 installation path

        Returns:
            Path to Geant4 installation or None if not found
        """
        # 1. Check environment variables first (highest priority)
        for env_var in self.ENV_VARS:
            if env_var in os.environ:
                path = Path(os.environ[env_var])
                if self.validate_geant4_path(path):
                    return path

        # 2. Check common installation paths for this platform
        common_paths = self.COMMON_PATHS.get(self.platform, [])
        for path_str in common_paths:
            path = Path(path_str)
            if self.validate_geant4_path(path):
                return path

        # 3. Try to find via system path (for Linux/macOS)
        if self.platform != 'Windows':
            system_path = self._find_via_system_path()
            if system_path:
                return system_path

        return None

    def validate_geant4_path(self, path: Path) -> bool:
        """
        Validate that a path is a valid Geant4 installation

        Args:
            path: Path to check

        Returns:
            True if path contains Geant4 installation
        """
        if not path.exists():
            return False

        # Check for characteristic Geant4 directories
        indicators = [
            path / 'share' / 'Geant4',
            path / 'include' / 'Geant4',
            path / 'lib',
        ]

        # At least one indicator must exist
        return any(ind.exists() for ind in indicators)

    def get_data_directories(self, g4_path: Path) -> dict:
        """
        Get Geant4 data directory environment variables

        Args:
            g4_path: Path to Geant4 installation

        Returns:
            Dictionary of environment variable names and paths
        """
        data_dir = g4_path / 'share' / 'Geant4' / 'data'
        if not data_dir.exists():
            data_dir = g4_path / 'share' / 'Geant4-11.3.2' / 'data'  # Version-specific

        if not data_dir.exists():
            return {}

        # Map data directories to environment variables
        data_map = {}

        # Common Geant4 data directories
        data_libs = {
            'G4ABLA': 'G4ABLA',
            'G4EMLOW': 'G4LEDATA',
            'G4ENSDFSTATE': 'G4ENSDFSTATEDATA',
            'G4INCL': 'G4INCLDATA',
            'G4NDL': 'G4NEUTRONHPDATA',
            'G4PARTICLEXS': 'G4PARTICLEXSDATA',
            'G4PII': 'G4PIIDATA',
            'G4SAIDDATA': 'G4SAIDXSDATA',
            'PhotonEvaporation': 'G4LEVELGAMMADATA',
            'RadioactiveDecay': 'G4RADIOACTIVEDATA',
            'RealSurface': 'G4REALSURFACEDATA',
        }

        for dir_name, env_var in data_libs.items():
            # Try to find directory with version number
            matching_dirs = list(data_dir.glob(f'{dir_name}*'))
            if matching_dirs:
                data_map[env_var] = str(matching_dirs[0])

        return data_map

    def _find_via_system_path(self) -> Optional[Path]:
        """Try to find Geant4 via system PATH (Linux/macOS)"""
        try:
            import subprocess
            result = subprocess.run(
                ['which', 'geant4-config'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # geant4-config found, get installation path
                config_result = subprocess.run(
                    ['geant4-config', '--prefix'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if config_result.returncode == 0:
                    path = Path(config_result.stdout.strip())
                    if self.validate_geant4_path(path):
                        return path
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

        return None

    def get_search_locations(self) -> List[str]:
        """Get list of all locations that were/will be searched"""
        locations = []

        # Environment variables
        for env_var in self.ENV_VARS:
            if env_var in os.environ:
                locations.append(f"${env_var} = {os.environ[env_var]}")
            else:
                locations.append(f"${env_var} (not set)")

        # Common paths
        common_paths = self.COMMON_PATHS.get(self.platform, [])
        locations.extend(common_paths)

        return locations


def setup_geant4_environment(g4_path: Path) -> Tuple[bool, str]:
    """
    Set up Geant4 environment variables for simulation

    Args:
        g4_path: Path to Geant4 installation

    Returns:
        Tuple of (success, message)
    """
    detector = Geant4PathDetector()

    if not detector.validate_geant4_path(g4_path):
        return False, f"Invalid Geant4 installation at: {g4_path}"

    # Set data directories
    data_dirs = detector.get_data_directories(g4_path)

    if not data_dirs:
        return False, f"Could not find Geant4 data directories in: {g4_path}"

    # Update environment
    for env_var, path in data_dirs.items():
        os.environ[env_var] = path

    # Set main installation path
    os.environ['G4INSTALL'] = str(g4_path)

    return True, f"Geant4 environment configured ({len(data_dirs)} data libraries)"
