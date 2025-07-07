// RunAction.cc - Optimized for BEAMER with minimal output
#include "RunAction.hh"
#include "PrimaryGeneratorAction.hh"
#include "DetectorConstruction.hh"
#include "OutputMessenger.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4AccumulableManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4AutoLock.hh"
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <cmath>
#include <chrono>
#include "EBLConstants.hh"

// Initialize static members
std::mutex RunAction::fArrayMergeMutex;
std::vector<G4double> RunAction::fMasterRadialProfile;
std::vector<std::vector<G4double>> RunAction::fMaster2DProfile;
G4bool RunAction::fMasterArraysInitialized = false;

// Define mutex for thread safety
namespace {
    G4Mutex arrayMergeMutex = G4MUTEX_INITIALIZER;
}

RunAction::RunAction(DetectorConstruction* detConstruction,
    PrimaryGeneratorAction* primaryGenerator)
    : G4UserRunAction(),
    fDetConstruction(detConstruction),
    fPrimaryGenerator(primaryGenerator),
    fTotalEnergyDeposit("TotalEnergyDeposit", 0.0),
    fResistEnergyTotal("ResistEnergy", 0.0),
    fSubstrateEnergyTotal("SubstrateEnergy", 0.0),
    fAboveResistEnergyTotal("AboveResistEnergy", 0.0),
    fNumEvents(0),
    fOutputDirectory(""),
    fPSFFilename("ebl_psf_data.csv"),
    fPSF2DFilename("ebl_2d_data.csv"),
    fSummaryFilename("simulation_summary.txt"),
    fBeamerFilename("beamer_psf.dat"),
    fOutputMessenger(nullptr)
{
    // Initialize LOCAL vectors for scoring (per thread)
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.resize(numBins, 0.0);

    // Skip 2D profile initialization for BEAMER-only mode
    // We don't need depth-resolved data

    // Register ONLY scalar accumulables
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Register(fTotalEnergyDeposit);
    accumulableManager->Register(fResistEnergyTotal);
    accumulableManager->Register(fSubstrateEnergyTotal);
    accumulableManager->Register(fAboveResistEnergyTotal);

    // Initialize master arrays once (thread-safe)
    G4AutoLock lock(&arrayMergeMutex);
    if (!fMasterArraysInitialized && G4Threading::IsMasterThread()) {
        fMasterRadialProfile.resize(numBins, 0.0);
        // Skip 2D master profile for BEAMER mode
        fMasterArraysInitialized = true;
    }

    // Create messenger for output control
    fOutputMessenger = new OutputMessenger(this);
}

RunAction::~RunAction()
{
    delete fOutputMessenger;
}

void RunAction::BeginOfRunAction(const G4Run* run)
{
    // Store start time for performance monitoring
    fStartTime = std::chrono::high_resolution_clock::now();

    // Inform the runManager to save random number seed
    G4RunManager::GetRunManager()->SetRandomNumberStore(false);

    // Reset accumulables to their initial values
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Reset();

    // Reset LOCAL data (thread-local storage)
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.assign(numBins, 0.0);

    fNumEvents = 0;

    // Master thread: reset master arrays
    if (G4Threading::IsMasterThread()) {
        G4AutoLock lock(&arrayMergeMutex);
        std::fill(fMasterRadialProfile.begin(), fMasterRadialProfile.end(), 0.0);

        G4cout << "\n### BEAMER PSF Generation - Run " << run->GetRunID() << " ###" << G4endl;
        G4cout << "### Optimized for resist-only energy scoring" << G4endl;
        G4cout << "### Using logarithmic binning: "
            << EBL::PSF::NUM_RADIAL_BINS << " bins from "
            << G4BestUnit(EBL::PSF::MIN_RADIUS, "Length") << " to "
            << G4BestUnit(EBL::PSF::MAX_RADIUS, "Length") << G4endl;

        if (G4Threading::IsMultithreadedApplication()) {
            G4cout << "### Running with " << G4Threading::GetNumberOfRunningWorkerThreads()
                << " worker threads" << G4endl;
        }
    }
}

void RunAction::EndOfRunAction(const G4Run* run)
{
    // Calculate elapsed time
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(endTime - fStartTime);

    G4int nofEvents = run->GetNumberOfEvent();
    if (nofEvents == 0) return;

    // Merge scalar accumulables
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Merge();

    // For both master and sequential mode, we need to handle the arrays
    if (G4Threading::IsMasterThread() || !G4Threading::IsMultithreadedApplication()) {

        // In sequential mode, the local arrays already have the data
        // In MT mode, copy from master arrays after workers have merged
        if (G4Threading::IsMultithreadedApplication()) {
            // Wait for all workers to finish merging
            G4Threading::WorkerThreadJoinsPool();

            // Copy master arrays to local for saving
            G4AutoLock lock(&arrayMergeMutex);
            fRadialEnergyProfile = fMasterRadialProfile;
        }

        fNumEvents = nofEvents;

        // Save only BEAMER-relevant results
        SaveResults();

        // Print performance summary
        G4cout << "\n--------------------BEAMER PSF Generation Complete------------------------------" << G4endl;
        G4cout << " Events processed: " << nofEvents << G4endl;
        G4cout << " Simulation time: " << duration.count() << " seconds" << G4endl;
        if (duration.count() > 0) {
            G4cout << " Performance: " << nofEvents / duration.count() << " events/second" << G4endl;
        }
        G4cout << " Total energy in resist: "
            << G4BestUnit(fResistEnergyTotal.GetValue(), "Energy") << G4endl;

        // Calculate percentage in resist (should be high for thin resists)
        if (fTotalEnergyDeposit.GetValue() > 0) {
            G4double resistFraction = fResistEnergyTotal.GetValue() / fTotalEnergyDeposit.GetValue();
            G4cout << " Fraction of energy in resist: " << resistFraction * 100 << "%" << G4endl;
        }
    }
    else {
        // Worker thread in MT mode: merge local arrays to master
        MergeLocalArrays();
    }
}

void RunAction::MergeLocalArrays()
{
    // Thread-safe merge of local arrays to master
    G4AutoLock lock(&arrayMergeMutex);

    // Merge radial profile
    for (size_t i = 0; i < fRadialEnergyProfile.size(); ++i) {
        fMasterRadialProfile[i] += fRadialEnergyProfile[i];
    }

    // Skip 2D profile merge for BEAMER mode
}

void RunAction::AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit)
{
    // Just accumulate in thread-local arrays
    G4double eventTotalEnergy = 0.0;
    for (size_t i = 0; i < fRadialEnergyProfile.size() && i < energyDeposit.size(); i++) {
        if (energyDeposit[i] > 0) {
            fRadialEnergyProfile[i] += energyDeposit[i];
            eventTotalEnergy += energyDeposit[i];
        }
    }

    // Update only the scalar accumulator
    if (eventTotalEnergy > 0) {
        fTotalEnergyDeposit += eventTotalEnergy;
    }

    fNumEvents++;
}

void RunAction::Add2DEnergyDeposit(const std::vector<std::vector<G4double>>& energy2D)
{
    // Skip for BEAMER mode - we don't need 2D data
}

void RunAction::AddRegionEnergy(G4double resist, G4double substrate, G4double above)
{
    // Only update scalar accumulables
    if (resist > 0) fResistEnergyTotal += resist;
    if (substrate > 0) fSubstrateEnergyTotal += substrate;
    if (above > 0) fAboveResistEnergyTotal += above;
}

// Helper function to get radius for logarithmic bin
G4double RunAction::GetBinRadius(G4int bin) const
{
    if (bin < 0) return 0.0;
    if (bin >= EBL::PSF::NUM_RADIAL_BINS) return EBL::PSF::MAX_RADIUS;

    if (!EBL::PSF::USE_LOG_BINNING) {
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        return (bin + 0.5) * binWidth;
    }

    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    G4double logLower = logMin + bin * logStep;
    G4double logUpper = logMin + (bin + 1) * logStep;
    G4double logCenter = (logLower + logUpper) / 2.0;

    return std::exp(logCenter);
}

void RunAction::GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const
{
    if (!EBL::PSF::USE_LOG_BINNING) {
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        rInner = bin * binWidth;
        rOuter = (bin + 1) * binWidth;
        return;
    }

    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    if (bin == 0) {
        rInner = 0.0;
        rOuter = std::exp(logMin + logStep);
    }
    else if (bin < EBL::PSF::NUM_RADIAL_BINS) {
        rInner = std::exp(logMin + bin * logStep);
        rOuter = std::exp(logMin + (bin + 1) * logStep);
    }
    else {
        rInner = EBL::PSF::MAX_RADIUS;
        rOuter = EBL::PSF::MAX_RADIUS;
    }
}

void RunAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    if (edep > 0) {
        fTotalEnergyDeposit += edep;
    }
}

void RunAction::SaveResults()
{
    G4cout << "\n=== Saving BEAMER PSF Results ===" << G4endl;

    std::string outputDir = fOutputDirectory.empty() ?
        EBL::Output::DEFAULT_DIRECTORY :
        std::string(fOutputDirectory);

    if (!outputDir.empty()) {
        try {
            std::filesystem::create_directories(outputDir);
        }
        catch (const std::exception& e) {
            G4cout << "Warning: Could not create output directory: " << e.what() << G4endl;
            outputDir = "";
        }
    }

    // Save only BEAMER-relevant files
    SaveCSVFormat(outputDir);      // Main PSF data
    SaveBEAMERFormat(outputDir);    // Direct BEAMER format

    // Optional: Save minimal summary
    SaveSummary(outputDir);

    // Skip 2D format for BEAMER mode
    // Save2DFormat(outputDir);
}

void RunAction::SaveCSVFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fPSFFilename) :
        actualOutputDir + "/" + std::string(fPSFFilename);

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
    G4double maxDensity = 0.0;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rCenter = GetBinRadius(i);
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);

        // Calculate annular area for this bin
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

        // Calculate energy density per unit area per event
        G4double energyDensity = (area > 0 && fNumEvents > 0) ?
            fRadialEnergyProfile[i] / (area * fNumEvents) : 0.0;

        if (energyDensity > maxDensity) {
            maxDensity = energyDensity;
        }

        if (fRadialEnergyProfile[i] > 0) {
            validBins++;
            totalEnergy += fRadialEnergyProfile[i];
        }

        // Output with full precision for analysis
        psfFile << std::fixed << std::setprecision(3) << rCenter / CLHEP::nanometer << ","
            << std::scientific << std::setprecision(6) << energyDensity / (CLHEP::eV / (CLHEP::nanometer * CLHEP::nanometer)) << ","
            << std::fixed << std::setprecision(3) << rInner / CLHEP::nanometer << ","
            << rOuter / CLHEP::nanometer << ","
            << fNumEvents
            << std::endl;
    }

    psfFile.close();
    G4cout << "PSF data saved successfully" << G4endl;
    G4cout << "Valid bins with energy: " << validBins << " / " << EBL::PSF::NUM_RADIAL_BINS << G4endl;
    G4cout << "Total energy in radial profile: " << G4BestUnit(totalEnergy, "Energy") << G4endl;
    G4cout << "Peak energy density: " << maxDensity / (CLHEP::eV / (CLHEP::nanometer * CLHEP::nanometer)) << " eV/nm²" << G4endl;
}

void RunAction::SaveBEAMERFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fBeamerFilename) :
        actualOutputDir + "/" + std::string(fBeamerFilename);

    G4cout << "Saving BEAMER format to: " << outputPath << G4endl;

    std::ofstream beamerFile(outputPath);
    if (!beamerFile.is_open()) {
        G4cerr << "Error: Could not open BEAMER output file: " << outputPath << G4endl;
        return;
    }

    // BEAMER format: radius(um) normalized_PSF
    // First normalize the PSF
    std::vector<G4double> normalizedPSF(EBL::PSF::NUM_RADIAL_BINS);
    G4double maxValue = 0.0;

    // Find maximum value for normalization
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

        if (fNumEvents > 0 && area > 0) {
            normalizedPSF[i] = fRadialEnergyProfile[i] / (area * fNumEvents);
            if (normalizedPSF[i] > maxValue) {
                maxValue = normalizedPSF[i];
            }
        }
    }

    // Normalize to maximum = 1.0 (BEAMER standard)
    if (maxValue > 0) {
        for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
            normalizedPSF[i] /= maxValue;
        }
    }

    // Write in BEAMER format
    beamerFile << "# EBL PSF for BEAMER - Geant4 Simulation (Resist-Only)" << std::endl;
    beamerFile << "# Beam energy: " << (fPrimaryGenerator ? fPrimaryGenerator->GetParticleGun()->GetParticleEnergy() / CLHEP::keV : 100.0) << " keV" << std::endl;
    beamerFile << "# Resist: " << (fDetConstruction ? fDetConstruction->GetActualResistThickness() / CLHEP::nanometer : 30.0) << " nm ";

    // Try to identify resist type from composition
    auto elements = fDetConstruction ? fDetConstruction->GetResistElements() : std::map<G4String, G4int>();
    if (elements.count("Al") > 0) {
        beamerFile << "Alucone";
    }
    else if (elements.count("Si") > 0) {
        beamerFile << "HSQ";
    }
    else {
        beamerFile << "Organic";
    }
    beamerFile << std::endl;

    beamerFile << "# Format: radius(um) PSF(normalized)" << std::endl;
    beamerFile << "# Total events: " << fNumEvents << std::endl;
    beamerFile << "# Normalization: Peak = 1.0" << std::endl;

    // Include point at origin for interpolation
    beamerFile << std::scientific << std::setprecision(6);

    // Add a very small radius point to help with interpolation
    if (normalizedPSF[0] > 0) {
        G4double r0 = EBL::PSF::MIN_RADIUS / 2.0;
        beamerFile << r0 / CLHEP::micrometer << " " << normalizedPSF[0] << std::endl;
    }

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rCenter = GetBinRadius(i);

        // Only output non-zero values to keep file size reasonable
        if (normalizedPSF[i] > 1e-12) {
            // Convert to um for BEAMER
            beamerFile << rCenter / CLHEP::micrometer << " "
                << normalizedPSF[i] << std::endl;
        }
    }

    beamerFile.close();
    G4cout << "BEAMER format saved successfully" << G4endl;

    // Calculate and report key PSF parameters
    G4double forward_fraction = 0;
    G4double total_integral = 0;

    // Calculate forward scattering fraction (< 1 μm)
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (GetBinRadius(i) < 1.0 * CLHEP::micrometer) {
            G4double rInner, rOuter;
            GetBinBoundaries(i, rInner, rOuter);
            G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);
            forward_fraction += normalizedPSF[i] * area;
            total_integral += normalizedPSF[i] * area;
        } else {
            G4double rInner, rOuter;
            GetBinBoundaries(i, rInner, rOuter);
            G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);
            total_integral += normalizedPSF[i] * area;
        }
    }

    if (total_integral > 0) {
        G4double alpha = forward_fraction / total_integral;
        G4double beta = 1.0 - alpha;

        G4cout << "\nPSF Parameters for BEAMER:" << G4endl;
        G4cout << "  Forward scatter fraction (α): " << alpha << G4endl;
        G4cout << "  Backscatter fraction (β): " << beta << G4endl;
    }
}

void RunAction::Save2DFormat(const std::string& outputDir)
{
    // Skip for BEAMER-only mode
    return;
}

void RunAction::SaveSummary(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string summaryPath = actualOutputDir.empty() ?
        std::string(fSummaryFilename) :
        actualOutputDir + "/" + std::string(fSummaryFilename);

    std::ofstream summaryFile(summaryPath);

    summaryFile << "BEAMER PSF Simulation Summary" << std::endl;
    summaryFile << "=============================" << std::endl;
    summaryFile << "Events simulated: " << fNumEvents << std::endl;
    summaryFile << "Total energy deposited: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << std::endl;
    summaryFile << "Energy in resist: " << G4BestUnit(fResistEnergyTotal.GetValue(), "Energy") << std::endl;

    G4double resistFraction = 0;
    if (fTotalEnergyDeposit.GetValue() > 0) {
        resistFraction = fResistEnergyTotal.GetValue() / fTotalEnergyDeposit.GetValue();
    }
    summaryFile << "Fraction in resist: " << resistFraction * 100 << "%" << std::endl;

    // Simulation time
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(endTime - fStartTime);
    summaryFile << "\nPerformance:" << std::endl;
    summaryFile << "Simulation time: " << duration.count() << " seconds" << std::endl;
    if (duration.count() > 0) {
        summaryFile << "Events per second: " << fNumEvents / duration.count() << std::endl;
    }

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