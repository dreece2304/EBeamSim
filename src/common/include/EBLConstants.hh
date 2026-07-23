// EBLConstants.hh - BEAMER Optimized Parameters (C++17 constexpr)
#ifndef EBLCONSTANTS_HH
#define EBLCONSTANTS_HH

#include "G4SystemOfUnits.hh"

namespace EBL {
    // Beam parameters (C++17 constexpr with inline)
    // NOTE: Point source (0nm) is used for PSF generation because BEAMER
    // applies short-range blur correction for beam diameter separately.
    // Using finite beam size here would double-count the blur effect.
    namespace Beam {
        inline constexpr G4double DEFAULT_ENERGY = 100.0 * keV;
        inline constexpr G4double DEFAULT_SPOT_SIZE = 0.0 * nm;  // Point source for PSF (BEAMER handles blur)
        inline constexpr G4double POSITION_SIGMA = 0.0 * nm;
        inline constexpr G4double DEFAULT_POSITION_Z = 1.0 * nm;  // Dynamic: 1nm above resist surface
    }

    // PSF calculation parameters - OPTIMIZED FOR BEAMER (inline constexpr)
    namespace PSF {
        inline constexpr G4bool USE_LOG_BINNING = true;
        inline constexpr G4int NUM_RADIAL_BINS = 150;  // Reduced from 200 for efficiency
        inline constexpr G4double MIN_RADIUS = 0.5 * nm;  // Slightly larger minimum
        inline constexpr G4double MAX_RADIUS = 100.0 * micrometer;  // 100 um is sufficient

        // Additional parameters for improved calculation
        inline constexpr G4double OVERFLOW_RADIUS = 200.0 * micrometer;  // For tracking beyond PSF
        inline constexpr G4int MIN_COUNTS_FOR_STATISTICS = 10;
        inline constexpr G4double SMOOTHING_WINDOW_FRACTION = 0.05;
    }

    // Energy thresholds - OPTIMIZED FOR BEAMER (inline constexpr)
    namespace Thresholds {
        // No filtering in resist for BEAMER accuracy
        inline constexpr G4double MIN_EDEP_TRACKING = 0.0 * eV;  // Track all energy in resist
        inline constexpr G4double ELECTRON_EDEP_FRACTION = 0.0;  // No fractional filtering
        inline constexpr G4double PHOTON_EDEP_THRESHOLD = 0.0 * eV;  // Track all photons in resist
        inline constexpr G4double MAX_TRACKING_RADIUS = 200.0 * micrometer;  // Beyond PSF max
    }

    // Material parameters (inline constexpr for better performance)
    namespace Materials {
        // HSQ resist composition and properties
        namespace HSQ {
            inline constexpr G4double DENSITY = 1.4 * g / cm3;
            inline constexpr G4double DEFAULT_THICKNESS = 30.0 * nm;
            inline constexpr G4int H_ATOMS = 8;
            inline constexpr G4int Si_ATOMS = 8;
            inline constexpr G4int O_ATOMS = 12;
            
            // Derived properties for optimization
            inline constexpr G4int TOTAL_ATOMS = H_ATOMS + Si_ATOMS + O_ATOMS;  // 28 atoms total
        }

        // Substrate properties
        namespace Substrate {
            inline constexpr G4double THICKNESS = 500.0 * micrometer;
            inline constexpr G4double RADIUS = 50.0 * mm;
        }
    }

    // Resist namespace (consolidated with Materials::HSQ for consistency)
    namespace Resist {
        inline constexpr G4double DEFAULT_THICKNESS = Materials::HSQ::DEFAULT_THICKNESS;
        inline constexpr G4double DEFAULT_DENSITY = Materials::HSQ::DENSITY;
    }

    // Geometry namespace (inline constexpr)
    namespace Geometry {
        inline constexpr G4double WORLD_SIZE = 1.0 * mm;  // Enough to contain 500um substrate + margin
        inline constexpr G4double SUBSTRATE_THICKNESS = Materials::Substrate::THICKNESS;
        inline constexpr G4double SUBSTRATE_RADIUS = Materials::Substrate::RADIUS;
        // Lateral (full-width) extent of substrate and resist. Half-width must cover
        // PSF::MAX_RADIUS plus the ~70um electron range in Si at 100 keV so the
        // backscatter tail is not truncated by electrons escaping the substrate side.
        // Must equal 2 * Thresholds::MAX_TRACKING_RADIUS.
        inline constexpr G4double SUBSTRATE_XY = 400.0 * micrometer;
    }

    // Physics parameters - OPTIMIZED FOR BEAMER (inline constexpr)
    namespace Physics {
        // Production cuts - fine in resist, coarse elsewhere
        inline constexpr G4double ELECTRON_RANGE_CUTOFF = 10.0 * nm;
        inline constexpr G4double PHOTON_RANGE_CUTOFF = 10.0 * nm;
        inline constexpr G4double MAX_STEP_SIZE = 2.0 * nm;  // Fine stepping for energy density maps
        inline constexpr G4bool USE_ADVANCED_MULTIPLE_SCATTERING = true;

        // Region-specific cuts for Geant4 11.3+ optimization
        inline constexpr G4double RESIST_CUT = 0.05 * nm;     // Ultra-fine for accuracy
        inline constexpr G4double RESIST_CUT_HIGH_Z = 0.01 * nm;  // Even finer for high-Z materials
        inline constexpr G4double SUBSTRATE_CUT = 10.0 * nm;  // Coarse for efficiency
        inline constexpr G4double WORLD_CUT = 100.0 * nm;     // Very coarse

        // Energy thresholds
        inline constexpr G4double MIN_TRACKING_ENERGY = 10.0 * eV;  // Standard materials
        inline constexpr G4double MIN_TRACKING_ENERGY_HIGH_Z = 5.0 * eV;  // For Sn-MLD, Bi resists

        // High-Z material specific settings
        inline constexpr G4double BREMSSTRAHLUNG_THRESHOLD_HIGH_Z = 100.0 * keV;
        inline constexpr G4double MSC_RANGE_FACTOR_HIGH_Z = 0.01;  // Finer multiple scattering

        // Importance sampling for PSF tails
        inline constexpr G4double IMPORTANCE_SAMPLING_RADIUS = 10.0 * micrometer;
        inline constexpr G4double IMPORTANCE_SAMPLING_WEIGHT = 10.0;  // Weight factor for rare events
        inline constexpr G4double SIGNIFICANT_ENERGY_THRESHOLD = 100.0 * eV;
    }

    // Output parameters - STREAMLINED FOR BEAMER (constexpr strings and flags)
    namespace Output {
        // File paths and names (constexpr for compile-time)
        inline constexpr const char* DEFAULT_OUTPUT_DIR = "output";
        inline constexpr const char* DEFAULT_DIRECTORY = "output";
        inline constexpr const char* DEFAULT_FILENAME = "psf_data.csv";
        inline constexpr const char* PSF_DATA_FILENAME = "psf_data.csv";
        inline constexpr const char* BEAMER_FILENAME = "psf_beamer.txt";  // Direct BEAMER format
        inline constexpr const char* SUMMARY_FILENAME = "simulation_summary.txt";
        inline constexpr const char* STATISTICS_FILENAME = "bin_statistics.csv";

        // Output options - OPTIMIZED FOR BEAMER performance
        inline constexpr G4bool SAVE_RAW_DATA = true;
        inline constexpr G4bool SAVE_SMOOTHED_DATA = false;  // Do smoothing in post-processing
        inline constexpr G4bool SAVE_BIN_STATISTICS = false;  // Not needed for production runs
        inline constexpr G4bool VERBOSE_PROGRESS = false;  // Minimize output overhead
    }

    // Analysis parameters (inline constexpr for performance)
    namespace Analysis {
        // Noise reduction parameters
        inline constexpr G4int SAVGOL_WINDOW_MIN = 5;
        inline constexpr G4int SAVGOL_POLYNOMIAL_ORDER = 3;
        inline constexpr G4double OUTLIER_THRESHOLD_SIGMA = 3.0;

        // Extrapolation parameters
        inline constexpr G4int TAIL_FIT_BINS = 10;
        inline constexpr G4double MIN_EXTRAPOLATION_FRACTION = 1.0e-10;

        // Validation parameters
        inline constexpr G4double ENERGY_CONSERVATION_TOLERANCE = 0.01;
        inline constexpr G4double POSITION_VALIDATION_MAX = 10.0 * meter;
        
        // Performance optimization constants
        inline constexpr G4double ZERO_THRESHOLD = 1.0e-15;  // Skip values smaller than this
        inline constexpr G4int BATCH_SIZE = 1000;  // Process data in batches for cache efficiency
    }

    // Debug parameters - MINIMIZED FOR PRODUCTION (inline constexpr)
    namespace Debug {
        inline constexpr G4bool VERBOSE_SCORING = false;  // Off for production runs
        inline constexpr G4int MAX_DEBUG_DEPOSITS = 0;    // No debug output in production
        inline constexpr G4int PROGRESS_UPDATE_INTERVAL = 100000;  // Less frequent updates
        inline constexpr G4bool TRACK_BIN_STATISTICS = false;  // Off for production
        inline constexpr G4int BIN_STATISTICS_INTERVAL = 1000000;  // Very infrequent
        
        // Development-only constants (can be enabled for debugging)
        inline constexpr G4bool ENABLE_TIMING = false;    // Performance timing
        inline constexpr G4bool ENABLE_MEMORY_TRACKING = false;  // Memory usage tracking
    }
    
    // Hardware-specific optimizations for JEOL systems
    namespace JEOL {
        inline constexpr G4double MAX_CLOCK_FREQUENCY = 50.0;  // MHz hardware limit
        inline constexpr G4double MIN_MACHINE_GRID_3_4 = 1.0 * nm;      // 3/4 lens mode
        inline constexpr G4double MIN_MACHINE_GRID_6_5 = 0.125 * nm;    // 6/5 lens mode
        inline constexpr G4double FIELD_SIZE_3_4 = 500.0 * micrometer;  // 3/4 lens field
        inline constexpr G4double FIELD_SIZE_6_5 = 62.5 * micrometer;   // 6/5 lens field
    }
}

#endif // EBLCONSTANTS_HH