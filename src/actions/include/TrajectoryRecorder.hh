// TrajectoryRecorder.hh - Thread-safe trajectory recording for visualization
#ifndef TrajectoryRecorder_hh
#define TrajectoryRecorder_hh 1

#include "G4ThreeVector.hh"
#include "G4Threading.hh"
#include "globals.hh"
#include <vector>
#include <map>
#include <mutex>
#include <fstream>
#include <string>

struct TrajectoryPoint {
    G4double x;      // nm
    G4double y;      // nm
    G4double z;      // nm
    G4double energy; // keV
    G4int trackID;
    G4int parentID;
    G4String particleName;
};

struct EventData {
    G4int eventID;
    std::vector<TrajectoryPoint> points;
};

class TrajectoryRecorder {
public:
    static TrajectoryRecorder* Instance();

    void SetEnabled(G4bool enabled) { fEnabled = enabled; }
    G4bool IsEnabled() const { return fEnabled; }

    void SetOutputFile(const G4String& filename);

    void StartNewEvent(G4int eventID);
    void RecordStep(G4int trackID, G4int parentID, const G4String& particle,
                   const G4ThreeVector& pos, G4double energy);
    void EndEvent();

    void WriteAllData();
    void Clear();

private:
    TrajectoryRecorder();
    ~TrajectoryRecorder();

    static TrajectoryRecorder* fInstance;
    static std::mutex fInstanceMutex;

    G4bool fEnabled;
    G4String fOutputFilename;

    // Thread-safe storage: map from thread ID to current event data
    std::mutex fDataMutex;
    std::map<G4int, EventData> fThreadCurrentEvent;  // Current event per thread
    std::vector<EventData> fAllEvents;               // Completed events (protected by mutex)
};

#endif
