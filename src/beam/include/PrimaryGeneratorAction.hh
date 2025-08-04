// PrimaryGeneratorAction.hh
#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"
#include "globals.hh"
#include "G4ThreeVector.hh"
#include <memory>

class G4ParticleGun;
class G4Event;
class DetectorConstruction;
class G4ParticleDefinition;
class PrimaryGeneratorMessenger;
class PatternGenerator;
class PatternParameters;

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
    
    // Pattern scanning mode
    enum BeamMode {
        SPOT_MODE = 0,     // Traditional single spot (Gaussian)
        PATTERN_MODE = 1   // Pattern scanning mode
    };
    
    void SetBeamMode(BeamMode mode) { fBeamMode = mode; }
    BeamMode GetBeamMode() const { return fBeamMode; }
    
    // Pattern control
    void SetPatternGenerator(std::unique_ptr<PatternGenerator> generator);
    PatternGenerator* GetPatternGenerator() { return fPatternGenerator.get(); }
    void InitializePattern(const PatternParameters& params);
    
    // Get current shot information (for RunAction)
    G4int GetCurrentShotNumber() const { return fCurrentShotNumber; }
    G4int GetTotalShots() const;
    G4int GetCurrentFieldID() const;

private:
    G4ParticleGun* fParticleGun;
    DetectorConstruction* fDetConstruction;
    G4ParticleDefinition* fElectron;

    // Beam parameters
    G4double fBeamEnergy;
    G4double fBeamSize;  // Beam diameter (FWHM)
    G4ThreeVector fBeamPosition;
    G4ThreeVector fBeamDirection;
    
    // Beam mode
    BeamMode fBeamMode;
    
    // Pattern scanning
    std::unique_ptr<PatternGenerator> fPatternGenerator;
    G4int fCurrentShotNumber;
    G4int fLastFieldID;

    // Messenger for UI commands
    PrimaryGeneratorMessenger* fMessenger;
};

#endif