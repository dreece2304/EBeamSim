#ifndef EBLTypes_h
#define EBLTypes_h 1

#include "globals.hh"
#include "G4ThreeVector.hh"
#include <vector>
#include <map>
#include <string>

namespace EBL {

    // Material definition structure
    struct MaterialDefinition {
        G4String name;
        G4double density;
        std::map<G4String, G4int> composition;
        G4String description;
    };

    // Beam parameters structure
    struct BeamParameters {
        G4double energy;
        G4double spotSize;
        G4ThreeVector position;
        G4ThreeVector direction;
        G4String particleType;
    };

    // PSF data point
    struct PSFDataPoint {
        G4double radius;
        G4double energy;
        G4double binLowerEdge;
        G4double binUpperEdge;
    };

    // Run statistics
    struct RunStatistics {
        G4int totalEvents;
        G4int processedEvents;
        G4double totalEnergyDeposited;
        G4double simulationTime;
        std::vector<G4double> radialProfile;
    };

} // namespace EBL

#endif