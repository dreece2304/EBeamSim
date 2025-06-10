// EventAction.cc
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

    // Initialize 2D array for depth-radius analysis
    f2DEnergyDeposit.resize(NUM_DEPTH_BINS);
    for (auto& depthBin : f2DEnergyDeposit) {
        depthBin.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);
    }
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

    // Reset 2D bins
    for (auto& depthBin : f2DEnergyDeposit) {
        std::fill(depthBin.begin(), depthBin.end(), 0.0);
    }

    // Improved progress reporting
    G4int eventID = event->GetEventID();

    // Get total events from run manager
    const G4Run* currentRun = G4RunManager::GetRunManager()->GetCurrentRun();
    G4int totalEvents = 0;
    if (currentRun) {
        totalEvents = currentRun->GetNumberOfEventToBeProcessed();
    }

    // Report progress at key intervals
    if (totalEvents > 0) {
        G4bool shouldReport = false;

        // Report at specific milestones
        if (eventID == 0) {
            shouldReport = true;
        }
        else if (eventID == totalEvents / 100 && eventID > 0) {  // 1%
            shouldReport = true;
        }
        else if (eventID == totalEvents * 2 / 100 && eventID > 0) {  // 2%
            shouldReport = true;
        }
        else if (eventID == totalEvents * 5 / 100 && eventID > 0) {  // 5%
            shouldReport = true;
        }
        else if (totalEvents >= 20 && eventID % (totalEvents / 20) == 0) {  // Every 5%
            shouldReport = true;
        }

        if (shouldReport) {
            G4double progress = 100.0 * eventID / totalEvents;
            G4cout << "\rProgress: " << std::fixed << std::setprecision(1)
                << progress << "% (" << eventID << "/" << totalEvents << " events)"
                << std::flush;
        }
    }
    else {
        // Fallback to simple progress reporting
        if (eventID < 10 || eventID % 10000 == 0) {
            G4cout << "Processing event " << eventID << G4endl;
        }
    }
}

void EventAction::EndOfEventAction(const G4Event* event)
{
    // Check if any energy was deposited in this event
    G4double totalEventEnergy = 0.0;
    G4int nonZeroBins = 0;
    for (size_t i = 0; i < fRadialEnergyDeposit.size(); i++) {
        if (fRadialEnergyDeposit[i] > 0) {
            totalEventEnergy += fRadialEnergyDeposit[i];
            nonZeroBins++;
        }
    }

    if (totalEventEnergy > 0) {
        G4int eventID = event->GetEventID();
        if (eventID < 10 || (eventID < 1000 && eventID % 100 == 0)) {
            G4cout << "Event " << eventID << " deposited "
                << G4BestUnit(totalEventEnergy, "Energy")
                << " in " << nonZeroBins << " radial bins" << G4endl;
            G4cout << "  Resist: " << G4BestUnit(fResistEnergy, "Energy")
                << ", Substrate: " << G4BestUnit(fSubstrateEnergy, "Energy")
                << ", Above: " << G4BestUnit(fAboveResistEnergy, "Energy") << G4endl;
        }
    }

    // Pass accumulated energy data to run action
    fRunAction->AddRadialEnergyDeposit(fRadialEnergyDeposit);
    fRunAction->Add2DEnergyDeposit(f2DEnergyDeposit);
    fRunAction->AddRegionEnergy(fResistEnergy, fSubstrateEnergy, fAboveResistEnergy);
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

G4int EventAction::GetDepthBin(G4double z) const
{
    // Define depth range: -50um to +150nm (covers substrate and above resist)
    const G4double minDepth = -50.0 * micrometer;
    const G4double maxDepth = 150.0 * nanometer;
    const G4double depthRange = maxDepth - minDepth;

    if (z < minDepth) return 0;
    if (z > maxDepth) return NUM_DEPTH_BINS - 1;

    G4int bin = static_cast<G4int>((z - minDepth) / depthRange * NUM_DEPTH_BINS);
    if (bin < 0) bin = 0;
    if (bin >= NUM_DEPTH_BINS) bin = NUM_DEPTH_BINS - 1;

    return bin;
}

void EventAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // Skip if no energy deposited
    if (edep <= 0) return;

    // Accumulate total energy deposit
    fEnergyDeposit += edep;

    // Calculate radial distance from beam axis (beam enters along z-axis)
    G4double r = std::sqrt(x * x + y * y);

    // Get logarithmic bin number for radius
    G4int radialBin = GetLogBin(r);

    // Get depth bin
    G4int depthBin = GetDepthBin(z);

    // Add energy to appropriate bins
    if (radialBin >= 0 && radialBin < static_cast<G4int>(fRadialEnergyDeposit.size())) {
        fRadialEnergyDeposit[radialBin] += edep;

        // Add to 2D histogram
        if (depthBin >= 0 && depthBin < NUM_DEPTH_BINS) {
            f2DEnergyDeposit[depthBin][radialBin] += edep;
        }
    }

    // Track energy by region
    G4double resistThickness = fDetConstruction->GetActualResistThickness();
    if (z >= 0 && z <= resistThickness) {
        fResistEnergy += edep;
    }
    else if (z < 0) {
        fSubstrateEnergy += edep;
    }
    else {
        fAboveResistEnergy += edep;
    }

    // Enhanced debug output for first few deposits
    static G4int debugCount = 0;
    if (debugCount < 50) {
        G4cout << "Energy deposit #" << debugCount << ": "
            << G4BestUnit(edep, "Energy") << " at r=" << G4BestUnit(r, "Length")
            << " z=" << G4BestUnit(z, "Length")
            << " (radial bin " << radialBin << ", depth bin " << depthBin << ")" << G4endl;
        debugCount++;
    }
}