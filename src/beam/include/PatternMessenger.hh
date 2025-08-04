// PatternMessenger.hh - UI commands for pattern scanning
#ifndef PatternMessenger_h
#define PatternMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class PrimaryGeneratorAction;
class G4UIdirectory;
class G4UIcmdWithAnInteger;
class G4UIcmdWithAString;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWith3VectorAndUnit;
class G4UIcmdWithoutParameter;
class G4UIcmdWithADouble;

class PatternMessenger : public G4UImessenger {
public:
    PatternMessenger(PrimaryGeneratorAction* primaryGen);
    virtual ~PatternMessenger();
    
    virtual void SetNewValue(G4UIcommand*, G4String);
    
private:
    PrimaryGeneratorAction* fPrimaryGenerator;
    
    // Directories
    G4UIdirectory* fPatternDirectory;
    G4UIdirectory* fJEOLDirectory;
    
    // Pattern commands
    G4UIcmdWithAString* fPatternTypeCmd;
    G4UIcmdWithADoubleAndUnit* fPatternSizeCmd;
    G4UIcmdWith3VectorAndUnit* fPatternCenterCmd;
    G4UIcmdWithoutParameter* fGeneratePatternCmd;
    G4UIcmdWithoutParameter* fClearPatternCmd;
    
    // JEOL parameters
    G4UIcmdWithAnInteger* fEOSModeCmd;
    G4UIcmdWithAnInteger* fShotPitchCmd;
    G4UIcmdWithADouble* fBeamCurrentCmd;  // in nA
    G4UIcmdWithADouble* fBaseDoseCmd;     // in uC/cm^2
    
    // Dose modulation
    G4UIcmdWithAnInteger* fShotRankCmd;
    G4UIcmdWithADouble* fModulationCmd;
    
    // Array pattern parameters
    G4UIcmdWithAnInteger* fArrayNxCmd;
    G4UIcmdWithAnInteger* fArrayNyCmd;
    G4UIcmdWithADoubleAndUnit* fArrayPitchXCmd;
    G4UIcmdWithADoubleAndUnit* fArrayPitchYCmd;
    
    // Beam mode
    G4UIcmdWithAString* fBeamModeCmd;
};

#endif