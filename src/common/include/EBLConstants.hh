// EBLConstants.hh
#ifndef EBLConstants_h
#define EBLConstants_h 1

#include "globals.hh"
#include "G4SystemOfUnits.hh"

namespace EBL {
    // Version information
    constexpr int VERSION_MAJOR = 1;
    constexpr int VERSION_MINOR = 0;
    constexpr int VERSION_PATCH = 0;

    // Default resist properties
    namespace Resist {
        constexpr G4double DEFAULT_THICKNESS = 30.0 * nanometer;
        constexpr G4double DEFAULT_DENSITY = 1.35 * g / cm3;

        // Material composition presets (updated from XPS)
        const G4String PMMA_COMPOSITION = "C:5,H:8,O:2";
        const G4String HSQ_COMPOSITION = "Si:1,H:1,O:1.5";
        const G4String ZEP_COMPOSITION = "C:11,H:14,O:1";
        const G4String ALUCONE_COMPOSITION = "Al:1,C:5,H:4,O:2";
        const G4String ALUCONE_EXPOSED_COMPOSITION = "Al:1,C:5,H:4,O:3";
    }

    // Beam parameters
    namespace Beam {
        constexpr G4double DEFAULT_ENERGY = 100.0 * keV;
        constexpr G4double DEFAULT_SPOT_SIZE = 2.0 * nanometer;
        constexpr G4double DEFAULT_POSITION_Z = 100.0 * nanometer;
    }

    // World and geometry
    namespace Geometry {
        constexpr G4double WORLD_SIZE = 400.0 * micrometer;
        constexpr G4double SUBSTRATE_THICKNESS = 200.0 * micrometer;
    }

    // PSF scoring parameters
    namespace PSF {
        constexpr G4bool USE_LOG_BINNING = true;
        constexpr G4int NUM_RADIAL_BINS = 250;
        constexpr G4double MIN_RADIUS = 0.05 * nanometer;
        constexpr G4double MAX_RADIUS = 100.0 * micrometer;
        constexpr G4double MIN_ENERGY_DEPOSIT = 1.0 * eV;
    }

    // Output configuration
    namespace Output {
        const G4String DEFAULT_FILENAME = "ebl_psf_data.csv";
        const G4String BEAMER_FILENAME = "beamer_psf.dat";
        const G4String SUMMARY_FILENAME = "simulation_summary.txt";
        const G4String DEFAULT_DIRECTORY = "";
    }
}

#endif