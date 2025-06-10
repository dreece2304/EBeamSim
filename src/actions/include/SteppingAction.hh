// SteppingAction.hh
#ifndef SteppingAction_h
#define SteppingAction_h 1

#include "G4UserSteppingAction.hh"
#include "globals.hh"
#include "G4LogicalVolume.hh"

class EventAction;
class DetectorConstruction;

class SteppingAction : public G4UserSteppingAction {
public:
    SteppingAction(EventAction* eventAction, DetectorConstruction* detConstruction);
    virtual ~SteppingAction();

    // Method from the base class
    virtual void UserSteppingAction(const G4Step*);

private:
    EventAction* fEventAction;
    DetectorConstruction* fDetConstruction;
    G4LogicalVolume* fScoringVolume;
};

#endif