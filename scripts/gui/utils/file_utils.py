"""
File utility functions for EBL simulation GUI
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
import datetime


class FileUtils:
    """Utility functions for file operations"""
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists, create if necessary"""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_unique_filename(base_path: Path, extension: str = "") -> Path:
        """Generate unique filename by adding timestamp or counter"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if extension and not extension.startswith('.'):
            extension = f".{extension}"
        
        stem = base_path.stem
        parent = base_path.parent
        
        # Try with timestamp first
        unique_path = parent / f"{stem}_{timestamp}{extension}"
        
        # If still exists, add counter
        counter = 1
        while unique_path.exists():
            unique_path = parent / f"{stem}_{timestamp}_{counter:02d}{extension}"
            counter += 1
        
        return unique_path
    
    @staticmethod
    def safe_copy(source: Path, destination: Path, backup: bool = True) -> bool:
        """Safely copy file with optional backup of destination"""
        try:
            if backup and destination.exists():
                backup_path = FileUtils.get_unique_filename(
                    destination.with_suffix('.backup' + destination.suffix)
                )
                shutil.copy2(destination, backup_path)
            
            FileUtils.ensure_directory(destination.parent)
            shutil.copy2(source, destination)
            return True
        except Exception:
            return False
    
    @staticmethod
    def safe_delete(file_path: Path, backup: bool = True) -> bool:
        """Safely delete file with optional backup"""
        try:
            if not file_path.exists():
                return True
            
            if backup:
                backup_dir = file_path.parent / "deleted_backups"
                FileUtils.ensure_directory(backup_dir)
                backup_path = FileUtils.get_unique_filename(
                    backup_dir / file_path.name
                )
                shutil.copy2(file_path, backup_path)
            
            file_path.unlink()
            return True
        except Exception:
            return False
    
    @staticmethod
    def cleanup_temp_files(directory: Path, pattern: str = "temp_*") -> int:
        """Clean up temporary files matching pattern"""
        count = 0
        try:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    count += 1
        except Exception:
            pass
        return count
    
    @staticmethod
    def get_file_size_human(file_path: Path) -> str:
        """Get human-readable file size"""
        try:
            size = file_path.stat().st_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except Exception:
            return "Unknown"
    
    @staticmethod
    def find_executable(name: str) -> Optional[Path]:
        """Find executable in PATH"""
        for path_str in os.environ.get("PATH", "").split(os.pathsep):
            path = Path(path_str)
            if (path / name).exists():
                return path / name
            if os.name == 'nt' and (path / f"{name}.exe").exists():
                return path / f"{name}.exe"
        return None
    
    @staticmethod
    def create_temp_directory(prefix: str = "ebl_sim_") -> Path:
        """Create temporary directory"""
        return Path(tempfile.mkdtemp(prefix=prefix))
    
    @staticmethod
    def validate_path(path_str: str) -> Tuple[bool, str]:
        """Validate path string"""
        try:
            path = Path(path_str)
            if path.exists():
                return True, "Path exists"
            elif path.parent.exists():
                return True, "Parent directory exists"
            else:
                return False, "Parent directory does not exist"
        except Exception as e:
            return False, f"Invalid path: {str(e)}"