#include "DataManager.hh"
#include "DataMessenger.hh"
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
    fLiveMonitoring(false),
    fPatternMode(false),
    fNx(0), fNy(0), fNz(0),
    fXMin(0), fXMax(0), fYMin(0), fYMax(0), fZMin(0), fZMax(0),
    fDx(0), fDy(0), fDz(0),
    fBeamCurrent(2.0), fElectronsPerPoint(1), fTotalPatternPoints(0),
    fMessenger(nullptr) {
    // Initialize with default number of bins
    InitializePSFBins(EBL::PSF::NUM_RADIAL_BINS);
    
    // Create messenger
    fMessenger = new DataMessenger(this);
}

DataManager::~DataManager() {
    // Clean up and save any remaining data
    if (fLiveDataStream && fLiveDataStream->is_open()) {
        fLiveDataStream->close();
    }
    delete fMessenger;
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
        std::filesystem::create_directories(std::string(fOutputDir));
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
    if (fPatternMode) {
        SaveDoseDistribution();
    } else {
        SavePSFData();
        SaveBEAMERFormat();
    }
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
void DataManager::AddPSFData(G4double radius, G4double energy) {
    // Wrapper function for PSF data collection
    // Simply delegates to AddRadialDeposit
    this->AddRadialDeposit(radius, energy);
}

// Pattern exposure methods
void DataManager::InitializeDoseGrid(G4int nx, G4int ny, G4int nz,
                                    G4double xMin, G4double xMax,
                                    G4double yMin, G4double yMax,
                                    G4double zMin, G4double zMax) {
    fNx = nx; fNy = ny; fNz = nz;
    fXMin = xMin; fXMax = xMax;
    fYMin = yMin; fYMax = yMax;
    fZMin = zMin; fZMax = zMax;
    
    // Calculate grid spacing
    fDx = (xMax - xMin) / nx;
    fDy = (yMax - yMin) / ny;
    fDz = (zMax - zMin) / nz;
    
    // Initialize 3D dose grid
    fDoseGrid.clear();
    fDoseGrid.resize(nx, std::vector<std::vector<G4double>>(ny, std::vector<G4double>(nz, 0.0)));
    
    G4cout << "Initialized dose grid: " << nx << "x" << ny << "x" << nz 
           << " cells, spacing: " << fDx/nm << "x" << fDy/nm << "x" << fDz/nm << " nm" << G4endl;
}

void DataManager::AddDoseDeposit(const G4ThreeVector& position, G4double energy) {
    // Find grid indices
    G4int ix = static_cast<G4int>(std::floor((position.x() - fXMin) / fDx));
    G4int iy = static_cast<G4int>(std::floor((position.y() - fYMin) / fDy));
    G4int iz = static_cast<G4int>(std::floor((position.z() - fZMin) / fDz));
    
    // Check bounds
    if (ix >= 0 && ix < fNx && iy >= 0 && iy < fNy && iz >= 0 && iz < fNz) {
        // Accumulate dose (energy deposited in this voxel)
        // Using atomic operations would be better for thread safety if using MT
        fDoseGrid[ix][iy][iz] += energy;
    }
}

void DataManager::SaveDoseDistribution() {
    std::string filename = fOutputDir + "/pattern_dose_distribution.csv";
    std::ofstream file(filename);
    
    if (!file.is_open()) {
        G4cerr << "Error: Could not open file " << filename << G4endl;
        return;
    }
    
    // Calculate dose conversion factor
    // Energy (keV) to dose (μC/cm²) conversion
    // Total charge = beam current × time = I × (n_points × dwell_time)
    // For normalization: dose per voxel = energy_deposited / (electrons_per_voxel × elementary_charge)
    // Then convert to μC/cm²
    G4double voxelArea = (fDx * fDy) / (cm * cm);  // Convert nm² to cm²
    G4double eCharge = 1.602176634e-19;  // Coulombs
    G4double keVToJoules = 1.602176634e-16;  // J/keV
    
    // Write header
    file << "# Pattern Dose Distribution" << std::endl;
    file << "# Grid: " << fNx << "x" << fNy << "x" << fNz << std::endl;
    file << "# Bounds: X[" << fXMin/nm << "," << fXMax/nm << "] Y[" 
         << fYMin/nm << "," << fYMax/nm << "] Z[" << fZMin/nm << "," << fZMax/nm << "] nm" << std::endl;
    file << "# Beam current: " << fBeamCurrent << " nA" << std::endl;
    file << "# Electrons per point: " << fElectronsPerPoint << std::endl;
    file << "X[nm],Y[nm],Z[nm],Energy[keV],Dose[uC/cm^2]" << std::endl;
    
    // Write dose data (only non-zero values to save space)
    for (G4int ix = 0; ix < fNx; ix++) {
        for (G4int iy = 0; iy < fNy; iy++) {
            for (G4int iz = 0; iz < fNz; iz++) {
                if (fDoseGrid[ix][iy][iz] > 0) {
                    G4double x = fXMin + (ix + 0.5) * fDx;
                    G4double y = fYMin + (iy + 0.5) * fDy;
                    G4double z = fZMin + (iz + 0.5) * fDz;
                    G4double energyKeV = fDoseGrid[ix][iy][iz]/keV;
                    
                    // Convert energy to dose
                    // The energy deposited represents the total from all electrons
                    // Dose (uC/cm^2) = (Energy deposited / Energy per electron) x (e charge / area)
                    // This is a simplified conversion - in reality need to track actual electrons
                    G4double dose = (energyKeV * eCharge * 1e6) / (voxelArea * fElectronsPerPoint * 100.0 * keV);
                    
                    file << x/nm << "," << y/nm << "," << z/nm << "," 
                         << energyKeV << "," << dose << std::endl;
                }
            }
        }
    }
    
    // Also save 2D projection (XY plane at resist surface)
    std::string filename2d = fOutputDir + "/pattern_dose_2d.csv";
    std::ofstream file2d(filename2d);
    file2d << "# 2D Dose Distribution (XY projection)" << std::endl;
    file2d << "# Integrated through Z-direction" << std::endl;
    file2d << "X[nm],Y[nm],Energy[keV],Dose[uC/cm^2]" << std::endl;
    
    // Sum dose through Z for 2D projection
    for (G4int ix = 0; ix < fNx; ix++) {
        for (G4int iy = 0; iy < fNy; iy++) {
            G4double totalDose = 0;
            for (G4int iz = 0; iz < fNz; iz++) {
                totalDose += fDoseGrid[ix][iy][iz];
            }
            if (totalDose > 0) {
                G4double x = fXMin + (ix + 0.5) * fDx;
                G4double y = fYMin + (iy + 0.5) * fDy;
                G4double energyKeV = totalDose/keV;
                G4double dose = (energyKeV * eCharge * 1e6) / (voxelArea * fElectronsPerPoint * 100.0 * keV);
                file2d << x/nm << "," << y/nm << "," << energyKeV << "," << dose << std::endl;
            }
        }
    }
    
    file.close();
    file2d.close();
    G4cout << "Pattern dose data saved to: " << filename << " and " << filename2d << G4endl;
}