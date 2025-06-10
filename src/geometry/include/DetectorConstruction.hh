// DetectorConstruction.hh
#ifndef DetectorConstruction_h
#define DetectorConstruction_h 1

#include "G4VUserDetectorConstruction.hh"
#include "globals.hh"
#include <map>
#include <vector>

class G4VPhysicalVolume;
class G4LogicalVolume;
class G4Region;
class G4Material;
class DetectorMessenger;

class DetectorConstruction : public G4VUserDetectorConstruction {
public:
    DetectorConstruction();
    virtual ~DetectorConstruction();

    virtual G4VPhysicalVolume* Construct();
    virtual void ConstructSDandField();

    // Parameter access methods
    G4LogicalVolume* GetScoringVolume() const { return fScoringVolume; }
    G4Region* GetResistRegion() const { return fResistRegion; }
    G4double GetActualResistThickness() const { return fActualResistThickness; }
    G4LogicalVolume* GetWorldVolume() const { return fWorldVolume; }

    // Parameter setting methods
    void SetResistThickness(G4double thickness);
    void SetResistDensity(G4double density);
    void SetResistVisualizationThickness(G4double thickness);
    void AddResistElement(G4String element, G4int count);
    void ClearResistElements();
    void SetResistComposition(G4String composition);  // Format: "Al:1,C:5,H:4,O:2"

    // Return current parameters
    G4double GetResistDensity() const { return fResistDensity; }
    std::map<G4String, G4int> GetResistElements() const { return fResistElements; }

protected:
    G4LogicalVolume* fScoringVolume;
    G4LogicalVolume* fWorldVolume;
    G4Region* fResistRegion;
    G4double fActualResistThickness;

    // Parameter storage
    G4double fResistDensity;
    G4double fResistVisualizationThickness;
    std::map<G4String, G4int> fResistElements;
    G4bool fParametersChanged;

    // Messenger for UI commands
    DetectorMessenger* fMessenger;

    // Helper methods
    G4Material* CreateResistMaterial();
};

#endif