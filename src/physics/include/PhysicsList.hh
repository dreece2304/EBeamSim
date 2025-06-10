// PhysicsList.hh
#ifndef PhysicsList_h
#define PhysicsList_h 1

#include "G4VModularPhysicsList.hh"
#include "globals.hh"

class G4VPhysicsConstructor;
class PhysicsMessenger;

class PhysicsList : public G4VModularPhysicsList
{
public:
    PhysicsList();
    virtual ~PhysicsList();

    // Mandatory methods
    virtual void ConstructParticle();
    virtual void ConstructProcess();
    virtual void SetCuts();

    // Optional: Add methods to change physics on the fly
    void SetEmPhysics(const G4String& name);

    // Setters for cuts
    void SetGammaCut(G4double val) { fCutForGamma = val; }
    void SetElectronCut(G4double val) { fCutForElectron = val; }
    void SetPositronCut(G4double val) { fCutForPositron = val; }

private:
    void SetupEmParameters();

private:
    G4VPhysicsConstructor* fEmPhysics;
    G4VPhysicsConstructor* fDecayPhysics;

    G4double fCutForGamma;
    G4double fCutForElectron;
    G4double fCutForPositron;

    PhysicsMessenger* fMessenger;
};

#endif