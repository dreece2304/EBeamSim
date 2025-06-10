#ifndef DataManager_h
#define DataManager_h 1

#include "globals.hh"
#include <vector>
#include <memory>
#include <fstream>

class DataManager {
public:
    // Singleton pattern for global access
    static DataManager* Instance();

    // Destructor
    ~DataManager();

    // Configuration
    void SetOutputDirectory(const G4String& dir);
    void SetRunID(G4int id);

    // PSF data management
    void InitializePSFBins(G4int nBins);
    void AddPSFData(G4double radius, G4double energy);
    void AddRadialDeposit(G4double radius, G4double energy);

    // Event data
    void BeginEvent(G4int eventID);
    void EndEvent();

    // Run data
    void BeginRun(G4int runID, G4int nEvents);
    void EndRun();

    // Analysis and output
    void SavePSFData();
    void SaveBEAMERFormat();
    void SaveSummary();
    void SaveAllData();

    // Getters
    G4String GetOutputDirectory() const { return fOutputDir; }
    G4int GetCurrentRunID() const { return fRunID; }
    G4int GetProcessedEvents() const { return fProcessedEvents; }

    // Real-time monitoring
    void EnableLiveMonitoring(G4bool enable) { fLiveMonitoring = enable; }
    G4double GetCurrentProgress() const;

private:
    // Private constructor for singleton
    DataManager();

    // Prevent copying
    DataManager(const DataManager&) = delete;
    DataManager& operator=(const DataManager&) = delete;

    // Static instance
    static DataManager* fInstance;

    // Data storage
    std::vector<G4double> fRadialEnergyProfile;
    std::vector<G4double> fRadialBinCenters;
    std::vector<std::pair<G4double, G4double>> fEventDeposits;

    // Configuration
    G4String fOutputDir;
    G4int fRunID;
    G4int fTotalEvents;
    G4int fProcessedEvents;
    G4bool fLiveMonitoring;

    // File streams
    std::unique_ptr<std::ofstream> fLiveDataStream;

    // Helper methods
    G4double GetBinRadius(G4int bin) const;
    void GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const;
    G4int GetRadialBin(G4double radius) const;
    void CreateOutputDirectory();
};

#endif