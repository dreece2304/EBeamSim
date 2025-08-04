// SteppingAction.cc - Optimized for BEAMER PSF with efficient logging
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"
#include "DataManager.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include <chrono>
#include <cstdio>

SteppingAction::SteppingAction(EventAction* eventAction, DetectorConstruction* detConstruction)
    : G4UserSteppingAction(),
    fEventAction(eventAction),
    fDetConstruction(detConstruction),
    fScoringVolume(nullptr)
{
}

SteppingAction::~SteppingAction()
{
}

void SteppingAction::UserSteppingAction(const G4Step* step)
{
    // Get energy deposit in this step
    G4double edep = step->GetTotalEnergyDeposit();

    // Skip immediately if no energy deposited
    if (edep <= 0) return;

    // Get position FIRST before any other calculations
    G4ThreeVector pos = step->GetPreStepPoint()->GetPosition();

    // CRITICAL OPTIMIZATION: Check if in resist layer immediately
    // For BEAMER, we only care about energy in resist
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (pos.z() < 0 || pos.z() > resistThickness) {
        return;  // Skip all non-resist energy deposits
    }

    // Now we know we're in resist, proceed with calculations
    // Calculate radial distance from beam axis
    G4double r = std::sqrt(pos.x() * pos.x() + pos.y() * pos.y());

    // Skip if radius is beyond reasonable bounds
    const G4double maxRadius = 200.0 * micrometer;  // Slightly beyond PSF max
    if (r > maxRadius) {
        return;
    }

    // For BEAMER PSF, we don't filter any energy deposits in resist
    // Every bit of energy matters for accurate proximity correction

    // OPTIMIZED reporting - minimize hot-path output
    static G4long resistDeposits = 0;
    static G4double totalResistEnergy = 0.0;
    static auto lastReportTime = std::chrono::steady_clock::now();

    resistDeposits++;
    totalResistEnergy += edep;

    // MUCH LESS FREQUENT reporting for large simulations
    auto currentTime = std::chrono::steady_clock::now();
    auto timeDiff = std::chrono::duration_cast<std::chrono::seconds>(currentTime - lastReportTime).count();

    // Adaptive reporting interval based on deposit rate
    G4int reportInterval = 15;  // Default 15 seconds

    // For very active simulations, report less frequently
    if (resistDeposits > 100000) {
        reportInterval = 30;  // 30 seconds for high-activity sims
    }
    if (resistDeposits > 1000000) {
        reportInterval = 60;  // 1 minute for very high-activity sims
    }

    if (timeDiff >= reportInterval) {
        // Use printf for speed (no C++ stream formatting overhead)
        printf("Resist energy deposits: %ld, Total energy: %.3f MeV\n",
               resistDeposits, totalResistEnergy / CLHEP::MeV);
        fflush(stdout);
        lastReportTime = currentTime;
    }

    // Add energy deposit to event action
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());
    
    // If in pattern mode, also accumulate dose in grid
    DataManager* dataManager = DataManager::Instance();
    // Pattern mode is indicated by having a dose grid initialized (fNx > 0)
    if (dataManager->GetNx() > 0) {
        dataManager->AddDoseDeposit(pos, edep);
    }

    // Track length is not needed for BEAMER PSF
    // fEventAction->AddTrackLength(step->GetStepLength());
}