// RunAction.cc - Complete Optimized Implementation with Minimal Accumulables
#include "RunAction.hh"
#include "PrimaryGeneratorAction.hh"
#include "DetectorConstruction.hh"
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
    fNumEvents(0)
{
    // Initialize LOCAL vectors for scoring (per thread)
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.resize(numBins, 0.0);

    // Initialize 2D profile
    const G4int numDepthBins = 100;
    f2DEnergyProfile.resize(numDepthBins);
    for (auto& depthBin : f2DEnergyProfile) {
        depthBin.resize(numBins, 0.0);
    }

    // Register ONLY scalar accumulables - not the arrays!
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Register(fTotalEnergyDeposit);
    accumulableManager->Register(fResistEnergyTotal);
    accumulableManager->Register(fSubstrateEnergyTotal);
    accumulableManager->Register(fAboveResistEnergyTotal);

    // Initialize master arrays once (thread-safe)
    G4AutoLock lock(&arrayMergeMutex);
    if (!fMasterArraysInitialized && G4Threading::IsMasterThread()) {
        fMasterRadialProfile.resize(numBins, 0.0);
        fMaster2DProfile.resize(numDepthBins);
        for (auto& depthBin : fMaster2DProfile) {
            depthBin.resize(numBins, 0.0);
        }
        fMasterArraysInitialized = true;
    }
}

RunAction::~RunAction()
{
}

void RunAction::BeginOfRunAction(const G4Run* run)
{
    // Inform the runManager to save random number seed
    G4RunManager::GetRunManager()->SetRandomNumberStore(false);

    // Reset accumulables to their initial values
    G4AccumulableManager* accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->Reset();

    // Reset LOCAL data (thread-local storage)
    const G4int numBins = EBL::PSF::NUM_RADIAL_BINS;
    fRadialEnergyProfile.assign(numBins, 0.0);

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

        G4cout << "### Run " << run->GetRunID() << " start." << G4endl;
        G4cout << "### Using logarithmic binning: "
            << EBL::PSF::NUM_RADIAL_BINS << " bins from "
            << G4BestUnit(EBL::PSF::MIN_RADIUS, "Length") << " to "
            << G4BestUnit(EBL::PSF::MAX_RADIUS, "Length") << G4endl;

        if (G4Threading::IsMultithreadedApplication()) {
            G4cout << "### Running with " << G4Threading::GetNumberOfRunningWorkerThreads()
                << " worker threads" << G4endl;
            G4cout << "### Using optimized minimal accumulables strategy" << G4endl;
        }
    }
}

void RunAction::EndOfRunAction(const G4Run* run)
{
    // Complete the progress bar
    G4cout << "\rProgress: 100.0% (" << run->GetNumberOfEvent() 
           << "/" << run->GetNumberOfEvent() << " events) - Complete!" 
           << G4endl << G4endl;
    // Complete the progress bar
    G4cout << "\rProgress: 100.0% (" << run->GetNumberOfEvent() 
           << "/" << run->GetNumberOfEvent() << " events) - Complete!" 
           << G4endl << G4endl;


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
            f2DEnergyProfile = fMaster2DProfile;
        }
        // In sequential mode, fRadialEnergyProfile already has the data

        fNumEvents = nofEvents;

        // Save results
        SaveResults();

        // Print results
        G4cout << "\n--------------------End of Run------------------------------\n"
            << " The run consists of " << nofEvents << " events" << G4endl;

        G4cout << " Total energy deposited: "
            << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << G4endl;
        G4cout << " Energy in resist: "
            << G4BestUnit(fResistEnergyTotal.GetValue(), "Energy") << G4endl;
        G4cout << " Energy in substrate: "
            << G4BestUnit(fSubstrateEnergyTotal.GetValue(), "Energy") << G4endl;
        G4cout << " Energy above resist: "
            << G4BestUnit(fAboveResistEnergyTotal.GetValue(), "Energy") << G4endl;
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

    // Merge 2D profile
    for (size_t d = 0; d < f2DEnergyProfile.size(); ++d) {
        for (size_t r = 0; r < f2DEnergyProfile[d].size(); ++r) {
            fMaster2DProfile[d][r] += f2DEnergyProfile[d][r];
        }
    }
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
    // Just accumulate in thread-local arrays
    for (size_t d = 0; d < energy2D.size() && d < f2DEnergyProfile.size(); d++) {
        for (size_t r = 0; r < energy2D[d].size() && r < f2DEnergyProfile[d].size(); r++) {
            if (energy2D[d][r] > 0) {
                f2DEnergyProfile[d][r] += energy2D[d][r];
            }
        }
    }
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
    G4cout << "=== Saving Results ===" << G4endl;
    G4cout << "Number of events processed: " << fNumEvents << G4endl;

    // Debug: Check if we have any data in the radial profile
    G4double totalRadialEnergy = 0.0;
    G4int nonZeroBins = 0;
    for (size_t i = 0; i < fRadialEnergyProfile.size(); ++i) {
        if (fRadialEnergyProfile[i] > 0) {
            totalRadialEnergy += fRadialEnergyProfile[i];
            nonZeroBins++;
        }
    }

    G4cout << "Total energy in radial profile: " << G4BestUnit(totalRadialEnergy, "Energy")
        << " in " << nonZeroBins << " bins" << G4endl;
    G4cout << "Total energy from accumulable: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << G4endl;

    std::string outputDir = EBL::Output::DEFAULT_DIRECTORY;
    if (!outputDir.empty()) {
        try {
            std::filesystem::create_directories(outputDir);
        }
        catch (const std::exception& e) {
            G4cout << "Warning: Could not create output directory: " << e.what() << G4endl;
            outputDir = "";
        }
    }

    SaveCSVFormat(outputDir);
    SaveBEAMERFormat(outputDir);
    Save2DFormat(outputDir);
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
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

        // Calculate energy density per unit area per event
        G4double energyDensity = (area > 0 && fNumEvents > 0) ?
            fRadialEnergyProfile[i] / (area * fNumEvents) : 0.0;

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
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

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

    beamerFile << "# Format: radius(um) PSF(1/um^2)" << std::endl;
    beamerFile << "# Total events: " << fNumEvents << std::endl;

    if (G4Threading::IsMultithreadedApplication()) {
        beamerFile << "# Threading: MT (" << G4Threading::GetNumberOfRunningWorkerThreads() << " threads)" << std::endl;
    }
    else {
        beamerFile << "# Threading: Sequential" << std::endl;
    }

    // Include point at origin for interpolation
    beamerFile << std::scientific << std::setprecision(6);

    // Add a very small radius point to help with interpolation
    if (normalizedPSF[0] > 0) {
        G4double r0 = EBL::PSF::MIN_RADIUS / 2.0;
        beamerFile << r0 / CLHEP::micrometer << " " << normalizedPSF[0] / (1.0 / (CLHEP::micrometer * CLHEP::micrometer)) << std::endl;
    }

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rCenter = GetBinRadius(i);

        // Only output non-zero values to keep file size reasonable
        if (normalizedPSF[i] > 0) {
            // Convert to um and 1/um^2 for BEAMER
            beamerFile << rCenter / CLHEP::micrometer << " "
                << normalizedPSF[i] / (1.0 / (CLHEP::micrometer * CLHEP::micrometer))
                << std::endl;
        }
    }

    beamerFile.close();
    G4cout << "BEAMER format saved successfully" << G4endl;

    // Calculate and report key PSF parameters
    G4double alpha = 0, beta = 0, eta = 0;

    // Estimate forward scattering range (alpha)
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (GetBinRadius(i) < 1.0 * CLHEP::micrometer) {
            alpha += normalizedPSF[i] * CLHEP::pi *
                (std::pow(GetBinRadius(i), 2) - (i > 0 ? std::pow(GetBinRadius(i - 1), 2) : 0));
        }
    }

    // Estimate backscattering contribution (beta)
    beta = 1.0 - alpha;  // Since total is normalized to 1

    // Estimate backscattering range (eta) - radius containing 90% of backscattered energy
    G4double backscatterEnergy = 0;
    for (G4int i = EBL::PSF::NUM_RADIAL_BINS - 1; i >= 0; i--) {
        if (GetBinRadius(i) > 1.0 * CLHEP::micrometer) {
            G4double rInner, rOuter;
            GetBinBoundaries(i, rInner, rOuter);
            backscatterEnergy += normalizedPSF[i] * CLHEP::pi * (rOuter * rOuter - rInner * rInner);
            if (backscatterEnergy > 0.9 * beta) {
                eta = GetBinRadius(i);
                break;
            }
        }
    }

    G4cout << "\nPSF Parameters for BEAMER:" << G4endl;
    G4cout << "  Forward scatter fraction (alpha): " << alpha << G4endl;
    G4cout << "  Backscatter fraction (beta): " << beta << G4endl;
    G4cout << "  Backscatter range (eta): " << eta / CLHEP::micrometer << " um" << G4endl;
}

void RunAction::Save2DFormat(const std::string& outputDir)
{
    std::string filename = outputDir.empty() ? "ebl_2d_data.csv" : outputDir + "/ebl_2d_data.csv";
    G4cout << "Saving 2D depth-radius data to: " << filename << G4endl;

    std::ofstream file(filename);
    if (!file.is_open()) {
        G4cerr << "Error: Could not open 2D output file: " << filename << G4endl;
        return;
    }

    // Write header with radius bins
    file << "Depth(nm)";
    for (G4int r = 0; r < EBL::PSF::NUM_RADIAL_BINS; r++) {
        G4double radius = GetBinRadius(r);
        file << "," << radius / CLHEP::nanometer;
    }
    file << std::endl;

    // Define depth range
    const G4double minDepth = -50.0 * CLHEP::micrometer;
    const G4double maxDepth = 150.0 * CLHEP::nanometer;
    const G4double depthRange = maxDepth - minDepth;
    const G4int numDepthBins = 100;

    // Write data rows
    for (G4int d = 0; d < numDepthBins; d++) {
        G4double depth = minDepth + (d + 0.5) * depthRange / numDepthBins;
        file << depth / CLHEP::nanometer;

        for (G4int r = 0; r < EBL::PSF::NUM_RADIAL_BINS; r++) {
            G4double rInner, rOuter;
            GetBinBoundaries(r, rInner, rOuter);
            G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

            G4double energyDensity = 0.0;
            if (area > 0 && fNumEvents > 0 && d < static_cast<G4int>(f2DEnergyProfile.size())) {
                energyDensity = f2DEnergyProfile[d][r] / (area * fNumEvents);
            }

            file << "," << energyDensity / (CLHEP::eV / (CLHEP::nanometer * CLHEP::nanometer));
        }
        file << std::endl;
    }

    file.close();
    G4cout << "2D data saved successfully" << G4endl;
}

void RunAction::SaveSummary(const std::string& outputDir)
{
    std::string summaryPath = outputDir.empty() ? "simulation_summary.txt" : outputDir + "/simulation_summary.txt";
    std::ofstream summaryFile(summaryPath);

    summaryFile << "EBL Simulation Summary" << std::endl;
    summaryFile << "=====================" << std::endl;
    summaryFile << "Events simulated: " << fNumEvents << std::endl;
    summaryFile << "Total energy deposited: " << G4BestUnit(fTotalEnergyDeposit.GetValue(), "Energy") << std::endl;

    if (G4Threading::IsMultithreadedApplication()) {
        summaryFile << "Threading mode: Multithreaded ("
            << G4Threading::GetNumberOfRunningWorkerThreads() << " threads)" << std::endl;
    }
    else {
        summaryFile << "Threading mode: Sequential" << std::endl;
    }

    summaryFile << "\nEnergy by region:" << std::endl;

    G4double totalE = fTotalEnergyDeposit.GetValue();
    if (totalE > 0) {
        summaryFile << "  Resist: " << G4BestUnit(fResistEnergyTotal.GetValue(), "Energy")
            << " (" << (fResistEnergyTotal.GetValue() / totalE * 100) << "%)" << std::endl;
        summaryFile << "  Substrate: " << G4BestUnit(fSubstrateEnergyTotal.GetValue(), "Energy")
            << " (" << (fSubstrateEnergyTotal.GetValue() / totalE * 100) << "%)" << std::endl;
        summaryFile << "  Above resist: " << G4BestUnit(fAboveResistEnergyTotal.GetValue(), "Energy")
            << " (" << (fAboveResistEnergyTotal.GetValue() / totalE * 100) << "%)" << std::endl;
    }

    // Find energy distribution statistics - FIXED VERSION for r=0 spike
    G4double e50 = 0, e90 = 0, e99 = 0;  // Radii containing 50%, 90%, 99% of energy
    G4double cumulativeEnergy = 0;
    G4double totalRadialEnergy = 0;

    // First calculate total energy in the radial profile
    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        totalRadialEnergy += fRadialEnergyProfile[i];
    }

    // Debug output
    summaryFile << "\nDebug: Total radial energy = " << G4BestUnit(totalRadialEnergy, "Energy") << std::endl;
    if (fRadialEnergyProfile.size() > 0) {
        summaryFile << "Debug: Energy in first bin = " << G4BestUnit(fRadialEnergyProfile[0], "Energy")
            << " (" << (totalRadialEnergy > 0 ? fRadialEnergyProfile[0] / totalRadialEnergy * 100 : 0) << "%)" << std::endl;
    }

    // Now find the radii - start from bin 1 to skip the r=0 singularity if needed
    G4double energyPerEvent = totalRadialEnergy / fNumEvents;

    // Check if most energy is in the first bin (r=0 spike)
    G4bool skipFirstBin = false;
    if (fRadialEnergyProfile.size() > 0 && totalRadialEnergy > 0) {
        G4double firstBinFraction = fRadialEnergyProfile[0] / totalRadialEnergy;
        if (firstBinFraction > 0.8) {  // If >80% of energy is at r=0
            skipFirstBin = true;
            summaryFile << "Note: " << (firstBinFraction * 100) << "% of energy at beam center, analyzing scattered energy only" << std::endl;
        }
    }

    // Calculate percentiles
    G4int startBin = skipFirstBin ? 1 : 0;
    G4double adjustedTotal = 0;

    // Recalculate total without first bin if skipping
    if (skipFirstBin) {
        for (G4int i = startBin; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
            adjustedTotal += fRadialEnergyProfile[i];
        }
    }
    else {
        adjustedTotal = totalRadialEnergy;
    }

    // Find percentiles
    if (adjustedTotal > 0) {
        for (G4int i = startBin; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
            cumulativeEnergy += fRadialEnergyProfile[i];
            G4double fraction = cumulativeEnergy / adjustedTotal;

            if (fraction >= 0.5 && e50 == 0) e50 = GetBinRadius(i);
            if (fraction >= 0.9 && e90 == 0) e90 = GetBinRadius(i);
            if (fraction >= 0.99 && e99 == 0) e99 = GetBinRadius(i);
        }
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

        // Output composition
        auto elements = fDetConstruction->GetResistElements();
        if (!elements.empty()) {
            summaryFile << "Composition: ";
            bool first = true;
            for (const auto& elem : elements) {
                if (!first) summaryFile << ", ";
                summaryFile << elem.first << ":" << elem.second;
                first = false;
            }
            summaryFile << std::endl;
        }
    }

    summaryFile.close();
    G4cout << "Summary saved to: " << summaryPath << G4endl;
}

