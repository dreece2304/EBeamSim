// ActionInitialization.cc - Updated with StackingAction for BEAMER efficiency
#include "ActionInitialization.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "EventAction.hh"
#include "SteppingAction.hh"
#include "StackingAction.hh"
#include "DetectorConstruction.hh"
#include "G4Threading.hh"

ActionInitialization::ActionInitialization(DetectorConstruction* detConstruction)
    : G4VUserActionInitialization(),
    fDetConstruction(detConstruction)
{
}

ActionInitialization::~ActionInitialization()
{
}

void ActionInitialization::BuildForMaster() const
{
    // This method is only called for the master thread in MT mode
    // Only RunAction needs to be created for the master
    RunAction* runAction = new RunAction(fDetConstruction, nullptr);
    SetUserAction(runAction);
}

void ActionInitialization::Build() const
{
    // This method is called for each worker thread in MT mode,
    // and once in sequential mode

    // Primary generator - thread local
    PrimaryGeneratorAction* primary = new PrimaryGeneratorAction(fDetConstruction);
    SetUserAction(primary);

    // Run action - thread local
    RunAction* runAction = new RunAction(fDetConstruction, primary);
    SetUserAction(runAction);

    // Event action - thread local
    EventAction* eventAction = new EventAction(runAction, fDetConstruction);
    SetUserAction(eventAction);

    // Stepping action - thread local
    SteppingAction* steppingAction = new SteppingAction(eventAction, fDetConstruction);
    SetUserAction(steppingAction);

    // BEAMER OPTIMIZATION: Add stacking action for track killing
    StackingAction* stackingAction = new StackingAction(fDetConstruction);
    SetUserAction(stackingAction);

    // Debug output to confirm thread creation
    if (G4Threading::IsWorkerThread()) {
        G4cout << ">>> Worker thread " << G4Threading::G4GetThreadId()
            << " initialized with BEAMER optimizations" << G4endl;
    } else {
        G4cout << ">>> Sequential mode initialized with BEAMER optimizations" << G4endl;
    }
}