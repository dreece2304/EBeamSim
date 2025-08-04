#!/usr/bin/env python3
"""
EBeamSim Project Cleanup Script
Removes unnecessary files to keep the project structure clean and efficient
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Files and patterns to remove
CLEANUP_PATTERNS = {
    "backup_files": [
        "**/*.backup*",
        "**/*.bak",
    ],
    "old_scripts": [
        "create_ebl_project.ps1",
        "create_widget_files.ps1", 
        "create_gui_structure.ps1",
        "fix_geant4_runtime_error.ps1",
        "quick_fix_parens.ps1",
        "update_includes.ps1",
        "update_ebl_gui_path.ps1",
        "update_source_files.ps1",
    ],
    "old_summaries": [
        "fix_summary.txt",
        "update_summary.txt",
        "scripts/gui/simulation_summary.txt",
    ],
    "old_logs": [
        "scripts/gui/ebl_sim_log_*.txt",
    ],
    "old_macros": [
        "gui_generated.mac",  # Old one in root
    ]
}

# Files to review (not automatically deleted)
REVIEW_FILES = [
    "run_with_env.bat",
    "install_ebl_gui.ps1",
    "update.ps1",
]


def cleanup_project(dry_run=True):
    """
    Clean up unnecessary files from the project
    
    Args:
        dry_run: If True, only shows what would be deleted without actually deleting
    """
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"EBeamSim Project Cleanup - {'DRY RUN' if dry_run else 'ACTUAL RUN'}")
    print(f"Project root: {project_root}")
    print("-" * 60)
    
    files_to_delete = []
    total_size = 0
    
    # Collect files matching patterns
    for category, patterns in CLEANUP_PATTERNS.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for pattern in patterns:
            if "**/" in pattern:
                # Glob pattern
                for file_path in project_root.glob(pattern):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        files_to_delete.append((file_path, size))
                        total_size += size
                        print(f"  - {file_path.relative_to(project_root)} ({size:,} bytes)")
            else:
                # Direct file path
                file_path = project_root / pattern
                if file_path.exists() and file_path.is_file():
                    size = file_path.stat().st_size
                    files_to_delete.append((file_path, size))
                    total_size += size
                    print(f"  - {file_path.relative_to(project_root)} ({size:,} bytes)")
    
    print(f"\n{'=' * 60}")
    print(f"Total files to delete: {len(files_to_delete)}")
    print(f"Total size to free: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    
    # Show files to review
    print(f"\n{'Files to Review Manually:':^60}")
    print("-" * 60)
    for file_name in REVIEW_FILES:
        file_path = project_root / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ? {file_name} ({size:,} bytes)")
    
    if not dry_run and files_to_delete:
        print(f"\n{'DELETING FILES':^60}")
        print("-" * 60)
        
        # Create backup directory with timestamp
        backup_dir = project_root / f"cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        print(f"Creating backup in: {backup_dir.relative_to(project_root)}")
        
        deleted_count = 0
        failed_count = 0
        
        for file_path, _ in files_to_delete:
            try:
                # Create backup
                rel_path = file_path.relative_to(project_root)
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                
                # Delete file
                file_path.unlink()
                deleted_count += 1
                print(f"  ✓ Deleted: {rel_path}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Failed to delete {rel_path}: {e}")
        
        print(f"\n{'CLEANUP COMPLETE':^60}")
        print(f"Files deleted: {deleted_count}")
        print(f"Files failed: {failed_count}")
        print(f"Backup created: {backup_dir.relative_to(project_root)}")
    
    else:
        print(f"\n{'DRY RUN COMPLETE':^60}")
        print("To actually delete files, run with --delete flag")
    
    return len(files_to_delete), total_size


def main():
    import sys
    
    dry_run = "--delete" not in sys.argv
    
    if not dry_run:
        response = input("\nAre you sure you want to delete these files? A backup will be created. (yes/no): ")
        if response.lower() != "yes":
            print("Cleanup cancelled.")
            return
    
    cleanup_project(dry_run)


if __name__ == "__main__":
    main()