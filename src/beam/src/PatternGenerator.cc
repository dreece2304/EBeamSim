// PatternGenerator.cc
#include "PatternGenerator.hh"
#include "G4SystemOfUnits.hh"
#include "G4PhysicalConstants.hh"
#include <cmath>
#include <sstream>

PatternGenerator::PatternGenerator()
    : fPatternType(SINGLE_SPOT),
      fPatternSize(1000.0 * nm),  // 1 um default
      fPatternCenter(G4ThreeVector(0, 0, 0)),
      fJEOLMode(MODE_3_4TH_LENS),
      fShotPitch(4),  // 4x machine grid default
      fMachineGrid(1.0 * nm),
      fFieldSize(500.0 * um),
      fBeamCurrent(2.0),  // 2 nA default
      fDose(300.0),  // 300 uC/cm2 default
      fDwellTime(0.0),
      fClockFrequency(0.0) {
    
    SetJEOLMode(fJEOLMode);  // Initialize mode-specific parameters
}

PatternGenerator::~PatternGenerator() {
    fExposurePoints.clear();
}

void PatternGenerator::SetJEOLMode(JEOLMode mode) {
    fJEOLMode = mode;
    
    switch (mode) {
        case MODE_3_4TH_LENS:
            fMachineGrid = 1.0 * nm;
            fFieldSize = 500.0 * um;
            break;
        case MODE_6_5TH_LENS:
            fMachineGrid = 0.125 * nm;
            fFieldSize = 62.5 * um;
            break;
    }
}

void PatternGenerator::SetShotPitch(G4int pitch) {
    // Shot pitch must be 1 or even multiple of machine grid
    if (pitch == 1 || (pitch > 0 && pitch % 2 == 0)) {
        fShotPitch = pitch;
    } else {
        G4cout << "Warning: Shot pitch must be 1 or even multiple. Using 4." << G4endl;
        fShotPitch = 4;
    }
}

void PatternGenerator::GeneratePattern() {
    // Clear previous pattern
    fExposurePoints.clear();
    
    // Calculate dwell time based on dose
    CalculateDwellTime();
    
    // Generate pattern based on type
    switch (fPatternType) {
        case SINGLE_SPOT:
            fExposurePoints.push_back(fPatternCenter);
            break;
        case SQUARE:
            GenerateSquarePattern();
            break;
        case LINE:
            GenerateLinePattern();
            break;
        case CUSTOM:
            GenerateCustomPattern();
            break;
    }
    
    G4cout << "Generated pattern with " << fExposurePoints.size() << " exposure points" << G4endl;
    G4cout << "Dwell time: " << fDwellTime << " microseconds" << G4endl;
    G4cout << "Clock frequency: " << fClockFrequency << " MHz" << G4endl;
    G4cout << "Electrons per point: " << GetElectronsPerPoint() << G4endl;
    G4cout << "Total electrons needed: " << GetElectronsPerPoint() * fExposurePoints.size() << G4endl;
}

void PatternGenerator::GenerateSquarePattern() {
    // Calculate exposure grid spacing
    G4double gridSpacing = fShotPitch * fMachineGrid;
    
    // Calculate number of points in each direction
    G4int nPoints = static_cast<G4int>(std::floor(fPatternSize / gridSpacing));
    if (nPoints == 0) nPoints = 1;  // At least one point
    
    // Generate points in a square grid
    G4double halfSize = (nPoints - 1) * gridSpacing / 2.0;
    
    for (G4int i = 0; i < nPoints; ++i) {
        for (G4int j = 0; j < nPoints; ++j) {
            G4double x = fPatternCenter.x() - halfSize + i * gridSpacing;
            G4double y = fPatternCenter.y() - halfSize + j * gridSpacing;
            G4double z = fPatternCenter.z();  // Pattern is in XY plane
            
            fExposurePoints.push_back(G4ThreeVector(x, y, z));
        }
    }
}

void PatternGenerator::CalculateDwellTime() {
    // Calculate exposure grid spacing in nm
    G4double exposureGrid = fShotPitch * fMachineGrid / nm;
    
    // Calculate clock frequency (MHz)
    // Dose (uC/cm2) = (Beam Current (pA) * 100) / (Shot Pitch^2 * Clock Frequency (MHz))
    // fBeamCurrent is in nA, so convert to pA: nA * 1000 = pA
    fClockFrequency = (fBeamCurrent * 1000.0 * 100.0) / (fDose * exposureGrid * exposureGrid);
    
    // Check hardware limit of 50 MHz
    if (fClockFrequency > 50.0) {
        G4cout << "Warning: Calculated clock frequency " << fClockFrequency 
               << " MHz exceeds 50 MHz limit. Clamping to 50 MHz." << G4endl;
        fClockFrequency = 50.0;
        
        // Recalculate actual dose with 50 MHz limit
        G4double actualDose = (fBeamCurrent * 1000.0 * 100.0) / (50.0 * exposureGrid * exposureGrid);
        G4cout << "Actual dose will be: " << actualDose << " uC/cm2" << G4endl;
    }
    
    // Calculate dwell time in microseconds
    fDwellTime = 1.0 / fClockFrequency;
}

G4bool PatternGenerator::IsValidConfiguration() const {
    // Check if pattern fits within field
    if (!CheckFieldBoundaries()) {
        return false;
    }
    
    // Check if clock frequency is valid
    if (fClockFrequency <= 0 || fClockFrequency > 50.0) {
        return false;
    }
    
    // Check shot pitch
    if (fShotPitch != 1 && fShotPitch % 2 != 0) {
        return false;
    }
    
    return true;
}

G4String PatternGenerator::GetConfigurationErrors() const {
    std::ostringstream errors;
    
    if (!CheckFieldBoundaries()) {
        errors << "Pattern exceeds field boundaries. ";
        errors << "Pattern size: " << fPatternSize/um << " um, ";
        errors << "Field size: " << fFieldSize/um << " um\n";
    }
    
    if (fClockFrequency <= 0) {
        errors << "Invalid clock frequency calculated.\n";
    } else if (fClockFrequency > 50.0) {
        errors << "Clock frequency exceeds 50 MHz hardware limit.\n";
    }
    
    if (fShotPitch != 1 && fShotPitch % 2 != 0) {
        errors << "Shot pitch must be 1 or even multiple of machine grid.\n";
    }
    
    return errors.str();
}

G4bool PatternGenerator::CheckFieldBoundaries() const {
    // Check if pattern fits within a single field
    G4double halfPattern = fPatternSize / 2.0;
    G4double maxCoord = std::max(
        std::abs(fPatternCenter.x()) + halfPattern,
        std::abs(fPatternCenter.y()) + halfPattern
    );
    
    return maxCoord <= fFieldSize / 2.0;
}

G4int PatternGenerator::GetElectronsPerPoint() const {
    // Calculate number of electrons needed per exposure point
    // to achieve the desired dose
    
    // Beam current in electrons/second
    // I (nA) = I (A) * 1e-9 = Q (C/s) * 1e-9
    // Number of electrons/second = I (A) / e = I (nA) * 1e-9 / e
    G4double electronsPerSecond = fBeamCurrent * 1.0e-9 / (1.602176634e-19); // nA to electrons/s
    
    // Dwell time is in microseconds
    G4double electronsPerPoint = electronsPerSecond * fDwellTime * 1.0e-6;
    
    // Return as integer (minimum 1)
    return std::max(1, static_cast<G4int>(std::round(electronsPerPoint)));
}

void PatternGenerator::GenerateLinePattern() {
    // Generate a horizontal line pattern along X-axis
    // Calculate exposure grid spacing
    G4double gridSpacing = fShotPitch * fMachineGrid;
    
    // Calculate number of points along the line
    G4int nPoints = static_cast<G4int>(std::floor(fPatternSize / gridSpacing));
    if (nPoints == 0) nPoints = 1;  // At least one point
    
    // Generate points along a horizontal line
    G4double halfLength = (nPoints - 1) * gridSpacing / 2.0;
    
    for (G4int i = 0; i < nPoints; ++i) {
        G4double x = fPatternCenter.x() - halfLength + i * gridSpacing;
        G4double y = fPatternCenter.y();
        G4double z = fPatternCenter.z();
        
        fExposurePoints.push_back(G4ThreeVector(x, y, z));
    }
    
    G4cout << "Generated line pattern with " << nPoints << " points" << G4endl;
}

void PatternGenerator::GenerateCustomPattern() {
    // For now, generate a cross pattern as an example
    // In future, this could load patterns from a file
    
    G4double gridSpacing = fShotPitch * fMachineGrid;
    G4int nPoints = static_cast<G4int>(std::floor(fPatternSize / gridSpacing));
    if (nPoints == 0) nPoints = 1;
    
    G4double halfLength = (nPoints - 1) * gridSpacing / 2.0;
    
    // Horizontal line
    for (G4int i = 0; i < nPoints; ++i) {
        G4double x = fPatternCenter.x() - halfLength + i * gridSpacing;
        G4double y = fPatternCenter.y();
        G4double z = fPatternCenter.z();
        fExposurePoints.push_back(G4ThreeVector(x, y, z));
    }
    
    // Vertical line (skip center point to avoid duplicate)
    for (G4int j = 0; j < nPoints; ++j) {
        if (j == nPoints/2) continue;  // Skip center point
        
        G4double x = fPatternCenter.x();
        G4double y = fPatternCenter.y() - halfLength + j * gridSpacing;
        G4double z = fPatternCenter.z();
        fExposurePoints.push_back(G4ThreeVector(x, y, z));
    }
    
    G4cout << "Generated custom cross pattern with " << fExposurePoints.size() << " points" << G4endl;
}