// PatternGenerator.hh - Base class for e-beam pattern generation
#ifndef PATTERNGENERATOR_HH
#define PATTERNGENERATOR_HH

#include "G4Types.hh"
#include "G4ThreeVector.hh"
#include "JEOLParameters.hh"
#include <vector>
#include <memory>

// Forward declarations
class DetectorConstruction;

// Structure to hold shot information
struct ShotPoint {
    G4ThreeVector position;  // X, Y position (Z is set by beam position)
    G4int shotRank;         // Dose modulation index (0-255)
    G4int fieldID;          // Which field this shot belongs to
    G4double dwellTime;     // Dwell time for this shot (calculated from dose)
    
    ShotPoint(G4double x, G4double y, G4int rank = 0, G4int field = 0)
        : position(x, y, 0), shotRank(rank), fieldID(field), dwellTime(0) {}
};

// Structure to hold field information
struct FieldInfo {
    G4int id;
    G4ThreeVector center;    // Field center position
    G4double size;          // Field size
    std::vector<G4int> shotIndices;  // Indices of shots in this field
    
    FieldInfo(G4int fieldId, G4double x, G4double y, G4double fieldSize)
        : id(fieldId), center(x, y, 0), size(fieldSize) {}
};

// Pattern parameters
class PatternParameters {
public:
    // Basic parameters
    JEOL::Pattern::Type patternType;
    G4ThreeVector centerPosition;
    G4double size;  // Pattern size (interpretation depends on type)
    
    // Exposure parameters
    G4int eosMode;
    G4int shotPitch;
    G4double beamCurrent;  // in nA
    G4double baseDose;     // in uC/cm^2
    
    // Dose modulation table (MODULAT)
    std::vector<G4double> modulationTable;  // 256 entries, multipliers for base dose
    
    // Array parameters (for array patterns)
    G4int arrayNx, arrayNy;
    G4double arrayPitchX, arrayPitchY;
    
    PatternParameters() 
        : patternType(JEOL::Pattern::SQUARE),
          centerPosition(0, 0, 0),
          size(1.0 * micrometer),
          eosMode(JEOL::Mode::MODE_3_4TH_LENS),
          shotPitch(4),
          beamCurrent(2.0),  // nA
          baseDose(400.0),   // uC/cm^2
          arrayNx(1), arrayNy(1),
          arrayPitchX(0), arrayPitchY(0) {
        // Initialize modulation table with 1.0 (no modulation)
        modulationTable.resize(256, 1.0);
    }
};

class PatternGenerator {
public:
    PatternGenerator(const PatternParameters& params, DetectorConstruction* detConstruction);
    virtual ~PatternGenerator() = default;
    
    // Generate the pattern (must be implemented by derived classes)
    virtual void GeneratePattern() = 0;
    
    // Get shot information
    const std::vector<ShotPoint>& GetShots() const { return fShots; }
    const std::vector<FieldInfo>& GetFields() const { return fFields; }
    
    // Get current shot for exposure
    const ShotPoint& GetCurrentShot() const;
    G4bool HasNextShot() const { return fCurrentShotIndex < static_cast<G4int>(fShots.size()) - 1; }
    void AdvanceToNextShot() { fCurrentShotIndex++; }
    void ResetShotSequence() { fCurrentShotIndex = 0; }
    
    // Get pattern information
    G4int GetTotalShots() const { return static_cast<G4int>(fShots.size()); }
    G4int GetTotalFields() const { return static_cast<G4int>(fFields.size()); }
    G4int GetCurrentShotIndex() const { return fCurrentShotIndex; }
    G4int GetCurrentFieldID() const;
    
    // Calculate dwell time for a shot
    G4double CalculateDwellTime(G4int shotRank) const;
    
    // Get pattern parameters
    const PatternParameters& GetParameters() const { return fParameters; }
    
    // Field management
    void AssignShotsToFields();
    G4bool IsFieldBoundary(const G4ThreeVector& pos1, const G4ThreeVector& pos2) const;
    
protected:
    // Helper methods for derived classes
    void AddShot(G4double x, G4double y, G4int shotRank = 0);
    void ClearPattern();
    
    // Get grid spacing
    G4double GetExposureGrid() const {
        return JEOL::GetExposureGrid(fParameters.eosMode, fParameters.shotPitch);
    }
    
    G4double GetFieldSize() const {
        return JEOL::GetFieldSize(fParameters.eosMode);
    }
    
    // Snap position to grid
    G4ThreeVector SnapToGrid(const G4ThreeVector& pos) const;
    
protected:
    PatternParameters fParameters;
    DetectorConstruction* fDetConstruction;
    
    std::vector<ShotPoint> fShots;
    std::vector<FieldInfo> fFields;
    
    G4int fCurrentShotIndex;
    
    // Calculated values
    G4double fClockFrequency;  // MHz
    G4double fBaseDwellTime;   // microseconds
};

#endif // PATTERNGENERATOR_HH