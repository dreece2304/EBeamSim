﻿// SteppingAction.cc
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
    // Get energy deposit in this step
    G4double edep = step->GetTotalEnergyDeposit();
    if (edep <= 0.) return;
    
    // Get position of energy deposition (use midpoint of step for accuracy)
    G4ThreeVector prePos = step->GetPreStepPoint()->GetPosition();
    G4ThreeVector postPos = step->GetPostStepPoint()->GetPosition();
    G4ThreeVector pos = (prePos + postPos) * 0.5;
    
    // Add ALL energy deposits to event action for PSF calculation
    // This captures energy in resist, substrate, and backscattered electrons
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());
    
    // Track statistics for validation
    static G4int totalSteps = 0;
    static G4int resistSteps = 0;
    static G4int substrateSteps = 0;
    static G4double totalEnergy = 0.0;
    
    totalSteps++;
    totalEnergy += edep;
    
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (pos.z() >= 0 && pos.z() <= resistThickness) {
        resistSteps++;
    } else if (pos.z() < 0) {
        substrateSteps++;
    }
    
    // Log every 100000 steps for monitoring
    if (totalSteps % 100000 == 0) {
        G4cout << "Steps: " << totalSteps 
               << " (Resist: " << resistSteps 
               << ", Substrate: " << substrateSteps 
               << "), Total E: " << G4BestUnit(totalEnergy, "Energy") 
               << G4endl;
    }
}
