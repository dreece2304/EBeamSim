// EBLConstants.hh - BEAMER Optimized Parameters
#ifndef EBLCONSTANTS_HH
#define EBLCONSTANTS_HH

#include "G4SystemOfUnits.hh"

namespace EBL {
    // Beam parameters
    namespace Beam {
        constexpr G4double DEFAULT_ENERGY = 100.0 * keV;
        constexpr G4double DEFAULT_SPOT_SIZE = 1.0 * nm;
        constexpr G4double POSITION_SIGMA = 0.0 * nm;
        constexpr G4double DEFAULT_POSITION_Z = 100.0 * nm;
    }

    // PSF calculation parameters - OPTIMIZED FOR BEAMER
    namespace PSF {
        constexpr G4bool USE_LOG_BINNING = true;
        constexpr G4int NUM_RADIAL_BINS = 150;  // Reduced from 200 for efficiency
        constexpr G4double MIN_RADIUS = 0.5 * nm;  // Slightly larger minimum
        constexpr G4double MAX_RADIUS = 100.0 * micrometer;  // 100 um is sufficient

        // Additional parameters for improved calculation
        constexpr G4double OVERFLOW_RADIUS = 200.0 * micrometer;  // For tracking beyond PSF
        constexpr G4int MIN_COUNTS_FOR_STATISTICS = 10;
        constexpr G4double SMOOTHING_WINDOW_FRACTION = 0.05;
    }

    // Energy thresholds - OPTIMIZED FOR BEAMER
    namespace Thresholds {
        // No filtering in resist for BEAMER accuracy
        constexpr G4double MIN_EDEP_TRACKING = 0.0 * eV;  // Track all energy in resist
        constexpr G4double ELECTRON_EDEP_FRACTION = 0.0;  // No fractional filtering
        constexpr G4double PHOTON_EDEP_THRESHOLD = 0.0 * eV;  // Track all photons in resist
        constexpr G4double MAX_TRACKING_RADIUS = 200.0 * micrometer;  // Beyond PSF max
    }

    // Material parameters
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

    // Resist namespace
    namespace Resist {
        constexpr G4double DEFAULT_THICKNESS = 30.0 * nm;
        constexpr G4double DEFAULT_DENSITY = 1.4 * g / cm3;
    }

    // Geometry namespace
    namespace Geometry {
        constexpr G4double WORLD_SIZE = 200.0 * mm;  // Large enough to contain substrate
        constexpr G4double SUBSTRATE_THICKNESS = 500.0 * micrometer;
        constexpr G4double SUBSTRATE_RADIUS = 50.0 * mm;
    }

    // Physics parameters - OPTIMIZED FOR BEAMER
    namespace Physics {
        // Fine in resist, coarse elsewhere
        constexpr G4double ELECTRON_RANGE_CUTOFF = 10.0 * nm;
        constexpr G4double PHOTON_RANGE_CUTOFF = 10.0 * nm;
        constexpr G4double MAX_STEP_SIZE = 5.0 * nm;
        constexpr G4bool USE_ADVANCED_MULTIPLE_SCATTERING = true;
    }

    // Output parameters - STREAMLINED FOR BEAMER
    namespace Output {
        constexpr const char* DEFAULT_OUTPUT_DIR = "output";
        constexpr const char* DEFAULT_DIRECTORY = "output";
        constexpr const char* DEFAULT_FILENAME = "psf_data.csv";
        constexpr const char* PSF_DATA_FILENAME = "psf_data.csv";
        constexpr const char* BEAMER_FILENAME = "psf_beamer.txt";  // Direct BEAMER format
        constexpr const char* SUMMARY_FILENAME = "simulation_summary.txt";
        constexpr const char* STATISTICS_FILENAME = "bin_statistics.csv";

        // Output options - OPTIMIZED FOR BEAMER
        constexpr G4bool SAVE_RAW_DATA = true;
        constexpr G4bool SAVE_SMOOTHED_DATA = false;  // Do smoothing in post
        constexpr G4bool SAVE_BIN_STATISTICS = false;  // Not needed for production
        constexpr G4bool VERBOSE_PROGRESS = false;  // Minimize output overhead
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

    // Debug parameters - MINIMIZED FOR PRODUCTION
    namespace Debug {
        constexpr G4bool VERBOSE_SCORING = false;  // Off for production
        constexpr G4int MAX_DEBUG_DEPOSITS = 0;    // No debug output
        constexpr G4int PROGRESS_UPDATE_INTERVAL = 100000;  // Less frequent updates
        constexpr G4bool TRACK_BIN_STATISTICS = false;  // Off for production
        constexpr G4int BIN_STATISTICS_INTERVAL = 1000000;  // Very infrequent
    }
}

#endif // EBLCONSTANTS_HH