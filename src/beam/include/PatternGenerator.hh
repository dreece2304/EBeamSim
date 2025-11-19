// PatternGenerator.hh
#ifndef PatternGenerator_h
#define PatternGenerator_h 1

#include "globals.hh"
#include "G4ThreeVector.hh"
#include <vector>

class PatternGenerator {
public:
    PatternGenerator();
    ~PatternGenerator() = default;  // Modern C++ default destructor

    // Pattern types
    enum PatternType {
        SINGLE_SPOT,
        SQUARE,
        LINE,
        CUSTOM
    };

    // JEOL operating modes
    enum JEOLMode {
        MODE_3_4TH_LENS,  // 500 um field, 1.0 nm machine grid
        MODE_6_5TH_LENS   // 62.5 um field, 0.125 nm machine grid
    };

    // Set pattern parameters (const-correct and noexcept where appropriate)
    void SetPatternType(PatternType type) noexcept { fPatternType = type; }
    void SetJEOLMode(JEOLMode mode) noexcept;
    void SetShotPitch(G4int pitch) noexcept;  // Must be even multiple of machine grid
    void SetPatternSize(G4double size) noexcept { fPatternSize = size; }
    void SetPatternCenter(const G4ThreeVector& center) { fPatternCenter = center; }
    
    // JEOL beam parameters (noexcept for simple setters)
    void SetBeamCurrent(G4double current) noexcept { fBeamCurrent = current; }  // nA
    void SetDose(G4double dose) noexcept { fDose = dose; }  // uC/cm2
    
    // Generate pattern
    void GeneratePattern();
    
    // Get exposure points and dwell times (const-correct and noexcept)
    const std::vector<G4ThreeVector>& GetExposurePoints() const noexcept { return fExposurePoints; }
    G4double GetDwellTime() const noexcept { return fDwellTime; }  // microseconds
    G4double GetClockFrequency() const noexcept { return fClockFrequency; }  // MHz
    G4int GetTotalPoints() const noexcept { return static_cast<G4int>(fExposurePoints.size()); }
    
    // Get JEOL parameters (noexcept getters)
    G4double GetMachineGrid() const noexcept { return fMachineGrid; }
    G4double GetExposureGrid() const noexcept { return fShotPitch * fMachineGrid; }
    G4double GetFieldSize() const noexcept { return fFieldSize; }
    
    // Calculate number of electrons per exposure point (noexcept)
    G4int GetElectronsPerPoint() const noexcept;
    
    // Check if parameters are valid (const-correct)
    G4bool IsValidConfiguration() const noexcept;
    G4String GetConfigurationErrors() const;

private:
    // Pattern parameters
    PatternType fPatternType;
    G4double fPatternSize;  // nm
    G4ThreeVector fPatternCenter;
    
    // JEOL parameters
    JEOLMode fJEOLMode;
    G4int fShotPitch;
    G4double fMachineGrid;  // nm
    G4double fFieldSize;    // nm
    G4double fBeamCurrent;  // nA
    G4double fDose;         // uC/cm2
    
    // Calculated parameters
    G4double fDwellTime;      // microseconds
    G4double fClockFrequency; // MHz
    
    // Generated pattern
    std::vector<G4ThreeVector> fExposurePoints;
    
    // Helper methods (const-correct where appropriate)
    void GenerateSquarePattern();
    void GenerateLinePattern();
    void GenerateCustomPattern();
    void CalculateDwellTime();
    G4bool CheckFieldBoundaries() const noexcept;
};

#endif