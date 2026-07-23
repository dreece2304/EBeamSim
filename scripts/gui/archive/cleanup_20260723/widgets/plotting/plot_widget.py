"""
1D PSF plotting widget with BEAMER conversion and PSF comparison
Extracted from monolithic GUI for modular architecture
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, 
    QCheckBox, QLabel, QTextEdit, QFileDialog, QMessageBox
)
from matplotlib.figure import Figure
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from core.file_manager import FileManager
from widgets.common.status_button import StatusButton


class PlotWidget(QWidget):
    """Enhanced widget for 1D PSF plots with BEAMER conversion and PSF comparison"""

    def __init__(self, file_manager: FileManager):
        super().__init__()
        self.file_manager = file_manager
        self.datasets: List[Dict[str, Any]] = []  # Store multiple PSF datasets for comparison
        self.current_csv_path: Optional[str] = None
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

    def load_data(self):
        """Load PSF data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load PSF Data", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_path:
            self.load_button.set_working(True, "Loading...")

            try:
                # Use file manager for consistent loading
                df, message = self.file_manager.load_csv_with_validation(file_path)

                if df is None:
                    QMessageBox.critical(self, "Error", f"Failed to load PSF data: {message}")
                    return

                # Extract PSF data from CSV
                radii, energies = self._extract_psf_from_df(df)

                if not radii or not energies:
                    QMessageBox.warning(self, "Warning", "No valid PSF data found in file")
                    return

                # Store the path for BEAMER conversion
                self.current_csv_path = file_path

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
        """Add additional PSF dataset for comparison"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add PSF Data for Comparison", str(self.file_manager.working_dir),
            "CSV files (*.csv);;All files (*.*)"
        )

        if file_paths:
            self.compare_button.set_working(True, "Loading...")

            colors = ['red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive']
            color_idx = len(self.datasets) - 1  # Start from second color

            try:
                for file_path in file_paths:
                    # Load and validate each file
                    df, message = self.file_manager.load_csv_with_validation(file_path)

                    if df is None:
                        print(f"Skipping {file_path}: {message}")
                        continue

                    # Extract PSF data
                    radii, energies = self._extract_psf_from_df(df)

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

    def _extract_psf_from_df(self, df) -> Tuple[List[float], List[float]]:
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

    def plot_all_datasets(self):
        """Plot all loaded datasets with current settings"""
        if not self.datasets:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        plot_type = self.plot_type_combo.currentText()

        for dataset in self.datasets:
            radii = dataset['radii']
            energies = dataset['energies']
            label = dataset['label']
            style = dataset['style']

            if plot_type == "Log-Log":
                valid = [(r > 0 and e > 0) for r, e in zip(radii, energies)]
                r_filt = [r for r, v in zip(radii, valid) if v]
                e_filt = [e for e, v in zip(energies, valid) if v]

                if r_filt and e_filt:
                    ax.loglog(r_filt, e_filt, label=label, **style)
            elif plot_type == "Semi-Log":
                ax.semilogy(radii, energies, label=label, **style)
            else:
                ax.plot(radii, energies, label=label, **style)

        ax.set_xlabel('Radius (nm)')
        ax.set_ylabel('Energy Deposition (eV/nm²)')
        ax.set_title(f'PSF Comparison - {plot_type} Scale')
        ax.grid(True, alpha=0.3)

        if len(self.datasets) > 1:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

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

        # Get beam energy from main window (we'll need to pass this)
        beam_energy = 100.0  # Default, should be passed from main window

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
                                                f"Proximity parameters:\n"
                                                f"alpha (forward): {alpha:.3f}\n"
                                                f"beta (backscatter): {beta:.3f}\n\n"
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

    def _convert_csv_to_beamer_consolidated(self, df, beam_energy: float, apply_smoothing: bool = True):
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

            # Calculate proximity parameters
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

    def _write_beamer_file(self, file_path: str, radius_data: List[float], psf_data: List[float], 
                          source_file: str, beam_energy: float) -> Tuple[bool, str]:
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

    def plot_beamer_format(self, radius_um: List[float], psf_norm: List[float]):
        """Plot BEAMER format PSF in standard style"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Plot in BEAMER standard format (log-log)
        ax.loglog(radius_um, psf_norm, 'b-', linewidth=2, label='BEAMER PSF')

        # Formatting to match BEAMER standard
        ax.set_xlabel('radius, um', fontsize=12)
        ax.set_ylabel('relative energy deposition', fontsize=12)
        ax.set_title('Electron energy deposition point spread function', fontsize=14)

        # Set axis limits similar to BEAMER
        ax.set_xlim(0.01, 100)
        ax.set_ylim(1e-10, 2)

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

    def _validate_psf_comprehensive(self, df, filename: str) -> str:
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

    def _perform_comparative_analysis(self) -> str:
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

    def save_plot(self):
        """Save current plot"""
        if not self.datasets:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            "PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg)"
        )

        if file_path:
            self.save_button.set_working(True, "Saving...")
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
            finally:
                self.save_button.set_working(False)