// PhysicsMessenger.cc
#include "PhysicsMessenger.hh"
#include "PhysicsList.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithAnInteger.hh"
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
    fFluoCmd->SetParameterName("FlourBool", true);
    fFluoCmd->SetDefaultValue(1);
    fFluoCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fAugerCmd = new G4UIcmdWithAnInteger("/process/em/auger", this);
    fAugerCmd->SetGuidance("Enable/disable Auger processes.");
    fAugerCmd->SetParameterName("AugerBool", true);
    fAugerCmd->SetDefaultValue(1);
    fAugerCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

PhysicsMessenger::~PhysicsMessenger()
{
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
}