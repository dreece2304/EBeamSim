// PatternGenerator.hh
#ifndef PatternGenerator_h
#define PatternGenerator_h 1

#include "globals.hh"
#include "G4ThreeVector.hh"
#include <vector>

class PatternGenerator {
public:
    PatternGenerator();
    ~PatternGenerator();

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

    // Set pattern parameters
    void SetPatternType(PatternType type) { fPatternType = type; }
    void SetJEOLMode(JEOLMode mode);
    void SetShotPitch(G4int pitch);  // Must be even multiple of machine grid
    void SetPatternSize(G4double size) { fPatternSize = size; }
    void SetPatternCenter(const G4ThreeVector& center) { fPatternCenter = center; }
    
    // JEOL beam parameters
    void SetBeamCurrent(G4double current) { fBeamCurrent = current; }  // nA
    void SetDose(G4double dose) { fDose = dose; }  // uC/cm2
    
    // Generate pattern
    void GeneratePattern();
    
    // Get exposure points and dwell times
    const std::vector<G4ThreeVector>& GetExposurePoints() const { return fExposurePoints; }
    G4double GetDwellTime() const { return fDwellTime; }  // microseconds
    G4double GetClockFrequency() const { return fClockFrequency; }  // MHz
    G4int GetTotalPoints() const { return static_cast<G4int>(fExposurePoints.size()); }
    
    // Get JEOL parameters
    G4double GetMachineGrid() const { return fMachineGrid; }
    G4double GetExposureGrid() const { return fShotPitch * fMachineGrid; }
    G4double GetFieldSize() const { return fFieldSize; }
    
    // Calculate number of electrons per exposure point
    G4int GetElectronsPerPoint() const;
    
    // Check if parameters are valid
    G4bool IsValidConfiguration() const;
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
    
    // Helper methods
    void GenerateSquarePattern();
    void GenerateLinePattern();
    void GenerateCustomPattern();
    void CalculateDwellTime();
    G4bool CheckFieldBoundaries() const;
};

#endif