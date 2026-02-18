#!/usr/bin/env python3
"""
PSF Visualization Viewer - Qt6 Image Browser

A simple PySide6-based viewer for browsing the generated PSF visualizations
for PhD defense preparation.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QSplitter,
    QScrollArea, QFrame, QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont, QKeySequence, QShortcut

# Output directory from psf_visualizer.py
OUTPUT_DIR = Path(__file__).parent / "psf_analysis_output"

# Figure descriptions for display
FIGURE_INFO = {
    # Enhanced visualizations (viridis, dual-view, etc.)
    "psf_dual_view.png": {
        "title": "★ Dual-View PSF (Forward + Full)",
        "description": "LEFT: Forward scattering detail (0-500nm) - determines lithography resolution. "
                      "RIGHT: Full range log-log plot showing proximity effect zone. "
                      "Best single figure for understanding PSF physics.",
        "placement": "Results Section - Primary PSF figure"
    },
    "stopping_power_analysis.png": {
        "title": "★ Stopping Power vs Backscatter",
        "description": "Explains the BD paradox: lower metal content → MORE backscatter! "
                      "Physics: lower stopping power allows deeper penetration into Si substrate, "
                      "resulting in more backscatter energy. Key insight for resist design.",
        "placement": "Results Section - Key finding"
    },
    "presentation_summary.png": {
        "title": "★ Presentation Summary (6-panel)",
        "description": "Complete 6-panel summary figure for presentations. Includes: "
                      "A) Forward scattering, B) Full PSF, C) Backscatter bar chart, "
                      "D) Z dependence, E) Stopping power paradox, F) Key findings.",
        "placement": "Presentation - Single summary slide"
    },
    "psf_viridis_overlay.png": {
        "title": "PSF Overlay (Viridis)",
        "description": "All 6 metalcone PSFs with viridis colormap. Solid lines = EG linker, "
                      "dashed = BD linker. Shows resist, forward scatter, and backscatter zones.",
        "placement": "Results Section - Main comparison"
    },
    "psf_log_log.png": {
        "title": "Log-Log Power Law Analysis",
        "description": "Log-log PSF plot revealing power-law behavior of scattering tails. "
                      "Reference slopes show r⁻² (Gaussian) and r⁻³ (screened) decay. "
                      "Important for PEC algorithm selection.",
        "placement": "Results Section - Advanced analysis"
    },
    "psf_metal_series_viridis.png": {
        "title": "Metal Series (Al/Zn/Sn)",
        "description": "Side-by-side comparison of each metal with both linkers. "
                      "Shows EG vs BD effect for each metal type separately.",
        "placement": "Results Section - Material comparison"
    },
    # Original visualizations
    "psf_overlay_all.png": {
        "title": "PSF Overlay (Original)",
        "description": "Primary comparison showing all 6 metalcone PSFs on a single plot. "
                      "Log scale reveals orders of magnitude difference in PSF tails.",
        "placement": "Results Section - Alternative view"
    },
    "psf_by_linker.png": {
        "title": "EG vs BD Linker Comparison",
        "description": "Side-by-side comparison showing organic linker effects. "
                      "EG-based metalcones have higher metal fractions (23-52%) vs "
                      "BD variants (18-44%).",
        "placement": "Results Section - Organic chemistry effects"
    },
    "psf_by_metal.png": {
        "title": "Metal Series Comparison",
        "description": "Demonstrates atomic number (Z) dependence of electron scattering. "
                      "Clear progression: Al (Z=13) → Zn (Z=30) → Sn (Z=50).",
        "placement": "Background/Theory Section OR Results"
    },
    "psf_forward_vs_backscatter.png": {
        "title": "Forward vs Backscatter Decomposition",
        "description": "Explains proximity effect physics. Short range (<500 nm): "
                      "forward scattering. Long range (>1 μm): backscatter.",
        "placement": "Background/Theory Section"
    },
    "metrics_comparison.png": {
        "title": "Energy Deposition Metrics",
        "description": "Bar chart comparing energy deposition metrics. Values >100% indicate "
                      "backscatter contribution.",
        "placement": "Results Section - Quantitative analysis"
    },
    "z_vs_backscatter.png": {
        "title": "Z vs Backscatter Correlation",
        "description": "Shows physical relationship between atomic number and energy deposition. "
                      "Validates Rutherford scattering physics (cross-section ~ Z²).",
        "placement": "Results Section - Physics validation"
    },
    "metal_fraction_correlation.png": {
        "title": "Metal Fraction Correlation",
        "description": "Connects composition to performance. Shows the stopping power paradox.",
        "placement": "Results Section - Material design implications"
    },
    # Presentation-quality single figures
    "psf_modern_dark.png": {
        "title": "★★ Modern Dark Theme",
        "description": "Neon-style PSF with cyan glow on dark background. "
                      "Great for modern presentations and dark-themed slides.",
        "placement": "Presentation - Hero figure"
    },
    "psf_modern_light.png": {
        "title": "★★ Modern Light Theme",
        "description": "Clean, professional light-themed PSF with subtle blue styling. "
                      "Perfect for academic papers and formal presentations.",
        "placement": "Presentation or Publication"
    },
    "psf_infographic.png": {
        "title": "★★ Infographic Style",
        "description": "PSF with physical schematic showing electron beam, resist, and substrate. "
                      "Includes simulation parameters box. Great for explaining the physics.",
        "placement": "Presentation - Educational figure"
    },
    "psf_minimal.png": {
        "title": "★★ Ultra-Minimal",
        "description": "Stripped-down elegant PSF. No clutter, maximum clarity. "
                      "Use when the data should speak for itself.",
        "placement": "Publication - Main figure"
    },
    "psf_gradient_bg.png": {
        "title": "★★ Gradient Background",
        "description": "Dramatic PSF with glowing line on dark gradient background. "
                      "Eye-catching for title slides or conference posters.",
        "placement": "Presentation - Impact figure"
    }
}


class ImageLabel(QLabel):
    """Scalable image label that maintains aspect ratio."""

    def __init__(self):
        super().__init__()
        self._pixmap = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            super().setPixmap(scaled)

    def resizeEvent(self, event):
        self._update_scaled_pixmap()
        super().resizeEvent(event)


class PSFViewer(QMainWindow):
    """Main viewer window for PSF visualizations."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSF Visualization Viewer - PhD Defense")
        self.setMinimumSize(1200, 800)

        # Find available images
        self.images = self._find_images()
        self.current_index = 0

        self._setup_ui()
        self._setup_shortcuts()

        # Load first image
        if self.images:
            self._select_image(0)

    def _find_images(self):
        """Find all PNG images in the output directory."""
        images = []
        if OUTPUT_DIR.exists():
            for png in sorted(OUTPUT_DIR.glob("*.png")):
                images.append(png)
        return images

    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - image list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        list_label = QLabel("Visualizations")
        list_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(list_label)

        self.image_list = QListWidget()
        self.image_list.setMinimumWidth(200)
        for img_path in self.images:
            name = img_path.name
            info = FIGURE_INFO.get(name, {})
            title = info.get("title", name)
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, img_path)
            self.image_list.addItem(item)
        self.image_list.currentRowChanged.connect(self._select_image)
        left_layout.addWidget(self.image_list)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self._prev_image)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self._next_image)
        nav_layout.addWidget(self.next_btn)
        left_layout.addLayout(nav_layout)

        splitter.addWidget(left_panel)

        # Center panel - image display
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(5, 5, 5, 5)

        self.title_label = QLabel("Select an image")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.title_label)

        # Image display with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.image_label = ImageLabel()
        self.image_label.setText("No image loaded")
        scroll.setWidget(self.image_label)
        center_layout.addWidget(scroll, 1)

        splitter.addWidget(center_panel)

        # Right panel - info
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        info_label = QLabel("Figure Information")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(info_label)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumWidth(250)
        self.info_text.setMaximumWidth(350)
        right_layout.addWidget(self.info_text)

        # Summary table display
        summary_label = QLabel("Summary Data")
        summary_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(summary_label)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier New", 9))
        self.summary_text.setMaximumHeight(200)
        self._load_summary()
        right_layout.addWidget(self.summary_text)

        splitter.addWidget(right_panel)

        # Set splitter sizes
        splitter.setSizes([200, 700, 300])

        # Status bar
        self.statusBar().showMessage(f"Found {len(self.images)} visualizations in {OUTPUT_DIR}")

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence(Qt.Key_Left), self, self._prev_image)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._next_image)
        QShortcut(QKeySequence(Qt.Key_Up), self, self._prev_image)
        QShortcut(QKeySequence(Qt.Key_Down), self, self._next_image)
        QShortcut(QKeySequence("Escape"), self, self.close)

    def _load_summary(self):
        """Load and display summary table."""
        summary_path = OUTPUT_DIR / "summary_table.txt"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                self.summary_text.setText(f.read())
        else:
            self.summary_text.setText("Summary table not found.\nRun psf_visualizer.py first.")

    def _select_image(self, index):
        """Select and display an image by index."""
        if 0 <= index < len(self.images):
            self.current_index = index
            img_path = self.images[index]

            # Update list selection
            self.image_list.setCurrentRow(index)

            # Load and display image
            pixmap = QPixmap(str(img_path))
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
                self.title_label.setText(img_path.name)
            else:
                self.image_label.setText(f"Failed to load: {img_path.name}")

            # Update info panel
            info = FIGURE_INFO.get(img_path.name, {})
            info_html = f"""
            <h3>{info.get('title', img_path.name)}</h3>
            <p><b>Suggested Placement:</b><br>{info.get('placement', 'N/A')}</p>
            <p><b>Description:</b><br>{info.get('description', 'No description available.')}</p>
            <p><b>File:</b> {img_path.name}</p>
            <p><b>Size:</b> {pixmap.width()} × {pixmap.height()} px</p>
            """
            self.info_text.setHtml(info_html)

            # Update navigation buttons
            self.prev_btn.setEnabled(index > 0)
            self.next_btn.setEnabled(index < len(self.images) - 1)

            self.statusBar().showMessage(f"Viewing: {img_path.name} ({index + 1}/{len(self.images)})")

    def _prev_image(self):
        """Go to previous image."""
        if self.current_index > 0:
            self._select_image(self.current_index - 1)

    def _next_image(self):
        """Go to next image."""
        if self.current_index < len(self.images) - 1:
            self._select_image(self.current_index + 1)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Check if output directory exists
    if not OUTPUT_DIR.exists():
        print(f"Output directory not found: {OUTPUT_DIR}")
        print("Run psf_visualizer.py first to generate figures.")
        return 1

    viewer = PSFViewer()
    viewer.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
