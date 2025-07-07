// OutputMessenger.hh
#ifndef OutputMessenger_h
#define OutputMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class RunAction;
class G4UIdirectory;
class G4UIcmdWithAString;

class OutputMessenger : public G4UImessenger {
public:
    OutputMessenger(RunAction* runAction);
    virtual ~OutputMessenger();

    virtual void SetNewValue(G4UIcommand*, G4String);

private:
    RunAction* fRunAction;

    G4UIdirectory* fOutputDir;
    G4UIcmdWithAString* fPSFFileCmd;
    G4UIcmdWithAString* fPSF2DFileCmd;
    G4UIcmdWithAString* fSummaryFileCmd;
    G4UIcmdWithAString* fBeamerFileCmd;
    G4UIcmdWithAString* fOutputDirCmd;
};

#endif