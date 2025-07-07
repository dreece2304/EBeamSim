// SteppingAction.cc - Complete file with improved energy tracking
#include "SteppingAction.hh"
#include "EventAction.hh"
#include "DetectorConstruction.hh"

#include "G4Step.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include <map>

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

    // Get track information
    G4Track* track = step->GetTrack();
    G4double kinEnergy = track->GetKineticEnergy();
    G4ParticleDefinition* particle = track->GetDefinition();
    G4String particleName = particle->GetParticleName();

    // Adaptive threshold based on particle and energy
    G4double threshold = 0.0;  // Start with no threshold

    // Only filter very low energy deposits from low-energy secondaries
    if (particleName == "e-" && kinEnergy < 100*eV) {
        threshold = 0.01*eV;  // Filter only noise from very low energy electrons
    }
    else if (particleName == "gamma" && kinEnergy < 100*eV) {
        threshold = 0.1*eV;   // Slightly higher threshold for soft photons
    }

    // Skip steps with energy below threshold
    if (edep < threshold) return;

    // Get position - use midpoint for better accuracy
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
        static G4int farWarnings = 0;
        if (farWarnings < 10) {
            G4cout << "Warning: Energy deposit at very large radius: "
                << G4BestUnit(r, "Length") << " (particle: " << particleName
                << ", E=" << kinEnergy/keV << " keV) - skipping" << G4endl;
            farWarnings++;
        }
        return;
    }

    // Check if in sensitive region
    G4LogicalVolume* volume = step->GetPreStepPoint()->GetTouchableHandle()
                              ->GetVolume()->GetLogicalVolume();

    // Track energy by volume
    G4String volumeName = volume->GetName();
    static std::map<G4String, G4double> volumeEnergy;
    static std::map<G4String, G4int> volumeCounts;
    volumeEnergy[volumeName] += edep;
    volumeCounts[volumeName]++;

    // Enhanced statistics tracking
    static G4int totalSteps = 0;
    static G4int filteredSteps = 0;
    static G4int resistSteps = 0;
    static G4int substrateSteps = 0;
    static G4double totalEnergy = 0.0;
    static G4double filteredEnergy = 0.0;
    static std::map<G4String, G4double> particleEnergy;
    static std::map<G4String, G4int> particleCounts;

    totalSteps++;
    if (edep >= threshold) {
        filteredSteps++;
        filteredEnergy += edep;
    }
    totalEnergy += edep;
    particleEnergy[particleName] += edep;
    particleCounts[particleName]++;

    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (pos.z() >= 0 && pos.z() <= resistThickness) {
        resistSteps++;
    }
    else if (pos.z() < 0) {
        substrateSteps++;
    }

    // Periodic reporting
    if (totalSteps % 1000000 == 0) {
        G4cout << "\n=== Stepping Action Statistics ===" << G4endl;
        G4cout << "Total steps: " << totalSteps << G4endl;
        G4cout << "Filtered steps: " << filteredSteps
               << " (" << (100.0*filteredSteps/totalSteps) << "%)" << G4endl;
        G4cout << "Steps by region - Resist: " << resistSteps
               << ", Substrate: " << substrateSteps
               << ", Above: " << (totalSteps - resistSteps - substrateSteps) << G4endl;
        G4cout << "Total energy: " << G4BestUnit(totalEnergy, "Energy")
               << ", Filtered: " << G4BestUnit(filteredEnergy, "Energy")
               << " (" << (filteredEnergy/totalEnergy*100) << "%)" << G4endl;

        G4cout << "\nEnergy by volume:" << G4endl;
        for (const auto& ve : volumeEnergy) {
            G4cout << "  " << ve.first << ": " << G4BestUnit(ve.second, "Energy")
                   << " (" << volumeCounts[ve.first] << " steps)" << G4endl;
        }

        G4cout << "\nEnergy by particle type:" << G4endl;
        for (const auto& pe : particleEnergy) {
            G4cout << "  " << pe.first << ": " << G4BestUnit(pe.second, "Energy")
                   << " (" << particleCounts[pe.first] << " steps)" << G4endl;
        }
        G4cout << "==========================\n" << G4endl;
    }

    // Add energy deposit to event action
    fEventAction->AddEnergyDeposit(edep, pos.x(), pos.y(), pos.z());

    // Track length for diagnostics
    fEventAction->AddTrackLength(stepLength);
}