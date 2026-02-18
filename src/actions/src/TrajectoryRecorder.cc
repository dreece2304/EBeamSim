// TrajectoryRecorder.cc - Thread-safe trajectory recording for visualization
#include "TrajectoryRecorder.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include <iostream>
#include <iomanip>
#include <algorithm>

TrajectoryRecorder* TrajectoryRecorder::fInstance = nullptr;
std::mutex TrajectoryRecorder::fInstanceMutex;

TrajectoryRecorder* TrajectoryRecorder::Instance() {
    std::lock_guard<std::mutex> lock(fInstanceMutex);
    if (!fInstance) {
        fInstance = new TrajectoryRecorder();
    }
    return fInstance;
}

TrajectoryRecorder::TrajectoryRecorder()
    : fEnabled(false),
      fOutputFilename("trajectories.json")
{
}

TrajectoryRecorder::~TrajectoryRecorder() {
}

void TrajectoryRecorder::SetOutputFile(const G4String& filename) {
    fOutputFilename = filename;
}

void TrajectoryRecorder::StartNewEvent(G4int eventID) {
    if (!fEnabled) return;

    G4int threadID = G4Threading::G4GetThreadId();
    if (threadID < 0) threadID = 0;  // Master thread

    std::lock_guard<std::mutex> lock(fDataMutex);

    // Save previous event from this thread if any
    auto it = fThreadCurrentEvent.find(threadID);
    if (it != fThreadCurrentEvent.end() && !it->second.points.empty()) {
        fAllEvents.push_back(std::move(it->second));
    }

    // Start new event for this thread
    fThreadCurrentEvent[threadID] = EventData{eventID, {}};
}

void TrajectoryRecorder::RecordStep(G4int trackID, G4int parentID,
                                    const G4String& particle,
                                    const G4ThreeVector& pos, G4double energy) {
    if (!fEnabled) return;

    G4int threadID = G4Threading::G4GetThreadId();
    if (threadID < 0) threadID = 0;

    TrajectoryPoint point;
    point.x = pos.x() / nm;
    point.y = pos.y() / nm;
    point.z = pos.z() / nm;
    point.energy = energy / keV;
    point.trackID = trackID;
    point.parentID = parentID;
    point.particleName = particle;

    std::lock_guard<std::mutex> lock(fDataMutex);
    auto it = fThreadCurrentEvent.find(threadID);
    if (it != fThreadCurrentEvent.end()) {
        it->second.points.push_back(point);
    }
}

void TrajectoryRecorder::EndEvent() {
    if (!fEnabled) return;

    G4int threadID = G4Threading::G4GetThreadId();
    if (threadID < 0) threadID = 0;

    std::lock_guard<std::mutex> lock(fDataMutex);

    auto it = fThreadCurrentEvent.find(threadID);
    if (it != fThreadCurrentEvent.end() && !it->second.points.empty()) {
        fAllEvents.push_back(std::move(it->second));
        fThreadCurrentEvent.erase(it);
    }
}

void TrajectoryRecorder::Clear() {
    std::lock_guard<std::mutex> lock(fDataMutex);
    fThreadCurrentEvent.clear();
    fAllEvents.clear();
}

void TrajectoryRecorder::WriteAllData() {
    std::lock_guard<std::mutex> lock(fDataMutex);

    // Collect any remaining events from threads
    for (auto& [threadID, eventData] : fThreadCurrentEvent) {
        if (!eventData.points.empty()) {
            fAllEvents.push_back(std::move(eventData));
        }
    }
    fThreadCurrentEvent.clear();

    if (fAllEvents.empty()) {
        G4cout << "TrajectoryRecorder: No trajectory data to write." << G4endl;
        return;
    }

    // Sort events by event ID for consistent output
    std::sort(fAllEvents.begin(), fAllEvents.end(),
              [](const EventData& a, const EventData& b) {
                  return a.eventID < b.eventID;
              });

    std::ofstream outFile(fOutputFilename);
    if (!outFile.is_open()) {
        G4cerr << "TrajectoryRecorder: Could not open " << fOutputFilename << G4endl;
        return;
    }

    // Write JSON format
    outFile << "{\n";
    outFile << "  \"events\": [\n";

    for (size_t eventIdx = 0; eventIdx < fAllEvents.size(); ++eventIdx) {
        const auto& event = fAllEvents[eventIdx];
        outFile << "    {\n";
        outFile << "      \"event_id\": " << event.eventID << ",\n";
        outFile << "      \"tracks\": {\n";

        // Group points by track ID
        std::map<G4int, std::vector<const TrajectoryPoint*>> trackPoints;
        for (const auto& point : event.points) {
            trackPoints[point.trackID].push_back(&point);
        }

        size_t trackCount = 0;
        for (const auto& [trackID, points] : trackPoints) {
            outFile << "        \"" << trackID << "\": {\n";
            outFile << "          \"particle\": \"" << points[0]->particleName << "\",\n";
            outFile << "          \"parent_id\": " << points[0]->parentID << ",\n";
            outFile << "          \"points\": [\n";

            for (size_t i = 0; i < points.size(); ++i) {
                outFile << "            ["
                       << std::fixed << std::setprecision(2)
                       << points[i]->x << ", "
                       << points[i]->y << ", "
                       << points[i]->z << ", "
                       << std::setprecision(3)
                       << points[i]->energy << "]";
                if (i < points.size() - 1) outFile << ",";
                outFile << "\n";
            }

            outFile << "          ]\n";
            outFile << "        }";
            if (++trackCount < trackPoints.size()) outFile << ",";
            outFile << "\n";
        }

        outFile << "      }\n";
        outFile << "    }";
        if (eventIdx < fAllEvents.size() - 1) outFile << ",";
        outFile << "\n";
    }

    outFile << "  ]\n";
    outFile << "}\n";

    outFile.close();

    G4cout << "TrajectoryRecorder: Wrote " << fAllEvents.size() << " events to "
           << fOutputFilename << G4endl;

    // Clear after writing
    fAllEvents.clear();
}
