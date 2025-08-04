// PatternMessenger.cc - Implementation of UI commands for pattern scanning
#include "PatternMessenger.hh"
#include "PrimaryGeneratorAction.hh"
#include "PatternGenerator.hh"
#include "SquarePatternGenerator.hh"
#include "JEOLParameters.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithAnInteger.hh"
#include "G4UIcmdWithAString.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWith3VectorAndUnit.hh"
#include "G4UIcmdWithoutParameter.hh"
#include "G4UIcmdWithADouble.hh"
#include "G4SystemOfUnits.hh"

PatternMessenger::PatternMessenger(PrimaryGeneratorAction* primaryGen)
    : G4UImessenger(),
      fPrimaryGenerator(primaryGen)
{
    // Pattern directory
    fPatternDirectory = new G4UIdirectory("/pattern/");
    fPatternDirectory->SetGuidance("Pattern scanning commands");
    
    // JEOL directory
    fJEOLDirectory = new G4UIdirectory("/pattern/jeol/");
    fJEOLDirectory->SetGuidance("JEOL-specific parameters");
    
    // Pattern type
    fPatternTypeCmd = new G4UIcmdWithAString("/pattern/type", this);
    fPatternTypeCmd->SetGuidance("Set pattern type");
    fPatternTypeCmd->SetGuidance("Available types: spot, square, line, rectangle, circle, array");
    fPatternTypeCmd->SetParameterName("type", false);
    fPatternTypeCmd->SetDefaultValue("square");
    fPatternTypeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Pattern size
    fPatternSizeCmd = new G4UIcmdWithADoubleAndUnit("/pattern/size", this);
    fPatternSizeCmd->SetGuidance("Set pattern size");
    fPatternSizeCmd->SetParameterName("size", false);
    fPatternSizeCmd->SetRange("size>0.");
    fPatternSizeCmd->SetUnitCategory("Length");
    fPatternSizeCmd->SetDefaultValue(1.0);
    fPatternSizeCmd->SetDefaultUnit("um");
    fPatternSizeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Pattern center
    fPatternCenterCmd = new G4UIcmdWith3VectorAndUnit("/pattern/center", this);
    fPatternCenterCmd->SetGuidance("Set pattern center position");
    fPatternCenterCmd->SetParameterName("x", "y", "z", false);
    fPatternCenterCmd->SetUnitCategory("Length");
    fPatternCenterCmd->SetDefaultUnit("nm");
    fPatternCenterCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Generate pattern
    fGeneratePatternCmd = new G4UIcmdWithoutParameter("/pattern/generate", this);
    fGeneratePatternCmd->SetGuidance("Generate pattern with current parameters");
    fGeneratePatternCmd->AvailableForStates(G4State_Idle);
    
    // Clear pattern
    fClearPatternCmd = new G4UIcmdWithoutParameter("/pattern/clear", this);
    fClearPatternCmd->SetGuidance("Clear current pattern");
    fClearPatternCmd->AvailableForStates(G4State_Idle);
    
    // EOS Mode
    fEOSModeCmd = new G4UIcmdWithAnInteger("/pattern/jeol/eosMode", this);
    fEOSModeCmd->SetGuidance("Set EOS mode (3: 4th lens, 6: 5th lens)");
    fEOSModeCmd->SetParameterName("mode", false);
    fEOSModeCmd->SetRange("mode==3 || mode==6");
    fEOSModeCmd->SetDefaultValue(3);
    fEOSModeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Shot pitch
    fShotPitchCmd = new G4UIcmdWithAnInteger("/pattern/jeol/shotPitch", this);
    fShotPitchCmd->SetGuidance("Set shot pitch (1 or even multiples of 2)");
    fShotPitchCmd->SetParameterName("pitch", false);
    fShotPitchCmd->SetRange("pitch>0");
    fShotPitchCmd->SetDefaultValue(4);
    fShotPitchCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Beam current
    fBeamCurrentCmd = new G4UIcmdWithADouble("/pattern/jeol/beamCurrent", this);
    fBeamCurrentCmd->SetGuidance("Set beam current in nA");
    fBeamCurrentCmd->SetParameterName("current", false);
    fBeamCurrentCmd->SetRange("current>0.");
    fBeamCurrentCmd->SetDefaultValue(2.0);
    fBeamCurrentCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Base dose
    fBaseDoseCmd = new G4UIcmdWithADouble("/pattern/jeol/baseDose", this);
    fBaseDoseCmd->SetGuidance("Set base dose in uC/cm^2");
    fBaseDoseCmd->SetParameterName("dose", false);
    fBaseDoseCmd->SetRange("dose>0.");
    fBaseDoseCmd->SetDefaultValue(400.0);
    fBaseDoseCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Shot rank for dose modulation
    fShotRankCmd = new G4UIcmdWithAnInteger("/pattern/jeol/shotRank", this);
    fShotRankCmd->SetGuidance("Set shot rank for dose modulation (0-255)");
    fShotRankCmd->SetParameterName("rank", false);
    fShotRankCmd->SetRange("rank>=0 && rank<=255");
    fShotRankCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Modulation value
    fModulationCmd = new G4UIcmdWithADouble("/pattern/jeol/modulation", this);
    fModulationCmd->SetGuidance("Set modulation factor for current shot rank");
    fModulationCmd->SetParameterName("factor", false);
    fModulationCmd->SetRange("factor>=0.");
    fModulationCmd->SetDefaultValue(1.0);
    fModulationCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Array parameters
    fArrayNxCmd = new G4UIcmdWithAnInteger("/pattern/array/nx", this);
    fArrayNxCmd->SetGuidance("Set number of patterns in X direction");
    fArrayNxCmd->SetParameterName("nx", false);
    fArrayNxCmd->SetRange("nx>0");
    fArrayNxCmd->SetDefaultValue(1);
    fArrayNxCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    fArrayNyCmd = new G4UIcmdWithAnInteger("/pattern/array/ny", this);
    fArrayNyCmd->SetGuidance("Set number of patterns in Y direction");
    fArrayNyCmd->SetParameterName("ny", false);
    fArrayNyCmd->SetRange("ny>0");
    fArrayNyCmd->SetDefaultValue(1);
    fArrayNyCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    fArrayPitchXCmd = new G4UIcmdWithADoubleAndUnit("/pattern/array/pitchX", this);
    fArrayPitchXCmd->SetGuidance("Set array pitch in X direction");
    fArrayPitchXCmd->SetParameterName("pitchX", false);
    fArrayPitchXCmd->SetRange("pitchX>0.");
    fArrayPitchXCmd->SetUnitCategory("Length");
    fArrayPitchXCmd->SetDefaultUnit("um");
    fArrayPitchXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    fArrayPitchYCmd = new G4UIcmdWithADoubleAndUnit("/pattern/array/pitchY", this);
    fArrayPitchYCmd->SetGuidance("Set array pitch in Y direction");
    fArrayPitchYCmd->SetParameterName("pitchY", false);
    fArrayPitchYCmd->SetRange("pitchY>0.");
    fArrayPitchYCmd->SetUnitCategory("Length");
    fArrayPitchYCmd->SetDefaultUnit("um");
    fArrayPitchYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
    
    // Beam mode
    fBeamModeCmd = new G4UIcmdWithAString("/pattern/beamMode", this);
    fBeamModeCmd->SetGuidance("Set beam mode: spot or pattern");
    fBeamModeCmd->SetParameterName("mode", false);
    fBeamModeCmd->SetCandidates("spot pattern");
    fBeamModeCmd->SetDefaultValue("spot");
    fBeamModeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

PatternMessenger::~PatternMessenger()
{
    delete fPatternDirectory;
    delete fJEOLDirectory;
    delete fPatternTypeCmd;
    delete fPatternSizeCmd;
    delete fPatternCenterCmd;
    delete fGeneratePatternCmd;
    delete fClearPatternCmd;
    delete fEOSModeCmd;
    delete fShotPitchCmd;
    delete fBeamCurrentCmd;
    delete fBaseDoseCmd;
    delete fShotRankCmd;
    delete fModulationCmd;
    delete fArrayNxCmd;
    delete fArrayNyCmd;
    delete fArrayPitchXCmd;
    delete fArrayPitchYCmd;
    delete fBeamModeCmd;
}

void PatternMessenger::SetNewValue(G4UIcommand* command, G4String newValue)
{
    // Static variables to store pattern parameters
    static PatternParameters patternParams;
    static G4int currentShotRank = 0;
    
    if (command == fPatternTypeCmd) {
        G4String type = newValue;
        if (type == "spot") patternParams.patternType = JEOL::Pattern::SINGLE_SPOT;
        else if (type == "square") patternParams.patternType = JEOL::Pattern::SQUARE;
        else if (type == "line") patternParams.patternType = JEOL::Pattern::LINE;
        else if (type == "rectangle") patternParams.patternType = JEOL::Pattern::RECTANGLE;
        else if (type == "circle") patternParams.patternType = JEOL::Pattern::CIRCLE;
        else if (type == "array") patternParams.patternType = JEOL::Pattern::ARRAY;
        else {
            G4cerr << "Unknown pattern type: " << type << G4endl;
        }
    }
    else if (command == fPatternSizeCmd) {
        patternParams.size = fPatternSizeCmd->GetNewDoubleValue(newValue);
    }
    else if (command == fPatternCenterCmd) {
        patternParams.centerPosition = fPatternCenterCmd->GetNew3VectorValue(newValue);
    }
    else if (command == fEOSModeCmd) {
        patternParams.eosMode = fEOSModeCmd->GetNewIntValue(newValue);
    }
    else if (command == fShotPitchCmd) {
        G4int pitch = fShotPitchCmd->GetNewIntValue(newValue);
        if (!JEOL::IsValidShotPitch(pitch)) {
            G4cerr << "Invalid shot pitch: " << pitch 
                   << ". Must be 1 or even multiple of 2." << G4endl;
            return;
        }
        patternParams.shotPitch = pitch;
    }
    else if (command == fBeamCurrentCmd) {
        patternParams.beamCurrent = fBeamCurrentCmd->GetNewDoubleValue(newValue);
    }
    else if (command == fBaseDoseCmd) {
        patternParams.baseDose = fBaseDoseCmd->GetNewDoubleValue(newValue);
    }
    else if (command == fShotRankCmd) {
        currentShotRank = fShotRankCmd->GetNewIntValue(newValue);
    }
    else if (command == fModulationCmd) {
        if (currentShotRank >= 0 && currentShotRank <= 255) {
            patternParams.modulationTable[currentShotRank] = 
                fModulationCmd->GetNewDoubleValue(newValue);
            G4cout << "Set modulation[" << currentShotRank << "] = " 
                   << patternParams.modulationTable[currentShotRank] << G4endl;
        }
    }
    else if (command == fArrayNxCmd) {
        patternParams.arrayNx = fArrayNxCmd->GetNewIntValue(newValue);
    }
    else if (command == fArrayNyCmd) {
        patternParams.arrayNy = fArrayNyCmd->GetNewIntValue(newValue);
    }
    else if (command == fArrayPitchXCmd) {
        patternParams.arrayPitchX = fArrayPitchXCmd->GetNewDoubleValue(newValue);
    }
    else if (command == fArrayPitchYCmd) {
        patternParams.arrayPitchY = fArrayPitchYCmd->GetNewDoubleValue(newValue);
    }
    else if (command == fGeneratePatternCmd) {
        fPrimaryGenerator->InitializePattern(patternParams);
    }
    else if (command == fClearPatternCmd) {
        fPrimaryGenerator->SetPatternGenerator(nullptr);
        fPrimaryGenerator->SetBeamMode(PrimaryGeneratorAction::SPOT_MODE);
        G4cout << "Pattern cleared, beam mode set to SPOT" << G4endl;
    }
    else if (command == fBeamModeCmd) {
        if (newValue == "spot") {
            fPrimaryGenerator->SetBeamMode(PrimaryGeneratorAction::SPOT_MODE);
        } else if (newValue == "pattern") {
            fPrimaryGenerator->SetBeamMode(PrimaryGeneratorAction::PATTERN_MODE);
        }
    }
}