// SquarePatternGenerator.hh - Square pattern generation for e-beam lithography
#ifndef SQUAREPATTERNGENERATOR_HH
#define SQUAREPATTERNGENERATOR_HH

#include "PatternGenerator.hh"

class SquarePatternGenerator : public PatternGenerator {
public:
    SquarePatternGenerator(const PatternParameters& params, 
                          DetectorConstruction* detConstruction);
    virtual ~SquarePatternGenerator() = default;
    
    // Generate square pattern with vector scanning
    virtual void GeneratePattern() override;
    
    // Set edge dose modulation for proximity effect testing
    void SetEdgeDoseModulation(G4double edgeModulation) {
        fEdgeModulation = edgeModulation;
    }
    
    // Set corner dose modulation
    void SetCornerDoseModulation(G4double cornerModulation) {
        fCornerModulation = cornerModulation;
    }
    
private:
    // Helper methods
    G4bool IsEdgeShot(G4double x, G4double y, G4double size) const;
    G4bool IsCornerShot(G4double x, G4double y, G4double size) const;
    G4int AssignShotRank(G4double x, G4double y, G4double size) const;
    
    // Generate different scanning strategies
    void GenerateRasterScan();      // Traditional raster scan
    void GenerateSerpentineScan();  // Serpentine (boustrophedon) scan
    void GenerateSpiralScan();      // Spiral from outside in
    
private:
    // Dose modulation factors
    G4double fEdgeModulation;    // Multiplier for edge shots
    G4double fCornerModulation;  // Multiplier for corner shots
    
    // Scanning strategy
    enum ScanStrategy {
        RASTER = 0,
        SERPENTINE = 1,
        SPIRAL = 2
    };
    ScanStrategy fScanStrategy;
};

#endif // SQUAREPATTERNGENERATOR_HH