// EventAction.cc - BEAMER Optimized (radial PSF only)
#include "EventAction.hh"
#include "RunAction.hh"
#include "DetectorConstruction.hh"
#include "EBLConstants.hh"
#include "G4UnitsTable.hh"
#include "G4Event.hh"
#include "G4RunManager.hh"
#include "G4Run.hh"
#include "G4SystemOfUnits.hh"
#include "G4AnalysisManager.hh"
#include <cmath>

EventAction::EventAction(RunAction* runAction, DetectorConstruction* detConstruction)
    : G4UserEventAction(),
    fRunAction(runAction),
    fDetConstruction(detConstruction),
    fEnergyDeposit(0.),
    fTotalTrackLength(0.),
    fResistEnergy(0.),
    fSubstrateEnergy(0.),
    fAboveResistEnergy(0.)
{
    // Initialize the radial bins for energy deposition
    fRadialEnergyDeposit.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);

    // Skip 2D initialization for BEAMER mode
}

EventAction::~EventAction()
{
}

void EventAction::BeginOfEventAction(const G4Event* event)
{
    fEnergyDeposit = 0.;
    fTotalTrackLength = 0.;
    fResistEnergy = 0.;
    fSubstrateEnergy = 0.;
    fAboveResistEnergy = 0.;

    // Reset radial energy bins
    std::fill(fRadialEnergyDeposit.begin(), fRadialEnergyDeposit.end(), 0.0);

    // Minimal progress reporting for BEAMER efficiency
    G4int eventID = event->GetEventID();

    // Only report at major milestones to reduce overhead
    const G4Run* currentRun = G4RunManager::GetRunManager()->GetCurrentRun();
    G4int totalEvents = 0;
    if (currentRun) {
        totalEvents = currentRun->GetNumberOfEventToBeProcessed();
    }

    if (totalEvents > 0) {
        // Report at 0%, 10%, 20%, ..., 100%
        G4double currentPercent = 100.0 * eventID / totalEvents;
        static G4int lastReportedDecile = -1;
        G4int currentDecile = static_cast<G4int>(currentPercent / 10.0);

        if (currentDecile != lastReportedDecile) {
            lastReportedDecile = currentDecile;
            G4cout << "Processing event " << eventID << " - "
                   << (currentDecile * 10) << "% complete" << G4endl;
            G4cout << std::flush;
        }
    }
}

void EventAction::EndOfEventAction(const G4Event* event)
{
    // For BEAMER, we only care about resist energy
    // Pass accumulated energy data to run action
    if (fResistEnergy > 0) {
        fRunAction->AddRadialEnergyDeposit(fRadialEnergyDeposit);
        fRunAction->AddRegionEnergy(fResistEnergy, fSubstrateEnergy, fAboveResistEnergy);
    }

    // Skip verbose event reporting for efficiency
}

// Helper function for logarithmic binning
G4int EventAction::GetLogBin(G4double radius) const
{
    if (!EBL::PSF::USE_LOG_BINNING) {
        // Linear binning
        G4double bin_width = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        G4int bin = static_cast<G4int>(radius / bin_width);
        if (bin >= EBL::PSF::NUM_RADIAL_BINS) bin = EBL::PSF::NUM_RADIAL_BINS - 1;
        return bin;
    }

    // Logarithmic binning
    if (radius <= 0) return -1;
    if (radius < EBL::PSF::MIN_RADIUS) return 0;
    if (radius >= EBL::PSF::MAX_RADIUS) return EBL::PSF::NUM_RADIAL_BINS - 1;

    // Logarithmic binning: bin = log(r/r_min) / log(r_max/r_min) * n_bins
    G4double logRatio = std::log(radius / EBL::PSF::MIN_RADIUS) /
        std::log(EBL::PSF::MAX_RADIUS / EBL::PSF::MIN_RADIUS);
    G4int bin = static_cast<G4int>(logRatio * (EBL::PSF::NUM_RADIAL_BINS - 1));

    // Ensure bin is within valid range
    if (bin < 0) bin = 0;
    if (bin >= EBL::PSF::NUM_RADIAL_BINS) bin = EBL::PSF::NUM_RADIAL_BINS - 1;

    return bin;
}

G4double EventAction::GetBinRadius(G4int bin) const
{
    if (bin < 0) return 0.0;
    if (bin >= EBL::PSF::NUM_RADIAL_BINS) return EBL::PSF::MAX_RADIUS;

    if (!EBL::PSF::USE_LOG_BINNING) {
        // Linear binning
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        return (bin + 0.5) * binWidth;  // Return center of bin
    }

    // Logarithmic binning - calculate center of log bin
    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    // Get bin boundaries in log space
    G4double logLower = logMin + bin * logStep;
    G4double logUpper = logMin + (bin + 1) * logStep;
    G4double logCenter = (logLower + logUpper) / 2.0;

    return std::exp(logCenter);
}

G4int EventAction::GetDepthBin(G4double z) const
{
    // Not used in BEAMER mode
    return 0;
}

void EventAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // BEAMER OPTIMIZATION: We know this is already filtered for resist only
    // by SteppingAction, so we can skip validation

    // Accumulate total energy deposit
    fEnergyDeposit += edep;
    fResistEnergy += edep;  // All energy is in resist

    // Calculate radial distance from beam axis
    G4double r = std::sqrt(x * x + y * y);

    // Get logarithmic bin number for radius
    G4int radialBin = GetLogBin(r);

    // Add energy to radial bin
    if (radialBin >= 0 && radialBin < static_cast<G4int>(fRadialEnergyDeposit.size())) {
        fRadialEnergyDeposit[radialBin] += edep;
    }

    // Skip all debug output and statistics for production efficiency
}