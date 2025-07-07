// RunAction.hh - BEAMER Optimized with Performance Monitoring
#ifndef RunAction_h
#define RunAction_h 1

#include "G4UserRunAction.hh"
#include "globals.hh"
#include <vector>
#include <mutex>
#include <chrono>
#include "G4Accumulable.hh"
#include "G4Threading.hh"

class G4Run;
class DetectorConstruction;
class PrimaryGeneratorAction;
class OutputMessenger;

class RunAction : public G4UserRunAction {
public:
    RunAction(DetectorConstruction* detConstruction,
        PrimaryGeneratorAction* primaryGenerator);
    virtual ~RunAction();

    virtual void BeginOfRunAction(const G4Run*);
    virtual void EndOfRunAction(const G4Run*);

    // Methods to accumulate energy deposition data
    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);
    void AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit);
    void Add2DEnergyDeposit(const std::vector<std::vector<G4double>>& energy2D);
    void AddRegionEnergy(G4double resist, G4double substrate, G4double above);

    // Access methods for analysis
    std::vector<G4double> GetRadialEnergyProfile() const { return fRadialEnergyProfile; }
    
    // Output filename setters
    void SetOutputDirectory(const G4String& dir) { fOutputDirectory = dir; }
    void SetPSFFilename(const G4String& name) { fPSFFilename = name; }
    void SetPSF2DFilename(const G4String& name) { fPSF2DFilename = name; }
    void SetSummaryFilename(const G4String& name) { fSummaryFilename = name; }
    void SetBeamerFilename(const G4String& name) { fBeamerFilename = name; }

private:
    DetectorConstruction* fDetConstruction;
    PrimaryGeneratorAction* fPrimaryGenerator;

    // For energy deposition analysis - thread local storage
    std::vector<G4double> fRadialEnergyProfile;
    std::vector<std::vector<G4double>> f2DEnergyProfile;

    // Only scalar accumulables - much more efficient!
    G4Accumulable<G4double> fTotalEnergyDeposit;
    G4Accumulable<G4double> fResistEnergyTotal;
    G4Accumulable<G4double> fSubstrateEnergyTotal;
    G4Accumulable<G4double> fAboveResistEnergyTotal;

    G4int fNumEvents;

    // For thread-safe accumulation of histograms
    static std::mutex fArrayMergeMutex;
    static std::vector<G4double> fMasterRadialProfile;
    static std::vector<std::vector<G4double>> fMaster2DProfile;
    static G4bool fMasterArraysInitialized;

    // Output filenames
    G4String fOutputDirectory;
    G4String fPSFFilename;
    G4String fPSF2DFilename;
    G4String fSummaryFilename;
    G4String fBeamerFilename;

    // Messenger for output control
    OutputMessenger* fOutputMessenger;
    
    // Performance monitoring
    std::chrono::high_resolution_clock::time_point fStartTime;

    // Helper functions for logarithmic binning
    G4double GetBinRadius(G4int bin) const;
    void GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const;

    // Analysis helpers
    void SaveResults();
    void SaveCSVFormat(const std::string& outputDir);
    void SaveBEAMERFormat(const std::string& outputDir);
    void Save2DFormat(const std::string& outputDir);
    void SaveSummary(const std::string& outputDir);

    // Thread-safe merge of local arrays to master
    void MergeLocalArrays();
};

#endif