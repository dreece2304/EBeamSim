// PhysicsMessenger.cc - Enhanced version
#include "PhysicsMessenger.hh"
#include "PhysicsList.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithAnInteger.hh"
#include "G4UIcmdWithABool.hh"
#include "G4UIcommand.hh"
#include "G4EmParameters.hh"

PhysicsMessenger::PhysicsMessenger(PhysicsList* physics)
    : G4UImessenger(),
    fPhysicsList(physics)
{
    fPhysicsDir = new G4UIdirectory("/process/");
    fPhysicsDir->SetGuidance("Process control commands.");

    fEmDir = new G4UIdirectory("/process/em/");
    fEmDir->SetGuidance("EM process control commands.");

    fFluoCmd = new G4UIcmdWithAnInteger("/process/em/fluo", this);
    fFluoCmd->SetGuidance("Enable/disable fluorescence.");
    fFluoCmd->SetParameterName("FluoBool", true);
    fFluoCmd->SetDefaultValue(1);
    fFluoCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fAugerCmd = new G4UIcmdWithAnInteger("/process/em/auger", this);
    fAugerCmd->SetGuidance("Enable/disable Auger processes.");
    fAugerCmd->SetParameterName("AugerBool", true);
    fAugerCmd->SetDefaultValue(1);
    fAugerCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    // Add new command for deexcitation ignore cut
    fDeexcitationCmd = new G4UIcmdWithABool("/process/em/deexcitationIgnoreCut", this);
    fDeexcitationCmd->SetGuidance("Enable/disable deexcitation below production cuts.");
    fDeexcitationCmd->SetParameterName("DeexIgnoreCut", true);
    fDeexcitationCmd->SetDefaultValue(true);
    fDeexcitationCmd->AvailableForStates(G4State_PreInit);

    // Add command for PIXE
    fPixeCmd = new G4UIcmdWithABool("/process/em/pixe", this);
    fPixeCmd->SetGuidance("Enable/disable Particle Induced X-ray Emission.");
    fPixeCmd->SetParameterName("PIXEBool", true);
    fPixeCmd->SetDefaultValue(true);
    fPixeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

PhysicsMessenger::~PhysicsMessenger()
{
    delete fPixeCmd;
    delete fDeexcitationCmd;
    delete fFluoCmd;
    delete fAugerCmd;
    delete fEmDir;
    delete fPhysicsDir;
}

void PhysicsMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    G4EmParameters* param = G4EmParameters::Instance();

    if (command == fFluoCmd) {
        G4bool flag = fFluoCmd->GetNewIntValue(newValue);
        param->SetFluo(flag);
        G4cout << "Fluorescence " << (flag ? "enabled" : "disabled") << G4endl;
    }
    else if (command == fAugerCmd) {
        G4bool flag = fAugerCmd->GetNewIntValue(newValue);
        param->SetAuger(flag);
        param->SetAugerCascade(flag);
        G4cout << "Auger processes " << (flag ? "enabled" : "disabled") << G4endl;
    }
    else if (command == fDeexcitationCmd) {
        G4bool flag = fDeexcitationCmd->GetNewBoolValue(newValue);
        param->SetDeexcitationIgnoreCut(flag);
        G4cout << "Deexcitation below cuts " << (flag ? "enabled" : "disabled") << G4endl;
    }
    else if (command == fPixeCmd) {
        G4bool flag = fPixeCmd->GetNewBoolValue(newValue);
        param->SetPixe(flag);
        G4cout << "PIXE " << (flag ? "enabled" : "disabled") << G4endl;
    }
}