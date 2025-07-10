// PhysicsList.cc - Optimized for BEAMER with region-specific cuts
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
    fCutForGamma(0.1 * nanometer),      // Ultra-fine for accuracy
    fCutForElectron(0.1 * nanometer),   // Ultra-fine for accuracy
    fCutForPositron(0.1 * nanometer),   // Ultra-fine for accuracy
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

    // CRITICAL: Enable all atomic deexcitation processes
    param->SetFluo(true);         // K-shell fluorescence
    param->SetAuger(true);        // Auger electrons
    param->SetAugerCascade(true); // Full Auger cascade
    param->SetPixe(true);         // PIXE (Particle Induced X-ray Emission)

    // CRITICAL for Auger/fluorescence below cuts
    param->SetDeexcitationIgnoreCut(true);

    // Energy range for accurate low-energy physics
    param->SetMinEnergy(10 * eV);     // Track down to 10 eV
    param->SetMaxEnergy(1 * GeV);
    param->SetLowestElectronEnergy(10 * eV);
    param->SetLowestMuHadEnergy(1 * keV);

    // Multiple scattering parameters - critical for PSF accuracy
    param->SetMscStepLimitType(fUseDistanceToBoundary);
    param->SetMscRangeFactor(0.02);   // Smaller = more accurate
    param->SetMscGeomFactor(2.5);
    param->SetMscSkin(3.0);
    param->SetMscSafetyFactor(0.6);

    // Lateral displacement
    param->SetMuHadLateralDisplacement(true);

    // Step function - controls step size
    param->SetStepFunction(0.1, 0.1 * nanometer);  // Max 10% energy loss, min 0.1 nm step
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

    // Number of bins for accuracy
    param->SetNumberOfBinsPerDecade(20);

    // Integral approach
    param->SetIntegral(true);

    // Verbose
    param->SetVerbose(0);  // Reduced for BEAMER production runs

    G4cout << "\n========================================" << G4endl;
    G4cout << "EM Parameters configured for BEAMER PSF:" << G4endl;
    G4cout << "  Resist-optimized with region-specific cuts" << G4endl;
    G4cout << "  Min tracking energy: " << param->MinKinEnergy() / eV << " eV" << G4endl;
    G4cout << "  Fluorescence: " << param->Fluo() << G4endl;
    G4cout << "  Auger: " << param->Auger() << G4endl;
    G4cout << "  Deexcitation ignore cut: " << param->DeexcitationIgnoreCut() << G4endl;
    G4cout << "========================================\n" << G4endl;
}

void PhysicsList::ConstructParticle()
{
    fDecayPhysics->ConstructParticle();
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
    // BEAMER OPTIMIZATION: Use region-specific cuts

    // Default global cuts (moderate)
    fCutForGamma = 1.0 * nanometer;
    fCutForElectron = 1.0 * nanometer;
    fCutForPositron = 1.0 * nanometer;

    // Set default production cuts
    SetCutValue(fCutForGamma, "gamma");
    SetCutValue(fCutForElectron, "e-");
    SetCutValue(fCutForPositron, "e+");

    // Report the cuts
    G4cout << "\nPhysicsList::SetCuts() - BEAMER Optimized Production Thresholds:" << G4endl;
    G4cout << "  Global defaults:" << G4endl;
    G4cout << "    Gamma:    " << G4BestUnit(fCutForGamma, "Length") << G4endl;
    G4cout << "    Electron: " << G4BestUnit(fCutForElectron, "Length") << G4endl;
    G4cout << "    Positron: " << G4BestUnit(fCutForPositron, "Length") << G4endl;

    // Set region-specific cuts
    G4RegionStore* regionStore = G4RegionStore::GetInstance();

    // CRITICAL: Ultra-fine cuts in resist region for PSF accuracy
    G4Region* resistRegion = regionStore->GetRegion("ResistRegion", false);
    if (resistRegion) {
        G4ProductionCuts* resistCuts = new G4ProductionCuts();
        // Ultra-fine cuts for maximum accuracy in resist
        resistCuts->SetProductionCut(0.05 * nanometer, "gamma");
        resistCuts->SetProductionCut(0.05 * nanometer, "e-");
        resistCuts->SetProductionCut(0.05 * nanometer, "e+");
        resistRegion->SetProductionCuts(resistCuts);

        G4cout << "  Resist region (ultra-fine for PSF accuracy): "
            << G4BestUnit(0.05 * nanometer, "Length") << G4endl;
    }

    // OPTIMIZATION: Coarser cuts in substrate for efficiency
    // We still track backscatter but with less detail
    G4Region* substrateRegion = regionStore->GetRegion("SubstrateRegion", false);
    if (substrateRegion) {
        G4ProductionCuts* substrateCuts = new G4ProductionCuts();
        // Much coarser cuts in substrate - 200x larger than resist
        substrateCuts->SetProductionCut(10.0 * nanometer, "gamma");
        substrateCuts->SetProductionCut(10.0 * nanometer, "e-");
        substrateCuts->SetProductionCut(10.0 * nanometer, "e+");
        substrateRegion->SetProductionCuts(substrateCuts);

        G4cout << "  Substrate region (coarse for efficiency): "
            << G4BestUnit(10.0 * nanometer, "Length") << G4endl;
    }

    // Add world region with even coarser cuts
    G4Region* defaultRegion = regionStore->GetRegion("DefaultRegionForTheWorld", false);
    if (defaultRegion) {
        G4ProductionCuts* worldCuts = new G4ProductionCuts();
        // Very coarse cuts outside substrate
        worldCuts->SetProductionCut(100.0 * nanometer, "gamma");
        worldCuts->SetProductionCut(100.0 * nanometer, "e-");
        worldCuts->SetProductionCut(100.0 * nanometer, "e+");
        defaultRegion->SetProductionCuts(worldCuts);

        G4cout << "  World region (very coarse): "
            << G4BestUnit(100.0 * nanometer, "Length") << G4endl;
    }

    // Dump the full particle/process list for verification
    if (GetVerboseLevel() > 0) {
        DumpCutValuesTable();
    }

    // Additional validation for BEAMER
    G4EmParameters* param = G4EmParameters::Instance();
    G4double lowestE = param->LowestElectronEnergy();

    G4cout << "\nBEAMER PSF Optimization Summary:" << G4endl;
    G4cout << "  Resist: Ultra-fine cuts (0.05 nm) for accuracy" << G4endl;
    G4cout << "  Substrate: Coarse cuts (10 nm) for efficiency" << G4endl;
    G4cout << "  Tracking threshold: " << lowestE/eV << " eV" << G4endl;
    G4cout << "  This configuration optimizes for resist-only PSF calculation\n" << G4endl;
}