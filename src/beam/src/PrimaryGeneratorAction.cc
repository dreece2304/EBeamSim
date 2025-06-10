// PrimaryGeneratorAction.cc
#include "PrimaryGeneratorAction.hh"
#include "PrimaryGeneratorMessenger.hh"
#include "DetectorConstruction.hh"
#include "EBLConstants.hh"

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

    // Create messenger for UI commands
    fMessenger = new PrimaryGeneratorMessenger(this);

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
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
    // Generate a Gaussian beam with specified diameter (FWHM)
    // FWHM = 2.355 * sigma, so sigma = FWHM / 2.355
    G4double sigma = fBeamSize / (2.0 * std::sqrt(2.0 * std::log(2.0)));

    // Sample position from 2D Gaussian distribution
    G4double x = G4RandGauss::shoot(0., sigma);
    G4double y = G4RandGauss::shoot(0., sigma);

    // Get the resist thickness to position beam correctly
    G4double resistThickness = fDetConstruction->GetActualResistThickness();

    // Default Z position: 100 nm above resist top surface
    // In our geometry, resist bottom is at z=0, top is at z=resistThickness
    G4double defaultZ = resistThickness + 100.0*nanometer;

    // Use user-specified Z if it's been set, otherwise use smart default
    G4double z = fBeamPosition.z();
    if (std::abs(z - EBL::Beam::DEFAULT_POSITION_Z) < 1.0*nanometer) {
        // User hasn't changed from default, use smart positioning
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

    // Set the electron position with Gaussian spread in x,y
    fParticleGun->SetParticlePosition(G4ThreeVector(x + fBeamPosition.x(),
                                                     y + fBeamPosition.y(),
                                                     z));

    // Set direction (typically straight down for EBL)
    fParticleGun->SetParticleMomentumDirection(fBeamDirection);

    // Set energy
    fParticleGun->SetParticleEnergy(fBeamEnergy);

    // Debug output for first few events
    G4int eventID = anEvent->GetEventID();
    if (eventID < 5 || (eventID < 100 && eventID % 20 == 0)) {
        G4cout << "Event " << eventID << ": e- at ("
               << (x + fBeamPosition.x())/nm << ", "
               << (y + fBeamPosition.y())/nm << ", "
               << z/nm << ") nm, "
               << "E=" << fBeamEnergy/keV << " keV" << G4endl;
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
