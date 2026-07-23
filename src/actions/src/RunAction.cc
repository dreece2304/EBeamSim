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
      fOverflowEnergyTotal("OverflowEnergy", 0.0),
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
    accumulableManager->RegisterAccumulable(&fOverflowEnergyTotal);

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
        // (Geant4 guarantees master EndOfRunAction runs after all workers finish)
        if (G4Threading::IsMultithreadedApplication()) {
            G4AutoLock lock(&arrayMergeMutex);
            fRadialEnergyProfile = fMasterRadialProfile;  // Copy, don't move (master arrays reused)
            f2DEnergyProfile = fMaster2DProfile;
        }

        fNumEvents = nofEvents;

        // Save results
        SaveResults();

        // Concise summary
        G4double resistFraction = fTotalEnergyDeposit.GetValue() > 0 ?
            fResistEnergyTotal.GetValue() / fTotalEnergyDeposit.GetValue() * 100.0 : 0.0;
        G4double eventsPerSec = duration.count() > 0 ? nofEvents / duration.count() : 0;

        G4cout << "Run complete: " << nofEvents << " events in " << duration.count() << "s"
               << " (" << eventsPerSec << " evt/s), "
               << std::fixed << std::setprecision(1) << resistFraction << "% in resist" << G4endl;
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

void RunAction::AddRegionEnergy(G4double resist, G4double substrate, G4double above,
                                G4double overflow)
{
    // Update scalar accumulables (optimized with single conditionals)
    if (resist > 0.0) fResistEnergyTotal += resist;
    if (substrate > 0.0) fSubstrateEnergyTotal += substrate;
    if (above > 0.0) fAboveResistEnergyTotal += above;
    if (overflow > 0.0) fOverflowEnergyTotal += overflow;
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
    std::string outputDir = fOutputDirectory.empty() ?
        EBL::Output::DEFAULT_DIRECTORY :
        std::string(fOutputDirectory);

    if (!outputDir.empty()) {
        try {
            std::filesystem::create_directories(outputDir);
        }
        catch (const std::exception&) {
            outputDir = "";
        }
    }

    // Save all output files
    SaveCSVFormat(outputDir);
    SaveBEAMERFormat(outputDir);
    SaveSummary(outputDir);
    Save2DFormat(outputDir);
    SaveEnergyEquivalenceReport(outputDir);
}

void RunAction::SaveCSVFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fPSFFilename) :
        actualOutputDir + "/" + std::string(fPSFFilename);

    std::ofstream psfFile(outputPath);
    if (!psfFile.is_open()) {
        G4cerr << "Error: Could not open: " << outputPath << G4endl;
        return;
    }

    psfFile << "Radius(nm),EnergyDeposition(eV/nm^2),BinLower(nm),BinUpper(nm),Events" << std::endl;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rCenter = GetBinRadius(i);
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);

        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);
        G4double energyDensity = (area > 0 && fNumEvents > 0) ?
            fRadialEnergyProfile[i] / (area * fNumEvents) : 0.0;

        psfFile << std::fixed << std::setprecision(3) << rCenter / CLHEP::nanometer << ","
                << std::scientific << std::setprecision(6) << energyDensity / (CLHEP::eV / (CLHEP::nanometer * CLHEP::nanometer)) << ","
                << std::fixed << std::setprecision(3) << rInner / CLHEP::nanometer << ","
                << rOuter / CLHEP::nanometer << ","
                << fNumEvents
                << std::endl;
    }

    psfFile.close();
}

void RunAction::SaveBEAMERFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fBeamerFilename) :
        actualOutputDir + "/" + std::string(fBeamerFilename);

    std::ofstream beamerFile(outputPath);
    if (!beamerFile.is_open()) {
        G4cerr << "Error: Could not open: " << outputPath << G4endl;
        return;
    }

    // Normalize PSF
    std::vector<G4double> normalizedPSF(EBL::PSF::NUM_RADIAL_BINS);
    G4double maxValue = 0.0;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);
        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);

        if (fNumEvents > 0 && area > 0) {
            normalizedPSF[i] = fRadialEnergyProfile[i] / (area * fNumEvents);
            if (normalizedPSF[i] > maxValue) maxValue = normalizedPSF[i];
        }
    }

    if (maxValue > 0) {
        for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
            normalizedPSF[i] /= maxValue;
        }
    }

    // Write header
    beamerFile << "# EBL PSF for BEAMER - Geant4 Simulation" << std::endl;
    beamerFile << "# Beam: " << PrimaryGeneratorAction::GetGlobalBeamEnergy() / CLHEP::keV << " keV, ";
    beamerFile << "Resist: " << (fDetConstruction ? fDetConstruction->GetActualResistThickness() / CLHEP::nanometer : 30.0) << " nm" << std::endl;
    beamerFile << "# Events: " << fNumEvents << std::endl;

    beamerFile << std::scientific << std::setprecision(6);

    if (normalizedPSF[0] > 0) {
        beamerFile << EBL::PSF::MIN_RADIUS / 2.0 / CLHEP::micrometer << " " << normalizedPSF[0] << std::endl;
    }

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; i++) {
        if (normalizedPSF[i] > 1e-12) {
            beamerFile << GetBinRadius(i) / CLHEP::micrometer << " " << normalizedPSF[i] << std::endl;
        }
    }

    beamerFile.close();
}

void RunAction::Save2DFormat(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string outputPath = actualOutputDir.empty() ?
        std::string(fPSF2DFilename) :
        actualOutputDir + "/" + std::string(fPSF2DFilename);

    std::ofstream file(outputPath);
    if (!file.is_open()) {
        G4cerr << "Error: Could not open: " << outputPath << G4endl;
        return;
    }

    if (f2DEnergyProfile.empty() || f2DEnergyProfile[0].empty()) {
        file << "# No 2D data collected" << std::endl;
        file.close();
        return;
    }

    G4double resistThickness = fDetConstruction ? fDetConstruction->GetActualResistThickness() : 30.0*CLHEP::nanometer;
    G4double totalDepth = resistThickness + 50.0*CLHEP::nanometer;

    // Header row with radius values
    file << "depth_nm";
    for (size_t j = 0; j < f2DEnergyProfile[0].size(); ++j) {
        G4double radius = (j + 0.5) * 50.0*CLHEP::micrometer / f2DEnergyProfile[0].size();
        file << "," << std::fixed << std::setprecision(1) << radius/CLHEP::nanometer;
    }
    file << std::endl;

    // Data rows
    for (size_t i = 0; i < f2DEnergyProfile.size(); ++i) {
        G4double depth = -50.0*CLHEP::nanometer + (i + 0.5) * totalDepth / f2DEnergyProfile.size();
        file << std::fixed << std::setprecision(2) << depth/CLHEP::nanometer;

        for (size_t j = 0; j < f2DEnergyProfile[i].size(); ++j) {
            file << "," << std::scientific << std::setprecision(6) << f2DEnergyProfile[i][j]/CLHEP::eV;
        }
        file << std::endl;
    }

    file.close();
}

void RunAction::SaveSummary(const std::string& outputDir)
{
    std::string actualOutputDir = fOutputDirectory.empty() ? outputDir : std::string(fOutputDirectory);
    std::string summaryPath = actualOutputDir.empty() ?
        std::string(fSummaryFilename) :
        actualOutputDir + "/" + std::string(fSummaryFilename);

    std::ofstream summaryFile(summaryPath);
    if (!summaryFile.is_open()) return;

    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(endTime - fStartTime);

    summaryFile << "BEAMER PSF Simulation Summary\n";
    summaryFile << "Events: " << fNumEvents << "\n";
    summaryFile << "Energy in resist: " << fResistEnergyTotal.GetValue()/CLHEP::eV << " eV\n";

    if (fTotalEnergyDeposit.GetValue() > 0) {
        summaryFile << "Resist fraction: " << fResistEnergyTotal.GetValue() / fTotalEnergyDeposit.GetValue() * 100 << "%\n";
    }

    // Energy deposited in resist beyond PSF::MAX_RADIUS (excluded from PSF bins)
    if (fResistEnergyTotal.GetValue() > 0) {
        summaryFile << "Overflow beyond PSF max radius: "
                    << fOverflowEnergyTotal.GetValue()/CLHEP::eV << " eV ("
                    << fOverflowEnergyTotal.GetValue() / fResistEnergyTotal.GetValue() * 100
                    << "% of resist energy)\n";
    }

    summaryFile << "Time: " << duration.count() << "s";
    if (duration.count() > 0) {
        summaryFile << " (" << fNumEvents / duration.count() << " evt/s)";
    }
    summaryFile << "\n";

    summaryFile << "Beam: " << PrimaryGeneratorAction::GetGlobalBeamEnergy()/CLHEP::keV << " keV\n";
    if (fDetConstruction) {
        summaryFile << "Resist: " << fDetConstruction->GetActualResistThickness()/CLHEP::nanometer << " nm, "
                   << fDetConstruction->GetResistDensity()/(CLHEP::g/CLHEP::cm3) << " g/cm3\n";
    }

    summaryFile.close();
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

    std::ofstream reportFile(equivalencePath);
    if (!reportFile.is_open()) return;

    G4double energyPerPrimary_eV = GetPerPrimaryResistEnergyAbsorption() / CLHEP::eV;
    G4double K_coefficient = CalculateEnergyAbsorptionCoefficient();

    G4double beamEnergy_keV = PrimaryGeneratorAction::GetGlobalBeamEnergy() / CLHEP::keV;
    G4double resistThickness_nm = fDetConstruction ?
        fDetConstruction->GetActualResistThickness() / CLHEP::nanometer : 30.0;

    reportFile << "E-BEAM TO UV ENERGY EQUIVALENCE REPORT\n\n";
    reportFile << "Beam: " << beamEnergy_keV << " keV, Resist: " << resistThickness_nm << " nm\n";
    reportFile << "Events: " << fNumEvents << "\n\n";
    reportFile << "Energy per primary: " << std::scientific << std::setprecision(4) << energyPerPrimary_eV << " eV\n";
    reportFile << "Absorption coefficient K: " << K_coefficient << " J/cm2 per uC/cm2\n\n";
    reportFile << "Formula: E_abs = K * D, where D = e-beam dose (uC/cm2)\n";
    reportFile << "UV_time = (K * D) / (UV_rate * Absorptance)\n";

    reportFile.close();
}