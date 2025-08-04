#!/usr/bin/env python3
"""
fix_pattern_preview.py

Quick fix to add automatic pattern preview to the Pattern Scanning tab
without needing a separate tab or button.
"""

def add_pattern_preview_to_scanning_tab(self):
    """Add this to the Pattern Scanning tab creation"""
    
    # Add a preview panel at the bottom of Pattern Scanning tab
    preview_group = QGroupBox("Pattern Preview")
    preview_layout = QVBoxLayout()
    
    # Small matplotlib canvas for pattern preview
    self.pattern_preview_figure = Figure(figsize=(4, 4))
    self.pattern_preview_canvas = FigureCanvas(self.pattern_preview_figure)
    self.pattern_preview_canvas.setMaximumHeight(300)
    preview_layout.addWidget(self.pattern_preview_canvas)
    
    # Info label
    self.pattern_preview_info = QLabel("Pattern preview will update automatically")
    preview_layout.addWidget(self.pattern_preview_info)
    
    preview_group.setLayout(preview_layout)
    
    # Add to main layout (at the end of create_pattern_tab)
    layout.addWidget(preview_group)
    
    # Connect all pattern controls to auto-update
    self.pattern_type_combo.currentTextChanged.connect(self.update_pattern_preview)
    self.pattern_size_spin.valueChanged.connect(self.update_pattern_preview)
    self.shot_pitch_spin.valueChanged.connect(self.update_pattern_preview)
    self.eos_mode_combo.currentIndexChanged.connect(self.update_pattern_preview)
    
    # Initial preview
    self.update_pattern_preview()

def update_pattern_preview(self):
    """Auto-update pattern preview when parameters change"""
    try:
        # Clear figure
        self.pattern_preview_figure.clear()
        ax = self.pattern_preview_figure.add_subplot(111)
        
        # Get parameters
        pattern_type = self.pattern_type_combo.currentText()
        size = self.pattern_size_spin.value()
        shot_pitch = self.shot_pitch_spin.value()
        eos_mode = 3 if self.eos_mode_combo.currentIndex() == 0 else 6
        
        # Calculate basic info
        machine_grid = 1.0 if eos_mode == 3 else 0.125  # nm
        exposure_grid = machine_grid * shot_pitch  # nm
        n_shots_1d = int(size * 1000 / exposure_grid)
        total_shots = n_shots_1d ** 2
        
        # Simple visualization
        if pattern_type == "square":
            # Draw square outline
            square = plt.Rectangle((-size/2, -size/2), size, size, 
                                 fill=False, edgecolor='blue', linewidth=2)
            ax.add_patch(square)
            
            # Show some shot points (not all for performance)
            if n_shots_1d <= 20:
                x = np.linspace(-size/2, size/2, n_shots_1d)
                y = np.linspace(-size/2, size/2, n_shots_1d)
                X, Y = np.meshgrid(x, y)
                ax.scatter(X.flatten(), Y.flatten(), c='red', s=1)
        
        ax.set_xlim(-size*0.6, size*0.6)
        ax.set_ylim(-size*0.6, size*0.6)
        ax.set_xlabel(f'X (μm)')
        ax.set_ylabel(f'Y (μm)')
        ax.set_title(f'{pattern_type.capitalize()} Pattern')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # Update info
        self.pattern_preview_info.setText(
            f"Shots: {total_shots:,} | "
            f"Grid: {exposure_grid:.1f} nm | "
            f"Time: ~{total_shots/50000:.1f} s"
        )
        
        self.pattern_preview_canvas.draw()
        
    except Exception as e:
        self.pattern_preview_info.setText(f"Preview error: {str(e)}")

# To integrate into existing GUI:
# 1. Add the preview panel to Pattern Scanning tab
# 2. Remove the separate Pattern Visualization tab
# 3. Move proximity analysis to its own dedicated tab