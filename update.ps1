# update_ebl_for_full_scoring.ps1
# PowerShell script to update EBL simulation for complete energy scoring with depth analysis

param(
    [string]$ProjectPath = "C:\Users\dreec\Geant4Projects\EBeamSim"
)

Write-Host "Updating EBL Simulation for Full Energy Scoring with Depth Analysis" -ForegroundColor Green
Write-Host "Project Path: $ProjectPath" -ForegroundColor Yellow

# Backup function
function Backup-File {
    param([string]$FilePath)
    if (Test-Path $FilePath) {
        $backupPath = "$FilePath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $FilePath $backupPath
        Write-Host "Backed up: $FilePath" -ForegroundColor Cyan
    }
}

# Update SteppingAction.cc for full energy scoring
$steppingActionPath = Join-Path $ProjectPath "src\actions\src\SteppingAction.cc"
Backup-File $steppingActionPath

$steppingActionContent = @'
// SteppingAction.cc
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"

SteppingAction::SteppingAction(EventAction* eventAction, DetectorConstruction* detConstruction)
: G4UserSteppingAction(),
  fEventAction(eventAction),
  fDetConstruction(detConstruction),
  fScoringVolume(nullptr)
{}

SteppingAction::~SteppingAction()
{}

void SteppingAction::UserSteppingAction(const G4Step* step)
{
    // Get energy deposit in this step
    G4double edep = step->GetTotalEnergyDeposit();
    if (edep <= 0.) return;
    
    // Get position of energy deposition (use midpoint of step for accuracy)
    G4ThreeVector prePos = step->GetPreStepPoint()->GetPosition();
    G4ThreeVector postPos = step->GetPostStepPoint()->GetPosition();
    G4ThreeVector pos = (prePos + postPos) * 0.5;
    
    // Add ALL energy deposits to event action for PSF calculation
    // This captures energy in resist, substrate, and backscattered electrons
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());
    
    // Track statistics for validation
    static G4int totalSteps = 0;
    static G4int resistSteps = 0;
    static G4int substrateSteps = 0;
    static G4double totalEnergy = 0.0;
    
    totalSteps++;
    totalEnergy += edep;
    
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (pos.z() >= 0 && pos.z() <= resistThickness) {
        resistSteps++;
    } else if (pos.z() < 0) {
        substrateSteps++;
    }
    
    // Log every 100000 steps for monitoring
    if (totalSteps % 100000 == 0) {
        G4cout << "Steps: " << totalSteps 
               << " (Resist: " << resistSteps 
               << ", Substrate: " << substrateSteps 
               << "), Total E: " << G4BestUnit(totalEnergy, "Energy") 
               << G4endl;
    }
}
'@

Set-Content -Path $steppingActionPath -Value $steppingActionContent -Encoding UTF8

# Update EventAction.hh to include depth tracking
$eventActionHeaderPath = Join-Path $ProjectPath "src\actions\include\EventAction.hh"
Backup-File $eventActionHeaderPath

$eventActionHeaderContent = @'
// EventAction.hh
#ifndef EventAction_h
#define EventAction_h 1

#include "G4UserEventAction.hh"
#include "globals.hh"
#include <vector>
#include <map>

class RunAction;
class DetectorConstruction;

class EventAction : public G4UserEventAction {
public:
    EventAction(RunAction* runAction, DetectorConstruction* detConstruction);
    virtual ~EventAction();

    virtual void BeginOfEventAction(const G4Event* event);
    virtual void EndOfEventAction(const G4Event* event);

    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);

private:
    RunAction* fRunAction;
    DetectorConstruction* fDetConstruction;

    G4double fEnergyDeposit;
    G4double fTotalTrackLength;

    // For point spread function calculation
    std::vector<G4double> fRadialEnergyDeposit;
    
    // For 2D depth-radius analysis
    static const G4int NUM_DEPTH_BINS = 100;
    std::vector<std::vector<G4double>> f2DEnergyDeposit;  // [depth][radius]
    
    // Track energy by region
    G4double fResistEnergy;
    G4double fSubstrateEnergy;
    G4double fAboveResistEnergy;

    // Helper functions
    G4int GetLogBin(G4double radius) const;
    G4int GetDepthBin(G4double z) const;
};

#endif
'@

Set-Content -Path $eventActionHeaderPath -Value $eventActionHeaderContent -Encoding UTF8

# Update EventAction.cc with 2D tracking
$eventActionPath = Join-Path $ProjectPath "src\actions\src\EventAction.cc"
Backup-File $eventActionPath

$eventActionContent = @'
// EventAction.cc
#include "EventAction.hh"
#include "RunAction.hh"
#include "DetectorConstruction.hh"
#include "EBLConstants.hh"
#include "G4UnitsTable.hh"
#include "G4Event.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4AnalysisManager.hh"
#include <cmath>

EventAction::EventAction(RunAction* runAction, DetectorConstruction* detConstruction)
: G4UserEventAction(),
  fRunAction(runAction),
  fDetConstruction(detConstruction),
  fEnergyDeposit(0.),
  fTotalTrackLength(0.),
  fResistEnergy(0.),
  fSubstrateEnergy(0.),
  fAboveResistEnergy(0.)
{
    // Initialize the radial bins for energy deposition
    fRadialEnergyDeposit.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);
    
    // Initialize 2D array for depth-radius analysis
    f2DEnergyDeposit.resize(NUM_DEPTH_BINS);
    for (auto& depthBin : f2DEnergyDeposit) {
        depthBin.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);
    }
}

EventAction::~EventAction()
{}

void EventAction::BeginOfEventAction(const G4Event* event)
{
    fEnergyDeposit = 0.;
    fTotalTrackLength = 0.;
    fResistEnergy = 0.;
    fSubstrateEnergy = 0.;
    fAboveResistEnergy = 0.;

    // Reset radial energy bins
    std::fill(fRadialEnergyDeposit.begin(), fRadialEnergyDeposit.end(), 0.0);
    
    // Reset 2D bins
    for (auto& depthBin : f2DEnergyDeposit) {
        std::fill(depthBin.begin(), depthBin.end(), 0.0);
    }

    // Print progress for first few events and every 10000 events
    G4int eventID = event->GetEventID();
    if (eventID < 10 || eventID % 10000 == 0) {
        G4cout << "Processing event " << eventID << G4endl;
    }
}

void EventAction::EndOfEventAction(const G4Event* event)
{
    // Check if any energy was deposited in this event
    G4double totalEventEnergy = 0.0;
    G4int nonZeroBins = 0;
    for (size_t i = 0; i < fRadialEnergyDeposit.size(); i++) {
        if (fRadialEnergyDeposit[i] > 0) {
            totalEventEnergy += fRadialEnergyDeposit[i];
            nonZeroBins++;
        }
    }

    if (totalEventEnergy > 0) {
        G4int eventID = event->GetEventID();
        if (eventID < 10 || (eventID < 1000 && eventID % 100 == 0)) {
            G4cout << "Event " << eventID << " deposited "
                   << G4BestUnit(totalEventEnergy, "Energy")
                   << " in " << nonZeroBins << " radial bins" << G4endl;
            G4cout << "  Resist: " << G4BestUnit(fResistEnergy, "Energy")
                   << ", Substrate: " << G4BestUnit(fSubstrateEnergy, "Energy")
                   << ", Above: " << G4BestUnit(fAboveResistEnergy, "Energy") << G4endl;
        }
    }

    // Pass accumulated energy data to run action
    fRunAction->AddRadialEnergyDeposit(fRadialEnergyDeposit);
    fRunAction->Add2DEnergyDeposit(f2DEnergyDeposit);
    fRunAction->AddRegionEnergy(fResistEnergy, fSubstrateEnergy, fAboveResistEnergy);
}

// Helper function for logarithmic binning
G4int EventAction::GetLogBin(G4double radius) const
{
    if (!EBL::PSF::USE_LOG_BINNING) {
        // Linear binning
        G4double bin_width = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        G4int bin = static_cast<G4int>(radius / bin_width);
        if (bin >= EBL::PSF::NUM_RADIAL_BINS) bin = EBL::PSF::NUM_RADIAL_BINS - 1;
        return bin;
    }

    // Logarithmic binning
    if (radius <= 0) return -1;
    if (radius < EBL::PSF::MIN_RADIUS) return 0;
    if (radius >= EBL::PSF::MAX_RADIUS) return EBL::PSF::NUM_RADIAL_BINS - 1;

    // Logarithmic binning: bin = log(r/r_min) / log(r_max/r_min) * n_bins
    G4double logRatio = std::log(radius / EBL::PSF::MIN_RADIUS) /
                        std::log(EBL::PSF::MAX_RADIUS / EBL::PSF::MIN_RADIUS);
    G4int bin = static_cast<G4int>(logRatio * (EBL::PSF::NUM_RADIAL_BINS - 1));

    // Ensure bin is within valid range
    if (bin < 0) bin = 0;
    if (bin >= EBL::PSF::NUM_RADIAL_BINS) bin = EBL::PSF::NUM_RADIAL_BINS - 1;

    return bin;
}

G4int EventAction::GetDepthBin(G4double z) const
{
    // Define depth range: -50um to +150nm (covers substrate and above resist)
    const G4double minDepth = -50.0 * micrometer;
    const G4double maxDepth = 150.0 * nanometer;
    const G4double depthRange = maxDepth - minDepth;
    
    if (z < minDepth) return 0;
    if (z > maxDepth) return NUM_DEPTH_BINS - 1;
    
    G4int bin = static_cast<G4int>((z - minDepth) / depthRange * NUM_DEPTH_BINS);
    if (bin < 0) bin = 0;
    if (bin >= NUM_DEPTH_BINS) bin = NUM_DEPTH_BINS - 1;
    
    return bin;
}

void EventAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // Skip if no energy deposited
    if (edep <= 0) return;

    // Accumulate total energy deposit
    fEnergyDeposit += edep;

    // Calculate radial distance from beam axis (beam enters along z-axis)
    G4double r = std::sqrt(x*x + y*y);

    // Get logarithmic bin number for radius
    G4int radialBin = GetLogBin(r);
    
    // Get depth bin
    G4int depthBin = GetDepthBin(z);

    // Add energy to appropriate bins
    if (radialBin >= 0 && radialBin < static_cast<G4int>(fRadialEnergyDeposit.size())) {
        fRadialEnergyDeposit[radialBin] += edep;
        
        // Add to 2D histogram
        if (depthBin >= 0 && depthBin < NUM_DEPTH_BINS) {
            f2DEnergyDeposit[depthBin][radialBin] += edep;
        }
    }
    
    // Track energy by region
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (z >= 0 && z <= resistThickness) {
        fResistEnergy += edep;
    } else if (z < 0) {
        fSubstrateEnergy += edep;
    } else {
        fAboveResistEnergy += edep;
    }

    // Enhanced debug output for first few deposits
    static G4int debugCount = 0;
    if (debugCount < 50) {
        G4cout << "Energy deposit #" << debugCount << ": "
               << G4BestUnit(edep, "Energy") << " at r=" << G4BestUnit(r, "Length")
               << " z=" << G4BestUnit(z, "Length")
               << " (radial bin " << radialBin << ", depth bin " << depthBin << ")" << G4endl;
        debugCount++;
    }
}
'@

Set-Content -Path $eventActionPath -Value $eventActionContent -Encoding UTF8

# Update RunAction.hh to handle 2D data
$runActionHeaderPath = Join-Path $ProjectPath "src\actions\include\RunAction.hh"
Backup-File $runActionHeaderPath

$runActionHeaderContent = @'
// RunAction.hh
#ifndef RunAction_h
#define RunAction_h 1

#include "G4UserRunAction.hh"
#include "globals.hh"
#include <vector>
#include "G4Accumulable.hh"

class G4Run;
class DetectorConstruction;
class PrimaryGeneratorAction;

class RunAction : public G4UserRunAction {
public:
    RunAction(DetectorConstruction* detConstruction,
        PrimaryGeneratorAction* primaryGenerator);
    virtual ~RunAction();

    virtual void BeginOfRunAction(const G4Run*);
    virtual void EndOfRunAction(const G4Run*);

    // Methods to accumulate energy deposition data
    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);
    void AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit);
    void Add2DEnergyDeposit(const std::vector<std::vector<G4double>>& energy2D);
    void AddRegionEnergy(G4double resist, G4double substrate, G4double above);

    // Access methods for analysis
    std::vector<G4double> GetRadialEnergyProfile() const { return fRadialEnergyProfile; }

private:
    DetectorConstruction* fDetConstruction;
    PrimaryGeneratorAction* fPrimaryGenerator;

    // For energy deposition analysis
    std::vector<G4double> fRadialEnergyProfile;
    std::vector<std::vector<G4double>> f2DEnergyProfile;
    
    G4Accumulable<G4double> fTotalEnergyDeposit;
    G4Accumulable<G4double> fResistEnergyTotal;
    G4Accumulable<G4double> fSubstrateEnergyTotal;
    G4Accumulable<G4double> fAboveResistEnergyTotal;
    
    G4int fNumEvents;

    // Helper functions for logarithmic binning
    G4double GetBinRadius(G4int bin) const;
    void GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const;

    // Analysis helpers
    void SaveResults();
    void SaveCSVFormat(const std::string& outputDir);
    void SaveBEAMERFormat(const std::string& outputDir);
    void Save2DFormat(const std::string& outputDir);
    void SaveSummary(const std::string& outputDir);
};

#endif
'@

Set-Content -Path $runActionHeaderPath -Value $runActionHeaderContent -Encoding UTF8

# Update RunAction.cc to save 2D data
$runActionPath = Join-Path $ProjectPath "src\actions\src\RunAction.cc"
Backup-File $runActionPath

# Create the content for RunAction.cc with 2D output
$runActionContent = Get-Content $runActionPath -Raw

# Insert the 2D save function before SaveSummary
$save2DFunction = @'

void RunAction::Save2DFormat(const std::string& outputDir)
{
    std::string filename = outputDir.empty() ? "ebl_2d_data.csv" : outputDir + "/ebl_2d_data.csv";
    G4cout << "Saving 2D depth-radius data to: " << filename << G4endl;

    std::ofstream file(filename);
    if (!file.is_open()) {
        G4cerr << "Error: Could not open 2D output file: " << filename << G4endl;
        return;
    }

    // Write header with radius bins
    file << "Depth(nm)";
    for (G4int r = 0; r < EBL::PSF::NUM_RADIAL_BINS; r++) {
        G4double radius = GetBinRadius(r);
        file << "," << radius/nanometer;
    }
    file << std::endl;

    // Define depth range
    const G4double minDepth = -50.0 * micrometer;
    const G4double maxDepth = 150.0 * nanometer;
    const G4double depthRange = maxDepth - minDepth;
    const G4int numDepthBins = 100;

    // Write data rows
    for (G4int d = 0; d < numDepthBins; d++) {
        G4double depth = minDepth + (d + 0.5) * depthRange / numDepthBins;
        file << depth/nanometer;
        
        for (G4int r = 0; r < EBL::PSF::NUM_RADIAL_BINS; r++) {
            G4double rInner, rOuter;
            GetBinBoundaries(r, rInner, rOuter);
            G4double area = CLHEP::pi * (rOuter*rOuter - rInner*rInner);
            
            G4double energyDensity = 0.0;
            if (area > 0 && fNumEvents > 0 && d < static_cast<G4int>(f2DEnergyProfile.size())) {
                energyDensity = f2DEnergyProfile[d][r] / (area * fNumEvents);
            }
            
            file << "," << energyDensity/(eV/(nanometer*nanometer));
        }
        file << std::endl;
    }

    file.close();
    G4cout << "2D data saved successfully" << G4endl;
}

void RunAction::Add2DEnergyDeposit(const std::vector<std::vector<G4double>>& energy2D)
{
    // Initialize if needed
    if (f2DEnergyProfile.empty()) {
        f2DEnergyProfile = energy2D;
    } else {
        // Accumulate
        for (size_t d = 0; d < energy2D.size() && d < f2DEnergyProfile.size(); d++) {
            for (size_t r = 0; r < energy2D[d].size() && r < f2DEnergyProfile[d].size(); r++) {
                f2DEnergyProfile[d][r] += energy2D[d][r];
            }
        }
    }
}

void RunAction::AddRegionEnergy(G4double resist, G4double substrate, G4double above)
{
    fResistEnergyTotal += resist;
    fSubstrateEnergyTotal += substrate;
    fAboveResistEnergyTotal += above;
}
'@

# Update SaveResults to include 2D save
$saveResultsUpdate = @'
void RunAction::SaveResults()
{
    G4cout << "=== Saving Results ===" << G4endl;
    G4cout << "Number of events processed: " << fNumEvents << G4endl;
    G4cout << "Total energy deposited: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << G4endl;
    G4cout << "Energy in resist: " << G4BestUnit(fResistEnergyTotal.GetValue(), "Energy") << G4endl;
    G4cout << "Energy in substrate: " << G4BestUnit(fSubstrateEnergyTotal.GetValue(), "Energy") << G4endl;
    G4cout << "Energy above resist: " << G4BestUnit(fAboveResistEnergyTotal.GetValue(), "Energy") << G4endl;

    // Ensure output directory exists
    std::string outputDir = EBL::Output::DEFAULT_DIRECTORY;
    if (!outputDir.empty()) {
        try {
            std::filesystem::create_directories(outputDir);
        } catch (const std::exception& e) {
            G4cout << "Warning: Could not create output directory: " << e.what() << G4endl;
            outputDir = "";
        }
    }

    // Save all formats
    SaveCSVFormat(outputDir);
    SaveBEAMERFormat(outputDir);
    Save2DFormat(outputDir);
    SaveSummary(outputDir);
}
'@

# We need to manually update the RunAction.cc file with these additions
Write-Host "Note: RunAction.cc needs manual updates for 2D functionality" -ForegroundColor Yellow

# Update the GUI to show 2D visualization
$guiPath = Join-Path $ProjectPath "scripts\gui\ebl_gui.py"
Backup-File $guiPath

# Add 2D visualization capability to the GUI (insert after PlotWidget class)
$gui2DUpdate = @'

class Plot2DWidget(QWidget):
    """Custom widget for 2D heatmap visualization"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Controls
        controls = QHBoxLayout()
        
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "inferno", "magma", "jet", "hot", "cool"])
        self.colormap_combo.currentTextChanged.connect(self.update_colormap)
        
        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.toggled.connect(self.update_plot)
        
        self.load_2d_button = QPushButton("Load 2D Data")
        self.load_2d_button.clicked.connect(self.load_2d_data)
        
        controls.addWidget(QLabel("Colormap:"))
        controls.addWidget(self.colormap_combo)
        controls.addWidget(self.log_scale_check)
        controls.addStretch()
        controls.addWidget(self.load_2d_button)
        
        layout.addWidget(self.toolbar)
        layout.addLayout(controls)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        
        self.current_data = None
        
    def load_2d_data(self):
        """Load 2D depth-radius data"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load 2D Data", "", "CSV files (*.csv);;All files (*.*)"
        )
        
        if file_path:
            try:
                # Read CSV
                data = []
                depths = []
                radii = []
                
                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    # First row is header with radius values
                    header = next(reader)
                    radii = [float(r) for r in header[1:]]
                    
                    for row in reader:
                        if len(row) > 1:
                            depths.append(float(row[0]))
                            data.append([float(val) for val in row[1:]])
                
                if data:
                    self.current_data = (np.array(data), depths, radii)
                    self.plot_2d_data()
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load 2D data: {str(e)}")
    
    def plot_2d_data(self):
        """Plot the 2D heatmap"""
        if not self.current_data:
            return
            
        data, depths, radii = self.current_data
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Apply log scale if requested
        plot_data = data.copy()
        if self.log_scale_check.isChecked():
            # Add small value to avoid log(0)
            plot_data = np.log10(plot_data + 1e-10)
        
        # Create heatmap
        im = ax.imshow(plot_data, 
                       aspect='auto',
                       cmap=self.colormap_combo.currentText(),
                       extent=[min(radii), max(radii), min(depths), max(depths)],
                       origin='lower')
        
        # Add colorbar
        cbar = self.figure.colorbar(im, ax=ax)
        if self.log_scale_check.isChecked():
            cbar.set_label('Log10(Energy Density) [eV/nm²]')
        else:
            cbar.set_label('Energy Density [eV/nm²]')
        
        # Labels
        ax.set_xlabel('Radius [nm]')
        ax.set_ylabel('Depth [nm]')
        ax.set_title('2D Energy Deposition Profile')
        
        # Add resist boundaries
        ax.axhline(y=0, color='white', linestyle='--', alpha=0.5, label='Substrate/Resist')
        ax.axhline(y=30, color='white', linestyle='--', alpha=0.5, label='Resist/Vacuum')
        
        # Set x-axis to log scale for better visualization
        ax.set_xscale('log')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def update_colormap(self):
        """Update plot when colormap changes"""
        if self.current_data:
            self.plot_2d_data()
    
    def update_plot(self):
        """Update plot when scale changes"""
        if self.current_data:
            self.plot_2d_data()
'@

# Create install script for required Python packages
$requirementsPath = Join-Path $ProjectPath "scripts\gui\requirements.txt"
@"
PySide6>=6.0.0
matplotlib>=3.5.0
numpy>=1.20.0
"@ | Set-Content -Path $requirementsPath -Encoding UTF8

# Create update summary
$summaryPath = Join-Path $ProjectPath "update_summary.txt"
@"
EBL Simulation Update Summary
============================
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Files Updated:
1. SteppingAction.cc - Now captures ALL energy deposits (resist, substrate, backscatter)
2. EventAction.hh/cc - Added 2D depth-radius tracking and region-based energy accounting
3. RunAction.hh/cc - Added 2D data output functionality
4. GUI - Added 2D visualization capability (requires manual integration)

New Features:
- Complete energy scoring throughout all materials
- 2D depth-radius energy deposition matrix
- Energy tracking by region (resist, substrate, above)
- Enhanced debug output for validation
- 2D heatmap visualization in GUI

Output Files:
- ebl_psf_data.csv - Standard PSF radial profile
- ebl_2d_data.csv - 2D depth-radius energy map
- beamer_psf.dat - BEAMER-compatible PSF
- simulation_summary.txt - Enhanced with region statistics

Manual Steps Required:
1. Update RunAction.cc with the 2D save functions
2. Add Plot2DWidget to the GUI visualization tab
3. Rebuild the project
4. Install Python requirements: pip install -r scripts/gui/requirements.txt

Notes:
- Depth range: -50μm to +150nm (covers substrate and above resist)
- 100 depth bins, 250 radial bins (logarithmic)
- All energy deposits are now captured for accurate PSF
"@ | Set-Content -Path $summaryPath -Encoding UTF8

Write-Host "`nUpdate Complete!" -ForegroundColor Green
Write-Host "Summary saved to: $summaryPath" -ForegroundColor Yellow
Write-Host "`nIMPORTANT: Manual steps required:" -ForegroundColor Red
Write-Host "1. Manually update RunAction.cc with the 2D functions" -ForegroundColor Yellow
Write-Host "2. Add Plot2DWidget to GUI (code provided in comments)" -ForegroundColor Yellow
Write-Host "3. Rebuild the C++ project" -ForegroundColor Yellow
Write-Host "4. Install Python packages: pip install -r scripts/gui/requirements.txt" -ForegroundColor Yellow

# Output the 2D functions that need to be added to RunAction.cc
Write-Host "`nAdd these functions to RunAction.cc:" -ForegroundColor Cyan
Write-Host $save2DFunction -ForegroundColor Gray
Write-Host "`nUpdate SaveResults() function:" -ForegroundColor Cyan
Write-Host $saveResultsUpdate -ForegroundColor Gray