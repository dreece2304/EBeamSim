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

    // Setters for cuts (noexcept for simple setters)
    void SetGammaCut(G4double val) noexcept { fCutForGamma = val; }
    void SetElectronCut(G4double val) noexcept { fCutForElectron = val; }
    void SetPositronCut(G4double val) noexcept { fCutForPositron = val; }

    // Legacy setters for backward compatibility
    void SetCutForGamma(G4double val) { SetGammaCut(val); }
    void SetCutForElectron(G4double val) { SetElectronCut(val); }
    void SetCutForPositron(G4double val) { SetPositronCut(val); }

    // Getters for cuts (const-correct)
    G4double GetGammaCut() const noexcept { return fCutForGamma; }
    G4double GetElectronCut() const noexcept { return fCutForElectron; }
    G4double GetPositronCut() const noexcept { return fCutForPositron; }

    // Method to re-check and reconfigure for high-Z materials after material update
    void ReconfigureForMaterial();

private:
    void SetupEmParameters();
    G4bool IsHighZMaterial() const;
    void ConfigureForHighZMaterial();

private:
    G4VPhysicsConstructor* fEmPhysics;
    G4VPhysicsConstructor* fDecayPhysics;
    G4VPhysicsConstructor* fEmDNAPhysics;  // For very low energy interactions

    G4double fCutForGamma;
    G4double fCutForElectron;
    G4double fCutForPositron;
    G4bool fUseHighZOptimization;  // Flag for high-Z material optimization

    PhysicsMessenger* fMessenger;
};

#endif