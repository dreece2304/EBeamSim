// EventAction.hh
#ifndef EventAction_h
#define EventAction_h 1

#include "G4UserEventAction.hh"
#include "globals.hh"
#include <vector>

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

    // Helper function for logarithmic binning
    G4int GetLogBin(G4double radius) const;
};

#endif