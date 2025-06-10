// DetectorMessenger.hh
#ifndef DetectorMessenger_h
#define DetectorMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class DetectorConstruction;
class G4UIdirectory;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWithAString;
class G4UIcmdWithoutParameter;

class DetectorMessenger : public G4UImessenger {
public:
    DetectorMessenger(DetectorConstruction* detector);
    virtual ~DetectorMessenger();

    virtual void SetNewValue(G4UIcommand*, G4String);

private:
    DetectorConstruction* fDetector;

    // UI directories and commands
    G4UIdirectory* fDetDirectory;

    G4UIcmdWithADoubleAndUnit* fThicknessCmd;
    G4UIcmdWithAString* fDensityCmd;
    G4UIcmdWithAString* fCompositionCmd;
    G4UIcmdWithoutParameter* fUpdateCmd;
};

#endif