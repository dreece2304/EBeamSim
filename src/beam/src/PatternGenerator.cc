// PatternGenerator.cc - Base class implementation for e-beam pattern generation
#include "PatternGenerator.hh"
#include "DetectorConstruction.hh"
#include "G4SystemOfUnits.hh"
#include <algorithm>
#include <cmath>

PatternGenerator::PatternGenerator(const PatternParameters& params, 
                                   DetectorConstruction* detConstruction)
    : fParameters(params),
      fDetConstruction(detConstruction),
      fCurrentShotIndex(0) {
    
    // Calculate clock frequency from dose and beam parameters
    G4double exposureGrid = GetExposureGrid();
    fClockFrequency = JEOL::CalculateClockFrequency(
        fParameters.beamCurrent * 1000.0,  // Convert nA to pA
        fParameters.baseDose,
        exposureGrid / nm  // Convert to nm for calculation
    );
    
    // Validate clock frequency
    if (fClockFrequency > JEOL::Exposure::MAX_CLOCK_FREQUENCY) {
        G4cout << "WARNING: Calculated clock frequency " << fClockFrequency 
               << " MHz exceeds maximum " << JEOL::Exposure::MAX_CLOCK_FREQUENCY 
               << " MHz. Clamping to maximum." << G4endl;
        fClockFrequency = JEOL::Exposure::MAX_CLOCK_FREQUENCY;
    }
    
    // Calculate base dwell time (1/frequency in microseconds)
    fBaseDwellTime = 1.0 / fClockFrequency;  // microseconds
    
    G4cout << "PatternGenerator initialized:" << G4endl;
    G4cout << "  EOS Mode: " << fParameters.eosMode << G4endl;
    G4cout << "  Shot Pitch: " << fParameters.shotPitch << G4endl;
    G4cout << "  Exposure Grid: " << exposureGrid/nm << " nm" << G4endl;
    G4cout << "  Beam Current: " << fParameters.beamCurrent << " nA" << G4endl;
    G4cout << "  Base Dose: " << fParameters.baseDose << " uC/cm^2" << G4endl;
    G4cout << "  Clock Frequency: " << fClockFrequency << " MHz" << G4endl;
    G4cout << "  Base Dwell Time: " << fBaseDwellTime << " us" << G4endl;
}

const ShotPoint& PatternGenerator::GetCurrentShot() const {
    if (fCurrentShotIndex >= static_cast<G4int>(fShots.size())) {
        G4Exception("PatternGenerator::GetCurrentShot",
                    "InvalidIndex", FatalException,
                    "Current shot index out of bounds");
    }
    return fShots[fCurrentShotIndex];
}

G4int PatternGenerator::GetCurrentFieldID() const {
    if (fCurrentShotIndex >= static_cast<G4int>(fShots.size())) return -1;
    return fShots[fCurrentShotIndex].fieldID;
}

G4double PatternGenerator::CalculateDwellTime(G4int shotRank) const {
    if (shotRank < 0 || shotRank > 255) {
        G4Exception("PatternGenerator::CalculateDwellTime",
                    "InvalidShotRank", JustWarning,
                    "Shot rank out of range [0-255]");
        shotRank = 0;
    }
    
    // Apply dose modulation
    G4double modulation = fParameters.modulationTable[shotRank];
    return fBaseDwellTime * modulation;
}

void PatternGenerator::AddShot(G4double x, G4double y, G4int shotRank) {
    // Snap to exposure grid
    G4ThreeVector gridPos = SnapToGrid(G4ThreeVector(x, y, 0));
    
    // Create shot point
    ShotPoint shot(gridPos.x(), gridPos.y(), shotRank);
    shot.dwellTime = CalculateDwellTime(shotRank);
    
    fShots.push_back(shot);
}

void PatternGenerator::ClearPattern() {
    fShots.clear();
    fFields.clear();
    fCurrentShotIndex = 0;
}

G4ThreeVector PatternGenerator::SnapToGrid(const G4ThreeVector& pos) const {
    G4double grid = GetExposureGrid();
    G4double x = std::round(pos.x() / grid) * grid;
    G4double y = std::round(pos.y() / grid) * grid;
    return G4ThreeVector(x, y, pos.z());
}

void PatternGenerator::AssignShotsToFields() {
    fFields.clear();
    if (fShots.empty()) return;
    
    G4double fieldSize = GetFieldSize();
    
    // Find bounding box of all shots
    G4double minX = fShots[0].position.x();
    G4double maxX = minX;
    G4double minY = fShots[0].position.y();
    G4double maxY = minY;
    
    for (const auto& shot : fShots) {
        minX = std::min(minX, shot.position.x());
        maxX = std::max(maxX, shot.position.x());
        minY = std::min(minY, shot.position.y());
        maxY = std::max(maxY, shot.position.y());
    }
    
    // Calculate field layout
    G4int nFieldsX = static_cast<G4int>(std::ceil((maxX - minX) / fieldSize)) + 1;
    G4int nFieldsY = static_cast<G4int>(std::ceil((maxY - minY) / fieldSize)) + 1;
    
    // Create field centers aligned to pattern center
    G4double patternCenterX = fParameters.centerPosition.x();
    G4double patternCenterY = fParameters.centerPosition.y();
    
    G4int fieldId = 0;
    for (G4int iy = 0; iy < nFieldsY; ++iy) {
        for (G4int ix = 0; ix < nFieldsX; ++ix) {
            G4double fieldCenterX = patternCenterX + (ix - nFieldsX/2.0 + 0.5) * fieldSize;
            G4double fieldCenterY = patternCenterY + (iy - nFieldsY/2.0 + 0.5) * fieldSize;
            
            fFields.emplace_back(fieldId++, fieldCenterX, fieldCenterY, fieldSize);
        }
    }
    
    // Assign shots to fields
    for (size_t i = 0; i < fShots.size(); ++i) {
        auto& shot = fShots[i];
        
        // Find which field this shot belongs to
        G4double halfField = fieldSize / 2.0;
        
        for (auto& field : fFields) {
            if (std::abs(shot.position.x() - field.center.x()) <= halfField &&
                std::abs(shot.position.y() - field.center.y()) <= halfField) {
                shot.fieldID = field.id;
                field.shotIndices.push_back(static_cast<G4int>(i));
                break;
            }
        }
    }
    
    G4cout << "Pattern assigned to " << fFields.size() << " fields:" << G4endl;
    G4cout << "  Field layout: " << nFieldsX << " x " << nFieldsY << G4endl;
    for (const auto& field : fFields) {
        if (!field.shotIndices.empty()) {
            G4cout << "  Field " << field.id << " at (" 
                   << field.center.x()/micrometer << ", " 
                   << field.center.y()/micrometer << ") um"
                   << " contains " << field.shotIndices.size() << " shots" << G4endl;
        }
    }
}

G4bool PatternGenerator::IsFieldBoundary(const G4ThreeVector& pos1, 
                                         const G4ThreeVector& pos2) const {
    G4double fieldSize = GetFieldSize();
    G4double halfField = fieldSize / 2.0;
    
    // Check if positions are in different fields
    for (const auto& field : fFields) {
        G4bool pos1InField = (std::abs(pos1.x() - field.center.x()) <= halfField &&
                              std::abs(pos1.y() - field.center.y()) <= halfField);
        G4bool pos2InField = (std::abs(pos2.x() - field.center.x()) <= halfField &&
                              std::abs(pos2.y() - field.center.y()) <= halfField);
        
        if (pos1InField != pos2InField) {
            return true;  // One is in field, other is not = boundary crossed
        }
    }
    
    return false;
}