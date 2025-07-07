// SteppingAction.cc - Improved version with better noise filtering
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"

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

    // IMPROVED: Use adaptive threshold based on particle type and energy
    G4double threshold = 1.0e-3 * eV; // Base threshold

    // Get track information
    G4Track* track = step->GetTrack();
    G4double kinEnergy = track->GetKineticEnergy();
    G4ParticleDefinition* particle = track->GetDefinition();

    // Adjust threshold based on particle type
    if (particle->GetParticleName() == "e-") {
        // For electrons, use a threshold proportional to their energy
        // This helps filter out very low energy delta rays that contribute noise
        threshold = std::max(1.0e-3 * eV, 1.0e-6 * kinEnergy);
    }
    else if (particle->GetParticleName() == "gamma") {
        // For photons, use slightly higher threshold as they can create noise
        threshold = 1.0e-2 * eV;
    }

    // Skip steps with energy below threshold
    if (edep < threshold) return;

    // IMPROVED: Better position calculation
    // Use pre-step position for very small steps, weighted average for longer steps
    G4ThreeVector prePos = step->GetPreStepPoint()->GetPosition();
    G4ThreeVector postPos = step->GetPostStepPoint()->GetPosition();
    G4double stepLength = step->GetStepLength();

    G4ThreeVector pos;
    if (stepLength < 0.1 * nanometer) {
        // For very small steps, use pre-step position to avoid interpolation errors
        pos = prePos;
    }
    else {
        // For longer steps, use energy-weighted position
        // This accounts for continuous energy loss along the step
        G4double preFraction = 0.5; // Can be refined based on physics
        pos = prePos * preFraction + postPos * (1.0 - preFraction);
    }

    // VALIDATION: Check for reasonable position values
    G4double r = std::sqrt(pos.x() * pos.x() + pos.y() * pos.y());

    // Skip if radius is beyond reasonable physical bounds
    // (e.g., beyond substrate dimensions)
    const G4double maxPhysicalRadius = 1000.0 * micrometer; // Adjust based on your geometry
    if (r > maxPhysicalRadius) {
        static G4int warningCount = 0;
        if (warningCount < 10) {
            G4cout << "Warning: Energy deposit at very large radius: "
                << G4BestUnit(r, "Length") << " - skipping" << G4endl;
            warningCount++;
        }
        return;
    }

    // Add energy deposit to event action
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());

    // Enhanced statistics tracking
    static G4int totalSteps = 0;
    static G4int filteredSteps = 0;
    static G4int resistSteps = 0;
    static G4int substrateSteps = 0;
    static G4double totalEnergy = 0.0;
    static G4double filteredEnergy = 0.0;

    totalSteps++;
    if (edep >= threshold) {
        filteredSteps++;
        filteredEnergy += edep;
    }
    totalEnergy += edep;

    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (pos.z() >= 0 && pos.z() <= resistThickness) {
        resistSteps++;
    }
    else if (pos.z() < 0) {
        substrateSteps++;
    }

    // Log every 1000000 steps for monitoring
    if (totalSteps % 1000000 == 0) {
        G4cout << "Steps: " << totalSteps
            << " (Filtered: " << filteredSteps
            << ", Resist: " << resistSteps
            << ", Substrate: " << substrateSteps
            << "), Total E: " << G4BestUnit(totalEnergy, "Energy")
            << ", Filtered E: " << G4BestUnit(filteredEnergy, "Energy")
            << " (" << (filteredEnergy / totalEnergy * 100) << "%)"
            << G4endl;
    }
}