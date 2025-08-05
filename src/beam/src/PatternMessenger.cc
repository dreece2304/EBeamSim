// PatternMessenger.cc
#include "PatternMessenger.hh"
#include "PrimaryGeneratorAction.hh"
#include "PatternGenerator.hh"
#include "DataManager.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithABool.hh"
#include "G4UIcmdWithAString.hh"
#include "G4UIcmdWithAnInteger.hh"
#include "G4UIcmdWithADouble.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWith3VectorAndUnit.hh"
#include "G4UIcommand.hh"
#include "G4SystemOfUnits.hh"

PatternMessenger::PatternMessenger(PrimaryGeneratorAction* primaryGen)
    : G4UImessenger(),
      fPrimaryGenerator(primaryGen),
      fPatternGenerator(primaryGen->GetPatternGenerator()) {
    
    fPatternDir = new G4UIdirectory("/pattern/");
    fPatternDir->SetGuidance("Pattern exposure control commands");
    
    // Enable/disable pattern mode
    fEnablePatternCmd = new G4UIcmdWithABool("/pattern/enable", this);
    fEnablePatternCmd->SetGuidance("Enable/disable pattern exposure mode");
    fEnablePatternCmd->SetParameterName("enable", false);
    fEnablePatternCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Pattern type
    fPatternTypeCmd = new G4UIcmdWithAString("/pattern/type", this);
    fPatternTypeCmd->SetGuidance("Set pattern type");
    fPatternTypeCmd->SetGuidance("  Choices: single_spot, square, line, custom");
    fPatternTypeCmd->SetParameterName("type", false);
    fPatternTypeCmd->SetCandidates("single_spot square line custom");
    fPatternTypeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // JEOL mode
    fJEOLModeCmd = new G4UIcmdWithAString("/pattern/jeolMode", this);
    fJEOLModeCmd->SetGuidance("Set JEOL operating mode");
    fJEOLModeCmd->SetGuidance("  Choices: mode3, mode6");
    fJEOLModeCmd->SetParameterName("mode", false);
    fJEOLModeCmd->SetCandidates("mode3 mode6");
    fJEOLModeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Shot pitch
    fShotPitchCmd = new G4UIcmdWithAnInteger("/pattern/shotPitch", this);
    fShotPitchCmd->SetGuidance("Set shot pitch (multiple of machine grid)");
    fShotPitchCmd->SetGuidance("Must be 1 or even number (2, 4, 6, ...)");
    fShotPitchCmd->SetParameterName("pitch", false);
    fShotPitchCmd->SetRange("pitch>=1");
    fShotPitchCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Pattern size
    fPatternSizeCmd = new G4UIcmdWithADoubleAndUnit("/pattern/size", this);
    fPatternSizeCmd->SetGuidance("Set pattern size (for square pattern)");
    fPatternSizeCmd->SetParameterName("size", false);
    fPatternSizeCmd->SetRange("size>0.");
    fPatternSizeCmd->SetUnitCategory("Length");
    fPatternSizeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Pattern center
    fPatternCenterCmd = new G4UIcmdWith3VectorAndUnit("/pattern/center", this);
    fPatternCenterCmd->SetGuidance("Set pattern center position");
    fPatternCenterCmd->SetParameterName("X", "Y", "Z", false);
    fPatternCenterCmd->SetUnitCategory("Length");
    fPatternCenterCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Beam current
    fBeamCurrentCmd = new G4UIcmdWithADoubleAndUnit("/pattern/beamCurrent", this);
    fBeamCurrentCmd->SetGuidance("Set beam current in nA");
    fBeamCurrentCmd->SetParameterName("current", false);
    fBeamCurrentCmd->SetRange("current>0.");
    fBeamCurrentCmd->SetDefaultUnit("nA");
    fBeamCurrentCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Dose - using G4UIcmdWithADouble instead of G4UIcmdWithADoubleAndUnit
    // since uC/cm2 is not a standard Geant4 unit
    fDoseCmd = new G4UIcmdWithADouble("/pattern/dose", this);
    fDoseCmd->SetGuidance("Set exposure dose in uC/cm2 (value only, no unit)");
    fDoseCmd->SetParameterName("dose", false);
    fDoseCmd->SetRange("dose>0.");
    fDoseCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Generate pattern command
    fGeneratePatternCmd = new G4UIcommand("/pattern/generate", this);
    fGeneratePatternCmd->SetGuidance("Generate pattern with current settings");
    fGeneratePatternCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

PatternMessenger::~PatternMessenger() {
    delete fEnablePatternCmd;
    delete fPatternTypeCmd;
    delete fJEOLModeCmd;
    delete fShotPitchCmd;
    delete fPatternSizeCmd;
    delete fPatternCenterCmd;
    delete fBeamCurrentCmd;
    delete fDoseCmd;
    delete fGeneratePatternCmd;
    delete fPatternDir;
}

void PatternMessenger::SetNewValue(G4UIcommand* command, G4String newValue) {
    if (command == fEnablePatternCmd) {
        fPrimaryGenerator->SetPatternMode(fEnablePatternCmd->GetNewBoolValue(newValue));
        
        // Also update DataManager
        DataManager* dm = DataManager::Instance();
        dm->EnablePatternMode(fEnablePatternCmd->GetNewBoolValue(newValue));
        
    } else if (command == fPatternTypeCmd) {
        if (newValue == "single_spot") {
            fPatternGenerator->SetPatternType(PatternGenerator::SINGLE_SPOT);
        } else if (newValue == "square") {
            fPatternGenerator->SetPatternType(PatternGenerator::SQUARE);
        } else if (newValue == "line") {
            fPatternGenerator->SetPatternType(PatternGenerator::LINE);
        } else if (newValue == "custom") {
            fPatternGenerator->SetPatternType(PatternGenerator::CUSTOM);
        }
        
    } else if (command == fJEOLModeCmd) {
        if (newValue == "mode3") {
            fPatternGenerator->SetJEOLMode(PatternGenerator::MODE_3_4TH_LENS);
        } else if (newValue == "mode6") {
            fPatternGenerator->SetJEOLMode(PatternGenerator::MODE_6_5TH_LENS);
        }
        
    } else if (command == fShotPitchCmd) {
        fPatternGenerator->SetShotPitch(fShotPitchCmd->GetNewIntValue(newValue));
        
    } else if (command == fPatternSizeCmd) {
        fPatternGenerator->SetPatternSize(fPatternSizeCmd->GetNewDoubleValue(newValue));
        
    } else if (command == fPatternCenterCmd) {
        fPatternGenerator->SetPatternCenter(fPatternCenterCmd->GetNew3VectorValue(newValue));
        
    } else if (command == fBeamCurrentCmd) {
        // Convert to nA
        G4double current = fBeamCurrentCmd->GetNewDoubleValue(newValue);
        G4double currentNa = current / (1.0e-9 * ampere);  // Convert to nA
        fPatternGenerator->SetBeamCurrent(currentNa);
        
        // Also update DataManager
        DataManager::Instance()->SetBeamCurrent(currentNa);
        
    } else if (command == fDoseCmd) {
        // Get dose value directly (no unit conversion needed)
        G4double dose = fDoseCmd->GetNewDoubleValue(newValue);
        fPatternGenerator->SetDose(dose);
        
    } else if (command == fGeneratePatternCmd) {
        fPatternGenerator->GeneratePattern();
        G4cout << "Pattern generated with " << fPatternGenerator->GetTotalPoints() 
               << " exposure points" << G4endl;
        
        // Update DataManager with pattern information
        DataManager* dm = DataManager::Instance();
        dm->SetElectronsPerPoint(fPatternGenerator->GetElectronsPerPoint());
        dm->SetTotalPatternPoints(fPatternGenerator->GetTotalPoints());
    }
}