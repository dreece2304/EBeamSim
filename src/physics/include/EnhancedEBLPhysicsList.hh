// EnhancedEBLPhysicsList.hh
// Optimized Physics List for Electron Beam Lithography
// Specialized for 50-300 keV electron transport with maximum accuracy

#ifndef EnhancedEBLPhysicsList_h
#define EnhancedEBLPhysicsList_h 1

#include "G4VModularPhysicsList.hh"
#include "globals.hh"

class G4VPhysicsConstructor;
class PhysicsMessenger;
class G4EmParameters;

class EnhancedEBLPhysicsList : public G4VModularPhysicsList
{
public:
    EnhancedEBLPhysicsList();
    virtual ~EnhancedEBLPhysicsList();

    // Mandatory methods
    virtual void ConstructParticle();
    virtual void ConstructProcess();
    virtual void SetCuts();

    // Enhanced physics model selection
    enum EBLPhysicsModel {
        EBL_LIVERMORE_ENHANCED,    // Livermore with EBL-specific tuning
        EBL_PENELOPE_OPTIMIZED,    // Penelope with low-energy optimization
        EBL_STANDARD_OPTION4,      // Standard EM Option 4 with modifications
        EBL_CUSTOM_HYBRID          // Custom hybrid model
    };

    void SetEBLPhysicsModel(EBLPhysicsModel model);
    void SetEnergyRange(G4double minE, G4double maxE);
    void SetResistOptimization(G4bool enable) { fResistOptimized = enable; }
    
    // EBL-specific optimizations
    void EnableProximityCalculation(G4bool enable) { fProximityMode = enable; }
    void SetResistComposition(const G4String& composition) { fResistComposition = composition; }
    void SetSubstrateComposition(const G4String& composition) { fSubstrateComposition = composition; }
    
    // Advanced stepping and tracking controls
    void SetMaxStepInResist(G4double step) { fMaxStepResist = step; }
    void SetMaxStepInSubstrate(G4double step) { fMaxStepSubstrate = step; }
    void EnableStepLimitation(G4bool enable) { fStepLimitation = enable; }
    
    // Secondary electron handling
    void SetSecondaryElectronTracking(G4bool enable) { fTrackSecondaries = enable; }
    void SetSecondaryElectronThreshold(G4double threshold) { fSecondaryThreshold = threshold; }
    
    // MSC optimization for EBL
    void SetMSCModel(G4int model); // 0=Urban, 1=WentzelVI, 2=GoudsmitSaunderson
    void SetMSCRangeFactor(G4double factor) { fMscRangeFactor = factor; }
    void SetMSCGeomFactor(G4double factor) { fMscGeomFactor = factor; }
    
    // Auger and fluorescence optimization
    void SetAugerOptimization(G4bool enable) { fAugerOptimized = enable; }
    void SetFluorescenceOptimization(G4bool enable) { fFluoOptimized = enable; }
    
    // Getters
    EBLPhysicsModel GetPhysicsModel() const { return fPhysicsModel; }
    G4double GetMinEnergy() const { return fMinEnergy; }
    G4double GetMaxEnergy() const { return fMaxEnergy; }
    
    // Performance and accuracy balance
    void SetAccuracyLevel(G4int level); // 1=fast, 2=balanced, 3=accurate, 4=ultra-accurate
    void SetThreadingOptimization(G4bool enable) { fThreadOptimized = enable; }

private:
    void SetupEBLParameters();
    void ConfigureLivermoreEnhanced();
    void ConfigurePenelopeOptimized();
    void ConfigureStandardOption4();
    void ConfigureCustomHybrid();
    void SetupRegionSpecificCuts();
    void OptimizeForResistMaterials();
    void SetupProximityCalculation();
    void ConfigureStepLimitation();
    void SetupAugerFluorescence();
    
    // Member variables
    G4VPhysicsConstructor* fEmPhysics;
    G4VPhysicsConstructor* fDecayPhysics;
    PhysicsMessenger* fMessenger;
    
    // Physics model and configuration
    EBLPhysicsModel fPhysicsModel;
    G4double fMinEnergy;
    G4double fMaxEnergy;
    
    // EBL-specific settings
    G4bool fResistOptimized;
    G4bool fProximityMode;
    G4String fResistComposition;
    G4String fSubstrateComposition;
    
    // Step control
    G4bool fStepLimitation;
    G4double fMaxStepResist;
    G4double fMaxStepSubstrate;
    
    // Secondary electron settings
    G4bool fTrackSecondaries;
    G4double fSecondaryThreshold;
    
    // MSC settings
    G4int fMscModel;
    G4double fMscRangeFactor;
    G4double fMscGeomFactor;
    
    // Auger/fluorescence settings
    G4bool fAugerOptimized;
    G4bool fFluoOptimized;
    
    // Performance settings
    G4int fAccuracyLevel;
    G4bool fThreadOptimized;
    
    // Production cuts
    G4double fCutResistElectron;
    G4double fCutResistGamma;
    G4double fCutSubstrateElectron;
    G4double fCutSubstrateGamma;
    G4double fCutWorldElectron;
    G4double fCutWorldGamma;
};

#endif