// EventAction.cc
#include "EventAction.hh"
#include "RunAction.hh"
#include "DetectorConstruction.hh"
#include "EBLConstants.hh"
#include "G4UnitsTable.hh"
#include "G4Event.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4AnalysisManager.hh"
#include <cmath>

EventAction::EventAction(RunAction* runAction, DetectorConstruction* detConstruction)
: G4UserEventAction(),
  fRunAction(runAction),
  fDetConstruction(detConstruction),
  fEnergyDeposit(0.),
  fTotalTrackLength(0.)
{
    // Initialize the radial bins for energy deposition
    fRadialEnergyDeposit.resize(EBL::PSF::NUM_RADIAL_BINS, 0.0);
}

EventAction::~EventAction()
{}

void EventAction::BeginOfEventAction(const G4Event* event)
{
    fEnergyDeposit = 0.;
    fTotalTrackLength = 0.;

    // Reset radial energy bins
    std::fill(fRadialEnergyDeposit.begin(), fRadialEnergyDeposit.end(), 0.0);

    // Print progress for first few events and every 10000 events
    G4int eventID = event->GetEventID();
    if (eventID < 10 || eventID % 10000 == 0) {
        G4cout << "Processing event " << eventID << G4endl;
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
                   << " in " << nonZeroBins << " bins" << G4endl;
        }
    }

    // Pass accumulated energy and track data to run action
    fRunAction->AddRadialEnergyDeposit(fRadialEnergyDeposit);
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

void EventAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // Skip if no energy deposited
    if (edep <= 0) return;

    // Accumulate total energy deposit
    fEnergyDeposit += edep;

    // Calculate radial distance from beam axis (beam enters along z-axis)
    G4double r = std::sqrt(x*x + y*y);

    // Get logarithmic bin number
    G4int bin = GetLogBin(r);

    // Add energy to appropriate radial bin
    if (bin >= 0 && bin < static_cast<G4int>(fRadialEnergyDeposit.size())) {
        fRadialEnergyDeposit[bin] += edep;

        // Enhanced debug output for first few deposits
        static G4int debugCount = 0;
        if (debugCount < 20) {  // Show more debug info
            G4cout << "Energy deposit #" << debugCount << ": "
                   << G4BestUnit(edep, "Energy") << " at r=" << G4BestUnit(r, "Length")
                   << " z=" << G4BestUnit(z, "Length")
                   << " (log bin " << bin << ")" << G4endl;
            debugCount++;
        }

        // Special logging for very close deposits (important for PSF peak)
        static G4int closeDepositCount = 0;
        if (r < 10*nanometer && closeDepositCount < 10) {
            G4cout << "Close deposit: " << G4BestUnit(edep, "Energy")
                   << " at r=" << r/nanometer << " nm (bin " << bin << ")" << G4endl;
            closeDepositCount++;
        }
    }
}
