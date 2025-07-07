// EventAction.hh - BEAMER Optimized (radial PSF only)
#ifndef EVENTACTION_HH
#define EVENTACTION_HH

#include "G4UserEventAction.hh"
#include "G4Types.hh"
#include <vector>

class RunAction;
class DetectorConstruction;
class G4Event;

class EventAction : public G4UserEventAction
{
public:
    EventAction(RunAction* runAction, DetectorConstruction* detConstruction);
    virtual ~EventAction();

    virtual void BeginOfEventAction(const G4Event* event);
    virtual void EndOfEventAction(const G4Event* event);

    // Add energy deposit at given position
    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);

    // Add track length - not used for BEAMER but kept for compatibility
    void AddTrackLength(G4double length) { fTotalTrackLength += length; }

private:
    RunAction* fRunAction;
    DetectorConstruction* fDetConstruction;

    // Event-level accumulation
    G4double fEnergyDeposit;
    G4double fTotalTrackLength;

    // Energy by region - simplified for BEAMER
    G4double fResistEnergy;
    G4double fSubstrateEnergy;
    G4double fAboveResistEnergy;

    // Radial energy distribution (1D) - this is all we need for BEAMER
    std::vector<G4double> fRadialEnergyDeposit;

    // 2D functionality removed for BEAMER efficiency
    // static constexpr G4int NUM_DEPTH_BINS = 100;
    // std::vector<std::vector<G4double>> f2DEnergyDeposit;

    // Helper functions
    G4int GetLogBin(G4double radius) const;
    G4int GetDepthBin(G4double z) const;  // Kept for compatibility but not used
    G4double GetBinRadius(G4int bin) const;
};

#endif