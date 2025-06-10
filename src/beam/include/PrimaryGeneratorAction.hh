// PrimaryGeneratorAction.hh
#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"
#include "globals.hh"
#include "G4ThreeVector.hh"

class G4ParticleGun;
class G4Event;
class DetectorConstruction;
class G4ParticleDefinition;
class PrimaryGeneratorMessenger;

class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
public:
    PrimaryGeneratorAction(DetectorConstruction* detConstruction);
    virtual ~PrimaryGeneratorAction();

    // Method from the base class
    virtual void GeneratePrimaries(G4Event*);

    // Access to the particle gun
    G4ParticleGun* GetParticleGun() { return fParticleGun; }

    // Beam property setters - using const reference for vectors
    void SetBeamEnergy(G4double energy);
    void SetBeamSize(G4double size); // Beam diameter in nm
    void SetBeamPosition(const G4ThreeVector& position);
    void SetBeamDirection(const G4ThreeVector& direction);

private:
    G4ParticleGun* fParticleGun;
    DetectorConstruction* fDetConstruction;
    G4ParticleDefinition* fElectron;

    // Beam parameters
    G4double fBeamEnergy;
    G4double fBeamSize;  // Beam diameter (FWHM)
    G4ThreeVector fBeamPosition;
    G4ThreeVector fBeamDirection;

    // Messenger for UI commands
    PrimaryGeneratorMessenger* fMessenger;
};

#endif