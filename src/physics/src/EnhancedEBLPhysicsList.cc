// EnhancedEBLPhysicsList.cc
// Implementation of optimized physics list for EBL applications

#include "EnhancedEBLPhysicsList.hh"
#include "PhysicsMessenger.hh"

#include "G4DecayPhysics.hh"
#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmExtraPhysics.hh"

#include "G4SystemOfUnits.hh"
#include "G4PhysicalConstants.hh"
#include "G4ParticleDefinition.hh"
#include "G4ProcessManager.hh"
#include "G4LossTableManager.hh"
#include "G4EmParameters.hh"
#include "G4UnitsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4ProductionCuts.hh"

// Step limitation process
#include "G4StepLimiter.hh"
#include "G4UserSpecialCuts.hh"

// Multiple scattering models
#include "G4UrbanMscModel.hh"
#include "G4WentzelVIModel.hh"
#include "G4GoudsmitSaundersonMscModel.hh"

// Ionization models
#include "G4MollerBhabhaModel.hh"
#include "G4BetheBlochModel.hh"
#include "G4BraggModel.hh"
#include "G4LivermoreIonisationModel.hh"
#include "G4PenelopeIonisationModel.hh"

// Bremsstrahlung models
#include "G4eBremsstrahlungModel.hh"
#include "G4LivermoreBremsstrahlungModel.hh"
#include "G4PenelopeBremsstrahlungModel.hh"

EnhancedEBLPhysicsList::EnhancedEBLPhysicsList()
    : G4VModularPhysicsList(),
    fEmPhysics(nullptr),
    fDecayPhysics(nullptr),
    fMessenger(nullptr),
    fPhysicsModel(EBL_LIVERMORE_ENHANCED),
    fMinEnergy(10.0 * eV),
    fMaxEnergy(1.0 * GeV),
    fResistOptimized(true),
    fProximityMode(false),
    fResistComposition("C:5,H:8,O:2"), // Default PMMA
    fSubstrateComposition("Si:1"),
    fStepLimitation(true),
    fMaxStepResist(0.1 * nm),
    fMaxStepSubstrate(5.0 * nm),
    fTrackSecondaries(true),
    fSecondaryThreshold(10.0 * eV),
    fMscModel(1), // WentzelVI default
    fMscRangeFactor(0.02),
    fMscGeomFactor(2.5),
    fAugerOptimized(true),
    fFluoOptimized(true),
    fAccuracyLevel(3), // Accurate by default
    fThreadOptimized(false),
    fCutResistElectron(0.01 * nm),
    fCutResistGamma(0.01 * nm),
    fCutSubstrateElectron(2.0 * nm),
    fCutSubstrateGamma(2.0 * nm),
    fCutWorldElectron(50.0 * nm),
    fCutWorldGamma(50.0 * nm)
{
    G4LossTableManager::Instance();
    SetVerboseLevel(1);

    // Default physics setup
    fDecayPhysics = new G4DecayPhysics();
    
    // Set initial physics model
    SetEBLPhysicsModel(fPhysicsModel);
    
    // Create messenger
    fMessenger = new PhysicsMessenger(this);
    
    G4cout << "EnhancedEBLPhysicsList initialized with EBL-optimized settings" << G4endl;
}

EnhancedEBLPhysicsList::~EnhancedEBLPhysicsList()
{
    delete fDecayPhysics;
    delete fEmPhysics;
    delete fMessenger;
}

void EnhancedEBLPhysicsList::SetEBLPhysicsModel(EBLPhysicsModel model)
{
    if (fEmPhysics) {
        delete fEmPhysics;
        fEmPhysics = nullptr;
    }
    
    fPhysicsModel = model;
    
    switch (model) {
        case EBL_LIVERMORE_ENHANCED:
            ConfigureLivermoreEnhanced();
            break;
        case EBL_PENELOPE_OPTIMIZED:
            ConfigurePenelopeOptimized();
            break;
        case EBL_STANDARD_OPTION4:
            ConfigureStandardOption4();
            break;
        case EBL_CUSTOM_HYBRID:
            ConfigureCustomHybrid();
            break;
    }
    
    G4cout << "EBL Physics Model set to: " << model << G4endl;
}

void EnhancedEBLPhysicsList::ConfigureLivermoreEnhanced()
{
    fEmPhysics = new G4EmLivermorePhysics();
    G4cout << "Using Livermore Enhanced Physics for EBL" << G4endl;
}

void EnhancedEBLPhysicsList::ConfigurePenelopeOptimized()
{
    fEmPhysics = new G4EmPenelopePhysics();
    G4cout << "Using Penelope Optimized Physics for EBL" << G4endl;
}

void EnhancedEBLPhysicsList::ConfigureStandardOption4()
{
    fEmPhysics = new G4EmStandardPhysics_option4();
    G4cout << "Using Standard Option4 Physics for EBL" << G4endl;
}

void EnhancedEBLPhysicsList::ConfigureCustomHybrid()
{
    // For now, use Livermore as base for custom hybrid
    fEmPhysics = new G4EmLivermorePhysics();
    G4cout << "Using Custom Hybrid Physics for EBL" << G4endl;
}

void EnhancedEBLPhysicsList::SetEnergyRange(G4double minE, G4double maxE)
{
    fMinEnergy = minE;
    fMaxEnergy = maxE;
    
    G4cout << "EBL Energy range set to: " 
           << G4BestUnit(minE, "Energy") << " - " 
           << G4BestUnit(maxE, "Energy") << G4endl;
}

void EnhancedEBLPhysicsList::SetAccuracyLevel(G4int level)
{
    fAccuracyLevel = level;
    
    switch (level) {
        case 1: // Fast
            fCutResistElectron = 0.5 * nm;
            fCutResistGamma = 0.5 * nm;
            fCutSubstrateElectron = 10.0 * nm;
            fCutSubstrateGamma = 10.0 * nm;
            fMaxStepResist = 1.0 * nm;
            fMscRangeFactor = 0.1;
            break;
        case 2: // Balanced
            fCutResistElectron = 0.1 * nm;
            fCutResistGamma = 0.1 * nm;
            fCutSubstrateElectron = 5.0 * nm;
            fCutSubstrateGamma = 5.0 * nm;
            fMaxStepResist = 0.5 * nm;
            fMscRangeFactor = 0.05;
            break;
        case 3: // Accurate
            fCutResistElectron = 0.01 * nm;
            fCutResistGamma = 0.01 * nm;
            fCutSubstrateElectron = 2.0 * nm;
            fCutSubstrateGamma = 2.0 * nm;
            fMaxStepResist = 0.1 * nm;
            fMscRangeFactor = 0.02;
            break;
        case 4: // Ultra-accurate
            fCutResistElectron = 0.005 * nm;
            fCutResistGamma = 0.005 * nm;
            fCutSubstrateElectron = 1.0 * nm;
            fCutSubstrateGamma = 1.0 * nm;
            fMaxStepResist = 0.05 * nm;
            fMscRangeFactor = 0.01;
            break;
        default:
            G4cerr << "Invalid accuracy level: " << level << G4endl;
            return;
    }
    
    G4cout << "Accuracy level set to: " << level 
           << " (1=fast, 2=balanced, 3=accurate, 4=ultra-accurate)" << G4endl;
}

void EnhancedEBLPhysicsList::SetMSCModel(G4int model)
{
    fMscModel = model;
    
    const char* modelNames[] = {"Urban", "WentzelVI", "GoudsmitSaunderson"};
    if (model >= 0 && model < 3) {
        G4cout << "MSC model set to: " << modelNames[model] << G4endl;
    }
}

void EnhancedEBLPhysicsList::ConstructParticle()
{
    fDecayPhysics->ConstructParticle();
    fEmPhysics->ConstructParticle();
}

void EnhancedEBLPhysicsList::ConstructProcess()
{
    // Transportation
    AddTransportation();

    // Electromagnetic physics
    fEmPhysics->ConstructProcess();

    // Decay physics
    fDecayPhysics->ConstructProcess();
    
    // Setup EBL-specific parameters
    SetupEBLParameters();
    
    // Configure step limitation if enabled
    if (fStepLimitation) {
        ConfigureStepLimitation();
    }
}

void EnhancedEBLPhysicsList::SetupEBLParameters()
{
    G4EmParameters* param = G4EmParameters::Instance();

    // Energy range settings
    param->SetMinEnergy(fMinEnergy);
    param->SetMaxEnergy(fMaxEnergy);
    param->SetLowestElectronEnergy(fMinEnergy);
    
    // Auger and fluorescence
    if (fAugerOptimized) {
        param->SetFluo(true);
        param->SetAuger(true);
        param->SetAugerCascade(true);
        param->SetDeexcitationIgnoreCut(true);
    }
    
    if (fFluoOptimized) {
        param->SetPixe(true);
    }
    
    // Multiple scattering optimization
    param->SetMscStepLimitType(fUseSafetyPlus);
    param->SetMscRangeFactor(fMscRangeFactor);
    param->SetMscGeomFactor(fMscGeomFactor);
    param->SetMscSkin(3.0);
    param->SetMscSafetyFactor(0.6);
    
    // Step function for energy loss
    G4double dRoverR = 0.1;  // Max 10% energy loss per step
    G4double finalRange = fMaxStepResist;
    if (fAccuracyLevel == 4) {
        dRoverR = 0.05;  // Ultra-accurate: 5% max energy loss
        finalRange = 0.02 * nm;
    }
    
    param->SetStepFunction(dRoverR, finalRange);
    param->SetStepFunctionMuHad(dRoverR, finalRange * 0.5);
    
    // Energy loss fluctuations
    param->SetLossFluctuations(true);
    param->SetLinearLossLimit(0.01);
    
    // Bremsstrahlung threshold
    if (fMaxEnergy < 1.0 * MeV) {
        param->SetBremsstrahlungTh(fMaxEnergy); // No bremsstrahlung below max energy
    }
    
    // Build CSDA range tables
    param->SetBuildCSDARange(true);
    param->SetUseCutAsFinalRange(false);
    
    // Integral approach for better accuracy
    param->SetIntegral(true);
    
    // Number of bins for physics tables
    G4int binsPerDecade = (fAccuracyLevel == 4) ? 50 : 
                          (fAccuracyLevel == 3) ? 30 : 20;
    param->SetNumberOfBinsPerDecade(binsPerDecade);
    
    // Apply cuts to secondaries
    param->SetApplyCuts(true);
    
    // Threading optimization
    if (fThreadOptimized) {
        param->SetWorkerVerbose(0);
    }
    
    G4cout << "\n========================================" << G4endl;
    G4cout << "Enhanced EBL Physics Parameters Set:" << G4endl;
    G4cout << "  Energy range: " << G4BestUnit(fMinEnergy, "Energy") 
           << " - " << G4BestUnit(fMaxEnergy, "Energy") << G4endl;
    G4cout << "  Accuracy level: " << fAccuracyLevel << G4endl;
    G4cout << "  MSC range factor: " << fMscRangeFactor << G4endl;
    G4cout << "  Auger optimized: " << fAugerOptimized << G4endl;
    G4cout << "  Fluorescence optimized: " << fFluoOptimized << G4endl;
    G4cout << "  Step limitation: " << fStepLimitation << G4endl;
    G4cout << "========================================\n" << G4endl;
}

void EnhancedEBLPhysicsList::ConfigureStepLimitation()
{
    // Add step limiters to all particles
    G4StepLimiter* stepLimiter = new G4StepLimiter();
    G4UserSpecialCuts* specialCuts = new G4UserSpecialCuts();
    
    auto particleIterator = GetParticleIterator();
    particleIterator->reset();
    
    while ((*particleIterator)()) {
        G4ParticleDefinition* particle = particleIterator->value();
        G4ProcessManager* pmanager = particle->GetProcessManager();
        
        if (particle->GetPDGCharge() != 0.0) { // Charged particles only
            pmanager->AddDiscreteProcess(stepLimiter);
            pmanager->AddDiscreteProcess(specialCuts);
        }
    }
    
    G4cout << "Step limitation configured for charged particles" << G4endl;
}

void EnhancedEBLPhysicsList::SetCuts()
{
    // Set default cuts first
    SetCutValue(fCutWorldElectron, "e-");
    SetCutValue(fCutWorldGamma, "gamma");
    SetCutValue(fCutWorldElectron, "e+");

    G4cout << "\nEnhanced EBL Physics List - Production Cuts:" << G4endl;
    G4cout << "  World default: " << G4BestUnit(fCutWorldElectron, "Length") << G4endl;

    // Region-specific cuts for EBL optimization
    SetupRegionSpecificCuts();

    if (GetVerboseLevel() > 0) {
        DumpCutValuesTable();
    }
    
    // Validation
    G4EmParameters* param = G4EmParameters::Instance();
    G4cout << "\nEBL Physics Validation:" << G4endl;
    G4cout << "  Min tracking energy: " << G4BestUnit(param->LowestElectronEnergy(), "Energy") << G4endl;
    G4cout << "  Deexcitation ignore cut: " << param->DeexcitationIgnoreCut() << G4endl;
    G4cout << "  Auger processes: " << param->Auger() << G4endl;
    G4cout << "  Fluorescence: " << param->Fluo() << G4endl;
    G4cout << "  MSC range factor: " << param->MscRangeFactor() << G4endl;
}

void EnhancedEBLPhysicsList::SetupRegionSpecificCuts()
{
    G4RegionStore* regionStore = G4RegionStore::GetInstance();
    
    // Ultra-fine cuts in resist for maximum accuracy
    G4Region* resistRegion = regionStore->GetRegion("ResistRegion", false);
    if (resistRegion) {
        G4ProductionCuts* resistCuts = new G4ProductionCuts();
        resistCuts->SetProductionCut(fCutResistGamma, "gamma");
        resistCuts->SetProductionCut(fCutResistElectron, "e-");
        resistCuts->SetProductionCut(fCutResistElectron, "e+");
        resistRegion->SetProductionCuts(resistCuts);
        
        G4cout << "  Resist region: " << G4BestUnit(fCutResistElectron, "Length") << G4endl;
    }
    
    // Moderate cuts in substrate for efficiency
    G4Region* substrateRegion = regionStore->GetRegion("SubstrateRegion", false);
    if (substrateRegion) {
        G4ProductionCuts* substrateCuts = new G4ProductionCuts();
        substrateCuts->SetProductionCut(fCutSubstrateGamma, "gamma");
        substrateCuts->SetProductionCut(fCutSubstrateElectron, "e-");
        substrateCuts->SetProductionCut(fCutSubstrateElectron, "e+");
        substrateRegion->SetProductionCuts(substrateCuts);
        
        G4cout << "  Substrate region: " << G4BestUnit(fCutSubstrateElectron, "Length") << G4endl;
    }
    
    // Coarse cuts in world region
    G4Region* worldRegion = regionStore->GetRegion("DefaultRegionForTheWorld", false);
    if (worldRegion) {
        G4ProductionCuts* worldCuts = new G4ProductionCuts();
        worldCuts->SetProductionCut(fCutWorldGamma, "gamma");
        worldCuts->SetProductionCut(fCutWorldElectron, "e-");
        worldCuts->SetProductionCut(fCutWorldElectron, "e+");
        worldRegion->SetProductionCuts(worldCuts);
        
        G4cout << "  World region: " << G4BestUnit(fCutWorldElectron, "Length") << G4endl;
    }
}