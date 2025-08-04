// PatternMessenger.hh
#ifndef PatternMessenger_h
#define PatternMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class PrimaryGeneratorAction;
class PatternGenerator;
class G4UIdirectory;
class G4UIcommand;
class G4UIcmdWithABool;
class G4UIcmdWithAString;
class G4UIcmdWithAnInteger;
class G4UIcmdWithADouble;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWith3VectorAndUnit;

class PatternMessenger: public G4UImessenger {
public:
    PatternMessenger(PrimaryGeneratorAction* primaryGen);
    virtual ~PatternMessenger();
    
    virtual void SetNewValue(G4UIcommand*, G4String);
    
private:
    PrimaryGeneratorAction* fPrimaryGenerator;
    PatternGenerator* fPatternGenerator;
    
    G4UIdirectory* fPatternDir;
    
    // Commands
    G4UIcmdWithABool* fEnablePatternCmd;
    G4UIcmdWithAString* fPatternTypeCmd;
    G4UIcmdWithAString* fJEOLModeCmd;
    G4UIcmdWithAnInteger* fShotPitchCmd;
    G4UIcmdWithADoubleAndUnit* fPatternSizeCmd;
    G4UIcmdWith3VectorAndUnit* fPatternCenterCmd;
    G4UIcmdWithADoubleAndUnit* fBeamCurrentCmd;
    G4UIcmdWithADouble* fDoseCmd;
    G4UIcommand* fGeneratePatternCmd;
};

#endif