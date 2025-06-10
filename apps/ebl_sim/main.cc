// ebl_sim.cc
#include "DetectorConstruction.hh"
#include "ActionInitialization.hh"
#include "PhysicsList.hh"

#include "G4RunManagerFactory.hh"
#include "G4UImanager.hh"
#include "G4UIcommand.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"
#include "Randomize.hh"
#include "G4SystemOfUnits.hh"

#include <iostream>

// Function to print usage info
void PrintUsage()
{
    G4cerr << "Usage: ebl_sim [OPTION] [MACRO]" << G4endl;
    G4cerr << "Options:" << G4endl;
    G4cerr << "  -m MACRO   Execute macro file" << G4endl;
    G4cerr << "  -u         Start UI session" << G4endl;
    G4cerr << "  -h         Print this help and exit" << G4endl;
}

int main(int argc, char** argv)
{
    // Parse command line options
    G4String macro;
    G4bool interactive = false;
    
    for (G4int i = 1; i < argc; i++) {
        G4String arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            PrintUsage();
            return 0;
        }
        else if (arg == "-u" || arg == "--ui") {
            interactive = true;
        }
        else if (arg == "-m" && i+1 < argc) {
            macro = argv[++i];
        }
        else if (arg[0] != '-') {
            // Assume it's a macro filename
            macro = arg;
        }
        else {
            PrintUsage();
            return 1;
        }
    }
    
    // Choose the Random engine and initialize with time-based seed
    CLHEP::HepRandom::setTheEngine(new CLHEP::RanecuEngine());
    G4long seed = time(NULL);
    CLHEP::HepRandom::setTheSeed(seed);
    
    // Construct the default run manager
    auto* runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Default);
    
    // Set mandatory user initialization classes
    DetectorConstruction* detConstruction = new DetectorConstruction();
    runManager->SetUserInitialization(detConstruction);
    
    PhysicsList* physicsList = new PhysicsList();
    runManager->SetUserInitialization(physicsList);
    
    ActionInitialization* actionInitialization = new ActionInitialization(detConstruction);
    runManager->SetUserInitialization(actionInitialization);
    
    // Initialize G4 kernel
    runManager->Initialize();
    
    // Initialize visualization
    G4VisManager* visManager = new G4VisExecutive("Quiet");
    visManager->Initialize();
    
    // Get the pointer to the UI manager
    G4UImanager* UImanager = G4UImanager::GetUIpointer();
    
    if (!macro.empty()) {
        // Batch mode - execute macro
        G4String command = "/control/execute " + macro;
        UImanager->ApplyCommand(command);
    }
    else if (interactive) {
        // Interactive mode with visualization
        G4UIExecutive* ui = new G4UIExecutive(argc, argv);
        
        // Initialize default visualization
        UImanager->ApplyCommand("/control/execute macros/init_vis.mac");
        
        // Start UI session
        ui->SessionStart();
        delete ui;
    }
    else {
        // No macro or UI specified - just run a simple simulation
        UImanager->ApplyCommand("/run/initialize");
        UImanager->ApplyCommand("/gun/energy 100 keV");
        UImanager->ApplyCommand("/run/beamOn 1000");
    }
    
    // Job termination
    delete visManager;
    delete runManager;
    
    return 0;
}