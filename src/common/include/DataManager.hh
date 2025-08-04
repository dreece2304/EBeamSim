#ifndef DataManager_h
#define DataManager_h 1

#include "globals.hh"
#include "G4ThreeVector.hh"
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
    
    // Pattern exposure data management
    void InitializeDoseGrid(G4int nx, G4int ny, G4int nz, 
                           G4double xMin, G4double xMax,
                           G4double yMin, G4double yMax,
                           G4double zMin, G4double zMax);
    void AddDoseDeposit(const G4ThreeVector& position, G4double energy);
    void SaveDoseDistribution();
    void EnablePatternMode(G4bool enable) { fPatternMode = enable; }
    void SetBeamCurrent(G4double current) { fBeamCurrent = current; }  // nA
    void SetElectronsPerPoint(G4int n) { fElectronsPerPoint = n; }
    void SetTotalPatternPoints(G4int n) { fTotalPatternPoints = n; }

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
    G4int GetNx() const { return fNx; }
    G4bool IsPatternMode() const { return fPatternMode; }
    G4int GetElectronsPerPoint() const { return fElectronsPerPoint; }
    G4int GetTotalPatternPoints() const { return fTotalPatternPoints; }

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
    
    // Pattern exposure data
    G4bool fPatternMode;
    std::vector<std::vector<std::vector<G4double>>> fDoseGrid;  // 3D dose grid
    G4int fNx, fNy, fNz;  // Grid dimensions
    G4double fXMin, fXMax, fYMin, fYMax, fZMin, fZMax;  // Grid bounds
    G4double fDx, fDy, fDz;  // Grid spacing
    G4double fBeamCurrent;  // nA
    G4int fElectronsPerPoint;  // For dose normalization
    G4int fTotalPatternPoints;  // Total exposure points in pattern

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
    
    // Messenger
    class DataMessenger* fMessenger;
};

#endif