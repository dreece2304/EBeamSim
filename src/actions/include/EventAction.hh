// EventAction.hh
#ifndef EventAction_h
#define EventAction_h 1

#include "G4UserEventAction.hh"
#include "globals.hh"
#include <vector>
#include <map>

class RunAction;
class DetectorConstruction;

class EventAction : public G4UserEventAction {
public:
    EventAction(RunAction* runAction, DetectorConstruction* detConstruction);
    virtual ~EventAction();

    virtual void BeginOfEventAction(const G4Event* event);
    virtual void EndOfEventAction(const G4Event* event);

    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);

private:
    RunAction* fRunAction;
    DetectorConstruction* fDetConstruction;

    G4double fEnergyDeposit;
    G4double fTotalTrackLength;

    // For point spread function calculation
    std::vector<G4double> fRadialEnergyDeposit;

    // For 2D depth-radius analysis
    static const G4int NUM_DEPTH_BINS = 100;
    std::vector<std::vector<G4double>> f2DEnergyDeposit;  // [depth][radius]

    // Track energy by region
    G4double fResistEnergy;
    G4double fSubstrateEnergy;
    G4double fAboveResistEnergy;

    // Helper functions - made inline for performance
    inline G4int GetLogBin(G4double radius) const;
    inline G4int GetDepthBin(G4double z) const;
};

#endif