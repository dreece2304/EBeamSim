// PhysicsList.hh
#ifndef PhysicsList_h
#define PhysicsList_h 1

#include "G4VModularPhysicsList.hh"
#include "globals.hh"

class G4VPhysicsConstructor;
class PhysicsMessenger;

class PhysicsList : public G4VModularPhysicsList {
public:
    PhysicsList();
    virtual ~PhysicsList();

    virtual void ConstructParticle();
    virtual void ConstructProcess();
    virtual void SetCuts();

private:
    // Electromagnetic physics options
    G4VPhysicsConstructor* fEmPhysics;
    G4VPhysicsConstructor* fDecayPhysics;

    // Production cuts by particle
    G4double fCutForGamma;
    G4double fCutForElectron;
    G4double fCutForPositron;

    // Messenger for UI commands
    PhysicsMessenger* fMessenger;

    // Setup method for EM parameters
    void SetupEmParameters();
};

#endif