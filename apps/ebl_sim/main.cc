// main.cc - EBL Simulation with Multi-Threading Support
#include "DetectorConstruction.hh"
#include "ActionInitialization.hh"
#include "PhysicsList.hh"

#include "G4RunManagerFactory.hh"
#include "G4UImanager.hh"
#include "G4UIcommand.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"
#include "G4UIterminal.hh"
#include "G4UItcsh.hh"
#include "Randomize.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"

#include <iostream>
#include <thread>

// Function to print usage info
void PrintUsage()
{
    G4cerr << "Usage: ebl_sim [OPTION] [MACRO]" << G4endl;
    G4cerr << "Options:" << G4endl;
    G4cerr << "  -m MACRO   Execute macro file" << G4endl;
    G4cerr << "  -n N       Override event count (run N events after macro)" << G4endl;
    G4cerr << "  -t N       Use N threads (0=sequential, default=auto)" << G4endl;
    G4cerr << "  -u         Start UI session (Qt-based)" << G4endl;
    G4cerr << "  -p         Pipe mode: stdin commands with visualization" << G4endl;
    G4cerr << "  -h         Print this help and exit" << G4endl;
}

int main(int argc, char** argv)
{
    // Parse command line options
    G4String macro;
    G4bool interactive = false;
    G4bool pipeMode = false;
    G4int nThreads = -1;  // -1 = auto-detect
    G4int nEvents = -1;   // -1 = use macro's beamOn count

    for (G4int i = 1; i < argc; i++) {
        G4String arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            PrintUsage();
            return 0;
        }
        else if (arg == "-u" || arg == "--ui") {
            interactive = true;
        }
        else if (arg == "-p" || arg == "--pipe") {
            pipeMode = true;
        }
        else if (arg == "-t" && i + 1 < argc) {
            nThreads = std::stoi(argv[++i]);
        }
        else if (arg == "-n" && i + 1 < argc) {
            nEvents = std::stoi(argv[++i]);
        }
        else if (arg == "-m" && i + 1 < argc) {
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
    G4long seed = static_cast<G4long>(time(NULL));
    CLHEP::HepRandom::setTheSeed(seed);

    // Determine number of threads
    G4int hwThreads = std::thread::hardware_concurrency();
    if (nThreads < 0) {
        // Auto-detect: use all cores minus 1 for system responsiveness
        nThreads = std::max(1, hwThreads - 1);
    }

    // Create run manager using factory (handles MT vs sequential automatically)
    G4RunManager* runManager = nullptr;

#ifdef G4MULTITHREADED
    if (nThreads > 0 && !interactive && !pipeMode) {
        // Use MT for batch mode
        runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::MT);
        runManager->SetNumberOfThreads(nThreads);
        G4cout << "====> Running in MT mode with " << nThreads << " threads "
               << "(hardware: " << hwThreads << " cores)" << G4endl;
    } else {
        // Use sequential for interactive/pipe mode (visualization requires it)
        runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Serial);
        G4cout << "====> Running in sequential mode" << G4endl;
    }
#else
    runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Serial);
    G4cout << "====> Running in sequential mode (MT not available)" << G4endl;
#endif

    // Set mandatory user initialization classes
    DetectorConstruction* detConstruction = new DetectorConstruction();
    runManager->SetUserInitialization(detConstruction);

    PhysicsList* physicsList = new PhysicsList();
    runManager->SetUserInitialization(physicsList);

    ActionInitialization* actionInitialization = new ActionInitialization(detConstruction);
    runManager->SetUserInitialization(actionInitialization);

    // NOTE: Do NOT call runManager->Initialize() here!
    // Let the macro's /run/initialize handle it so that material settings
    // from the macro are applied BEFORE geometry construction.

    // Initialize visualization
    G4VisManager* visManager = new G4VisExecutive("Quiet");
    visManager->Initialize();

    // Get the pointer to the UI manager
    G4UImanager* UImanager = G4UImanager::GetUIpointer();

    if (!macro.empty()) {
        // Batch mode - execute macro
        G4String command = "/control/execute " + macro;
        UImanager->ApplyCommand(command);

        // If -n specified, run additional events after macro
        if (nEvents > 0) {
            G4cout << "Running " << nEvents << " events (from -n flag)" << G4endl;
            UImanager->ApplyCommand("/run/beamOn " + std::to_string(nEvents));
            UImanager->ApplyCommand("/ebl/trajectory/write");
        }
    }
    else if (pipeMode) {
        // Pipe mode - read commands from stdin with visualization
        // Initialize visualization first
        UImanager->ApplyCommand("/control/execute macros/runs/init_vis.mac");

        // Create terminal session that reads from stdin
        G4UIsession* session = new G4UIterminal(new G4UItcsh());
        session->SessionStart();
        delete session;
    }
    else if (interactive) {
        // Interactive mode with visualization (Qt-based)
        G4UIExecutive* ui = new G4UIExecutive(argc, argv);

        // Initialize default visualization
        UImanager->ApplyCommand("/control/execute macros/runs/init_vis.mac");

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
