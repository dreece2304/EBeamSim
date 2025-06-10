// RunAction.hh
#ifndef RunAction_h
#define RunAction_h 1

#include "G4UserRunAction.hh"
#include "globals.hh"
#include <vector>
#include "G4Accumulable.hh"

class G4Run;
class DetectorConstruction;
class PrimaryGeneratorAction;

class RunAction : public G4UserRunAction {
public:
    RunAction(DetectorConstruction* detConstruction,
        PrimaryGeneratorAction* primaryGenerator);
    virtual ~RunAction();

    virtual void BeginOfRunAction(const G4Run*);
    virtual void EndOfRunAction(const G4Run*);

    // Methods to accumulate energy deposition data
    void AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z);
    void AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit);

    // Access methods for analysis
    std::vector<G4double> GetRadialEnergyProfile() const { return fRadialEnergyProfile; }

private:
    DetectorConstruction* fDetConstruction;
    PrimaryGeneratorAction* fPrimaryGenerator;

    // For energy deposition analysis
    std::vector<G4double> fRadialEnergyProfile;
    G4Accumulable<G4double> fTotalEnergyDeposit;
    G4int fNumEvents;

    // Helper functions for logarithmic binning
    G4double GetBinRadius(G4int bin) const;
    void GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const;

    // Analysis helpers
    void SaveResults();
    void SaveCSVFormat(const std::string& outputDir);
    void SaveBEAMERFormat(const std::string& outputDir);
    void SaveSummary(const std::string& outputDir);
};

#endif