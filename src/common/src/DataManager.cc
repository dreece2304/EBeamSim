#include "DataManager.hh"
#include "EBLConstants.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <cmath>

// Initialize static member
DataManager* DataManager::fInstance = nullptr;

DataManager* DataManager::Instance() {
    if (!fInstance) {
        fInstance = new DataManager();
    }
    return fInstance;
}

DataManager::DataManager()
    : fOutputDir(EBL::Output::DEFAULT_OUTPUT_DIR),
    fRunID(0),
    fTotalEvents(0),
    fProcessedEvents(0),
    fLiveMonitoring(false) {
    // Initialize with default number of bins
    InitializePSFBins(EBL::PSF::NUM_RADIAL_BINS);
}

DataManager::~DataManager() {
    // Clean up and save any remaining data
    if (fLiveDataStream && fLiveDataStream->is_open()) {
        fLiveDataStream->close();
    }
}

void DataManager::InitializePSFBins(G4int nBins) {
    fRadialEnergyProfile.clear();
    fRadialEnergyProfile.resize(nBins, 0.0);

    fRadialBinCenters.clear();
    fRadialBinCenters.resize(nBins);

    // Pre-calculate bin centers
    for (G4int i = 0; i < nBins; ++i) {
        fRadialBinCenters[i] = GetBinRadius(i);
    }
}

void DataManager::SetOutputDirectory(const G4String& dir) {
    fOutputDir = dir;
    CreateOutputDirectory();
}

void DataManager::CreateOutputDirectory() {
    try {
        std::filesystem::create_directories(fOutputDir);
    }
    catch (const std::exception& e) {
        G4cerr << "Warning: Could not create output directory: " << e.what() << G4endl;
    }
}

void DataManager::BeginRun(G4int runID, G4int nEvents) {
    fRunID = runID;
    fTotalEvents = nEvents;
    fProcessedEvents = 0;

    // Reset data
    std::fill(fRadialEnergyProfile.begin(), fRadialEnergyProfile.end(), 0.0);

    // Open live monitoring file if enabled
    if (fLiveMonitoring) {
        std::string liveFile = fOutputDir + "/live_data.csv";
        fLiveDataStream = std::make_unique<std::ofstream>(liveFile);
        *fLiveDataStream << "Event,Progress,TotalEnergy" << std::endl;
    }

    G4cout << "DataManager: Starting run " << runID << " with " << nEvents << " events" << G4endl;
}

void DataManager::EndRun() {
    G4cout << "DataManager: Run " << fRunID << " complete. "
        << fProcessedEvents << "/" << fTotalEvents << " events processed." << G4endl;

    // Save all data
    SaveAllData();

    // Close live monitoring
    if (fLiveDataStream && fLiveDataStream->is_open()) {
        fLiveDataStream->close();
    }
}

void DataManager::BeginEvent(G4int eventID) {
    fEventDeposits.clear();
}

void DataManager::EndEvent() {
    fProcessedEvents++;

    // Process event deposits
    for (const auto& deposit : fEventDeposits) {
        G4int bin = GetRadialBin(deposit.first);
        if (bin >= 0 && bin < static_cast<G4int>(fRadialEnergyProfile.size())) {
            fRadialEnergyProfile[bin] += deposit.second;
        }
    }

    // Live monitoring update
    if (fLiveMonitoring && fLiveDataStream && fProcessedEvents % 1000 == 0) {
        G4double totalEnergy = 0;
        for (const auto& e : fRadialEnergyProfile) {
            totalEnergy += e;
        }
        *fLiveDataStream << fProcessedEvents << ","
            << GetCurrentProgress() << ","
            << totalEnergy / eV << std::endl;
    }
}

void DataManager::AddRadialDeposit(G4double radius, G4double energy) {
    fEventDeposits.push_back({ radius, energy });
}

G4double DataManager::GetBinRadius(G4int bin) const {
    if (bin < 0 || bin >= EBL::PSF::NUM_RADIAL_BINS) return 0.0;

    if (!EBL::PSF::USE_LOG_BINNING) {
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        return (bin + 0.5) * binWidth;
    }

    // Logarithmic binning
    G4double logMin = std::log(EBL::PSF::MIN_RADIUS);
    G4double logMax = std::log(EBL::PSF::MAX_RADIUS);
    G4double logStep = (logMax - logMin) / EBL::PSF::NUM_RADIAL_BINS;

    G4double logLower = logMin + bin * logStep;
    G4double logUpper = logMin + (bin + 1) * logStep;
    G4double logCenter = (logLower + logUpper) / 2.0;

    return std::exp(logCenter);
}

void DataManager::GetBinBoundaries(G4int bin, G4double& rInner, G4double& rOuter) const {
    if (!EBL::PSF::USE_LOG_BINNING) {
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
        rInner = 0.0;
        rOuter = std::exp(logMin + logStep);
    }
    else {
        rInner = std::exp(logMin + bin * logStep);
        rOuter = std::exp(logMin + (bin + 1) * logStep);
    }
}

G4int DataManager::GetRadialBin(G4double radius) const {
    if (!EBL::PSF::USE_LOG_BINNING) {
        G4double binWidth = EBL::PSF::MAX_RADIUS / EBL::PSF::NUM_RADIAL_BINS;
        G4int bin = static_cast<G4int>(radius / binWidth);
        return std::min(bin, EBL::PSF::NUM_RADIAL_BINS - 1);
    }

    // Logarithmic binning
    if (radius <= 0) return -1;
    if (radius < EBL::PSF::MIN_RADIUS) return 0;
    if (radius >= EBL::PSF::MAX_RADIUS) return EBL::PSF::NUM_RADIAL_BINS - 1;

    G4double logRatio = std::log(radius / EBL::PSF::MIN_RADIUS) /
        std::log(EBL::PSF::MAX_RADIUS / EBL::PSF::MIN_RADIUS);
    G4int bin = static_cast<G4int>(logRatio * (EBL::PSF::NUM_RADIAL_BINS - 1));

    return std::max(0, std::min(bin, EBL::PSF::NUM_RADIAL_BINS - 1));
}

void DataManager::SavePSFData() {
    std::string filename = fOutputDir + "/" + EBL::Output::PSF_DATA_FILENAME;
    std::ofstream file(filename);

    if (!file.is_open()) {
        G4cerr << "Error: Could not open file " << filename << G4endl;
        return;
    }

    file << "Radius(nm),EnergyDeposition(eV/nm^2),BinLower(nm),BinUpper(nm),Events" << std::endl;

    for (G4int i = 0; i < EBL::PSF::NUM_RADIAL_BINS; ++i) {
        G4double rCenter = GetBinRadius(i);
        G4double rInner, rOuter;
        GetBinBoundaries(i, rInner, rOuter);

        G4double area = CLHEP::pi * (rOuter * rOuter - rInner * rInner);
        G4double energyDensity = (area > 0 && fProcessedEvents > 0) ?
            fRadialEnergyProfile[i] / (area * fProcessedEvents) : 0.0;

        file << std::fixed << std::setprecision(3) << rCenter / nanometer << ","
            << std::scientific << std::setprecision(6) << energyDensity / (eV / (nanometer * nanometer)) << ","
            << std::fixed << std::setprecision(3) << rInner / nanometer << ","
            << rOuter / nanometer << ","
            << fProcessedEvents << std::endl;
    }

    file.close();
    G4cout << "PSF data saved to: " << filename << G4endl;
}

void DataManager::SaveAllData() {
    SavePSFData();
    SaveBEAMERFormat();
    SaveSummary();
}

G4double DataManager::GetCurrentProgress() const {
    return (fTotalEvents > 0) ?
        static_cast<G4double>(fProcessedEvents) / fTotalEvents : 0.0;
}

// Implement SaveBEAMERFormat() and SaveSummary() similar to RunAction
void DataManager::SaveBEAMERFormat() {
    // Implementation similar to RunAction::SaveBEAMERFormat()
}

void DataManager::SaveSummary() {
    // Implementation similar to RunAction::SaveSummary()
}