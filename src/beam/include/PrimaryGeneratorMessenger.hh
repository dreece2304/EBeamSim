// PrimaryGeneratorMessenger.hh
#ifndef PrimaryGeneratorMessenger_h
#define PrimaryGeneratorMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class PrimaryGeneratorAction;
class G4UIdirectory;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWith3VectorAndUnit;
class G4UIcmdWith3Vector;
class G4UIcmdWithAString;

class PrimaryGeneratorMessenger : public G4UImessenger {
public:
    PrimaryGeneratorMessenger(PrimaryGeneratorAction* primaryGen);
    virtual ~PrimaryGeneratorMessenger();

    virtual void SetNewValue(G4UIcommand*, G4String);

private:
    PrimaryGeneratorAction* fPrimaryGenerator;

    G4UIdirectory* fGunDirectory;
    G4UIcmdWithAString* fParticleCmd;
    G4UIcmdWithADoubleAndUnit* fEnergyCmd;
    G4UIcmdWith3VectorAndUnit* fPositionCmd;
    G4UIcmdWith3Vector* fDirectionCmd;
    G4UIcmdWithADoubleAndUnit* fBeamSizeCmd;
};

#endif