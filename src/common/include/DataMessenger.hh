// DataMessenger.hh
#ifndef DataMessenger_h
#define DataMessenger_h 1

#include "G4UImessenger.hh"
#include "globals.hh"

class DataManager;
class G4UIdirectory;
class G4UIcommand;

class DataMessenger: public G4UImessenger {
public:
    DataMessenger(DataManager* dataManager);
    virtual ~DataMessenger();
    
    virtual void SetNewValue(G4UIcommand*, G4String);
    
private:
    DataManager* fDataManager;
    
    G4UIdirectory* fDataDir;
    
    // Commands
    G4UIcommand* fInitDoseGridCmd;
};

#endif