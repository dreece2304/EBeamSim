// PhysicsList.cc - Complete file with accuracy improvements
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
    // This allows deexcitation products to be generated even if their
    // energy is below the production cuts - essential for accurate energy deposition
    param->SetDeexcitationIgnoreCut(true);

    // Energy range for accurate low-energy physics
    param->SetMinEnergy(10 * eV);     // Track down to 10 eV - critical for resist chemistry
    param->SetMaxEnergy(1 * GeV);
    param->SetLowestElectronEnergy(10 * eV);
    param->SetLowestMuHadEnergy(1 * keV);

    // Multiple scattering parameters - critical for PSF accuracy
    param->SetMscStepLimitType(fUseDistanceToBoundary);
    param->SetMscRangeFactor(0.02);   // Smaller = more accurate, default is 0.04
    param->SetMscGeomFactor(2.5);     // Default value
    param->SetMscSkin(3.0);           // Number of skind depths
    param->SetMscSafetyFactor(0.6);   // Safety factor for geometry

    // Lateral displacement
    param->SetMuHadLateralDisplacement(true);

    // Step function - controls step size
    param->SetStepFunction(0.1, 0.1 * nanometer);  // Max 10% energy loss, min 0.1 nm step
    param->SetStepFunctionMuHad(0.1, 0.05 * nanometer);

    // Energy loss parameters
    param->SetLossFluctuations(true);   // Landau fluctuations
    param->SetLinearLossLimit(0.01);    // 1% linear loss limit
    param->SetBuildCSDARange(true);     // Continuous slowing down approximation
    param->SetUseCutAsFinalRange(false);

    // Bremsstrahlung
    param->SetBremsstrahlungTh(1 * MeV);

    // Angular settings
    param->SetFactorForAngleLimit(1.0); // No artificial angular limit

    // Apply cuts
    param->SetApplyCuts(true);

    // Number of bins for accuracy
    param->SetNumberOfBinsPerDecade(20); // Fine binning for cross sections

    // Integral approach
    param->SetIntegral(true);

    // Verbose
    param->SetVerbose(1);

    // Print configuration
    G4cout << "\n========================================" << G4endl;
    G4cout << "EM Parameters configured for EBL:" << G4endl;
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
    // CRITICAL: Use very small cuts for accurate simulation
    // These are production thresholds, not tracking cuts
    fCutForGamma = 0.1 * nanometer;     // 0.1 nm
    fCutForElectron = 0.1 * nanometer;  // 0.1 nm
    fCutForPositron = 0.1 * nanometer;  // 0.1 nm

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

    // Ultra-fine cuts in resist region
    G4Region* resistRegion = regionStore->GetRegion("ResistRegion", false);
    if (resistRegion) {
        G4ProductionCuts* resistCuts = new G4ProductionCuts();
        // Even finer cuts in resist for maximum accuracy
        resistCuts->SetProductionCut(0.05 * nanometer, "gamma");
        resistCuts->SetProductionCut(0.05 * nanometer, "e-");
        resistCuts->SetProductionCut(0.05 * nanometer, "e+");
        resistRegion->SetProductionCuts(resistCuts);

        G4cout << "  Ultra-fine cuts for resist region: "
            << G4BestUnit(0.05 * nanometer, "Length") << G4endl;
    }

    // Fine cuts in substrate region (less critical but still important)
    G4Region* substrateRegion = regionStore->GetRegion("SubstrateRegion", false);
    if (substrateRegion) {
        G4ProductionCuts* substrateCuts = new G4ProductionCuts();
        substrateCuts->SetProductionCut(0.5 * nanometer, "gamma");
        substrateCuts->SetProductionCut(0.5 * nanometer, "e-");
        substrateCuts->SetProductionCut(0.5 * nanometer, "e+");
        substrateRegion->SetProductionCuts(substrateCuts);

        G4cout << "  Fine cuts for substrate region: "
            << G4BestUnit(0.5 * nanometer, "Length") << G4endl;
    }

    // Dump the full particle/process list for verification
    if (GetVerboseLevel() > 0) {
        DumpCutValuesTable();
    }

    // Additional validation
    G4EmParameters* param = G4EmParameters::Instance();
    G4double lowestE = param->LowestElectronEnergy();
    G4cout << "\nLowest electron tracking energy: "
        << G4BestUnit(lowestE, "Energy") << G4endl;

    // Calculate approximate range of lowest energy electron
    // Range ~ (E/2)^2 / (dE/dx) ~ E^2 for low energies
    // This is a rough approximation for validation
    G4double approxRange = std::pow(lowestE/eV, 1.7) * 0.1 * nanometer;
    G4cout << "Approximate range at " << lowestE/eV << " eV: "
           << approxRange/nanometer << " nm" << G4endl;

    // Warning if cuts might be too large
    if (fCutForElectron > 1.0 * nanometer) {
        G4cout << "\nWARNING: Electron production cut > 1 nm may be too coarse for EBL simulation!"
            << G4endl;
        G4cout << "         PSF accuracy requires sub-nm production thresholds." << G4endl;
    }

    if (fCutForElectron > approxRange) {
        G4cout << "\nWARNING: Production cut larger than range of lowest tracked energy!"
               << G4endl;
        G4cout << "         This may lead to energy non-conservation." << G4endl;
    }

    G4cout << "\nNOTE: These are production thresholds, not tracking cuts." << G4endl;
    G4cout << "      Particles are tracked down to " << lowestE/eV << " eV" << G4endl;
    G4cout << "      regardless of production thresholds.\n" << G4endl;
}