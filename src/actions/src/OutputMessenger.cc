// OutputMessenger.cc
#include "OutputMessenger.hh"
#include "RunAction.hh"
#include "G4UIdirectory.hh"
#include "G4UIcmdWithAString.hh"

OutputMessenger::OutputMessenger(RunAction* runAction)
    : G4UImessenger(),
    fRunAction(runAction)
{
    fOutputDir = new G4UIdirectory("/ebl/output/");
    fOutputDir->SetGuidance("Output file control");

    fOutputDirCmd = new G4UIcmdWithAString("/ebl/output/setDirectory", this);
    fOutputDirCmd->SetGuidance("Set output directory");
    fOutputDirCmd->SetParameterName("directory", false);
    fOutputDirCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fPSFFileCmd = new G4UIcmdWithAString("/ebl/output/setPSFFile", this);
    fPSFFileCmd->SetGuidance("Set PSF output filename");
    fPSFFileCmd->SetParameterName("filename", false);
    fPSFFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fPSF2DFileCmd = new G4UIcmdWithAString("/ebl/output/setPSF2DFile", this);
    fPSF2DFileCmd->SetGuidance("Set 2D PSF output filename");
    fPSF2DFileCmd->SetParameterName("filename", false);
    fPSF2DFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fSummaryFileCmd = new G4UIcmdWithAString("/ebl/output/setSummaryFile", this);
    fSummaryFileCmd->SetGuidance("Set summary output filename");
    fSummaryFileCmd->SetParameterName("filename", false);
    fSummaryFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fBeamerFileCmd = new G4UIcmdWithAString("/ebl/output/setBeamerFile", this);
    fBeamerFileCmd->SetGuidance("Set BEAMER output filename");
    fBeamerFileCmd->SetParameterName("filename", false);
    fBeamerFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

OutputMessenger::~OutputMessenger()
{
    delete fPSFFileCmd;
    delete fPSF2DFileCmd;
    delete fSummaryFileCmd;
    delete fBeamerFileCmd;
    delete fOutputDirCmd;
    delete fOutputDir;
}

void OutputMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    if (command == fOutputDirCmd) {
        fRunAction->SetOutputDirectory(newValue);
    }
    else if (command == fPSFFileCmd) {
        fRunAction->SetPSFFilename(newValue);
    }
    else if (command == fPSF2DFileCmd) {
        fRunAction->SetPSF2DFilename(newValue);
    }
    else if (command == fSummaryFileCmd) {
        fRunAction->SetSummaryFilename(newValue);
    }
    else if (command == fBeamerFileCmd) {
        fRunAction->SetBeamerFilename(newValue);
    }
}