"""
PlotWidget - 1D PSF visualization and BEAMER conversion

Extracted from ebl_gui.py (July 2026 modularization). Behavior is unchanged;
only the class was moved out of the monolith.
"""

import csv
import re
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import scipy.interpolate

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QRadioButton, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QSlider, QListWidget, QListWidgetItem, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit, QSizePolicy, QSplitter,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from widgets.common.status_button import StatusButton

class PlotWidget(QWidget):
    """Enhanced widget for 1D PSF plots with BEAMER conversion and PSF comparison"""

    def __init__(self, file_manager):
        super().__init__()
        self.file_manager = file_manager
        self.datasets = []  # Store multiple PSF datasets for comparison
        self.current_csv_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Plot controls
        controls = QHBoxLayout()

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Linear", "Log-Log", "Semi-Log"])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot_type)

        # Enhanced control buttons
        self.load_button = StatusButton("Load PSF Data")
        self.load_button.clicked.connect(self.load_data)

        self.compare_button = StatusButton("Add for Comparison")
        self.compare_button.clicked.connect(self.add_comparison_data)
        self.compare_button.set_status(False, "Load initial PSF data first")

        self.ref_library_button = StatusButton("Reference Library")
        self.ref_library_button.clicked.connect(self.load_reference_psf_dialog)
        self.ref_library_button.set_status(True, "Add standard PSFs for comparison")

        self.clear_button = StatusButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all_data)
        self.clear_button.set_status(False, "No data to clear")

        self.save_button = StatusButton("Save Plot")
        self.save_button.clicked.connect(self.save_plot)
        self.save_button.set_status(False, "Load PSF data first")

        controls.addWidget(QLabel("Plot Type:"))
        controls.addWidget(self.plot_type_combo)
        controls.addStretch()
        controls.addWidget(self.load_button)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.ref_library_button)
        controls.addWidget(self.clear_button)
        controls.addWidget(self.save_button)

        # BEAMER conversion controls (consolidated functionality)
        beamer_controls = QHBoxLayout()

        self.beamer_button = StatusButton("Convert to BEAMER")
        self.beamer_button.clicked.connect(self.convert_to_beamer_consolidated)
        self.beamer_button.set_status(False, "Load PSF data first")

        self.validate_button = StatusButton("Validate PSF")
        self.validate_button.clicked.connect(self.validate_psf_consolidated)
        self.validate_button.set_status(False, "Load PSF data first")

        self.smooth_check = QCheckBox("Apply Smoothing")
        self.smooth_check.setChecked(True)

        # Comparison analysis button
        self.analyze_button = StatusButton("Analyze Comparison")
        self.analyze_button.clicked.connect(self.analyze_comparison)
        self.analyze_button.set_status(False, "Load multiple PSF datasets first")

        beamer_controls.addWidget(QLabel("Analysis Tools:"))
        beamer_controls.addWidget(self.beamer_button)
        beamer_controls.addWidget(self.validate_button)
        beamer_controls.addWidget(self.analyze_button)
        beamer_controls.addWidget(self.smooth_check)
        beamer_controls.addStretch()

        # PSF comparison info panel
        comparison_group = QGroupBox("Loaded PSF Datasets")
        comparison_layout = QVBoxLayout()

        self.comparison_list = QTextEdit()
        self.comparison_list.setMaximumHeight(80)
        self.comparison_list.setReadOnly(True)
        comparison_layout.addWidget(self.comparison_list)

        comparison_group.setLayout(comparison_layout)

        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addLayout(beamer_controls)
        layout.addWidget(comparison_group)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def _load_beamer_format_file(self, file_path):
        """
        Load BEAMER format file (.dat or .txt)

        Args:
            file_path: Path to BEAMER format file

        Returns:
            Tuple of (radii_nm, psf_values) or (None, None) on error
        """
        try:
            radius_um = []
            psf = []

            with open(file_path, 'r') as f:
                for line in f:
                    # Skip comments and empty lines
                    if not line.startswith('#') and line.strip():
                        try:
                            r, p = map(float, line.split())
                            radius_um.append(r)
                            psf.append(p)
                        except ValueError:
                            continue  # Skip malformed lines

            if not radius_um or not psf:
                return None, None

            # Convert radius from micrometers to nanometers for consistency with CSV format
            radius_nm = [r * 1000.0 for r in radius_um]

            return radius_nm, psf

        except Exception as e:
            print(f"Error loading BEAMER file: {e}")
            return None, None

    def load_data(self):
        """Load PSF data from CSV or BEAMER format file (.csv, .dat, .txt)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", str(self.file_manager.working_dir),
            "PSF files (*.csv *.dat *.txt);;CSV files (*.csv);;BEAMER files (*.dat *.txt);;All files (*.*)"
        )

        if file_path:
            self.load_button.set_working(True, "Loading...")

            try:
                # Detect file type and load appropriately
                file_ext = Path(file_path).suffix.lower()

                if file_ext == '.csv':
                    # Load CSV format
                    df, message = self.file_manager.load_csv_with_validation(file_path)

                    if df is None:
                        QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                        return

                    # Extract PSF data from CSV
                    radii, energies = self._extract_psf_from_df(df)

                elif file_ext in ['.dat', '.txt']:
                    # Load BEAMER format
                    radii, energies = self._load_beamer_format_file(file_path)

                else:
                    QMessageBox.warning(self, "Unsupported Format",
                                      f"File extension '{file_ext}' is not supported.\n"
                                      "Supported formats: .csv, .dat, .txt")
                    return

                if not radii or not energies:
                    QMessageBox.warning(self, "Warning", "No valid PSF data found in file")
                    return

                # Store the path for BEAMER conversion (only for CSV files)
                if file_ext == '.csv':
                    self.current_csv_path = file_path
                else:
                    self.current_csv_path = None  # BEAMER files don't need conversion

                # Clear existing data and add this as primary dataset
                self.datasets = []
                dataset_info = {
                    'radii': radii,
                    'energies': energies,
                    'label': f"PSF - {Path(file_path).stem}",
                    'file_path': file_path,
                    'style': {'color': 'blue', 'linewidth': 2}
                }
                self.datasets.append(dataset_info)

                # Update UI state
                self.beamer_button.set_status(True)
                self.validate_button.set_status(True)
                self.save_button.set_status(True)
                self.compare_button.set_status(True)
                self.clear_button.set_status(True)

                # Plot the data
                self.plot_all_datasets()
                self.update_comparison_list()

                # Show success message
                QMessageBox.information(self, "Success",
                                        f"Loaded PSF data: {len(radii)} points")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            finally:
                self.load_button.set_working(False)

    def add_comparison_data(self):
        """Add additional PSF dataset for comparison (supports CSV and BEAMER formats)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add PSF Data for Comparison", str(self.file_manager.working_dir),
            "PSF files (*.csv *.dat *.txt);;CSV files (*.csv);;BEAMER files (*.dat *.txt);;All files (*.*)"
        )

        if file_paths:
            self.compare_button.set_working(True, "Loading...")

            colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive']
            color_idx = len(self.datasets) - 1  # Start from second color

            try:
                for file_path in file_paths:
                    # Detect file type
                    file_ext = Path(file_path).suffix.lower()

                    if file_ext == '.csv':
                        # Load CSV format
                        df, message = self.file_manager.load_csv_with_validation(file_path)

                        if df is None:
                            print(f"Skipping {file_path}: {message}")
                            continue

                        # Extract PSF data
                        radii, energies = self._extract_psf_from_df(df)

                    elif file_ext in ['.dat', '.txt']:
                        # Load BEAMER format
                        radii, energies = self._load_beamer_format_file(file_path)

                        if not radii or not energies:
                            print(f"Skipping {file_path}: Failed to load BEAMER format")
                            continue

                    else:
                        print(f"Skipping {file_path}: Unsupported format '{file_ext}'")
                        continue

                    if radii and energies:
                        dataset_info = {
                            'radii': radii,
                            'energies': energies,
                            'label': Path(file_path).stem,
                            'file_path': file_path,
                            'style': {
                                'color': colors[color_idx % len(colors)],
                                'linewidth': 2,
                                'linestyle': '--' if color_idx > 3 else '-'
                            }
                        }
                        self.datasets.append(dataset_info)
                        color_idx += 1

                if len(self.datasets) > 1:
                    # Enable comparison analysis
                    self.analyze_button.set_status(True)

                    # Replot all datasets
                    self.plot_all_datasets()
                    self.update_comparison_list()

                    QMessageBox.information(self, "Success",
                                            f"Added {len(file_paths)} datasets. Total: {len(self.datasets)}")
                else:
                    QMessageBox.warning(self, "Warning", "No valid datasets were added")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add comparison data: {str(e)}")
            finally:
                self.compare_button.set_working(False)

    def load_reference_psf_dialog(self):
        """Show dialog to select and load reference PSFs from library"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel

        # Define reference library (to be populated from data/reference_psfs/)
        ref_library = {
            'PMMA 100nm': {
                'file': 'ref_PMMA_100nm_beamer.dat',
                'description': 'Standard PMMA resist (C₅H₈O₂) at 100nm - traditional negative-tone',
                'color': 'green',
                'thickness': 100
            },
            'HSQ 100nm': {
                'file': 'ref_HSQ_100nm_beamer.dat',
                'description': 'Hydrogen Silsesquioxane (SiH₁O₁.₅) at 100nm - traditional negative-tone',
                'color': 'orange',
                'thickness': 100
            },
            'Alucone XPS 30nm': {
                'file': 'ref_AluconeXPS_30nm_beamer.dat',
                'description': 'Aluminum alkoxide (AlC₅H₄O₂) at 30nm - modern inorganic',
                'color': 'blue',
                'thickness': 30
            },
            'Sn-MLD 30nm': {
                'file': 'ref_SnMLD_30nm_beamer.dat',
                'description': 'Tin oxo-cage MLD (SnC₈H₈O₄) at 30nm - high-Z resist',
                'color': 'red',
                'thickness': 30
            }
        }

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Reference PSF Library")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout()

        # Header
        header = QLabel("Select standard reference PSFs to add for comparison:")
        header.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 10px;")
        layout.addWidget(header)

        # Create checkboxes for each reference PSF
        checkboxes = {}
        for name, info in ref_library.items():
            checkbox = QCheckBox(f"{name}")
            checkbox.setToolTip(info['description'])

            # Check if file exists
            script_dir = Path(__file__).parent
            ref_file = script_dir.parent.parent / 'data' / 'reference_psfs' / info['file']

            if not ref_file.exists():
                checkbox.setEnabled(False)
                checkbox.setText(f"{name} (not yet generated)")
                checkbox.setToolTip(f"{info['description']}\n\nRun: ./scripts/generate_reference_psfs.sh to create this PSF")

            checkboxes[name] = checkbox
            layout.addWidget(checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes.values() if cb.isEnabled()])

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes.values()])

        load_btn = QPushButton("Load Selected")
        load_btn.clicked.connect(dialog.accept)
        load_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(load_btn)
        button_layout.addWidget(cancel_btn)

        layout.addSpacing(10)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Show dialog and load selected PSFs
        if dialog.exec() == QDialog.Accepted:
            selected = [name for name, cb in checkboxes.items() if cb.isChecked()]

            if selected:
                self.load_reference_psfs(selected, ref_library)
            else:
                QMessageBox.information(self, "No Selection", "No reference PSFs were selected")

    def load_reference_psfs(self, selected_names, ref_library):
        """Load selected reference PSFs from library"""
        script_dir = Path(__file__).parent
        ref_dir = script_dir.parent.parent / 'data' / 'reference_psfs'

        self.ref_library_button.set_working(True, "Loading...")

        loaded_count = 0
        try:
            for name in selected_names:
                info = ref_library[name]
                ref_file = ref_dir / info['file']

                if not ref_file.exists():
                    print(f"Warning: {ref_file} not found, skipping")
                    continue

                # Load BEAMER format
                radii, energies = self._load_beamer_format_file(ref_file)

                if radii and energies:
                    dataset_info = {
                        'radii': radii,
                        'energies': energies,
                        'label': name,
                        'file_path': str(ref_file),
                        'style': {
                            'color': info['color'],
                            'linewidth': 2.5,
                            'linestyle': '-',
                            'alpha': 0.8
                        }
                    }
                    self.datasets.append(dataset_info)
                    loaded_count += 1

            if loaded_count > 0:
                # If this is the first data loaded, set it as current
                if len(self.datasets) == loaded_count:
                    self.current_data = {
                        'radii': self.datasets[0]['radii'],
                        'energies': self.datasets[0]['energies'],
                        'label': self.datasets[0]['label'],
                        'filename': self.datasets[0]['label']
                    }

                # Enable comparison features
                if len(self.datasets) > 1:
                    self.analyze_button.set_status(True)

                # Enable controls
                self.compare_button.set_status(True)
                self.clear_button.set_status(True)
                self.save_button.set_status(True)

                # Replot all datasets
                self.plot_all_datasets()
                self.update_comparison_list()

                QMessageBox.information(self, "Success",
                                        f"Loaded {loaded_count} reference PSF(s) for comparison")
            else:
                QMessageBox.warning(self, "Warning", "No reference PSFs could be loaded")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load reference PSFs: {str(e)}")
        finally:
            self.ref_library_button.set_working(False)

    def _extract_psf_from_df(self, df):
        """Extract radius and energy data from DataFrame"""
        radii, energies = [], []

        # Try different column name variations
        radius_cols = ['Radius(nm)', 'radius', 'Radius', 'r', 'R']
        energy_cols = ['EnergyDeposition(eV/nm^2)', 'Energy', 'energy', 'E', 'PSF']

        radius_col = None
        energy_col = None

        for col in radius_cols:
            if col in df.columns:
                radius_col = col
                break

        for col in energy_cols:
            if col in df.columns:
                energy_col = col
                break

        if radius_col is None or energy_col is None:
            # Try first two numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                radius_col = numeric_cols[0]
                energy_col = numeric_cols[1]

        if radius_col is not None and energy_col is not None:
            for _, row in df.iterrows():
                try:
                    r = float(row[radius_col])
                    e = float(row[energy_col])
                    if not (np.isnan(r) or np.isnan(e)):
                        radii.append(r)
                        energies.append(e)
                except (ValueError, TypeError):
                    continue

        return radii, energies

    def _calculate_fwhm(self, radii, energies):
        """
        Calculate Full Width at Half Maximum

        Args:
            radii: Array of radius values
            energies: Array of energy values

        Returns:
            Tuple of (fwhm_value, peak_index) or (None, None) if cannot calculate
        """
        if len(radii) < 3 or len(energies) < 3:
            return None, None

        # Find peak
        peak_idx = np.argmax(energies)
        peak_energy = energies[peak_idx]
        half_max = peak_energy / 2.0

        # Find indices where energy > half_max
        above_half = np.array(energies) > half_max

        if np.sum(above_half) < 2:
            return None, peak_idx

        # Find first and last crossing points
        indices_above = np.where(above_half)[0]

        if len(indices_above) >= 2:
            r_left = radii[indices_above[0]]
            r_right = radii[indices_above[-1]]
            fwhm = r_right - r_left
            return fwhm, peak_idx

        return None, peak_idx

    def _calculate_containment_radius(self, radii, energies, fraction):
        """
        Calculate radius containing specified fraction of total dose

        Args:
            radii: Array of radius values
            energies: Array of energy deposition values
            fraction: Fraction of total energy (e.g., 0.5 for R50, 0.9 for R90)

        Returns:
            Radius value containing specified fraction
        """
        radii = np.array(radii)
        energies = np.array(energies)

        # Calculate annular energy (2πr × E × dr)
        dr = np.diff(radii, prepend=0)
        annular_energy = 2 * np.pi * radii * energies * dr

        # Calculate cumulative energy
        cumulative = np.cumsum(annular_energy)
        total_energy = cumulative[-1]

        if total_energy == 0:
            return radii[-1]

        # Normalize to fraction
        cumulative_fraction = cumulative / total_energy

        # Find radius at specified fraction
        idx = np.argmax(cumulative_fraction >= fraction)

        if idx > 0:
            return radii[idx]
        else:
            return radii[-1]

    def plot_all_datasets(self):
        """Plot all loaded datasets with FWHM markers and dose metrics"""
        if not self.datasets:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        plot_type = self.plot_type_combo.currentText()

        # Track statistics for display
        stats_list = []

        for dataset in self.datasets:
            radii = dataset['radii']
            energies = dataset['energies']
            label = dataset['label']
            style = dataset['style']
            color = style.get('color', 'blue')

            if plot_type == "Log-Log":
                valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
                r_filt = [r for r, v in zip(radii, valid) if v]
                e_filt = [e for e, v in zip(energies, valid) if v]

                if r_filt and e_filt:
                    ax.loglog(r_filt, e_filt, label=label, **style)
                    # Use filtered data for metrics
                    radii_calc = r_filt
                    energies_calc = e_filt
                else:
                    continue
            elif plot_type == "Semi-Log":
                ax.semilogy(radii, energies, label=label, **style)
                radii_calc = radii
                energies_calc = energies
            else:
                ax.plot(radii, energies, label=label, **style)
                radii_calc = radii
                energies_calc = energies

            # Calculate and display FWHM
            fwhm, peak_idx = self._calculate_fwhm(radii_calc, energies_calc)

            if fwhm is not None and peak_idx is not None:
                # Add vertical line at FWHM
                ax.axvline(x=fwhm, color=color, linestyle=':', alpha=0.4, linewidth=1.5)

                # Add annotation (avoid clutter - only if first 3 datasets)
                if len(stats_list) < 3:
                    peak_energy = energies_calc[peak_idx]
                    if plot_type == "Linear":
                        y_pos = peak_energy / 2
                    else:
                        y_pos = peak_energy / 2  # Works for log scale too

                    ax.annotate(f'FWHM: {fwhm:.1f} nm',
                               xy=(fwhm, y_pos),
                               xytext=(fwhm * 1.3, y_pos),
                               color=color,
                               fontsize=8,
                               arrowprops=dict(arrowstyle='->', color=color, lw=0.8, alpha=0.6))

            # Calculate dose metrics
            r50 = self._calculate_containment_radius(radii_calc, energies_calc, 0.5)
            r90 = self._calculate_containment_radius(radii_calc, energies_calc, 0.9)

            # Store statistics
            stats_list.append({
                'label': label,
                'fwhm': fwhm if fwhm else np.nan,
                'r50': r50,
                'r90': r90,
                'peak': np.max(energies_calc) if len(energies_calc) > 0 else 0
            })

        ax.set_xlabel('Radius (nm)', fontsize=11)
        ax.set_ylabel('Energy Deposition (eV/nm²)', fontsize=11)
        ax.set_title(f'PSF Comparison - {plot_type} Scale', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, which='both')

        if len(self.datasets) > 1:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        elif len(self.datasets) == 1:
            ax.legend(loc='best', fontsize=9)

        # Add statistics text box (if we have stats)
        if stats_list and len(stats_list) <= 4:  # Only show for up to 4 datasets
            stats_text = 'PSF Metrics:\n'
            for stat in stats_list:
                stats_text += f"\n{stat['label']}:\n"
                if not np.isnan(stat['fwhm']):
                    stats_text += f"  FWHM: {stat['fwhm']:.1f} nm\n"
                stats_text += f"  R50: {stat['r50']:.1f} nm\n"
                stats_text += f"  R90: {stat['r90']:.1f} nm\n"

            # Position text box
            ax.text(0.02, 0.02, stats_text, transform=ax.transAxes,
                   fontsize=8, verticalalignment='bottom',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7, pad=0.5))

        self.figure.tight_layout()
        self.canvas.draw()

    def update_plot_type(self):
        """Update plot when type changes"""
        if self.datasets:
            self.plot_all_datasets()

    def update_comparison_list(self):
        """Update the comparison list display"""
        if not self.datasets:
            self.comparison_list.setPlainText("No PSF datasets loaded")
            return

        text_lines = []
        for i, dataset in enumerate(self.datasets):
            file_name = Path(dataset['file_path']).name
            point_count = len(dataset['radii'])
            max_energy = max(dataset['energies']) if dataset['energies'] else 0
            text_lines.append(f"{i+1}. {file_name} ({point_count} points, max: {max_energy:.2e})")

        self.comparison_list.setPlainText("\n".join(text_lines))

    def clear_all_data(self):
        """Clear all loaded datasets"""
        reply = QMessageBox.question(self, "Clear All Data",
                                     "Remove all loaded PSF datasets?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.datasets = []
            self.current_csv_path = None

            # Reset UI state
            self.beamer_button.set_status(False, "Load PSF data first")
            self.validate_button.set_status(False, "Load PSF data first")
            self.save_button.set_status(False, "Load PSF data first")
            self.compare_button.set_status(False, "Load initial PSF data first")
            self.analyze_button.set_status(False, "Load multiple PSF datasets first")
            self.clear_button.set_status(False, "No data to clear")

            # Clear plot and comparison list
            self.figure.clear()
            self.canvas.draw()
            self.update_comparison_list()

    def convert_to_beamer_consolidated(self):
        """Consolidated BEAMER conversion using the best method"""
        if not self.current_csv_path:
            QMessageBox.warning(self, "Warning", "No PSF data loaded for conversion")
            return

        # Use the beam energy currently set in the main window; 100 keV only
        # as a last-resort fallback if the widget is ever used standalone
        main_window = self.window()
        if hasattr(main_window, 'energy_spin'):
            beam_energy = main_window.energy_spin.value()
        else:
            beam_energy = 100.0

        self.beamer_button.set_working(True, "Converting...")

        try:
            # Load the CSV data
            df, message = self.file_manager.load_csv_with_validation(self.current_csv_path)

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {message}")
                return

            # Use consolidated conversion method
            result = self._convert_csv_to_beamer_consolidated(
                df, beam_energy, self.smooth_check.isChecked()
            )

            if result:
                output_radius, output_psf, alpha, beta = result

                # Ask for save location
                default_name = Path(self.current_csv_path).stem + "_beamer.txt"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save BEAMER Format", default_name,
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    # Write BEAMER format
                    success, message = self._write_beamer_file(
                        file_path, output_radius, output_psf,
                        self.current_csv_path, beam_energy
                    )

                    if success:
                        # Show success with parameters
                        QMessageBox.information(self, "BEAMER Conversion Complete",
                                                f"PSF saved to: {Path(file_path).name}\n\n"
                                                f"Energy split (not the Gaussian alpha/beta ranges):\n"
                                                f"forward fraction (r < 1 um): {alpha:.3f}\n"
                                                f"backscatter fraction (r > 1 um): {beta:.3f}\n\n"
                                                f"Data points: {len(output_radius)}")

                        # Offer to visualize BEAMER format
                        reply = QMessageBox.question(self, "Visualize BEAMER Format",
                                                     "Would you like to plot the BEAMER format PSF?",
                                                     QMessageBox.Yes | QMessageBox.No)

                        if reply == QMessageBox.Yes:
                            self.plot_beamer_format(output_radius, output_psf)
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to save file: {message}")
            else:
                QMessageBox.critical(self, "Error", "Failed to convert PSF data")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"BEAMER conversion failed: {str(e)}")
        finally:
            self.beamer_button.set_working(False)

    def _convert_csv_to_beamer_consolidated(self, df, beam_energy, apply_smoothing=True):
        """Consolidated BEAMER conversion - best method from analysis"""
        try:
            # Extract PSF data
            radii, energies = self._extract_psf_from_df(df)

            if not radii or not energies:
                return None

            # Convert to numpy arrays
            radius_nm = np.array(radii)
            energy_density = np.array(energies)

            # Get non-zero data
            mask = energy_density > 0
            if not mask.any():
                return None

            radius_nm = radius_nm[mask]
            energy_density = energy_density[mask]

            # Convert to micrometers
            radius_um = radius_nm / 1000.0

            # Normalize to maximum = 1.0 (BEAMER standard)
            max_density = np.max(energy_density)
            psf_normalized = energy_density / max_density

            # Apply smoothing if requested (Savitzky-Golay filter)
            if apply_smoothing and len(psf_normalized) > 7:
                from scipy.signal import savgol_filter

                # Smooth only the tail region (r > 10 um)
                smooth_start = np.where(radius_um > 10.0)[0]
                if len(smooth_start) > 0:
                    start_idx = smooth_start[0]
                    if len(psf_normalized) - start_idx > 7:
                        window = min(7, len(psf_normalized) - start_idx)
                        if window % 2 == 0:
                            window -= 1
                        psf_normalized[start_idx:] = savgol_filter(
                            psf_normalized[start_idx:], window, 3
                        )

            # Prepare output data
            output_radius = []
            output_psf = []

            # Add point at 0.01 um if needed
            if radius_um[0] > 0.02:
                output_radius.append(0.01)
                output_psf.append(psf_normalized[0])

            # Add all valid points
            for r, p in zip(radius_um, psf_normalized):
                if p > 1e-12:  # Filter noise floor
                    output_radius.append(r)
                    output_psf.append(p)

            # Extrapolate tail if needed
            if output_radius[-1] < 100.0 and len(output_radius) > 10:
                # Fit exponential to last 10 points
                n_fit = min(10, len(output_radius) // 2)
                r_fit = np.array(output_radius[-n_fit:])
                p_fit = np.array(output_psf[-n_fit:])

                if np.all(p_fit > 0):
                    # Fit in log space
                    coeffs = np.polyfit(r_fit, np.log(p_fit), 1)

                    # Extrapolate
                    r_extrap = output_radius[-1]
                    while r_extrap < 100.0:
                        r_extrap *= 1.2
                        p_extrap = np.exp(coeffs[0] * r_extrap + coeffs[1])

                        if p_extrap < 1e-10:
                            break

                        output_radius.append(r_extrap)
                        output_psf.append(p_extrap)

            # Energy split diagnostics. NOTE: these are the forward/backscatter
            # ENERGY FRACTIONS (dimensionless), not the double-Gaussian range
            # parameters alpha/beta in um.
            forward_energy = 0
            total_energy = 0

            for i in range(len(output_radius)-1):
                r1, r2 = output_radius[i], output_radius[i+1]
                p1, p2 = output_psf[i], output_psf[i+1]

                dr = r2 - r1
                avg_r = (r1 + r2) / 2
                avg_p = (p1 + p2) / 2
                contrib = 2 * np.pi * avg_r * avg_p * dr

                total_energy += contrib
                if avg_r < 1.0:
                    forward_energy += contrib

            alpha = forward_energy / total_energy if total_energy > 0 else 0
            beta = 1 - alpha

            return output_radius, output_psf, alpha, beta

        except Exception as e:
            print(f"BEAMER conversion error: {str(e)}")
            return None

    def _write_beamer_file(self, file_path, radius_data, psf_data, source_file, beam_energy):
        """Write data to BEAMER format file"""
        try:
            with open(file_path, 'w') as f:
                f.write("# Electron beam PSF for BEAMER proximity correction\n")
                f.write("# Generated from Geant4 simulation by EBL GUI\n")
                f.write(f"# Source: {Path(source_file).name}\n")
                f.write(f"# Beam energy: {beam_energy} keV\n")
                f.write("# Format: radius(um) relative_energy_deposition\n")
                f.write("# PSF normalized to maximum = 1.0\n")
                f.write("#\n")

                for r, p in zip(radius_data, psf_data):
                    f.write(f"{r:.6e} {p:.6e}\n")

            return True, "File saved successfully"
        except Exception as e:
            return False, str(e)

    def _calculate_optimal_axis_limits(self, radii, values, axis='both'):
        """
        Calculate optimal axis limits based on actual data range

        Args:
            radii: Array of radius values
            values: Array of PSF/energy values
            axis: 'x', 'y', or 'both'

        Returns:
            Tuple of (x_min, x_max, y_min, y_max) or subset based on axis
        """
        import numpy as np

        # Filter out non-positive values for log scale
        valid_mask = (np.array(radii) > 0) & (np.array(values) > 0)
        valid_radii = np.array(radii)[valid_mask]
        valid_values = np.array(values)[valid_mask]

        if len(valid_radii) == 0 or len(valid_values) == 0:
            # Fallback to defaults
            return (0.01, 100, 1e-10, 2) if axis == 'both' else None

        # X-axis (radius) limits with log-space padding
        min_radius = np.min(valid_radii)
        max_radius = np.max(valid_radii)
        x_padding_factor = 0.5  # Half decade padding in log space
        x_min = min_radius / (10 ** x_padding_factor)
        x_max = max_radius * (10 ** x_padding_factor)

        # Y-axis (PSF) limits using 0.1% threshold strategy
        max_value = np.max(valid_values)
        min_significant = max_value * 0.001  # 0.1% threshold
        min_data = np.min(valid_values)

        # Use whichever is larger: 0.1% of peak or actual minimum (clamped at 1e-10)
        y_min = max(min_significant, min_data, 1e-10) / (10 ** 1.0)  # One decade below
        y_max = max_value * (10 ** 0.5)  # Half decade above

        if axis == 'x':
            return (x_min, x_max)
        elif axis == 'y':
            return (y_min, y_max)
        else:  # 'both'
            return (x_min, x_max, y_min, y_max)

    def plot_beamer_format(self, radius_um, psf_norm):
        """Plot BEAMER format PSF in standard style with dynamic axis limits"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Plot in BEAMER standard format (log-log)
        ax.loglog(radius_um, psf_norm, 'b-', linewidth=2, label='BEAMER PSF')

        # Formatting to match BEAMER standard
        ax.set_xlabel('radius, um', fontsize=12)
        ax.set_ylabel('relative energy deposition', fontsize=12)
        ax.set_title('Electron energy deposition point spread function', fontsize=14)

        # Set dynamic axis limits based on actual data
        x_min, x_max, y_min, y_max = self._calculate_optimal_axis_limits(radius_um, psf_norm)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

        # Grid
        ax.grid(True, which="both", ls="-", alpha=0.2)

        # Legend
        ax.legend(loc='upper right')

        self.figure.tight_layout()
        self.canvas.draw()

    def validate_psf_consolidated(self):
        """Consolidated PSF validation using the best method"""
        if not self.current_csv_path:
            QMessageBox.warning(self, "Warning", "No PSF data loaded for validation")
            return

        self.validate_button.set_working(True, "Validating...")

        try:
            # Load and validate
            df, message = self.file_manager.load_csv_with_validation(self.current_csv_path)

            if df is None:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {message}")
                return

            report = self._validate_psf_comprehensive(df, Path(self.current_csv_path).name)

            # Show report in dialog
            dialog = QMessageBox(self)
            dialog.setWindowTitle("PSF Validation Report")
            dialog.setText(report)
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok)
            dialog.setDetailedText(
                "Comprehensive validation checks:\n"
                "• Data integrity (no negative values)\n"
                "• Monotonicity (decreasing trend)\n"
                "• Statistical quality (noise levels)\n"
                "• Physical reasonableness (R50, R90 values)\n"
                "• Energy conservation\n"
                "• Format compliance"
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Validation failed: {str(e)}")
        finally:
            self.validate_button.set_working(False)

    def _validate_psf_comprehensive(self, df, filename):
        """Comprehensive PSF validation - consolidated best method"""
        report = f"PSF VALIDATION: {filename}\n" + "="*60 + "\n\n"

        # Check for required columns
        radii, energies = self._extract_psf_from_df(df)

        if not radii or not energies:
            report += "❌ Could not extract PSF data from file\n"
            return report

        # Convert to arrays
        radius = np.array(radii)
        energy = np.array(energies)

        # Test 1: Negative values
        if np.any(energy < 0):
            report += f"❌ Found {np.sum(energy < 0)} negative energy values\n"
        else:
            report += "✅ No negative energy values\n"

        # Test 2: Data range
        nonzero = energy > 0
        if np.any(nonzero):
            report += f"✅ Data points: {len(energy)} ({np.sum(nonzero)} non-zero)\n"
            report += f"✅ Radius range: {radius[nonzero].min():.1f} - {radius[nonzero].max():.1f} nm\n"

            # Test 3: Monotonicity (general trend)
            if len(energy[nonzero]) > 10:
                # Use moving average to check trend
                window = min(5, len(energy) // 4)
                if window >= 3:
                    smoothed = np.convolve(energy, np.ones(window)/window, mode='valid')
                    increases = np.sum(np.diff(smoothed) > 0)
                    increase_frac = increases / len(smoothed)

                    if increase_frac < 0.3:
                        report += "✅ PSF shows generally decreasing trend\n"
                    else:
                        report += f"⚠️ PSF has {increase_frac*100:.1f}% increasing segments\n"

            # Test 4: Statistical quality
            tail_mask = radius > 1000  # Beyond 1 μm
            if np.any(tail_mask & nonzero):
                tail_energy = energy[tail_mask & nonzero]
                if len(tail_energy) > 5:
                    cv = np.std(tail_energy) / np.mean(tail_energy)
                    if cv < 0.5:
                        report += "✅ Good statistical quality in tail\n"
                    elif cv < 1.0:
                        report += "⚠️ Moderate noise in tail region\n"
                    else:
                        report += "❌ High noise in tail region\n"

            # Test 5: Physical reasonableness (R50, R90)
            if len(radius) > 1:
                # Calculate cumulative energy
                total = 0
                for i in range(len(radius)-1):
                    if energy[i] > 0 and energy[i+1] > 0:
                        dr = radius[i+1] - radius[i]
                        avg_e = (energy[i] + energy[i+1]) / 2
                        avg_r = (radius[i] + radius[i+1]) / 2
                        contrib = 2 * np.pi * avg_r * avg_e * dr
                        total += contrib

                cumulative = 0
                r50 = None
                r90 = None

                for i in range(len(radius)-1):
                    if energy[i] > 0 and energy[i+1] > 0:
                        dr = radius[i+1] - radius[i]
                        avg_e = (energy[i] + energy[i+1]) / 2
                        avg_r = (radius[i] + radius[i+1]) / 2
                        contrib = 2 * np.pi * avg_r * avg_e * dr
                        cumulative += contrib

                        if r50 is None and cumulative > 0.5 * total:
                            r50 = radius[i]
                        if r90 is None and cumulative > 0.9 * total:
                            r90 = radius[i]

                if r50 and r90:
                    report += f"✅ R50: {r50:.1f} nm, R90: {r90:.1f} nm\n"
                    ratio = r90 / r50
                    if 2 < ratio < 100:
                        report += f"✅ R90/R50 ratio: {ratio:.1f} (reasonable)\n"
                    else:
                        report += f"⚠️ R90/R50 ratio: {ratio:.1f} (check parameters)\n"
        else:
            report += "❌ No non-zero data found\n"

        return report

    def analyze_comparison(self):
        """Analyze multiple PSF datasets for comparison"""
        if len(self.datasets) < 2:
            QMessageBox.warning(self, "Warning", "Need at least 2 PSF datasets for comparison")
            return

        self.analyze_button.set_working(True, "Analyzing...")

        try:
            # Perform comparative analysis
            analysis_report = self._perform_comparative_analysis()

            # Show analysis in dialog
            dialog = QMessageBox(self)
            dialog.setWindowTitle("PSF Comparison Analysis")
            dialog.setText(analysis_report)
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Save)

            result = dialog.exec()

            if result == QMessageBox.Save:
                # Save analysis report
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Analysis Report", "psf_comparison_report.txt",
                    "Text files (*.txt);;All files (*.*)"
                )

                if file_path:
                    with open(file_path, 'w') as f:
                        f.write(analysis_report)
                    QMessageBox.information(self, "Success", f"Analysis saved to {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
        finally:
            self.analyze_button.set_working(False)

    def _perform_comparative_analysis(self):
        """Perform detailed comparison of multiple PSF datasets"""
        report = "PSF COMPARATIVE ANALYSIS\n"
        report += "=" * 50 + "\n\n"

        # Basic statistics for each dataset
        for i, dataset in enumerate(self.datasets):
            radii = np.array(dataset['radii'])
            energies = np.array(dataset['energies'])

            report += f"Dataset {i+1}: {dataset['label']}\n"
            report += "-" * 30 + "\n"

            # Basic stats
            max_energy = np.max(energies)
            max_radius_idx = np.argmax(energies)
            max_radius = radii[max_radius_idx]

            report += f"Peak energy: {max_energy:.2e} eV/nm² at r={max_radius:.1f} nm\n"
            report += f"Data range: {radii.min():.1f} - {radii.max():.1f} nm\n"
            report += f"Points: {len(radii)}\n\n"

        # Comparative metrics
        report += "COMPARATIVE METRICS\n"
        report += "=" * 20 + "\n"

        # Compare peak positions and heights
        peaks = []
        for dataset in self.datasets:
            energies = np.array(dataset['energies'])
            radii = np.array(dataset['radii'])
            max_idx = np.argmax(energies)
            peaks.append({
                'label': dataset['label'],
                'peak_energy': energies[max_idx],
                'peak_radius': radii[max_idx]
            })

        # Find relative differences
        baseline = peaks[0]
        report += f"Baseline: {baseline['label']}\n\n"

        for i, peak in enumerate(peaks[1:], 1):
            energy_ratio = peak['peak_energy'] / baseline['peak_energy']
            radius_diff = peak['peak_radius'] - baseline['peak_radius']

            report += f"Dataset {i+1} vs Baseline:\n"
            report += f"  Energy ratio: {energy_ratio:.3f}x\n"
            report += f"  Peak shift: {radius_diff:+.1f} nm\n\n"

        # Recommendations
        report += "ANALYSIS RECOMMENDATIONS\n"
        report += "=" * 25 + "\n"

        # Check for systematic trends
        energy_ratios = [p['peak_energy'] / baseline['peak_energy'] for p in peaks[1:]]

        if all(r > 1.1 for r in energy_ratios):
            report += "• All variants show higher peak energy - consider dose effects\n"
        elif all(r < 0.9 for r in energy_ratios):
            report += "• All variants show lower peak energy - check material properties\n"
        else:
            report += "• Mixed energy responses - investigate parameter correlations\n"

        peak_shifts = [p['peak_radius'] - baseline['peak_radius'] for p in peaks[1:]]
        if all(s > 2 for s in peak_shifts):
            report += "• Consistent peak broadening observed\n"
        elif all(s < -2 for s in peak_shifts):
            report += "• Consistent peak sharpening observed\n"

        return report

    def _show_save_plot_dialog(self):
        """Show dialog for presentation-ready plot export settings"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                                       QRadioButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
                                       QLabel, QPushButton, QComboBox, QFormLayout)

        dialog = QDialog(self)
        dialog.setWindowTitle("Save Plot - Presentation Settings")
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout()

        # Size presets group
        size_group = QGroupBox("Plot Size")
        size_layout = QVBoxLayout()

        size_button_group = QButtonGroup(dialog)
        size_presets = {
            "Presentation (7×7 cm)": (7, 7),
            "Presentation Wide (10×7 cm)": (10, 7),
            "Presentation Tall (7×10 cm)": (7, 10),
            "Paper Half-Column (8.5×6 cm)": (8.5, 6),
            "Paper Full-Column (17×12 cm)": (17, 12),
            "Paper Full-Page (17×20 cm)": (17, 20),
            "Custom": None
        }

        self._size_radios = {}
        for i, (name, size) in enumerate(size_presets.items()):
            radio = QRadioButton(name)
            size_button_group.addButton(radio, i)
            size_layout.addWidget(radio)
            self._size_radios[name] = (radio, size)

            if name == "Presentation (7×7 cm)":  # Default selection
                radio.setChecked(True)

        # Custom size inputs
        custom_layout = QFormLayout()
        self._custom_width = QDoubleSpinBox()
        self._custom_width.setRange(1, 50)
        self._custom_width.setValue(7)
        self._custom_width.setSuffix(" cm")
        self._custom_width.setEnabled(False)

        self._custom_height = QDoubleSpinBox()
        self._custom_height.setRange(1, 50)
        self._custom_height.setValue(7)
        self._custom_height.setSuffix(" cm")
        self._custom_height.setEnabled(False)

        custom_layout.addRow("Width:", self._custom_width)
        custom_layout.addRow("Height:", self._custom_height)
        size_layout.addLayout(custom_layout)

        # Enable custom inputs when custom radio selected
        def toggle_custom(checked):
            if self._size_radios["Custom"][0].isChecked():
                self._custom_width.setEnabled(True)
                self._custom_height.setEnabled(True)
            else:
                self._custom_width.setEnabled(False)
                self._custom_height.setEnabled(False)

        for radio, _ in self._size_radios.values():
            radio.toggled.connect(toggle_custom)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # Quality settings group
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QFormLayout()

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(150, 600)
        self._dpi_spin.setValue(300)
        self._dpi_spin.setSingleStep(50)
        self._dpi_spin.setSuffix(" DPI")
        quality_layout.addRow("Resolution:", self._dpi_spin)

        self._font_scale = QDoubleSpinBox()
        self._font_scale.setRange(0.5, 3.0)
        self._font_scale.setValue(1.3)
        self._font_scale.setSingleStep(0.1)
        self._font_scale.setSuffix("×")
        self._font_scale.setToolTip("Font size multiplier for better readability")
        quality_layout.addRow("Font Scale:", self._font_scale)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout()

        self._show_legend = QCheckBox("Include legend")
        self._show_legend.setChecked(False)  # Default: no legend
        self._show_legend.setToolTip("Show/hide legend on saved plot")
        display_layout.addWidget(self._show_legend)

        self._show_metrics = QCheckBox("Include metrics (FWHM, R50, R90)")
        self._show_metrics.setChecked(False)  # Default: no metrics
        self._show_metrics.setToolTip("Show/hide statistics text box")
        display_layout.addWidget(self._show_metrics)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG (Raster)", "PDF (Vector)", "SVG (Vector)", "EPS (Vector)"])
        self._format_combo.setCurrentIndex(1)  # Default to PDF
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        save_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Execute dialog
        if dialog.exec() != QDialog.Accepted:
            return None

        # Get selected size
        for name, (radio, size) in self._size_radios.items():
            if radio.isChecked():
                if name == "Custom":
                    size_cm = (self._custom_width.value(), self._custom_height.value())
                else:
                    size_cm = size
                break

        # Get DPI and font scale
        dpi = self._dpi_spin.value()
        font_scale = self._font_scale.value()

        # Get display options
        show_legend = self._show_legend.isChecked()
        show_metrics = self._show_metrics.isChecked()

        # Get format and file path
        format_text = self._format_combo.currentText()
        format_map = {
            "PNG (Raster)": ("PNG files (*.png)", ".png"),
            "PDF (Vector)": ("PDF files (*.pdf)", ".pdf"),
            "SVG (Vector)": ("SVG files (*.svg)", ".svg"),
            "EPS (Vector)": ("EPS files (*.eps)", ".eps")
        }
        file_filter, ext = format_map[format_text]

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", file_filter
        )

        if not file_path:
            return None

        # Ensure correct extension
        if not file_path.lower().endswith(ext):
            file_path += ext

        return file_path, size_cm, dpi, font_scale, show_legend, show_metrics

    def _save_plot_with_settings(self, file_path, size_cm, dpi, font_scale, show_legend, show_metrics):
        """Save plot with presentation-ready formatting"""
        import matplotlib.pyplot as plt

        # Store current figure settings
        old_size = self.figure.get_size_inches()
        old_dpi = self.figure.dpi

        # Convert cm to inches (matplotlib uses inches)
        size_inches = (size_cm[0] / 2.54, size_cm[1] / 2.54)

        # Temporarily modify figure for export
        self.figure.set_size_inches(size_inches)
        self.figure.set_dpi(dpi)

        # Store original visibility states for restoration
        hidden_artists = []

        # Enhance fonts and line widths for all axes
        for ax in self.figure.axes:
            # Increase font sizes
            ax.title.set_fontsize(11 * font_scale)
            ax.title.set_fontweight('bold')
            ax.xaxis.label.set_fontsize(10 * font_scale)
            ax.yaxis.label.set_fontsize(10 * font_scale)
            ax.tick_params(labelsize=9 * font_scale)

            # Make tick marks more visible
            ax.tick_params(width=1.5, length=6)

            # Increase line widths for plot elements
            for line in ax.get_lines():
                current_width = line.get_linewidth()
                line.set_linewidth(current_width * 1.5)

            # Enhance grid if present
            if ax.get_xgridlines():
                ax.grid(True, alpha=0.3, linewidth=0.8)

            # Handle legend visibility
            legend = ax.get_legend()
            if legend:
                if show_legend:
                    # Make legend more readable
                    legend.set_frame_on(True)
                    legend.get_frame().set_alpha(0.9)
                    legend.get_frame().set_linewidth(1.0)
                    for text in legend.get_texts():
                        text.set_fontsize(9 * font_scale)
                else:
                    # Hide legend for export
                    legend.set_visible(False)
                    hidden_artists.append(legend)

            # Handle metrics text box visibility (if present)
            if not show_metrics:
                for text in ax.texts:
                    # Hide text boxes (typically metrics/statistics)
                    if text.get_visible():
                        text.set_visible(False)
                        hidden_artists.append(text)

        # Save with tight bounding box and high quality
        self.figure.savefig(
            file_path,
            dpi=dpi,
            bbox_inches='tight',
            pad_inches=0.05,
            facecolor='white',
            edgecolor='none'
        )

        # Restore original settings
        self.figure.set_size_inches(old_size)
        self.figure.set_dpi(old_dpi)

        # Restore visibility of hidden elements
        for artist in hidden_artists:
            artist.set_visible(True)

        # Reset formatting (re-draw current plot)
        # This will restore original line widths and fonts
        self.canvas.draw()

    def save_plot(self):
        """Save current plot with presentation-ready options"""
        if not self.datasets:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        result = self._show_save_plot_dialog()
        if not result:
            return

        file_path, size_cm, dpi, font_scale, show_legend, show_metrics = result

        self.save_button.set_working(True, "Saving...")
        try:
            self._save_plot_with_settings(file_path, size_cm, dpi, font_scale, show_legend, show_metrics)
            QMessageBox.information(self, "Success",
                                  f"Plot saved to {Path(file_path).name}\n"
                                  f"Size: {size_cm[0]}×{size_cm[1]} cm @ {dpi} DPI")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
        finally:
            self.save_button.set_working(False)

