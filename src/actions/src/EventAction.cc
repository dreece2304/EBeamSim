// EventAction.cc - BEAMER Optimized with efficient logging for large simulations + 2D Data
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
#include <cstdio>

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
    // Initialize the radial bins for energy deposition (1D - for BEAMER)
    fRadialEnergyDeposit.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);

    // RE-ENABLE 2D data collection for visualization
    f2DEnergyDeposit.resize(NUM_DEPTH_BINS);
    for (auto& radialBins : f2DEnergyDeposit) {
        radialBins.resize(NUM_RADIAL_BINS, 0.0);
    }

    G4cout << "EventAction initialized with:" << G4endl;
    G4cout << "  1D radial bins: " << EBL::PSF::NUM_RADIAL_BINS << " (for BEAMER PSF)" << G4endl;
    G4cout << "  2D bins: " << NUM_DEPTH_BINS << " x " << NUM_RADIAL_BINS << " (for visualization)" << G4endl;
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

    // Reset radial energy bins (1D)
    std::fill(fRadialEnergyDeposit.begin(), fRadialEnergyDeposit.end(), 0.0);

    // Reset 2D energy bins
    for (auto& radialBins : f2DEnergyDeposit) {
        std::fill(radialBins.begin(), radialBins.end(), 0.0);
    }

    // OPTIMIZED progress reporting for large simulations
    G4int eventID = event->GetEventID();

    const G4Run* currentRun = G4RunManager::GetRunManager()->GetCurrentRun();
    G4int totalEvents = 0;
    if (currentRun) {
        totalEvents = currentRun->GetNumberOfEventToBeProcessed();
    }

    if (totalEvents > 0) {
        // Adaptive reporting frequency to minimize I/O overhead
        G4int reportInterval;

        if (totalEvents <= 10000) {
            reportInterval = 1000;          // Every 1k events for small sims
        } else if (totalEvents <= 100000) {
            reportInterval = 5000;          // Every 5k events for medium sims
        } else if (totalEvents <= 1000000) {
            reportInterval = 25000;         // Every 25k events for large sims
        } else {
            reportInterval = 100000;        // Every 100k events for very large sims
        }

        // Only report at intervals (reduces I/O by 10-100x)
        if (eventID % reportInterval == 0 && eventID > 0) {
            G4double percent = 100.0 * eventID / totalEvents;

            // Use printf for faster output (no C++ stream overhead)
            printf("Processing event %d - %.1f%% complete\n", eventID, percent);
            fflush(stdout);  // Immediate flush only when needed
        }

        // Emergency progress report for very long gaps
        if (totalEvents > 1000000 && eventID % 500000 == 0 && eventID > 0) {
            printf(">>> Milestone: %d/%d events (%.1f%%)\n",
                   eventID, totalEvents, 100.0 * eventID / totalEvents);
            fflush(stdout);
        }
    }
}

void EventAction::EndOfEventAction(const G4Event* event)
{
    // Pass accumulated energy data to run action
    if (fResistEnergy > 0 || fSubstrateEnergy > 0 || fAboveResistEnergy > 0) {
        // 1D data for BEAMER PSF
        fRunAction->AddRadialEnergyDeposit(fRadialEnergyDeposit);

        // 2D data for visualization
        fRunAction->Add2DEnergyDeposit(f2DEnergyDeposit);

        // Region energy totals
        fRunAction->AddRegionEnergy(fResistEnergy, fSubstrateEnergy, fAboveResistEnergy);
    }

    // Skip verbose event reporting for efficiency
}

// Helper function for logarithmic binning (1D)
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

// 2D binning functions
G4int EventAction::GetDepthBin(G4double z) const
{
    // Get resist thickness
    G4double resistThickness = fDetConstruction->GetActualResistThickness();

    // For 2D visualization, we want to include some substrate
    G4double totalDepth = resistThickness + 50.0 * nanometer;  // 50 nm into substrate

    // Linear binning for depth
    if (z < -50.0 * nanometer) return 0;  // Deep substrate
    if (z > resistThickness) return NUM_DEPTH_BINS - 1;  // Above resist

    // Shift z so that z=0 (resist bottom) maps to bin ~50
    G4double shiftedZ = z + 50.0 * nanometer;
    G4double binWidth = totalDepth / NUM_DEPTH_BINS;
    G4int bin = static_cast<G4int>(shiftedZ / binWidth);

    if (bin < 0) bin = 0;
    if (bin >= NUM_DEPTH_BINS) bin = NUM_DEPTH_BINS - 1;

    return bin;
}

G4double EventAction::GetDepthBinCenter(G4int bin) const
{
    if (bin < 0 || bin >= NUM_DEPTH_BINS) return 0.0;

    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    G4double totalDepth = resistThickness + 50.0 * nanometer;
    G4double binWidth = totalDepth / NUM_DEPTH_BINS;

    // Convert back from shifted coordinates
    G4double shiftedZ = (bin + 0.5) * binWidth;
    return shiftedZ - 50.0 * nanometer;
}

void EventAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // Get resist boundaries
    G4double resistThickness = fDetConstruction->GetActualResistThickness();

    // Accumulate total energy deposit
    fEnergyDeposit += edep;

    // Classify by region
    if (z >= 0 && z <= resistThickness) {
        fResistEnergy += edep;
    } else if (z < 0) {
        fSubstrateEnergy += edep;
    } else {
        fAboveResistEnergy += edep;
    }

    // Calculate radial distance from beam axis
    G4double r = std::sqrt(x * x + y * y);

    // 1D radial binning (for BEAMER PSF) - ALL energy deposits
    G4int radialBin1D = GetLogBin(r);
    if (radialBin1D >= 0 && radialBin1D < static_cast<G4int>(fRadialEnergyDeposit.size())) {
        fRadialEnergyDeposit[radialBin1D] += edep;
    }

    // 2D binning (for visualization) - ALL energy deposits
    G4int depthBin = GetDepthBin(z);

    // For 2D, use linear radial binning to match typical 2D visualization
    G4double maxRadius2D = 50.0 * micrometer;  // Reasonable max for 2D viz
    G4int radialBin2D = static_cast<G4int>((r / maxRadius2D) * NUM_RADIAL_BINS);
    if (radialBin2D >= NUM_RADIAL_BINS) radialBin2D = NUM_RADIAL_BINS - 1;

    if (depthBin >= 0 && depthBin < NUM_DEPTH_BINS &&
        radialBin2D >= 0 && radialBin2D < NUM_RADIAL_BINS) {
        f2DEnergyDeposit[depthBin][radialBin2D] += edep;
    }

    // Skip all debug output and statistics for production efficiency
}