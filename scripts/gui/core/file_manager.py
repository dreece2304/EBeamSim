"""
Unified file management for consistent handling across the application
"""

import csv
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Any
import pandas as pd


class FileManager:
    """Unified file management for consistent handling across the application"""

    def __init__(self, working_dir: str):
        self.working_dir = Path(working_dir)
        self.recent_files: List[str] = []
        self.supported_formats = {
            'csv': ['csv'],
            'beamer': ['txt', 'dat'],
            'config': ['json'],
            'macro': ['mac']
        }

    def validate_file_format(self, file_path: str, expected_type: str) -> Tuple[bool, str]:
        """Validate file format before loading"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"

        if expected_type in self.supported_formats:
            valid_extensions = self.supported_formats[expected_type]
            if file_path.suffix.lower().lstrip('.') not in valid_extensions:
                return False, f"Expected {expected_type} file, got {file_path.suffix}"

        return True, "Valid file format"

    def load_csv_with_validation(self, file_path: str, 
                                progress_callback: Optional[Callable[[str], None]] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """Load CSV with validation and progress reporting"""
        try:
            if progress_callback:
                progress_callback("Validating file format...")

            valid, message = self.validate_file_format(file_path, 'csv')
            if not valid:
                return None, message

            if progress_callback:
                progress_callback("Loading CSV data...")

            df = pd.read_csv(file_path)

            if progress_callback:
                progress_callback("Validating data structure...")

            # Basic validation
            if df.empty:
                return None, "CSV file is empty"

            self._add_to_recent(file_path)
            return df, "Successfully loaded"

        except Exception as e:
            return None, f"Error loading CSV: {str(e)}"

    def save_with_backup(self, data: Any, file_path: str, backup: bool = True) -> Tuple[bool, str]:
        """Save data with optional backup creation"""
        try:
            file_path = Path(file_path)

            # Create backup if file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f".backup{file_path.suffix}")
                file_path.rename(backup_path)

            # Save based on file type
            if file_path.suffix.lower() == '.csv':
                if isinstance(data, pd.DataFrame):
                    data.to_csv(file_path, index=False)
                else:
                    # Assume it's structured data for CSV
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
            else:
                # Text files
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(data))

            return True, f"Saved to {file_path}"

        except Exception as e:
            return False, f"Error saving: {str(e)}"

    def get_recent_simulation_files(self) -> List[Path]:
        """Find recent simulation output files"""
        patterns = [
            "*psf*.csv",
            "*_E*keV_*.csv",
            "ebl_psf_data.csv",
            "ebl_2d_data.csv"
        ]

        recent_files = []
        for pattern in patterns:
            files = list(self.working_dir.glob(pattern))
            recent_files.extend(files)

        # Sort by modification time, most recent first
        recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return recent_files[:10]  # Return up to 10 most recent

    def _add_to_recent(self, file_path: str) -> None:
        """Add file to recent files list"""
        file_path = str(file_path)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:20]  # Keep last 20

    @property
    def recent_files_list(self) -> List[str]:
        """Get copy of recent files list"""
        return self.recent_files.copy()

    def clear_recent_files(self) -> None:
        """Clear the recent files list"""
        self.recent_files.clear()