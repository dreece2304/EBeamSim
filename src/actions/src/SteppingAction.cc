// SteppingAction.cc - Optimized for BEAMER PSF (resist-only energy scoring)
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include <chrono>

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

    // Get track information for debugging/validation only
    static G4long resistDeposits = 0;
    static G4double totalResistEnergy = 0.0;
    static auto lastReportTime = std::chrono::steady_clock::now();

    resistDeposits++;
    totalResistEnergy += edep;

    // Periodic reporting (every 5 seconds) to show progress without overhead
    auto currentTime = std::chrono::steady_clock::now();
    auto timeDiff = std::chrono::duration_cast<std::chrono::seconds>(currentTime - lastReportTime).count();

    if (timeDiff >= 5) {
        G4cout << "Resist energy deposits: " << resistDeposits
               << ", Total energy: " << G4BestUnit(totalResistEnergy, "Energy")
               << G4endl;
        lastReportTime = currentTime;
    }

    // Add energy deposit to event action
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());

    // Track length is not needed for BEAMER PSF
    // fEventAction->AddTrackLength(step->GetStepLength());
}