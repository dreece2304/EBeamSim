// JEOLParameters.hh - JEOL JBX-6300FS System Parameters
#ifndef JEOLPARAMETERS_HH
#define JEOLPARAMETERS_HH

#include "G4SystemOfUnits.hh"
#include <vector>

namespace JEOL {
    // EOS Modes (Lens Modes)
    namespace Mode {
        constexpr G4int MODE_3_4TH_LENS = 3;
        constexpr G4int MODE_6_5TH_LENS = 6;
    }
    
    // Field Parameters
    namespace Field {
        // 4th Lens Mode (EOS Mode 3)
        constexpr G4double SIZE_MODE_3 = 500.0 * micrometer;
        constexpr G4double MACHINE_GRID_MODE_3 = 1.0 * nm;
        
        // 5th Lens Mode (EOS Mode 6)
        constexpr G4double SIZE_MODE_6 = 62.5 * micrometer;
        constexpr G4double MACHINE_GRID_MODE_6 = 0.125 * nm;
        
        // Field grid resolution (2^19 points per axis)
        constexpr G4int GRID_POINTS_PER_AXIS = 524288;
        
        // Field stitching tolerances
        constexpr G4double STITCH_ERROR_TYPICAL = 20.0 * nm;
        constexpr G4double STITCH_ERROR_BEST = 5.0 * nm;
    }
    
    // Beam Current Configurations
    namespace BeamCurrent {
        // Mode 3 (4th Lens) configurations
        constexpr G4double MODE3_1NA = 1.0;    // nA
        constexpr G4double MODE3_2NA = 2.0;
        constexpr G4double MODE3_8NA = 8.0;
        constexpr G4double MODE3_20NA = 20.0;
        
        // Mode 6 (5th Lens) configurations
        constexpr G4double MODE6_500PA = 0.5;  // nA (500 pA)
        constexpr G4double MODE6_2NA = 2.0;
        
        // Aperture assignments
        constexpr G4int APERTURE_A3 = 3;
        constexpr G4int APERTURE_A5 = 5;
        constexpr G4int APERTURE_A7 = 7;
    }
    
    // Exposure Parameters
    namespace Exposure {
        // Clock frequency limits
        constexpr G4double MAX_CLOCK_FREQUENCY = 50.0;  // MHz
        constexpr G4double MIN_CLOCK_FREQUENCY = 0.001; // MHz
        
        // Shot pitch constraints (must be 1 or even multiples of 2)
        constexpr G4int MIN_SHOT_PITCH = 1;
        constexpr G4int MAX_SHOT_PITCH = 100;  // Practical limit
        
        // Dose range
        constexpr G4double MIN_DOSE = 1.0;      // uC/cm^2
        constexpr G4double MAX_DOSE = 10000.0;  // uC/cm^2
        constexpr G4double TYPICAL_HSQ_DOSE = 400.0; // uC/cm^2 at 100kV
        
        // Shot rank (dose modulation)
        constexpr G4int MIN_SHOT_RANK = 0;
        constexpr G4int MAX_SHOT_RANK = 255;
        constexpr G4int NUM_SHOT_RANKS = 256;
    }
    
    // Pattern Parameters
    namespace Pattern {
        // Pattern types
        enum Type {
            SINGLE_SPOT = 0,
            LINE = 1,
            RECTANGLE = 2,
            SQUARE = 3,
            CIRCLE = 4,
            ARRAY = 5
        };
        
        // Vector scanning parameters
        constexpr G4double MIN_FEATURE_SIZE = 1.0 * nm;
        constexpr G4double BEAM_SETTLING_TIME = 0.1; // microseconds
        
        // Array pattern defaults
        constexpr G4int DEFAULT_ARRAY_SIZE = 10;
        constexpr G4double DEFAULT_PITCH = 100.0 * nm;
    }
    
    // Helper Functions
    inline G4double CalculateDose(G4double beamCurrent_pA, 
                                  G4double clockFreq_MHz, 
                                  G4double shotPitch_nm) {
        // Dose [uC/cm^2] = (Current[pA] * 100) / (Frequency[MHz] * GridStep[nm]^2)
        return (beamCurrent_pA * 100.0) / (clockFreq_MHz * shotPitch_nm * shotPitch_nm);
    }
    
    inline G4double CalculateClockFrequency(G4double beamCurrent_pA, 
                                            G4double dose_uCcm2, 
                                            G4double shotPitch_nm) {
        // Rearranged dose equation to solve for frequency
        return (beamCurrent_pA * 100.0) / (dose_uCcm2 * shotPitch_nm * shotPitch_nm);
    }
    
    inline G4bool IsValidShotPitch(G4int shotPitch) {
        // Shot pitch must be 1 or an even number
        return (shotPitch == 1) || (shotPitch % 2 == 0);
    }
    
    inline G4double GetMachineGrid(G4int eosMode) {
        return (eosMode == Mode::MODE_3_4TH_LENS) ? 
               Field::MACHINE_GRID_MODE_3 : 
               Field::MACHINE_GRID_MODE_6;
    }
    
    inline G4double GetFieldSize(G4int eosMode) {
        return (eosMode == Mode::MODE_3_4TH_LENS) ? 
               Field::SIZE_MODE_3 : 
               Field::SIZE_MODE_6;
    }
    
    inline G4double GetExposureGrid(G4int eosMode, G4int shotPitch) {
        return GetMachineGrid(eosMode) * shotPitch;
    }
}

#endif // JEOLPARAMETERS_HH