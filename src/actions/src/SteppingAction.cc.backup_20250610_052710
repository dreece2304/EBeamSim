// SteppingAction.cc
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"

SteppingAction::SteppingAction(EventAction* eventAction, DetectorConstruction* detConstruction)
: G4UserSteppingAction(),
  fEventAction(eventAction),
  fDetConstruction(detConstruction),
  fScoringVolume(nullptr)
{}

SteppingAction::~SteppingAction()
{}

void SteppingAction::UserSteppingAction(const G4Step* step)
{
    // Get the scoring volume if not already set
    if (!fScoringVolume) {
        fScoringVolume = fDetConstruction->GetScoringVolume();
    }
    
    // Check if step is in scoring volume
    G4LogicalVolume* volume = step->GetPreStepPoint()->GetTouchableHandle()
                              ->GetVolume()->GetLogicalVolume();
    
    if (volume != fScoringVolume) return;
    
    // Get energy deposit in this step
    G4double edep = step->GetTotalEnergyDeposit();
    
    if (edep <= 0.) return;
    
    // Get position of energy deposition
    G4ThreeVector pos = step->GetPostStepPoint()->GetPosition();
    
    // Add energy deposit to event action
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());
}