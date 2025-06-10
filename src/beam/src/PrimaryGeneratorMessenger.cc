// PrimaryGeneratorMessenger.cc
#include "PrimaryGeneratorMessenger.hh"
#include "PrimaryGeneratorAction.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWith3VectorAndUnit.hh"
#include "G4UIcmdWith3Vector.hh"
#include "G4UIcmdWithAString.hh"
#include "G4SystemOfUnits.hh"
#include "G4ParticleTable.hh"

PrimaryGeneratorMessenger::PrimaryGeneratorMessenger(PrimaryGeneratorAction* primaryGen)
: G4UImessenger(),
  fPrimaryGenerator(primaryGen)
{
    fGunDirectory = new G4UIdirectory("/gun/");
    fGunDirectory->SetGuidance("Particle gun control commands.");

    fParticleCmd = new G4UIcmdWithAString("/gun/particle", this);
    fParticleCmd->SetGuidance("Set particle type.");
    fParticleCmd->SetParameterName("ParticleType", false);
    fParticleCmd->SetDefaultValue("e-");
    fParticleCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fEnergyCmd = new G4UIcmdWithADoubleAndUnit("/gun/energy", this);
    fEnergyCmd->SetGuidance("Set particle kinetic energy.");
    fEnergyCmd->SetParameterName("Energy", false);
    fEnergyCmd->SetRange("Energy>0.");
    fEnergyCmd->SetUnitCategory("Energy");
    fEnergyCmd->SetDefaultUnit("keV");
    fEnergyCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fPositionCmd = new G4UIcmdWith3VectorAndUnit("/gun/position", this);
    fPositionCmd->SetGuidance("Set particle initial position.");
    fPositionCmd->SetParameterName("X", "Y", "Z", false);
    fPositionCmd->SetUnitCategory("Length");
    fPositionCmd->SetDefaultUnit("nm");
    fPositionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fDirectionCmd = new G4UIcmdWith3Vector("/gun/direction", this);
    fDirectionCmd->SetGuidance("Set particle momentum direction.");
    fDirectionCmd->SetParameterName("Px", "Py", "Pz", false);
    fDirectionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fBeamSizeCmd = new G4UIcmdWithADoubleAndUnit("/gun/beamSize", this);
    fBeamSizeCmd->SetGuidance("Set beam diameter (FWHM).");
    fBeamSizeCmd->SetParameterName("BeamSize", false);
    fBeamSizeCmd->SetRange("BeamSize>=0.");
    fBeamSizeCmd->SetUnitCategory("Length");
    fBeamSizeCmd->SetDefaultUnit("nm");
    fBeamSizeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

PrimaryGeneratorMessenger::~PrimaryGeneratorMessenger()
{
    delete fBeamSizeCmd;
    delete fDirectionCmd;
    delete fPositionCmd;
    delete fEnergyCmd;
    delete fParticleCmd;
    delete fGunDirectory;
}

void PrimaryGeneratorMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    if (command == fParticleCmd) {
        // Handle particle type change
        G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
        G4ParticleDefinition* particle = particleTable->FindParticle(newValue);
        if (particle) {
            fPrimaryGenerator->GetParticleGun()->SetParticleDefinition(particle);
        }
    }
    else if (command == fEnergyCmd) {
        fPrimaryGenerator->SetBeamEnergy(fEnergyCmd->GetNewDoubleValue(newValue));
    }
    else if (command == fPositionCmd) {
        fPrimaryGenerator->SetBeamPosition(fPositionCmd->GetNew3VectorValue(newValue));
    }
    else if (command == fDirectionCmd) {
        fPrimaryGenerator->SetBeamDirection(fDirectionCmd->GetNew3VectorValue(newValue));
    }
    else if (command == fBeamSizeCmd) {
        fPrimaryGenerator->SetBeamSize(fBeamSizeCmd->GetNewDoubleValue(newValue));
    }
}