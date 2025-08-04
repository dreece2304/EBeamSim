// PrimaryGeneratorAction.cc
#include "PrimaryGeneratorAction.hh"
#include "PrimaryGeneratorMessenger.hh"
#include "PatternMessenger.hh"
#include "DetectorConstruction.hh"
#include "EBLConstants.hh"
#include "PatternGenerator.hh"
#include "SquarePatternGenerator.hh"

#include "G4LogicalVolumeStore.hh"
#include "G4LogicalVolume.hh"
#include "G4Box.hh"
#include "G4RunManager.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"  // For G4BestUnit
#include "Randomize.hh"

PrimaryGeneratorAction::PrimaryGeneratorAction(DetectorConstruction* detConstruction)
: G4VUserPrimaryGeneratorAction(),
  fParticleGun(nullptr),
  fDetConstruction(detConstruction),
  fElectron(nullptr),
  fBeamEnergy(EBL::Beam::DEFAULT_ENERGY),
  fBeamSize(EBL::Beam::DEFAULT_SPOT_SIZE),
  fBeamPosition(G4ThreeVector(0., 0., EBL::Beam::DEFAULT_POSITION_Z)),
  fBeamDirection(G4ThreeVector(0., 0., -1.)),  // Downward
  fBeamMode(SPOT_MODE),
  fPatternGenerator(nullptr),
  fCurrentShotNumber(0),
  fLastFieldID(-1),
  fMessenger(nullptr)
{
    G4int n_particle = 1;
    fParticleGun = new G4ParticleGun(n_particle);

    // Default particle kinematic
    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    fElectron = particleTable->FindParticle("e-");

    fParticleGun->SetParticleDefinition(fElectron);
    fParticleGun->SetParticleEnergy(fBeamEnergy);
    fParticleGun->SetParticlePosition(fBeamPosition);
    fParticleGun->SetParticleMomentumDirection(fBeamDirection);

    // Create messengers for UI commands
    fMessenger = new PrimaryGeneratorMessenger(this);
    new PatternMessenger(this);  // Self-registering with G4UImanager

    G4cout << "PrimaryGeneratorAction initialized with:" << G4endl;
    G4cout << "  Beam energy: " << G4BestUnit(fBeamEnergy, "Energy") << G4endl;
    G4cout << "  Beam size (FWHM): " << G4BestUnit(fBeamSize, "Length") << G4endl;
    G4cout << "  Default position: (" << fBeamPosition.x()/nm << ", "
           << fBeamPosition.y()/nm << ", " << fBeamPosition.z()/nm << ") nm" << G4endl;
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
    delete fParticleGun;
    delete fMessenger;
    // PatternMessenger is automatically deleted by G4UImanager
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    G4double x, y, z;
    
    // Get the resist thickness to position beam correctly
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    
    // Default Z position: 100 nm above resist top surface
    G4double defaultZ = resistThickness + 100.0*nanometer;
    
    if (fBeamMode == PATTERN_MODE && fPatternGenerator) {
        // Pattern scanning mode
        if (fCurrentShotNumber == 0) {
            G4cout << "Starting pattern exposure with " 
                   << fPatternGenerator->GetTotalShots() << " shots" << G4endl;
        }
        
        // Get current shot position
        const ShotPoint& shot = fPatternGenerator->GetCurrentShot();
        x = shot.position.x();
        y = shot.position.y();
        
        // Check for field change
        G4int currentFieldID = shot.fieldID;
        if (currentFieldID != fLastFieldID) {
            if (fLastFieldID >= 0) {
                G4cout << "Field transition: " << fLastFieldID 
                       << " -> " << currentFieldID << G4endl;
            }
            fLastFieldID = currentFieldID;
        }
        
        // Apply Gaussian beam spread around shot position
        G4double sigma = fBeamSize / (2.0 * std::sqrt(2.0 * std::log(2.0)));
        x += G4RandGauss::shoot(0., sigma);
        y += G4RandGauss::shoot(0., sigma);
        
        // Progress reporting
        if (fCurrentShotNumber % 1000 == 0 || 
            fCurrentShotNumber == fPatternGenerator->GetTotalShots() - 1) {
            G4double progress = 100.0 * fCurrentShotNumber / fPatternGenerator->GetTotalShots();
            G4cout << "Pattern progress: " << fCurrentShotNumber 
                   << "/" << fPatternGenerator->GetTotalShots() 
                   << " (" << progress << "%)" << G4endl;
        }
        
        // Advance to next shot for next event
        fCurrentShotNumber++;
        if (fPatternGenerator->HasNextShot()) {
            fPatternGenerator->AdvanceToNextShot();
        } else {
            // Pattern complete, reset for next run
            G4cout << "Pattern exposure complete!" << G4endl;
            fPatternGenerator->ResetShotSequence();
            fCurrentShotNumber = 0;
            fLastFieldID = -1;
        }
    } else {
        // Traditional spot mode with Gaussian beam
        G4double sigma = fBeamSize / (2.0 * std::sqrt(2.0 * std::log(2.0)));
        x = fBeamPosition.x() + G4RandGauss::shoot(0., sigma);
        y = fBeamPosition.y() + G4RandGauss::shoot(0., sigma);
    }
    
    // Use user-specified Z if it's been set, otherwise use smart default
    z = fBeamPosition.z();
    if (std::abs(z - EBL::Beam::DEFAULT_POSITION_Z) < 1.0*nanometer) {
        z = defaultZ;
    }
    
    // Warn if beam position seems wrong
    static G4bool warnedAboutPosition = false;
    if (!warnedAboutPosition) {
        if (z < resistThickness) {
            G4cout << "WARNING: Beam starts inside or below resist! z="
                   << G4BestUnit(z, "Length") << " < resist top="
                   << G4BestUnit(resistThickness, "Length") << G4endl;
            warnedAboutPosition = true;
        } else if (z > resistThickness + 10.0*micrometer) {
            G4cout << "WARNING: Beam starts very far from resist! z="
                   << G4BestUnit(z, "Length") << " >> resist top="
                   << G4BestUnit(resistThickness, "Length") << G4endl;
            warnedAboutPosition = true;
        }
    }
    
    // Set the electron position
    fParticleGun->SetParticlePosition(G4ThreeVector(x, y, z));
    
    // Set direction (typically straight down for EBL)
    fParticleGun->SetParticleMomentumDirection(fBeamDirection);
    
    // Set energy
    fParticleGun->SetParticleEnergy(fBeamEnergy);
    
    // Debug output for first few events
    G4int eventID = anEvent->GetEventID();
    if (eventID < 5 || (eventID < 100 && eventID % 20 == 0)) {
        G4cout << "Event " << eventID << ": e- at ("
               << x/nm << ", " << y/nm << ", " << z/nm << ") nm, "
               << "E=" << fBeamEnergy/keV << " keV";
        if (fBeamMode == PATTERN_MODE) {
            G4cout << " (Shot " << fCurrentShotNumber - 1 << ")";
        }
        G4cout << G4endl;
    }
    
    // Generate the primary electron
    fParticleGun->GeneratePrimaryVertex(anEvent);
}

void PrimaryGeneratorAction::SetBeamEnergy(G4double energy)
{
    fBeamEnergy = energy;
    G4cout << "Beam energy set to " << G4BestUnit(energy, "Energy") << G4endl;
}

void PrimaryGeneratorAction::SetBeamSize(G4double size)
{
    fBeamSize = size;
    G4cout << "Beam diameter (FWHM) set to " << G4BestUnit(size, "Length") << G4endl;
}

void PrimaryGeneratorAction::SetBeamPosition(const G4ThreeVector& position)
{
    fBeamPosition = position;
    G4cout << "Beam position set to (" << position.x()/nm << ", "
           << position.y()/nm << ", " << position.z()/nm << ") nm" << G4endl;
}

void PrimaryGeneratorAction::SetBeamDirection(const G4ThreeVector& direction)
{
    fBeamDirection = direction.unit(); // Normalize
    G4cout << "Beam direction set to (" << fBeamDirection.x() << ", "
           << fBeamDirection.y() << ", " << fBeamDirection.z() << ")" << G4endl;
}

void PrimaryGeneratorAction::SetPatternGenerator(std::unique_ptr<PatternGenerator> generator)
{
    fPatternGenerator = std::move(generator);
    fCurrentShotNumber = 0;
    fLastFieldID = -1;
    
    if (fPatternGenerator) {
        G4cout << "Pattern generator set with " 
               << fPatternGenerator->GetTotalShots() << " shots in "
               << fPatternGenerator->GetTotalFields() << " fields" << G4endl;
    }
}

void PrimaryGeneratorAction::InitializePattern(const PatternParameters& params)
{
    // Create appropriate pattern generator based on pattern type
    switch (params.patternType) {
        case JEOL::Pattern::SQUARE:
            fPatternGenerator = std::make_unique<SquarePatternGenerator>(params, fDetConstruction);
            break;
        default:
            G4Exception("PrimaryGeneratorAction::InitializePattern",
                        "InvalidPatternType", FatalException,
                        "Unsupported pattern type");
    }
    
    // Generate the pattern
    if (fPatternGenerator) {
        fPatternGenerator->GeneratePattern();
        fCurrentShotNumber = 0;
        fLastFieldID = -1;
        SetBeamMode(PATTERN_MODE);
    }
}

G4int PrimaryGeneratorAction::GetTotalShots() const
{
    if (fPatternGenerator) {
        return fPatternGenerator->GetTotalShots();
    }
    return 0;
}

G4int PrimaryGeneratorAction::GetCurrentFieldID() const
{
    if (fPatternGenerator) {
        return fPatternGenerator->GetCurrentFieldID();
    }
    return -1;
}
