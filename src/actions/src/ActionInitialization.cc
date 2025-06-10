// ActionInitialization.cc
#include "ActionInitialization.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "EventAction.hh"
#include "SteppingAction.hh"
#include "DetectorConstruction.hh"

ActionInitialization::ActionInitialization(DetectorConstruction* detConstruction)
: G4VUserActionInitialization(),
  fDetConstruction(detConstruction)
{}

ActionInitialization::~ActionInitialization()
{}

void ActionInitialization::BuildForMaster() const
{
    RunAction* runAction = new RunAction(fDetConstruction, nullptr);
    SetUserAction(runAction);
}

void ActionInitialization::Build() const
{
    // Primary generator
    PrimaryGeneratorAction* primary = new PrimaryGeneratorAction(fDetConstruction);
    SetUserAction(primary);
    
    // Run action
    RunAction* runAction = new RunAction(fDetConstruction, primary);
    SetUserAction(runAction);
    
    // Event action
    EventAction* eventAction = new EventAction(runAction, fDetConstruction);
    SetUserAction(eventAction);
    
    // Stepping action
    SteppingAction* steppingAction = new SteppingAction(eventAction, fDetConstruction);
    SetUserAction(steppingAction);
}