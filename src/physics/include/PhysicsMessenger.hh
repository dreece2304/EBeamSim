// PhysicsMessenger.hh
#ifndef PhysicsMessenger_h
#define PhysicsMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class PhysicsList;
class G4UIdirectory;
class G4UIcmdWithAnInteger;

class PhysicsMessenger : public G4UImessenger {
public:
    PhysicsMessenger(PhysicsList* physics);
    virtual ~PhysicsMessenger();

    virtual void SetNewValue(G4UIcommand*, G4String);

private:
    PhysicsList* fPhysicsList;

    G4UIdirectory* fPhysicsDir;
    G4UIdirectory* fEmDir;
    G4UIcmdWithAnInteger* fFluoCmd;
    G4UIcmdWithAnInteger* fAugerCmd;
};

#endif