// StackingAction.hh - Track killing for BEAMER efficiency
#ifndef StackingAction_h
#define StackingAction_h 1

#include "G4UserStackingAction.hh"
#include "globals.hh"

class DetectorConstruction;
class G4Track;

class StackingAction : public G4UserStackingAction
{
public:
    StackingAction(DetectorConstruction* detector);
    virtual ~StackingAction();

    virtual G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track* track);
    virtual void NewStage();
    virtual void PrepareNewEvent();

private:
    DetectorConstruction* fDetector;
    G4double fResistTop;        // Top of resist layer
    G4double fResistBottom;     // Bottom of resist layer (0)
    G4double fKillEnergyThreshold;  // Energy threshold for killing

    // Statistics
    G4int fKilledTracks;
    G4int fTotalTracks;
    G4int fEventNumber;
};

#endif