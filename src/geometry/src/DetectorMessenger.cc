// DetectorMessenger.cc
#include "DetectorMessenger.hh"
#include "DetectorConstruction.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWithADouble.hh"
#include "G4UIcmdWithAString.hh"
#include "G4UIcmdWithoutParameter.hh"
#include "G4SystemOfUnits.hh"
#include "G4RunManager.hh"

DetectorMessenger::DetectorMessenger(DetectorConstruction* detector)
: G4UImessenger(),
  fDetector(detector)
{
    // Create directories for UI commands
    fDetDirectory = new G4UIdirectory("/det/");
    fDetDirectory->SetGuidance("Detector construction control commands.");

    // Commands
    fThicknessCmd = new G4UIcmdWithADoubleAndUnit("/det/setResistThickness", this);
    fThicknessCmd->SetGuidance("Set the resist thickness.");
    fThicknessCmd->SetParameterName("Thickness", false);
    fThicknessCmd->SetRange("Thickness>0.");
    fThicknessCmd->SetUnitCategory("Length");
    fThicknessCmd->SetDefaultUnit("nm");
    fThicknessCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fDensityCmd = new G4UIcmdWithAString("/det/setResistDensity", this);
    fDensityCmd->SetGuidance("Set the resist density (e.g., '1.35 g/cm3').");
    fDensityCmd->SetParameterName("Density", false);
    fDensityCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fCompositionCmd = new G4UIcmdWithAString("/det/setResistComposition", this);
    fCompositionCmd->SetGuidance("Set the resist composition in format 'Al:1,C:5,H:4,O:2'.");
    fCompositionCmd->SetParameterName("Composition", false);
    fCompositionCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

    fUpdateCmd = new G4UIcmdWithoutParameter("/det/update", this);
    fUpdateCmd->SetGuidance("Update detector geometry after parameter changes.");
    fUpdateCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

DetectorMessenger::~DetectorMessenger()
{
    delete fThicknessCmd;
    delete fDensityCmd;
    delete fCompositionCmd;
    delete fUpdateCmd;
    delete fDetDirectory;
}

void DetectorMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    if (command == fThicknessCmd) {
        fDetector->SetResistThickness(fThicknessCmd->GetNewDoubleValue(newValue));
    }
    else if (command == fDensityCmd) {
        // Parse density with units (e.g., "1.35 g/cm3")
        std::istringstream iss(newValue);
        G4double value;
        G4String unit;
        iss >> value >> unit;

        G4double density = value * (g/cm3);  // Assume g/cm3 for now
        fDetector->SetResistDensity(density);
    }
    else if (command == fCompositionCmd) {
        // Remove quotes if present
        G4String composition = newValue;

        // Remove leading and trailing quotes
        if (static_cast<G4int>(composition.length()) >= 2) {
            if (composition[0] == '"' && composition[static_cast<G4int>(composition.length())-1] == '"') {
                composition = composition.substr(1, static_cast<G4int>(composition.length())-2);
            }
        }

        // Also remove single quotes if used
        if (static_cast<G4int>(composition.length()) >= 2) {
            if (composition[0] == '\'' && composition[static_cast<G4int>(composition.length())-1] == '\'') {
                composition = composition.substr(1, static_cast<G4int>(composition.length())-2);
            }
        }

        G4cout << "Setting resist composition to: " << composition << G4endl;
        fDetector->SetResistComposition(composition);
    }
    else if (command == fUpdateCmd) {
        // Force geometry update
        G4RunManager::GetRunManager()->GeometryHasBeenModified();
        G4cout << "Detector geometry updated." << G4endl;
    }
}