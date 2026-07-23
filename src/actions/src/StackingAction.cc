// StackingAction.cc - Track killing for BEAMER efficiency with optimized reporting
#include "StackingAction.hh"
#include "DetectorConstruction.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4RunManager.hh"
#include <cstdio>

StackingAction::StackingAction(DetectorConstruction* detector)
    : G4UserStackingAction(),
      fDetector(detector),
      fResistTop(0),
      fResistBottom(0),
      fKillEnergyThreshold(10*eV),  // Only kill extremely low energy particles
      fKilledTracks(0),
      fTotalTracks(0),
      fEventNumber(0)
{
    // Get resist dimensions
    if (fDetector) {
        fResistTop = fDetector->GetActualResistThickness();
        fResistBottom = 0.0;
    }
}

StackingAction::~StackingAction()
{
    // Report final statistics
    if (fTotalTracks > 0) {
        printf("\n=== StackingAction Final Statistics ===\n");
        printf("Total tracks: %d\n", fTotalTracks);
        printf("Killed tracks: %d\n", fKilledTracks);
        printf("Kill rate: %.1f%%\n", (100.0 * fKilledTracks / fTotalTracks));
        printf("======================================\n");
        fflush(stdout);
    }
}

G4ClassificationOfNewTrack StackingAction::ClassifyNewTrack(const G4Track* track)
{
    fTotalTracks++;

    // Get track properties
    G4double z = track->GetPosition().z();
    G4double energy = track->GetKineticEnergy();
    G4ParticleDefinition* particle = track->GetDefinition();
    G4String particleName = particle->GetParticleName();

    // BEAMER optimization: Kill tracks that won't contribute to resist energy

    // 1. Kill very low energy electrons VERY deep in substrate (more conservative)
    if (particleName == "e-" && z < -50*micrometer && energy < 100*eV) {
        fKilledTracks++;
        return fKill;
    }

    // 2. Kill low energy particles far above resist
    if (z > fResistTop + 1*micrometer && energy < fKillEnergyThreshold) {
        fKilledTracks++;
        return fKill;
    }

    // 3. Kill very low energy photons anywhere (they won't reach resist)
    if (particleName == "gamma" && energy < 10*eV) {
        fKilledTracks++;
        return fKill;
    }

    // 4. Handle backscattered electrons carefully - they contribute to PSF tails
    if (particleName == "e-") {
        G4ThreeVector momentum = track->GetMomentumDirection();

        // IMPORTANT: Backscattered electrons (moving upward from substrate)
        if (z < 0 && momentum.z() > 0 && energy > 1*keV) {
            // This is likely a backscattered electron - process immediately!
            return fUrgent;  // High priority for backscattered electrons
        }

        // If very deep in substrate and moving downward with very low energy
        if (z < -20*micrometer && momentum.z() < 0 && energy < 500*eV) {
            fKilledTracks++;
            return fKill;
        }

        // If far above resist and moving upward with very low energy
        if (z > fResistTop + 5*micrometer && momentum.z() > 0 && energy < 100*eV) {
            fKilledTracks++;
            return fKill;
        }
    }

    // 5. Range-based killing: estimate if particle can reach resist (more conservative)
    if (particleName == "e-" && energy < 1*keV) {  // Only apply to very low energy electrons
        // Rough estimate of electron range in silicon
        // R ~= 0.4 * E^1.75 (R in um, E in keV)
        G4double energyKeV = energy / keV;
        G4double estimatedRange = 0.4 * std::pow(energyKeV, 1.75) * micrometer;

        // If in substrate and definitely can't reach resist (with safety factor)
        if (z < 0 && std::abs(z) > estimatedRange * 2.0 + 1*micrometer) {
            fKilledTracks++;
            return fKill;
        }

        // If above resist and definitely can't reach back (with safety factor)
        if (z > fResistTop && (z - fResistTop) > estimatedRange * 2.0) {
            fKilledTracks++;
            return fKill;
        }
    }

    // OPTIMIZED statistics reporting - much less frequent for large simulations
    G4long reportInterval;
    if (fTotalTracks < 1000000) {
        reportInterval = 100000;      // Every 100k tracks initially
    } else if (fTotalTracks < 10000000) {
        reportInterval = 500000;      // Every 500k tracks for medium load
    } else {
        reportInterval = 1000000;     // Every 1M tracks for high load
    }

    if (fTotalTracks % reportInterval == 0) {
        G4double killRate = 100.0 * fKilledTracks / fTotalTracks;
        printf("StackingAction: Processed %d tracks, killed %.1f%%\n",
               fTotalTracks, killRate);
        fflush(stdout);
    }

    // Track all others urgently
    return fUrgent;
}

void StackingAction::NewStage()
{
    // Called when urgent stack becomes empty
    // Can be used for stage-by-stage processing
}

void StackingAction::PrepareNewEvent()
{
    // Reset event-level counters if needed
    fEventNumber++;

    // Update resist thickness in case it changed
    if (fDetector) {
        fResistTop = fDetector->GetActualResistThickness();
    }
}