#include "RunAction.hh"
#include "PrimaryGeneratorAction.hh"
#include "DetectorConstruction.hh"
#include "G4Run.hh"
#include "G4AccumulableManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <cmath>
#include "EBLConstants.hh"

RunAction::RunAction(DetectorConstruction* detConstruction,
                     PrimaryGeneratorAction* primaryGenerator)
: G4UserRunAction(),
  fDetConstruction(detConstruction),
  fPrimaryGenerator(primaryGenerator),
  fTotalEnergyDeposit("TotalEnergyDeposit", 0.0),
  fNumEvents(0)
{
    // Initialize vectors for scoring
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.resize(numBins, 0.0);

    // Register this class to the accumulation manager
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Register(fTotalEnergyDeposit);
}

RunAction::~RunAction()
{
}

// Helper function to get radius for logarithmic bin
G4double RunAction::GetBinRadius(G4int bin) const
{
    if (bin < 0) return 0.0;
    if (bin >= EBL::PSF::NUM_RADIAL_BINS) return EBL::PSF::MAX_RADIUS;

    if (!EBL::PSF::USE_LOG_BINNING) {
        // Linear binning
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        return (bin + 0.5) * binWidth;
    }

    // Logarithmic binning - calculate center of log bin
    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    // Get bin boundaries
    G4double logLower = logMin + bin * logStep;
    G4double logUpper = logMin + (bin + 1) * logStep;
    G4double logCenter = (logLower + logUpper) / 2.0;

    return std::exp(logCenter);
}

// Get bin boundaries for area calculation
void RunAction::GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const
{
    if (!EBL::PSF::USE_LOG_BINNING) {
        // Linear binning
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        rInner = bin * binWidth;
        rOuter = (bin + 1) * binWidth;
        return;
    }

    // Logarithmic binning
    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    if (bin == 0) {
        rInner = 0.0;  // First bin includes center
        rOuter = std::exp(logMin + logStep);
    } else if (bin < EBL::PSF::NUM_RADIAL_BINS) {
        rInner = std::exp(logMin + bin * logStep);
        rOuter = std::exp(logMin + (bin + 1) * logStep);
    } else {
        rInner = EBL::PSF::MAX_RADIUS;
        rOuter = EBL::PSF::MAX_RADIUS;
    }
}

void RunAction::BeginOfRunAction(const G4Run* run)
{
    G4cout << "### Run " << run->GetRunID() << " start." << G4endl;
    G4cout << "### Using logarithmic binning: "
           << EBL::PSF::NUM_RADIAL_BINS << " bins from "
           << G4BestUnit(EBL::PSF::MIN_RADIUS, "Length") << " to "
           << G4BestUnit(EBL::PSF::MAX_RADIUS, "Length") << G4endl;

    // Reset accumulables
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Reset();

    // Reset the radial energy profile
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.assign(numBins, 0.0);

    // Reset event counter
    fNumEvents = 0;
}

void RunAction::EndOfRunAction(const G4Run* run)
{
    G4int nofEvents = run->GetNumberOfEvent();
    if (nofEvents == 0) return;

    // Merge accumulables
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Merge();

    // Save results
    SaveResults();

    // Print results
    G4cout << "\n--------------------End of Run------------------------------\n"
           << " The run consists of " << nofEvents << " events" << G4endl;

    G4cout << " Total energy deposited in resist: "
           << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << G4endl;
}

void RunAction::AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit)
{
    // Make sure sizes match
    if (energyDeposit.size() != fRadialEnergyProfile.size()) {
        G4cerr << "Error: Size mismatch in AddRadialEnergyDeposit" << G4endl;
        return;
    }

    // Add deposits to profile AND update total energy
    G4double eventTotalEnergy = 0.0;
    for (size_t i = 0; i < fRadialEnergyProfile.size(); i++) {
        fRadialEnergyProfile[i] += energyDeposit[i];
        eventTotalEnergy += energyDeposit[i];
    }

    // Update the total energy accumulator
    fTotalEnergyDeposit += eventTotalEnergy;

    fNumEvents++;
}

void RunAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    // This method is not used when EventAction handles binning
    // But kept for compatibility
    fTotalEnergyDeposit += edep;
}

void RunAction::SaveResults()
{
    G4cout << "=== Saving Results ===" << G4endl;
    G4cout << "Number of events processed: " << fNumEvents << G4endl;
    G4cout << "Total energy deposited: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << G4endl;

    // Ensure output directory exists
    std::string outputDir = EBL::Output::DEFAULT_DIRECTORY;
    if (!outputDir.empty()) {
        try {
            std::filesystem::create_directories(outputDir);
        } catch (const std::exception& e) {
            G4cout << "Warning: Could not create output directory: " << e.what() << G4endl;
            outputDir = "";
        }
    }

    // Save standard CSV format
    SaveCSVFormat(outputDir);

    // Save BEAMER format
    SaveBEAMERFormat(outputDir);

    // Save summary
    SaveSummary(outputDir);
}

void RunAction::SaveCSVFormat(const std::string& outputDir)
{
    std::string outputPath = outputDir.empty() ?
        std::string(EBL::Output::DEFAULT_FILENAME) :
        outputDir + "/" + std::string(EBL::Output::DEFAULT_FILENAME);

    G4cout << "Saving PSF data to: " << outputPath << G4endl;

    std::ofstream psfFile(outputPath);
    if (!psfFile.is_open()) {
        G4cerr << "Error: Could not open output file: " << outputPath << G4endl;
        return;
    }

    // Write header
    psfFile << "Radius(nm),EnergyDeposition(eV/nm^2),BinLower(nm),BinUpper(nm),Events" << std::endl;

    G4int validBins = 0;
    G4double totalEnergy = 0.0;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (fRadialEnergyProfile[i] > 0) {
            validBins++;
            totalEnergy += fRadialEnergyProfile[i];
        }

        G4double rCenter = GetBinRadius(i);
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);

        // Calculate annular area for this bin
        G4double area = CLHEP::pi * (rOuter*rOuter - rInner*rInner);

        // Calculate energy density per unit area per event
        G4double energyDensity = (area > 0 && fNumEvents > 0) ?
            fRadialEnergyProfile[i] / (area * fNumEvents) : 0.0;

        // Output with full precision for analysis
        psfFile << std::fixed << std::setprecision(3) << rCenter/nanometer << ","
                << std::scientific << std::setprecision(6) << energyDensity/(eV/(nanometer*nanometer)) << ","
                << std::fixed << std::setprecision(3) << rInner/nanometer << ","
                << rOuter/nanometer << ","
                << fNumEvents
                << std::endl;
    }

    psfFile.close();
    G4cout << "PSF data saved successfully" << G4endl;
    G4cout << "Valid bins with energy: " << validBins << " / " << EBL::PSF::NUM_RADIAL_BINS << G4endl;
    G4cout << "Total energy in profile: " << G4BestUnit(totalEnergy, "Energy") << G4endl;
}

void RunAction::SaveBEAMERFormat(const std::string& outputDir)
{
    std::string outputPath = outputDir.empty() ?
        std::string(EBL::Output::BEAMER_FILENAME) :
        outputDir + "/" + std::string(EBL::Output::BEAMER_FILENAME);

    G4cout << "Saving BEAMER format to: " << outputPath << G4endl;

    std::ofstream beamerFile(outputPath);
    if (!beamerFile.is_open()) {
        G4cerr << "Error: Could not open BEAMER output file: " << outputPath << G4endl;
        return;
    }

    // BEAMER format: radius(um) normalized_PSF
    // First normalize the PSF
    std::vector<G4double> normalizedPSF(EBL::PSF::NUM_RADIAL_BINS);
    G4double totalIntegral = 0.0;

    // Calculate integral for normalization
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);
        G4double area = CLHEP::pi * (rOuter*rOuter - rInner*rInner);

        if (fNumEvents > 0) {
            normalizedPSF[i] = fRadialEnergyProfile[i] / (area * fNumEvents);
            totalIntegral += normalizedPSF[i] * area;
        }
    }

    // Normalize so integral over all space = 1
    if (totalIntegral > 0) {
        for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
            normalizedPSF[i] /= totalIntegral;
        }
    }

    // Write in BEAMER format
    beamerFile << "# EBL PSF for BEAMER - Geant4 Simulation" << std::endl;
    beamerFile << "# Beam energy: " << (fPrimaryGenerator ? fPrimaryGenerator->GetParticleGun()->GetParticleEnergy()/keV : 100.0) << " keV" << std::endl;
    beamerFile << "# Resist: " << (fDetConstruction ? fDetConstruction->GetActualResistThickness()/nanometer : 30.0) << " nm ";

    // Try to identify resist type from composition
    auto elements = fDetConstruction ? fDetConstruction->GetResistElements() : std::map<G4String, G4int>();
    if (elements.count("Al") > 0) {
        beamerFile << "Alucone";
    } else if (elements.count("Si") > 0) {
        beamerFile << "HSQ";
    } else {
        beamerFile << "Organic";
    }
    beamerFile << std::endl;

    beamerFile << "# Format: radius(um) PSF(1/um^2)" << std::endl;
    beamerFile << "# Total events: " << fNumEvents << std::endl;

    // Include point at origin for interpolation
    beamerFile << std::scientific << std::setprecision(6);

    // Add a very small radius point to help with interpolation
    if (normalizedPSF[0] > 0) {
        G4double r0 = EBL::PSF::MIN_RADIUS / 2.0;
        beamerFile << r0/micrometer << " " << normalizedPSF[0]/(1.0/(micrometer*micrometer)) << std::endl;
    }

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rCenter = GetBinRadius(i);

        // Only output non-zero values to keep file size reasonable
        if (normalizedPSF[i] > 0) {
            // Convert to um and 1/um^2 for BEAMER
            beamerFile << rCenter/micrometer << " "
                       << normalizedPSF[i]/(1.0/(micrometer*micrometer))
                       << std::endl;
        }
    }

    beamerFile.close();
    G4cout << "BEAMER format saved successfully" << G4endl;

    // Calculate and report key PSF parameters
    G4double alpha = 0, beta = 0, eta = 0;

    // Estimate forward scattering range (alpha)
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (GetBinRadius(i) < 1.0*micrometer) {
            alpha += normalizedPSF[i] * CLHEP::pi *
                     (std::pow(GetBinRadius(i), 2) - (i > 0 ? std::pow(GetBinRadius(i-1), 2) : 0));
        }
    }

    // Estimate backscattering contribution (beta)
    beta = 1.0 - alpha;  // Since total is normalized to 1

    // Estimate backscattering range (eta) - radius containing 90% of backscattered energy
    G4double backscatterEnergy = 0;
    for (G4int i = EBL::PSF::NUM_RADIAL_BINS - 1; i >= 0; i--) {
        if (GetBinRadius(i) > 1.0*micrometer) {
            G4double rInner, rOuter;
            GetBinBoundaries(i, rInner, rOuter);
            backscatterEnergy += normalizedPSF[i] * CLHEP::pi * (rOuter*rOuter - rInner*rInner);
            if (backscatterEnergy > 0.9 * beta) {
                eta = GetBinRadius(i);
                break;
            }
        }
    }

    G4cout << "\nPSF Parameters for BEAMER:" << G4endl;
    G4cout << "  Forward scatter fraction (alpha): " << alpha << G4endl;
    G4cout << "  Backscatter fraction (beta): " << beta << G4endl;
    G4cout << "  Backscatter range (eta): " << eta/micrometer << " um" << G4endl;
}

void RunAction::SaveSummary(const std::string& outputDir)
{
    std::string summaryPath = outputDir.empty() ? "simulation_summary.txt" : outputDir + "/simulation_summary.txt";
    std::ofstream summaryFile(summaryPath);

    summaryFile << "EBL Simulation Summary" << std::endl;
    summaryFile << "=====================" << std::endl;
    summaryFile << "Events simulated: " << fNumEvents << std::endl;
    summaryFile << "Total energy deposited: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << std::endl;

    // Find energy distribution statistics
    G4double e50 = 0, e90 = 0, e99 = 0;  // Radii containing 50%, 90%, 99% of energy
    G4double cumulativeEnergy = 0;
    G4double totalEnergy = fTotalEnergyDeposit.GetValue() / fNumEvents;  // Per event

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS && totalEnergy > 0; i++) {
        cumulativeEnergy += fRadialEnergyProfile[i] / fNumEvents;
        G4double fraction = cumulativeEnergy / totalEnergy;

        if (fraction >= 0.5 && e50 == 0) e50 = GetBinRadius(i);
        if (fraction >= 0.9 && e90 == 0) e90 = GetBinRadius(i);
        if (fraction >= 0.99 && e99 == 0) e99 = GetBinRadius(i);
    }

    summaryFile << "\nEnergy distribution:" << std::endl;
    summaryFile << "50% of energy within: " << G4BestUnit(e50, "Length") << std::endl;
    summaryFile << "90% of energy within: " << G4BestUnit(e90, "Length") << std::endl;
    summaryFile << "99% of energy within: " << G4BestUnit(e99, "Length") << std::endl;

    // Beam and resist info
    if (fPrimaryGenerator) {
        summaryFile << "\nBeam parameters:" << std::endl;
        summaryFile << "Energy: " << G4BestUnit(fPrimaryGenerator->GetParticleGun()->GetParticleEnergy(), "Energy") << std::endl;
    }

    if (fDetConstruction) {
        summaryFile << "\nResist parameters:" << std::endl;
        summaryFile << "Thickness: " << G4BestUnit(fDetConstruction->GetActualResistThickness(), "Length") << std::endl;
        summaryFile << "Density: " << G4BestUnit(fDetConstruction->GetResistDensity(), "Volumic Mass") << std::endl;
    }

    summaryFile.close();
    G4cout << "Summary saved to: " << summaryPath << G4endl;
}
