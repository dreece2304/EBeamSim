// DataMessenger.cc
#include "DataMessenger.hh"
#include "DataManager.hh"

#include "G4UIdirectory.hh"
#include "G4UIcommand.hh"
#include "G4UIparameter.hh"
#include "G4SystemOfUnits.hh"

DataMessenger::DataMessenger(DataManager* dataManager)
    : G4UImessenger(),
      fDataManager(dataManager) {
    
    fDataDir = new G4UIdirectory("/data/");
    fDataDir->SetGuidance("Data management commands");
    
    // Initialize dose grid command
    fInitDoseGridCmd = new G4UIcommand("/data/initDoseGrid", this);
    fInitDoseGridCmd->SetGuidance("Initialize dose accumulation grid");
    fInitDoseGridCmd->SetGuidance("Parameters: nx ny nz xMin xMax yMin yMax zMin zMax unit");
    
    auto p1 = new G4UIparameter("nx", 'i', false);
    p1->SetGuidance("Number of grid cells in X");
    fInitDoseGridCmd->SetParameter(p1);
    
    auto p2 = new G4UIparameter("ny", 'i', false);
    p2->SetGuidance("Number of grid cells in Y");
    fInitDoseGridCmd->SetParameter(p2);
    
    auto p3 = new G4UIparameter("nz", 'i', false);
    p3->SetGuidance("Number of grid cells in Z");
    fInitDoseGridCmd->SetParameter(p3);
    
    auto p4 = new G4UIparameter("xMin", 'd', false);
    p4->SetGuidance("Minimum X coordinate");
    fInitDoseGridCmd->SetParameter(p4);
    
    auto p5 = new G4UIparameter("xMax", 'd', false);
    p5->SetGuidance("Maximum X coordinate");
    fInitDoseGridCmd->SetParameter(p5);
    
    auto p6 = new G4UIparameter("yMin", 'd', false);
    p6->SetGuidance("Minimum Y coordinate");
    fInitDoseGridCmd->SetParameter(p6);
    
    auto p7 = new G4UIparameter("yMax", 'd', false);
    p7->SetGuidance("Maximum Y coordinate");
    fInitDoseGridCmd->SetParameter(p7);
    
    auto p8 = new G4UIparameter("zMin", 'd', false);
    p8->SetGuidance("Minimum Z coordinate");
    fInitDoseGridCmd->SetParameter(p8);
    
    auto p9 = new G4UIparameter("zMax", 'd', false);
    p9->SetGuidance("Maximum Z coordinate");
    fInitDoseGridCmd->SetParameter(p9);
    
    auto p10 = new G4UIparameter("unit", 's', false);
    p10->SetGuidance("Length unit");
    p10->SetDefaultValue("nm");
    fInitDoseGridCmd->SetParameter(p10);
    
    fInitDoseGridCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

DataMessenger::~DataMessenger() {
    delete fInitDoseGridCmd;
    delete fDataDir;
}

void DataMessenger::SetNewValue(G4UIcommand* command, G4String newValue) {
    if (command == fInitDoseGridCmd) {
        G4int nx, ny, nz;
        G4double xMin, xMax, yMin, yMax, zMin, zMax;
        G4String unit;
        
        std::istringstream is(newValue);
        is >> nx >> ny >> nz >> xMin >> xMax >> yMin >> yMax >> zMin >> zMax >> unit;
        
        // Convert to internal units
        G4double unitValue = G4UIcommand::ValueOf(unit);
        xMin *= unitValue;
        xMax *= unitValue;
        yMin *= unitValue;
        yMax *= unitValue;
        zMin *= unitValue;
        zMax *= unitValue;
        
        fDataManager->InitializeDoseGrid(nx, ny, nz, xMin, xMax, yMin, yMax, zMin, zMax);
    }
}