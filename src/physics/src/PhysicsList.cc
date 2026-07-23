// PhysicsList.cc - Optimized for BEAMER with region-specific cuts
#include "PhysicsList.hh"
#include "PhysicsMessenger.hh"
#include "../../geometry/include/DetectorConstruction.hh"
#include "EBLConstants.hh"

#include "G4DecayPhysics.hh"
#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmExtraPhysics.hh"
// #include "G4EmDNAPhysics_option2.hh"  // Disabled - causes process duplication

#include "G4SystemOfUnits.hh"
#include "G4NistManager.hh"
#include "G4Element.hh"
#include "G4ParticleDefinition.hh"
#include "G4ProcessManager.hh"
#include "G4LossTableManager.hh"
#include "G4EmParameters.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4UnitsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4ProductionCuts.hh"
#include "G4RunManager.hh"

#include <sstream>

PhysicsList::PhysicsList()
    : G4VModularPhysicsList(),
    fEmPhysics(nullptr),
    fDecayPhysics(nullptr),
    fEmDNAPhysics(nullptr),
    fCutForGamma(0.1 * nanometer),      // Ultra-fine for accuracy
    fCutForElectron(0.1 * nanometer),   // Ultra-fine for accuracy
    fCutForPositron(0.1 * nanometer),   // Ultra-fine for accuracy
    fUseHighZOptimization(false),
    fMessenger(nullptr)
{
    G4LossTableManager::Instance();

    // Set verbosity
    SetVerboseLevel(1);

    // Default physics
    fDecayPhysics = new G4DecayPhysics();

    // EM physics - Use Livermore for better low-energy accuracy (down to 10 eV)
    fEmPhysics = new G4EmLivermorePhysics();

    // CRITICAL: Add step limiter physics to respect G4UserLimits in geometry
    // Without this, user limits in DetectorConstruction have no effect
    RegisterPhysics(new G4StepLimiterPhysics());

    // DNA physics disabled - causes process duplication with Livermore
    // Would need separate implementation for < 100 eV region
    fEmDNAPhysics = nullptr;

    // Check if we need high-Z optimization
    fUseHighZOptimization = IsHighZMaterial();

    // Configure EM parameters before initialization
    SetupEmParameters();

    // Apply high-Z specific configurations if needed
    if (fUseHighZOptimization) {
        ConfigureForHighZMaterial();
    }

    // Create messenger for UI commands
    fMessenger = new PhysicsMessenger(this);
}

PhysicsList::~PhysicsList()
{
    delete fDecayPhysics;
    delete fEmPhysics;
    if (fEmDNAPhysics) delete fEmDNAPhysics;
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

    // Explicitly activate deexcitation for resist region
    param->SetDeexActiveRegion("ResistRegion", true, true, true);

    // Energy range for accurate low-energy physics
    G4double minEnergy = fUseHighZOptimization ?
        EBL::Physics::MIN_TRACKING_ENERGY_HIGH_Z :
        EBL::Physics::MIN_TRACKING_ENERGY;

    param->SetMinEnergy(minEnergy);
    param->SetMaxEnergy(1 * GeV);
    param->SetLowestElectronEnergy(minEnergy);
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

    // Minimal output - key settings only
    G4cout << "Physics: Livermore EM, " << param->MinKinEnergy()/eV << " eV threshold, "
           << "Fluo=" << param->Fluo() << " Auger=" << param->Auger() << G4endl;
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

    // DNA physics disabled - would need separate implementation
    // if (fEmDNAPhysics) {
    //     fEmDNAPhysics->ConstructProcess();
    // }

    // Decay physics
    fDecayPhysics->ConstructProcess();

    // CRITICAL FIX: Construct ALL registered physics modules
    // This includes G4StepLimiterPhysics which enforces G4UserLimits from DetectorConstruction.
    // Without this, user limits have NO effect and electrons skip through resist in huge steps!
    G4int idx = 0;
    const G4VPhysicsConstructor* physics;
    while ((physics = GetPhysics(idx)) != nullptr) {
        G4String name = physics->GetPhysicsName();
        // Skip if it's one we already handled manually (EM, Decay)
        // Only construct registered modules we haven't handled
        if (name != fEmPhysics->GetPhysicsName() &&
            name != fDecayPhysics->GetPhysicsName()) {
            const_cast<G4VPhysicsConstructor*>(physics)->ConstructProcess();
            G4cout << "Constructed registered physics: " << name << G4endl;
        }
        idx++;
    }
}

void PhysicsList::SetCuts()
{
    // Re-check for high-Z materials now that geometry is constructed
    // (The check in constructor happens before macro sets the composition)
    G4bool wasHighZ = fUseHighZOptimization;
    fUseHighZOptimization = IsHighZMaterial();

    if (fUseHighZOptimization && !wasHighZ) {
        // Material was updated to high-Z after initial construction
        ConfigureForHighZMaterial();
    }

    // BEAMER OPTIMIZATION: Use region-specific cuts

    // Default global cuts (moderate)
    fCutForGamma = 1.0 * nanometer;
    fCutForElectron = 1.0 * nanometer;
    fCutForPositron = 1.0 * nanometer;

    // Set default production cuts
    SetCutValue(fCutForGamma, "gamma");
    SetCutValue(fCutForElectron, "e-");
    SetCutValue(fCutForPositron, "e+");

    ApplyRegionCuts();
}

void PhysicsList::ApplyRegionCuts()
{
    // Reuses each region's existing G4ProductionCuts so this can be called
    // again after a material change without leaking or losing the couple table
    G4RegionStore* regionStore = G4RegionStore::GetInstance();

    auto setRegionCuts = [](G4Region* region, G4double cutValue) {
        if (!region) return;
        G4ProductionCuts* cuts = region->GetProductionCuts();
        if (!cuts) {
            cuts = new G4ProductionCuts();
            region->SetProductionCuts(cuts);
        }
        cuts->SetProductionCut(cutValue, "gamma");
        cuts->SetProductionCut(cutValue, "e-");
        cuts->SetProductionCut(cutValue, "e+");
    };

    // CRITICAL: Ultra-fine cuts in resist region for PSF accuracy;
    // even finer for high-Z materials
    const G4double resistCutValue = fUseHighZOptimization ?
        EBL::Physics::RESIST_CUT_HIGH_Z :
        EBL::Physics::RESIST_CUT;
    setRegionCuts(regionStore->GetRegion("ResistRegion", false), resistCutValue);

    // Coarser cuts in substrate for efficiency (backscatter still tracked)
    setRegionCuts(regionStore->GetRegion("SubstrateRegion", false),
                  EBL::Physics::SUBSTRATE_CUT);

    // World region with coarse cuts
    setRegionCuts(regionStore->GetRegion("DefaultRegionForTheWorld", false),
                  EBL::Physics::WORLD_CUT);

    // Fresh stream so inherited precision/fixed flags on G4cout can't
    // truncate small cut values (e.g. 0.01 printed as 0.0)
    std::ostringstream cutsMsg;
    cutsMsg << "Cuts: Resist=" << resistCutValue / nanometer << "nm"
            << ", Substrate=" << EBL::Physics::SUBSTRATE_CUT / nanometer << "nm"
            << ", World=" << EBL::Physics::WORLD_CUT / nanometer << "nm"
            << (fUseHighZOptimization ? " [High-Z]" : "");
    G4cout << cutsMsg.str() << G4endl;
}

G4bool PhysicsList::IsHighZMaterial() const
{
    // Get the detector construction to check resist composition
    const auto* runManager = G4RunManager::GetRunManager();
    if (!runManager) return false;

    const auto* detector = dynamic_cast<const DetectorConstruction*>(
        runManager->GetUserDetectorConstruction());
    if (!detector) return false;

    // Any constituent with Z >= 30 (Zn, Zr, Sn, Hf, W, Bi, ...) gets the
    // high-Z treatment: finer cuts, Mott correction, lower brems threshold
    auto* nist = G4NistManager::Instance();
    for (const auto& elem : detector->GetResistElements()) {
        const G4Element* element = nist->FindOrBuildElement(elem.first);
        if (element && element->GetZasInt() >= 30) {
            return true;
        }
    }
    return false;
}

void PhysicsList::ConfigureForHighZMaterial()
{
    G4EmParameters* param = G4EmParameters::Instance();

    // High-Z optimizations: lower bremsstrahlung threshold, finer MSC
    param->SetBremsstrahlungTh(EBL::Physics::BREMSSTRAHLUNG_THRESHOLD_HIGH_Z);
    param->SetMscRangeFactor(EBL::Physics::MSC_RANGE_FACTOR_HIGH_Z);
    param->SetMscMuHadRangeFactor(0.2);
    param->SetNumberOfBinsPerDecade(30);
    param->SetUseMottCorrection(true);

    G4cout << "High-Z config: Mott=ON, MSC=" << EBL::Physics::MSC_RANGE_FACTOR_HIGH_Z
           << ", Bins=30/decade" << G4endl;
}

void PhysicsList::ReconfigureForMaterial()
{
    G4bool wasHighZ = fUseHighZOptimization;
    fUseHighZOptimization = IsHighZMaterial();

    if (fUseHighZOptimization != wasHighZ) {
        SetupEmParameters();
        if (fUseHighZOptimization) {
            ConfigureForHighZMaterial();
        }
        // Region cut values changed (resist 0.05nm <-> 0.01nm): re-apply and
        // tell the run manager so the couple/physics tables rebuild at next beamOn.
        // GeometryHasBeenModified() alone does not pick up changed cut values.
        ApplyRegionCuts();
        auto* runManager = G4RunManager::GetRunManager();
        if (runManager) {
            runManager->PhysicsHasBeenModified();
        }
    }
}