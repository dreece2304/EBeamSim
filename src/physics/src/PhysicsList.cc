// PhysicsList.cc - Compatible with Geant4 11.3.2
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
    fCutForGamma(0.1 * nanometer),
    fCutForElectron(0.1 * nanometer),
    fCutForPositron(0.1 * nanometer),
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
    param->SetFluo(true);
    param->SetAuger(true);
    param->SetAugerCascade(true);
    param->SetPixe(true);

    // CRITICAL for Auger/fluorescence below cuts
    param->SetDeexcitationIgnoreCut(true);

    // Set energy range - these are set differently in 11.3
    param->SetMinEnergy(10 * eV);
    param->SetMaxEnergy(1 * GeV);
    param->SetLowestElectronEnergy(10 * eV);
    param->SetLowestMuHadEnergy(1 * keV);

    // Multiple scattering parameters - these should work in 11.3
    param->SetMscStepLimitType(fUseDistanceToBoundary);
    param->SetMscRangeFactor(0.02);
    param->SetMscGeomFactor(2.5);
    param->SetMscSkin(3.0);
    param->SetMscSafetyFactor(0.6);

    // Lateral displacement
    param->SetMuHadLateralDisplacement(true);
    // SetMscLateralDisplacement doesn't exist in 11.3.2

    // Step function
    param->SetStepFunction(0.1, 0.1 * nanometer);
    param->SetStepFunctionMuHad(0.1, 0.05 * nanometer);

    // Energy loss parameters
    param->SetLossFluctuations(true);
    param->SetLinearLossLimit(0.01);
    param->SetBuildCSDARange(true);
    param->SetUseCutAsFinalRange(false);

    // Bremsstrahlung
    param->SetBremsstrahlungTh(1 * MeV);

    // Angular settings
    param->SetFactorForAngleLimit(1.0);

    // Apply cuts
    param->SetApplyCuts(true);

    // Number of bins
    param->SetNumberOfBinsPerDecade(20);

    // Note: SetDEDXBinning and SetLambdaBinning might not exist in 11.3.2
    // These are often set through SetNumberOfBinsPerDecade which affects all tables

    // Integral approach
    param->SetIntegral(true);

    // Note: SetSpline, SetMinKinEnergy, SetMaxKinEnergy don't exist as setters in 11.3.2
    // The min/max energies are read-only properties

    // Verbose
    param->SetVerbose(1);

    // Print configuration
    G4cout << "\n========================================" << G4endl;
    G4cout << "EM Parameters configured for EBL (Geant4 11.3.2):" << G4endl;
    G4cout << "  Min energy: " << param->MinKinEnergy() / eV << " eV" << G4endl;
    G4cout << "  Max energy: " << param->MaxKinEnergy() / MeV << " MeV" << G4endl;
    G4cout << "  Fluorescence: " << param->Fluo() << G4endl;
    G4cout << "  Auger: " << param->Auger() << G4endl;
    G4cout << "  Auger cascade: " << param->AugerCascade() << G4endl;
    G4cout << "  Deexcitation ignore cut: " << param->DeexcitationIgnoreCut() << G4endl;
    G4cout << "  PIXE: " << param->Pixe() << G4endl;
    G4cout << "  MSC range factor: " << param->MscRangeFactor() << G4endl;
    G4cout << "  Number of bins per decade: " << param->NumberOfBinsPerDecade() << G4endl;
    G4cout << "========================================\n" << G4endl;
}

void PhysicsList::ConstructParticle()
{
    fDecayPhysics->ConstructParticle();

    // Ensure EM particles are constructed
    fEmPhysics->ConstructParticle();
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
    // Set default production cuts
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
        resistCuts->SetProductionCut(0.1 * nanometer, "gamma");
        resistCuts->SetProductionCut(0.1 * nanometer, "e-");
        resistCuts->SetProductionCut(0.1 * nanometer, "e+");
        resistRegion->SetProductionCuts(resistCuts);

        G4cout << "  Special cuts for resist region: "
            << G4BestUnit(0.1 * nanometer, "Length") << G4endl;
    }

    // Dump the full particle/process list for verification
    if (GetVerboseLevel() > 0) {
        DumpCutValuesTable();
    }

    // Additional checks
    G4EmParameters* param = G4EmParameters::Instance();
    G4double lowestE = param->LowestElectronEnergy();
    G4cout << "\nLowest electron tracking energy: "
        << G4BestUnit(lowestE, "Energy") << G4endl;

    // Warning if cuts might be too large
    if (fCutForElectron > 1.0 * nanometer) {
        G4cout << "\nWARNING: Electron production cut > 1 nm may be too coarse for EBL simulation!"
            << G4endl;
        G4cout << "         PSF accuracy requires sub-nm production thresholds." << G4endl;
    }
}