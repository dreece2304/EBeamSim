// RunAction.cc - BEAMER Optimized with Performance Monitoring
#include "RunAction.hh"
#include "OutputMessenger.hh"
#include "DetectorConstruction.hh"
#include "PrimaryGeneratorAction.hh"
#include "EBLConstants.hh"

#include "G4RunManager.hh"
#include "G4Run.hh"
#include "G4AccumulableManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4AutoLock.hh"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <cmath>
#include <algorithm>
#include <chrono>

// Static member definitions
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

    // Initialize 2D profile for visualization capabilities
    const G4int depthBins = 100;  // NUM_DEPTH_BINS
    const G4int radialBins = 150; // NUM_RADIAL_BINS for 2D
    f2DEnergyProfile.resize(depthBins);
    for (auto& radialRow : f2DEnergyProfile) {
        radialRow.resize(radialBins, 0.0);
    }

    // Register scalar accumulables (Geant4 11.1+ compatible)
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->RegisterAccumulable(&fTotalEnergyDeposit);
    accumulableManager->RegisterAccumulable(&fResistEnergyTotal);
    accumulableManager->RegisterAccumulable(&fSubstrateEnergyTotal);
    accumulableManager->RegisterAccumulable(&fAboveResistEnergyTotal);

    // Initialize master arrays once (thread-safe)
    G4AutoLock lock(&arrayMergeMutex);
    if (!fMasterArraysInitialized && G4Threading::IsMasterThread()) {
        fMasterRadialProfile.resize(numBins, 0.0);
        fMaster2DProfile.resize(depthBins);
        for (auto& radialRow : fMaster2DProfile) {
            radialRow.resize(radialBins, 0.0);
        }
        fMasterArraysInitialized = true;
    }

    // Create messenger for output control
    fOutputMessenger = new OutputMessenger(this);

    G4cout << "RunAction initialized for thread "
           << (G4Threading::IsWorkerThread() ? "worker" : "master/sequential") << G4endl;
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

    // Reset 2D profile
    for (auto& depthBin : f2DEnergyProfile) {
        std::fill(depthBin.begin(), depthBin.end(), 0.0);
    }

    fNumEvents = 0;

    // Master thread: reset master arrays
    if (G4Threading::IsMasterThread()) {
        G4AutoLock lock(&arrayMergeMutex);
        std::fill(fMasterRadialProfile.begin(), fMasterRadialProfile.end(), 0.0);
        for (auto& depthBin : fMaster2DProfile) {
            std::fill(depthBin.begin(), depthBin.end(), 0.0);
        }

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

    // Merge scalar accumulables (updated for Geant4 11.3+)
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Merge();

    // For both master and sequential mode, we need to handle the arrays
    if (G4Threading::IsMasterThread() || !G4Threading::IsMultithreadedApplication()) {

        // In sequential mode, the local arrays already have the data
        // In MT mode, copy from master arrays after workers have merged
        if (G4Threading::IsMultithreadedApplication()) {
            // Wait for all workers to finish merging
            G4Threading::WorkerThreadJoinsPool();

            // Move master arrays to local for saving (C++11 optimization)
            G4AutoLock lock(&arrayMergeMutex);
            fRadialEnergyProfile = std::move(fMasterRadialProfile);
            f2DEnergyProfile = std::move(fMaster2DProfile);
        }

        fNumEvents = nofEvents;

        // Save BEAMER-relevant results
        SaveResults();

        // Report validation metrics
        ReportValidationMetrics();

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
        G4cout << "------------------------------------------------------------------------------\n" << G4endl;
    }
    else {
        // Worker thread in MT mode: merge local arrays to master
        MergeLocalArrays();
    }
}

void RunAction::MergeLocalArrays()
{
    // Thread-safe merge of local arrays to master (optimized for Geant4 11.3+)
    G4AutoLock lock(&arrayMergeMutex);

    // Merge radial profile - bounds checking for safety
    const size_t radialSize = std::min(fRadialEnergyProfile.size(), fMasterRadialProfile.size());
    for (size_t i = 0; i < radialSize; ++i) {
        if (fRadialEnergyProfile[i] > 0.0) { // Skip zero values for efficiency
            fMasterRadialProfile[i] += fRadialEnergyProfile[i];
        }
    }

    // Merge 2D profile with optimized bounds checking
    const size_t profileDepth = std::min(f2DEnergyProfile.size(), fMaster2DProfile.size());
    for (size_t i = 0; i < profileDepth; ++i) {
        const size_t profileWidth = std::min(f2DEnergyProfile[i].size(), fMaster2DProfile[i].size());
        for (size_t j = 0; j < profileWidth; ++j) {
            if (f2DEnergyProfile[i][j] > 0.0) { // Skip zero values for efficiency
                fMaster2DProfile[i][j] += f2DEnergyProfile[i][j];
            }
        }
    }
}

void RunAction::AddRadialEnergyDeposit(const std::vector<G4double>& energyDeposit)
{
    // Accumulate in thread-local arrays (optimized with const correctness)
    G4double eventTotalEnergy = 0.0;
    const size_t minSize = std::min(fRadialEnergyProfile.size(), energyDeposit.size());
    
    for (size_t i = 0; i < minSize; ++i) {
        if (energyDeposit[i] > 0.0) {
            fRadialEnergyProfile[i] += energyDeposit[i];
            eventTotalEnergy += energyDeposit[i];
        }
    }

    // Update scalar accumulator only if energy was deposited
    if (eventTotalEnergy > 0.0) {
        fTotalEnergyDeposit += eventTotalEnergy;
    }

    ++fNumEvents;
}

void RunAction::Add2DEnergyDeposit(const std::vector<std::vector<G4double>>& energy2D)
{
    // Add 2D energy deposition data (optimized with bounds checking)
    const size_t depthSize = std::min(energy2D.size(), f2DEnergyProfile.size());
    for (size_t i = 0; i < depthSize; ++i) {
        const size_t radialSize = std::min(energy2D[i].size(), f2DEnergyProfile[i].size());
        for (size_t j = 0; j < radialSize; ++j) {
            if (energy2D[i][j] > 0.0) { // Skip zero values for efficiency
                f2DEnergyProfile[i][j] += energy2D[i][j];
            }
        }
    }
}

void RunAction::AddRegionEnergy(G4double resist, G4double substrate, G4double above)
{
    // Update scalar accumulables (optimized with single conditionals)
    if (resist > 0.0) fResistEnergyTotal += resist;
    if (substrate > 0.0) fSubstrateEnergyTotal += substrate;
    if (above > 0.0) fAboveResistEnergyTotal += above;
}

void RunAction::AddEnergyDeposit(G4double edep, G4double x, G4double y, G4double z)
{
    if (edep > 0.0) {
        fTotalEnergyDeposit += edep;

        // Calculate radial distance and add to appropriate bin (optimized)
        const G4double r = std::sqrt(x*x + y*y);

        // Find the radial bin
        G4int bin = -1;
        if (EBL::PSF::USE_LOG_BINNING) {
            if (r > 0 && r >= EBL::PSF::MIN_RADIUS && r < EBL::PSF::MAX_RADIUS) {
                G4double logRatio = std::log(r / EBL::PSF::MIN_RADIUS) /
                                   std::log(EBL::PSF::MAX_RADIUS / EBL::PSF::MIN_RADIUS);
                bin = static_cast<G4int>(logRatio * (EBL::PSF::NUM_RADIAL_BINS - 1));
            } else if (r > 0 && r < EBL::PSF::MIN_RADIUS) {
                bin = 0;
            }
        } else {
            G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
            bin = static_cast<G4int>(r / binWidth);
            if (bin >= EBL::PSF::NUM_RADIAL_BINS) bin = EBL::PSF::NUM_RADIAL_BINS - 1;
        }

        if (bin >= 0 && bin < static_cast<G4int>(fRadialEnergyProfile.size())) {
            fRadialEnergyProfile[bin] += edep;
        }
    }
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

    // Save BEAMER-relevant files
    SaveCSVFormat(outputDir);      // Main PSF data
    SaveBEAMERFormat(outputDir);   // Direct BEAMER format
    SaveSummary(outputDir);        // Minimal summary
    Save2DFormat(outputDir);       // 2D format for visualization
    SaveEnergyEquivalenceReport(outputDir); // UV-ebeam energy equivalence
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
            // Calculate normalized energy density (no importance sampling correction)
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
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

        if (GetBinRadius(i) < 1.0 * CLHEP::micrometer) {
            forward_fraction += normalizedPSF[i] * area;
        }
        total_integral += normalizedPSF[i] * area;
    }

    if (total_integral > 0) {
        G4double alpha = forward_fraction / total_integral;
        G4double beta = 1.0 - alpha;

        G4cout << "\nPSF Parameters for BEAMER:" << G4endl;
        G4cout << "  Forward scatter fraction (alpha): " << alpha << G4endl;
        G4cout << "  Backscatter fraction (beta): " << beta << G4endl;
    }
}

void RunAction::Save2DFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fPSF2DFilename) :
        actualOutputDir + "/" + std::string(fPSF2DFilename);

    std::ofstream file(outputPath);
    if (!file.is_open()) {
        G4cerr << "Error: Could not open 2D file " << outputPath << G4endl;
        return;
    }

    // Check if we have 2D data
    if (f2DEnergyProfile.empty() || f2DEnergyProfile[0].empty()) {
        G4cout << "Warning: No 2D energy profile data to save" << G4endl;
        file << "# No 2D data collected" << std::endl;
        file.close();
        return;
    }

    G4cout << "Saving 2D data: " << f2DEnergyProfile.size() << " x " << f2DEnergyProfile[0].size() << " bins" << G4endl;

    // Calculate physical coordinates
    G4double resistThickness = fDetConstruction ? fDetConstruction->GetActualResistThickness() : 30.0*CLHEP::nanometer;
    G4double totalDepth = resistThickness + 50.0*CLHEP::nanometer;

    // Count non-zero entries for verification
    G4int nonZeroCount = 0;
    G4double totalEnergy2D = 0.0;
    const size_t depthBins = f2DEnergyProfile.size();
    const size_t radiusBins = depthBins > 0 ? f2DEnergyProfile[0].size() : 0;
    
    for (size_t i = 0; i < depthBins; ++i) {
        for (size_t j = 0; j < radiusBins; ++j) {
            if (f2DEnergyProfile[i][j] > 0) {
                nonZeroCount++;
                totalEnergy2D += f2DEnergyProfile[i][j];
            }
        }
    }

    G4cout << "2D profile has " << nonZeroCount << " non-zero bins, total energy: "
           << totalEnergy2D/CLHEP::eV << " eV" << G4endl;

    // Save in pandas-compatible CSV format with proper indexing
    // First row: header with radius values
    file << "depth_nm";  // Index column name
    for (size_t j = 0; j < f2DEnergyProfile[0].size(); ++j) {
        G4double radius = (j + 0.5) * 50.0*CLHEP::micrometer / f2DEnergyProfile[0].size();
        file << "," << std::fixed << std::setprecision(1) << radius/CLHEP::nanometer;
    }
    file << std::endl;

    // Data rows: depth value followed by energy values
    for (size_t i = 0; i < f2DEnergyProfile.size(); ++i) {
        // Calculate depth for this row (center of depth bin)
        G4double depth = -50.0*CLHEP::nanometer + (i + 0.5) * totalDepth / f2DEnergyProfile.size();
        file << std::fixed << std::setprecision(2) << depth/CLHEP::nanometer;

        // Write energy values for all radii at this depth
        for (size_t j = 0; j < f2DEnergyProfile[i].size(); ++j) {
            file << "," << std::scientific << std::setprecision(6) << f2DEnergyProfile[i][j]/CLHEP::eV;
        }
        file << std::endl;
    }

    file.close();
    G4cout << "2D data saved to: " << outputPath << " (pandas-compatible matrix format)" << G4endl;

    // Additional verification
    G4cout << "Depth range: " << (-50.0) << " to "
           << (-50.0 + totalDepth/CLHEP::nanometer) << " nm" << G4endl;
    G4cout << "Radius range: 0 to " << (50.0) << " um" << G4endl;
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

// Energy equivalence methods for UV-ebeam dose correlation
G4double RunAction::GetPerPrimaryResistEnergyAbsorption() const
{
    if (fNumEvents == 0) return 0.0;
    return fResistEnergyTotal.GetValue() / fNumEvents;
}

G4double RunAction::CalculateEnergyAbsorptionCoefficient() const
{
    // Calculate K = E_film(1) × 6.2415×10^12 (conversion factor from eV to J and electrons to µC)
    // This gives J/cm² per µC/cm² for e-beam dose
    G4double energyPerPrimary_eV = GetPerPrimaryResistEnergyAbsorption() / CLHEP::eV;
    
    // Conversion: eV × (1.602176×10^-19 J/eV) × (6.2415×10^12 electrons/µC) = J per µC
    // Simplified: eV × 6.2415×10^12 × 1.602176×10^-19 = eV × 0.999999 ≈ eV × 1.0
    // For practical purposes: K ≈ energyPerPrimary_eV × 1.0e-6 (to convert eV to µJ)
    
    const G4double eV_to_J = 1.602176e-19;
    const G4double electrons_per_microCoulomb = 6.2415e12;
    
    G4double K = energyPerPrimary_eV * eV_to_J * electrons_per_microCoulomb; // J/cm² per µC/cm²
    
    return K;
}

G4double RunAction::CalculateUVEquivalentTime(G4double ebeamDose_uC_cm2, G4double uvFluenceRate_J_cm2_min, G4double uvAbsorptance) const
{
    // Calculate absorbed energy density for e-beam dose
    G4double K = CalculateEnergyAbsorptionCoefficient();
    G4double ebeamAbsorbedEnergy_J_cm2 = K * ebeamDose_uC_cm2;
    
    // Calculate UV absorbed energy rate
    G4double uvAbsorbedRate_J_cm2_min = uvFluenceRate_J_cm2_min * uvAbsorptance;
    
    // Calculate equivalent UV exposure time
    if (uvAbsorbedRate_J_cm2_min > 0) {
        return ebeamAbsorbedEnergy_J_cm2 / uvAbsorbedRate_J_cm2_min; // minutes
    }
    
    return 0.0;
}

void RunAction::SaveEnergyEquivalenceReport(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string equivalencePath = actualOutputDir.empty() ?
        "energy_equivalence_report.txt" :
        actualOutputDir + "/energy_equivalence_report.txt";

    G4cout << "Saving energy equivalence report to: " << equivalencePath << G4endl;

    std::ofstream reportFile(equivalencePath);
    if (!reportFile.is_open()) {
        G4cerr << "Error: Could not open energy equivalence report file: " << equivalencePath << G4endl;
        return;
    }

    // Calculate key parameters
    G4double energyPerPrimary_eV = GetPerPrimaryResistEnergyAbsorption() / CLHEP::eV;
    G4double energyPerPrimary_J = GetPerPrimaryResistEnergyAbsorption() * 1.602176e-19;
    G4double K_coefficient = CalculateEnergyAbsorptionCoefficient();
    
    // Get beam and resist parameters
    G4double beamEnergy_keV = fPrimaryGenerator ? 
        fPrimaryGenerator->GetParticleGun()->GetParticleEnergy() / CLHEP::keV : 100.0;
    G4double resistThickness_nm = fDetConstruction ? 
        fDetConstruction->GetActualResistThickness() / CLHEP::nanometer : 30.0;
    G4double resistDensity_g_cm3 = fDetConstruction ? 
        fDetConstruction->GetResistDensity() / (CLHEP::g/CLHEP::cm3) : 1.4;
    
    // Write comprehensive report
    reportFile << "═══════════════════════════════════════════════════════════════" << std::endl;
    reportFile << "    E-BEAM TO UV ENERGY EQUIVALENCE ANALYSIS REPORT" << std::endl;
    reportFile << "═══════════════════════════════════════════════════════════════" << std::endl;
    reportFile << std::endl;
    
    reportFile << "SIMULATION PARAMETERS:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "Events simulated: " << fNumEvents << std::endl;
    reportFile << "Beam energy: " << beamEnergy_keV << " keV" << std::endl;
    reportFile << "Resist thickness: " << resistThickness_nm << " nm" << std::endl;
    reportFile << "Resist density: " << resistDensity_g_cm3 << " g/cm³" << std::endl;
    
    // Print resist composition
    if (fDetConstruction) {
        auto elements = fDetConstruction->GetResistElements();
        reportFile << "Resist composition: ";
        bool first = true;
        for (const auto& elem : elements) {
            if (!first) reportFile << ", ";
            reportFile << elem.first << ":" << elem.second;
            first = false;
        }
        reportFile << std::endl;
    }
    reportFile << std::endl;
    
    reportFile << "ENERGY ABSORPTION ANALYSIS:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "Total energy deposited in resist: " << fResistEnergyTotal.GetValue()/CLHEP::eV << " eV" << std::endl;
    reportFile << "Energy per primary electron (E_film): " << std::scientific << std::setprecision(4) 
               << energyPerPrimary_eV << " eV" << std::endl;
    reportFile << "Energy per primary electron: " << std::scientific << std::setprecision(4) 
               << energyPerPrimary_J << " J" << std::endl;
    reportFile << "Energy absorption coefficient (K): " << std::scientific << std::setprecision(4) 
               << K_coefficient << " J/cm² per µC/cm²" << std::endl;
    reportFile << std::endl;
    
    reportFile << "UV EQUIVALENCE CALCULATIONS:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "Formula: E_abs,film(D) = K × D" << std::endl;
    reportFile << "Where: D = e-beam dose (µC/cm²)" << std::endl;
    reportFile << "       K = " << std::scientific << std::setprecision(4) << K_coefficient << " J/cm² per µC/cm²" << std::endl;
    reportFile << std::endl;
    
    // Example calculations for common e-beam doses
    std::vector<G4double> commonDoses = {500, 1000, 2000, 5000, 10000, 15000}; // µC/cm²
    G4double uvFluenceRate = 0.060; // J/cm²/min (from your measurements)
    std::vector<G4double> uvAbsorptanceEstimates = {0.1, 0.3, 0.5, 0.8}; // Range of possible values
    
    reportFile << "EXAMPLE DOSE EQUIVALENCES:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "Assuming UV fluence rate: " << uvFluenceRate << " J/cm²/min (254 nm at 4\")" << std::endl;
    reportFile << std::endl;
    
    for (G4double absorptance : uvAbsorptanceEstimates) {
        reportFile << "UV Absorptance: " << absorptance << std::endl;
        reportFile << "E-beam Dose → Absorbed Energy → UV Time Required" << std::endl;
        reportFile << "(µC/cm²)    → (J/cm²)        → (minutes)" << std::endl;
        
        for (G4double dose : commonDoses) {
            G4double absorbedEnergy = K_coefficient * dose;
            G4double uvTime = CalculateUVEquivalentTime(dose, uvFluenceRate, absorptance);
            
            reportFile << std::fixed << std::setprecision(0) << std::setw(8) << dose 
                      << " → " << std::scientific << std::setprecision(3) << absorbedEnergy
                      << " → " << std::fixed << std::setprecision(1) << std::setw(8) << uvTime << std::endl;
        }
        reportFile << std::endl;
    }
    
    reportFile << "USAGE INSTRUCTIONS:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "1. Measure UV absorptance of your resist at 254 nm" << std::endl;
    reportFile << "2. Measure your UV lamp fluence rate (J/cm²/min)" << std::endl;
    reportFile << "3. For any e-beam dose D (µC/cm²):" << std::endl;
    reportFile << "   UV_time = (K × D) / (UV_rate × Absorptance)" << std::endl;
    reportFile << "   Where K = " << std::scientific << std::setprecision(4) << K_coefficient << " J/cm² per µC/cm²" << std::endl;
    reportFile << std::endl;
    
    reportFile << "SCIENTIFIC RATIONALE:" << std::endl;
    reportFile << "─────────────────────────────────────────────────────────────" << std::endl;
    reportFile << "This analysis enables comparison of e-beam and UV irradiation" << std::endl;
    reportFile << "based on absorbed energy density in the resist film." << std::endl;
    reportFile << "If graphitization is energy-density driven, UV and e-beam" << std::endl;
    reportFile << "should show similar effects at equivalent absorbed energies." << std::endl;
    reportFile << "If not, it indicates mechanism-specific processes." << std::endl;
    reportFile << std::endl;
    
    reportFile << "Generated by EBL Simulation Suite" << std::endl;
    reportFile << "Geant4 Monte Carlo with 100 keV electron physics" << std::endl;
    
    reportFile.close();
    G4cout << "Energy equivalence report saved successfully" << G4endl;
    
    // Also print key results to console
    G4cout << "\n=== ENERGY EQUIVALENCE SUMMARY ===" << G4endl;
    G4cout << "Energy per primary: " << std::scientific << std::setprecision(3) 
           << energyPerPrimary_eV << " eV" << G4endl;
    G4cout << "Absorption coefficient K: " << std::scientific << std::setprecision(3) 
           << K_coefficient << " J/cm² per µC/cm²" << G4endl;
    G4cout << "Example: 5000 µC/cm² → " << std::scientific << std::setprecision(3)
           << (K_coefficient * 5000) << " J/cm² absorbed energy" << G4endl;
}

G4double RunAction::CalculateRMSRadius() const
{
    // Calculate RMS radius of energy deposition (lateral spread)
    G4double totalEnergy = 0.0;
    G4double weightedR2Sum = 0.0;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (fRadialEnergyProfile[i] > 0) {
            G4double rCenter = GetBinRadius(i);
            G4double energy = fRadialEnergyProfile[i];

            totalEnergy += energy;
            weightedR2Sum += energy * rCenter * rCenter;
        }
    }

    if (totalEnergy > 0) {
        return std::sqrt(weightedR2Sum / totalEnergy);
    }
    return 0.0;
}

G4double RunAction::CalculateForwardBackscatterRatio() const
{
    // Calculate ratio of energy in resist to energy in substrate
    if (fSubstrateEnergyTotal.GetValue() > 0) {
        return fResistEnergyTotal.GetValue() / fSubstrateEnergyTotal.GetValue();
    }
    return -1.0;  // Invalid if no substrate energy
}

G4double RunAction::CalculateEnergyConservation() const
{
    // Check energy conservation (should be close to 1.0)
    if (!fPrimaryGenerator || fNumEvents == 0) return 0.0;

    G4double beamEnergy = fPrimaryGenerator->GetParticleGun()->GetParticleEnergy();
    G4double totalBeamEnergy = beamEnergy * fNumEvents;

    G4double totalDepositedEnergy = fResistEnergyTotal.GetValue() +
                                   fSubstrateEnergyTotal.GetValue() +
                                   fAboveResistEnergyTotal.GetValue();

    if (totalBeamEnergy > 0) {
        return totalDepositedEnergy / totalBeamEnergy;
    }
    return 0.0;
}

void RunAction::ReportValidationMetrics()
{
    G4cout << "\n=== VALIDATION METRICS ===" << G4endl;

    // RMS Radius (lateral spread)
    G4double rmsRadius = CalculateRMSRadius();
    G4cout << "RMS Radius (lateral spread): " << G4BestUnit(rmsRadius, "Length") << G4endl;

    // Forward/Backscatter ratio
    G4double fbRatio = CalculateForwardBackscatterRatio();
    if (fbRatio > 0) {
        G4cout << "Forward/Backscatter ratio: " << fbRatio << G4endl;
        G4cout << "  (Energy in resist / Energy in substrate)" << G4endl;
    }

    // Energy conservation check
    G4double energyConservation = CalculateEnergyConservation();
    G4cout << "Energy conservation: " << energyConservation * 100 << "%" << G4endl;
    if (std::abs(1.0 - energyConservation) > 0.05) {
        G4cout << "  WARNING: Energy conservation > 5% deviation!" << G4endl;
    }

    // PSF quality metrics
    G4int nonZeroBins = 0;
    G4double peakValue = 0.0;
    G4int peakBin = 0;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (fRadialEnergyProfile[i] > 0) {
            nonZeroBins++;
            if (fRadialEnergyProfile[i] > peakValue) {
                peakValue = fRadialEnergyProfile[i];
                peakBin = i;
            }
        }
    }

    G4cout << "PSF Statistics:" << G4endl;
    G4cout << "  Non-zero bins: " << nonZeroBins << " / " << EBL::PSF::NUM_RADIAL_BINS << G4endl;
    G4cout << "  Peak at radius: " << G4BestUnit(GetBinRadius(peakBin), "Length") << G4endl;

    // Check for adequate statistics in PSF tails
    G4int tailBins = 0;
    for (G4int i = EBL::PSF::NUM_RADIAL_BINS * 3/4; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (fRadialEnergyProfile[i] > 0) tailBins++;
    }

    G4cout << "  Tail statistics (>75% of range): " << tailBins << " bins with data" << G4endl;
    if (tailBins < 5) {
        G4cout << "  WARNING: Poor statistics in PSF tails - consider more events" << G4endl;
    }

    G4cout << "=========================\n" << G4endl;
}