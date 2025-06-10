// PhysicsList.cc
#include "PhysicsList.hh"
#include "PhysicsMessenger.hh"

#include "G4DecayPhysics.hh"
#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmExtraPhysics.hh"

#include "G4SystemOfUnits.hh"
#include "G4ParticleDefinition.hh"
#include "G4ProcessManager.hh"
#include "G4LossTableManager.hh"
#include "G4EmParameters.hh"
#include "G4UnitsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4ProductionCuts.hh"

PhysicsList::PhysicsList()
: G4VModularPhysicsList(),
  fEmPhysics(nullptr),
  fDecayPhysics(nullptr),
  fCutForGamma(0.1*nanometer),     // Very fine cuts for accuracy
  fCutForElectron(0.1*nanometer),  // Critical for PSF resolution
  fCutForPositron(0.1*nanometer),
  fMessenger(nullptr)
{
    G4LossTableManager::Instance();

    // Set verbosity
    SetVerboseLevel(1);

    // Default physics
    fDecayPhysics = new G4DecayPhysics();

    // EM physics - Use Livermore for better low-energy accuracy (down to 10 eV)
    fEmPhysics = new G4EmLivermorePhysics();

    // Configure EM parameters before initialization
    SetupEmParameters();

    // Create messenger for UI commands
    fMessenger = new PhysicsMessenger(this);
}

PhysicsList::~PhysicsList()
{
    delete fDecayPhysics;
    delete fEmPhysics;
    delete fMessenger;
}

void PhysicsList::SetupEmParameters()
{
    // Get EM parameters instance
    G4EmParameters* param = G4EmParameters::Instance();

    // Enable all secondary particle production
    param->SetFluo(true);           // Fluorescence
    param->SetAuger(true);          // Auger electrons
    param->SetAugerCascade(true);   // Full Auger cascade
    param->SetPixe(true);           // Particle induced X-ray emission

    // Set energy range - critical for capturing all electrons
    param->SetMinEnergy(10*eV);     // Track electrons down to 10 eV
    param->SetMaxEnergy(1*GeV);     // Up to 1 GeV
    param->SetLowestElectronEnergy(10*eV);  // Don't kill low-energy electrons
    param->SetLowestMuHadEnergy(1*keV);

    // Multiple scattering parameters - critical for PSF accuracy
    param->SetMscStepLimitType(fUseDistanceToBoundary);  // Most accurate
    param->SetMscRangeFactor(0.02);    // Smaller = more accurate (default 0.04)
    param->SetMscGeomFactor(2.5);      // Default, good for thin layers
    param->SetMscSkin(3.0);            // Default

    // Very important: small step near boundaries for accurate position
    param->SetStepFunction(0.1, 0.1*nanometer);  // dRoverRange, finalRange

    // Energy loss parameters
    param->SetLossFluctuations(true);   // Include Landau fluctuations
    param->SetLinearLossLimit(0.01);    // 1% - default
    param->SetBuildCSDARange(true);     // Build CSDA range tables

    // Bremsstrahlung and pair production
    param->SetBremsstrahlungTh(1*MeV);  // Enable above 1 MeV

    // Apply cuts properly
    param->SetApplyCuts(true);

    // Number of bins for tables - more bins = better accuracy
    param->SetNumberOfBinsPerDecade(20);  // Default is 7, we want more

    // Verbose output for debugging
    param->SetVerbose(1);

    // Print to verify
    G4cout << "\nEM Parameters configured for EBL:" << G4endl;
    G4cout << "  Min energy: " << param->MinKinEnergy()/eV << " eV" << G4endl;
    G4cout << "  Max energy: " << param->MaxKinEnergy()/MeV << " MeV" << G4endl;
    G4cout << "  Fluorescence: " << param->Fluo() << G4endl;
    G4cout << "  Auger: " << param->Auger() << G4endl;
    G4cout << "  MSC range factor: " << param->MscRangeFactor() << G4endl;
    G4cout << "  Number of bins per decade: " << param->NumberOfBinsPerDecade() << G4endl;
}

void PhysicsList::ConstructParticle()
{
    fDecayPhysics->ConstructParticle();
}

void PhysicsList::ConstructProcess()
{
    // Transportation
    AddTransportation();

    // Electromagnetic physics
    fEmPhysics->ConstructProcess();

    // Decay physics
    fDecayPhysics->ConstructProcess();
}

void PhysicsList::SetCuts()
{
    // Set default production cuts - these are CRITICAL for PSF accuracy
    SetCutValue(fCutForGamma, "gamma");
    SetCutValue(fCutForElectron, "e-");
    SetCutValue(fCutForPositron, "e+");

    // Report the cuts
    G4cout << "\nPhysicsList::SetCuts() - Production thresholds:" << G4endl;
    G4cout << "  Gamma:    " << G4BestUnit(fCutForGamma, "Length") << G4endl;
    G4cout << "  Electron: " << G4BestUnit(fCutForElectron, "Length") << G4endl;
    G4cout << "  Positron: " << G4BestUnit(fCutForPositron, "Length") << G4endl;

    // Set region-specific cuts if regions exist
    G4RegionStore* regionStore = G4RegionStore::GetInstance();
    G4Region* resistRegion = regionStore->GetRegion("ResistRegion", false);

    if (resistRegion) {
        G4ProductionCuts* resistCuts = new G4ProductionCuts();
        resistCuts->SetProductionCut(0.1*nanometer, "gamma");
        resistCuts->SetProductionCut(0.1*nanometer, "e-");
        resistCuts->SetProductionCut(0.1*nanometer, "e+");
        resistRegion->SetProductionCuts(resistCuts);

        G4cout << "  Special cuts for resist region: "
               << G4BestUnit(0.1*nanometer, "Length") << G4endl;
    }

    // Dump the full particle/process list for verification
    if (GetVerboseLevel() > 0) {
        DumpCutValuesTable();
    }

    // Additional check for energy thresholds
    G4EmParameters* param = G4EmParameters::Instance();
    G4double lowestE = param->LowestElectronEnergy();
    G4cout << "\nLowest electron tracking energy: "
           << G4BestUnit(lowestE, "Energy") << G4endl;

    // Warning if cuts might be too large for EBL
    if (fCutForElectron > 1.0*nanometer) {
        G4cout << "\nWARNING: Electron production cut > 1 nm may be too coarse for EBL simulation!"
               << G4endl;
        G4cout << "         PSF accuracy requires sub-nm production thresholds." << G4endl;
    }
}