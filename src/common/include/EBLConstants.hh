// EBLConstants.hh - Complete version with all required constants
#ifndef EBLCONSTANTS_HH
#define EBLCONSTANTS_HH

#include "G4SystemOfUnits.hh"

namespace EBL {
    // Beam parameters
    namespace Beam {
        constexpr G4double DEFAULT_ENERGY = 100.0 * keV;
        constexpr G4double DEFAULT_SPOT_SIZE = 1.0 * nm;
        constexpr G4double POSITION_SIGMA = 0.0 * nm;
        constexpr G4double DEFAULT_POSITION_Z = 100.0 * nm;  // Added
    }

    // PSF calculation parameters
    namespace PSF {
        constexpr G4bool USE_LOG_BINNING = true;
        constexpr G4int NUM_RADIAL_BINS = 200;
        constexpr G4double MIN_RADIUS = 0.1 * nm;
        constexpr G4double MAX_RADIUS = 100.0 * micrometer;

        // Additional parameters for improved calculation
        constexpr G4double OVERFLOW_RADIUS = 1000.0 * micrometer;
        constexpr G4int MIN_COUNTS_FOR_STATISTICS = 10;
        constexpr G4double SMOOTHING_WINDOW_FRACTION = 0.05;
    }

    // Energy thresholds
    namespace Thresholds {
        constexpr G4double MIN_EDEP_TRACKING = 1.0e-3 * eV;
        constexpr G4double ELECTRON_EDEP_FRACTION = 1.0e-6;
        constexpr G4double PHOTON_EDEP_THRESHOLD = 1.0e-2 * eV;
        constexpr G4double MAX_TRACKING_RADIUS = 1000.0 * micrometer;
    }

    // Material parameters - REORGANIZED WITH PROPER NAMESPACES
    namespace Materials {
        // HSQ resist
        namespace HSQ {
            constexpr G4double DENSITY = 1.4 * g / cm3;
            constexpr G4double DEFAULT_THICKNESS = 30.0 * nm;
            constexpr G4int H_ATOMS = 8;
            constexpr G4int Si_ATOMS = 8;
            constexpr G4int O_ATOMS = 12;
        }

        // Substrate
        namespace Substrate {
            constexpr G4double THICKNESS = 500.0 * micrometer;
            constexpr G4double RADIUS = 50.0 * mm;
        }
    }

    // ADD MISSING Resist namespace
    namespace Resist {
        constexpr G4double DEFAULT_THICKNESS = 30.0 * nm;
        constexpr G4double DEFAULT_DENSITY = 1.4 * g / cm3;
    }

    // ADD MISSING Geometry namespace
    namespace Geometry {
        constexpr G4double WORLD_SIZE = 1.0 * mm;
        constexpr G4double SUBSTRATE_THICKNESS = 500.0 * micrometer;
        constexpr G4double SUBSTRATE_RADIUS = 50.0 * mm;
    }

    // Physics parameters
    namespace Physics {
        constexpr G4double ELECTRON_RANGE_CUTOFF = 10.0 * nm;
        constexpr G4double PHOTON_RANGE_CUTOFF = 10.0 * nm;
        constexpr G4double MAX_STEP_SIZE = 5.0 * nm;
        constexpr G4bool USE_ADVANCED_MULTIPLE_SCATTERING = true;
    }

    // Output parameters - FIXED WITH CORRECT NAMES
    namespace Output {
        constexpr const char* DEFAULT_OUTPUT_DIR = "output";  // Fixed name
        constexpr const char* DEFAULT_DIRECTORY = "output";   // Keep for compatibility
        constexpr const char* DEFAULT_FILENAME = "psf_data.csv";
        constexpr const char* PSF_DATA_FILENAME = "psf_data.csv";  // Added
        constexpr const char* BEAMER_FILENAME = "psf_beamer.txt";
        constexpr const char* SUMMARY_FILENAME = "simulation_summary.txt";
        constexpr const char* STATISTICS_FILENAME = "bin_statistics.csv";

        // Output options
        constexpr G4bool SAVE_RAW_DATA = true;
        constexpr G4bool SAVE_SMOOTHED_DATA = true;
        constexpr G4bool SAVE_BIN_STATISTICS = true;
        constexpr G4bool VERBOSE_PROGRESS = true;
    }

    // Analysis parameters
    namespace Analysis {
        // Noise reduction parameters
        constexpr G4int SAVGOL_WINDOW_MIN = 5;
        constexpr G4int SAVGOL_POLYNOMIAL_ORDER = 3;
        constexpr G4double OUTLIER_THRESHOLD_SIGMA = 3.0;

        // Extrapolation parameters
        constexpr G4int TAIL_FIT_BINS = 10;
        constexpr G4double MIN_EXTRAPOLATION_FRACTION = 1.0e-10;

        // Validation parameters
        constexpr G4double ENERGY_CONSERVATION_TOLERANCE = 0.01;
        constexpr G4double POSITION_VALIDATION_MAX = 10.0 * meter;
    }

    // Debug parameters
    namespace Debug {
        constexpr G4bool VERBOSE_SCORING = false;
        constexpr G4int MAX_DEBUG_DEPOSITS = 50;
        constexpr G4int PROGRESS_UPDATE_INTERVAL = 10000;
        constexpr G4bool TRACK_BIN_STATISTICS = true;
        constexpr G4int BIN_STATISTICS_INTERVAL = 100000;
    }
}

#endif // EBLCONSTANTS_HH