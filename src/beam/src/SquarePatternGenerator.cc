// SquarePatternGenerator.cc - Implementation of square pattern generation
#include "SquarePatternGenerator.hh"
#include "G4SystemOfUnits.hh"
#include <cmath>

SquarePatternGenerator::SquarePatternGenerator(const PatternParameters& params,
                                               DetectorConstruction* detConstruction)
    : PatternGenerator(params, detConstruction),
      fEdgeModulation(1.0),
      fCornerModulation(1.0),
      fScanStrategy(SERPENTINE) {  // Default to serpentine for efficiency
    
    // Validate that pattern type is square
    if (fParameters.patternType != JEOL::Pattern::SQUARE) {
        G4Exception("SquarePatternGenerator::SquarePatternGenerator",
                    "InvalidPatternType", JustWarning,
                    "Pattern type is not SQUARE, will generate square anyway");
    }
}

void SquarePatternGenerator::GeneratePattern() {
    ClearPattern();
    
    G4cout << "Generating square pattern:" << G4endl;
    G4cout << "  Size: " << fParameters.size/micrometer << " um" << G4endl;
    G4cout << "  Center: (" << fParameters.centerPosition.x()/micrometer 
           << ", " << fParameters.centerPosition.y()/micrometer << ") um" << G4endl;
    
    // Generate based on selected strategy
    switch (fScanStrategy) {
        case RASTER:
            GenerateRasterScan();
            break;
        case SERPENTINE:
            GenerateSerpentineScan();
            break;
        case SPIRAL:
            GenerateSpiralScan();
            break;
        default:
            GenerateSerpentineScan();
    }
    
    // Assign shots to fields
    AssignShotsToFields();
    
    G4cout << "Pattern generation complete:" << G4endl;
    G4cout << "  Total shots: " << GetTotalShots() << G4endl;
    G4cout << "  Total fields: " << GetTotalFields() << G4endl;
    
    // Calculate total exposure time
    G4double totalTime = 0;
    for (const auto& shot : fShots) {
        totalTime += shot.dwellTime;
    }
    G4cout << "  Estimated exposure time: " << totalTime << " us ("
           << totalTime/1e6 << " s)" << G4endl;
}

void SquarePatternGenerator::GenerateRasterScan() {
    G4double halfSize = fParameters.size / 2.0;
    G4double grid = GetExposureGrid();
    
    // Calculate number of shots in each direction
    G4int nShots = static_cast<G4int>(fParameters.size / grid);
    if (nShots * grid < fParameters.size) nShots++;  // Round up
    
    // Generate shots in raster pattern (left to right, top to bottom)
    for (G4int iy = 0; iy < nShots; ++iy) {
        G4double y = fParameters.centerPosition.y() - halfSize + iy * grid;
        
        for (G4int ix = 0; ix < nShots; ++ix) {
            G4double x = fParameters.centerPosition.x() - halfSize + ix * grid;
            
            // Check if still within square bounds
            if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                
                G4int shotRank = AssignShotRank(x, y, fParameters.size);
                AddShot(x, y, shotRank);
            }
        }
    }
}

void SquarePatternGenerator::GenerateSerpentineScan() {
    G4double halfSize = fParameters.size / 2.0;
    G4double grid = GetExposureGrid();
    
    // Calculate number of shots in each direction
    G4int nShots = static_cast<G4int>(fParameters.size / grid);
    if (nShots * grid < fParameters.size) nShots++;  // Round up
    
    // Generate shots in serpentine pattern (reduces stage movement)
    for (G4int iy = 0; iy < nShots; ++iy) {
        G4double y = fParameters.centerPosition.y() - halfSize + iy * grid;
        
        // Alternate direction for each row
        if (iy % 2 == 0) {
            // Left to right
            for (G4int ix = 0; ix < nShots; ++ix) {
                G4double x = fParameters.centerPosition.x() - halfSize + ix * grid;
                
                if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                    std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                    
                    G4int shotRank = AssignShotRank(x, y, fParameters.size);
                    AddShot(x, y, shotRank);
                }
            }
        } else {
            // Right to left
            for (G4int ix = nShots - 1; ix >= 0; --ix) {
                G4double x = fParameters.centerPosition.x() - halfSize + ix * grid;
                
                if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                    std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                    
                    G4int shotRank = AssignShotRank(x, y, fParameters.size);
                    AddShot(x, y, shotRank);
                }
            }
        }
    }
}

void SquarePatternGenerator::GenerateSpiralScan() {
    G4double halfSize = fParameters.size / 2.0;
    G4double grid = GetExposureGrid();
    
    // Calculate number of shots in each direction
    G4int nShots = static_cast<G4int>(fParameters.size / grid);
    if (nShots * grid < fParameters.size) nShots++;  // Round up
    
    // Generate shots in spiral pattern from outside in
    G4int left = 0, right = nShots - 1;
    G4int top = 0, bottom = nShots - 1;
    
    while (left <= right && top <= bottom) {
        // Top row (left to right)
        for (G4int ix = left; ix <= right; ++ix) {
            G4double x = fParameters.centerPosition.x() - halfSize + ix * grid;
            G4double y = fParameters.centerPosition.y() - halfSize + top * grid;
            
            if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                
                G4int shotRank = AssignShotRank(x, y, fParameters.size);
                AddShot(x, y, shotRank);
            }
        }
        top++;
        
        // Right column (top to bottom)
        for (G4int iy = top; iy <= bottom; ++iy) {
            G4double x = fParameters.centerPosition.x() - halfSize + right * grid;
            G4double y = fParameters.centerPosition.y() - halfSize + iy * grid;
            
            if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                
                G4int shotRank = AssignShotRank(x, y, fParameters.size);
                AddShot(x, y, shotRank);
            }
        }
        right--;
        
        // Bottom row (right to left)
        if (top <= bottom) {
            for (G4int ix = right; ix >= left; --ix) {
                G4double x = fParameters.centerPosition.x() - halfSize + ix * grid;
                G4double y = fParameters.centerPosition.y() - halfSize + bottom * grid;
                
                if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                    std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                    
                    G4int shotRank = AssignShotRank(x, y, fParameters.size);
                    AddShot(x, y, shotRank);
                }
            }
            bottom--;
        }
        
        // Left column (bottom to top)
        if (left <= right) {
            for (G4int iy = bottom; iy >= top; --iy) {
                G4double x = fParameters.centerPosition.x() - halfSize + left * grid;
                G4double y = fParameters.centerPosition.y() - halfSize + iy * grid;
                
                if (std::abs(x - fParameters.centerPosition.x()) <= halfSize &&
                    std::abs(y - fParameters.centerPosition.y()) <= halfSize) {
                    
                    G4int shotRank = AssignShotRank(x, y, fParameters.size);
                    AddShot(x, y, shotRank);
                }
            }
            left++;
        }
    }
}

G4bool SquarePatternGenerator::IsEdgeShot(G4double x, G4double y, G4double size) const {
    G4double halfSize = size / 2.0;
    G4double centerX = fParameters.centerPosition.x();
    G4double centerY = fParameters.centerPosition.y();
    G4double grid = GetExposureGrid();
    
    // Check if on edge (within one grid spacing of boundary)
    G4bool onLeftEdge = std::abs(x - (centerX - halfSize)) < grid;
    G4bool onRightEdge = std::abs(x - (centerX + halfSize)) < grid;
    G4bool onTopEdge = std::abs(y - (centerY + halfSize)) < grid;
    G4bool onBottomEdge = std::abs(y - (centerY - halfSize)) < grid;
    
    return (onLeftEdge || onRightEdge || onTopEdge || onBottomEdge);
}

G4bool SquarePatternGenerator::IsCornerShot(G4double x, G4double y, G4double size) const {
    G4double halfSize = size / 2.0;
    G4double centerX = fParameters.centerPosition.x();
    G4double centerY = fParameters.centerPosition.y();
    G4double grid = GetExposureGrid();
    
    // Check if near corner (within one grid spacing in both x and y)
    G4bool nearLeft = std::abs(x - (centerX - halfSize)) < grid;
    G4bool nearRight = std::abs(x - (centerX + halfSize)) < grid;
    G4bool nearTop = std::abs(y - (centerY + halfSize)) < grid;
    G4bool nearBottom = std::abs(y - (centerY - halfSize)) < grid;
    
    return ((nearLeft || nearRight) && (nearTop || nearBottom));
}

G4int SquarePatternGenerator::AssignShotRank(G4double x, G4double y, G4double size) const {
    // Default shot rank assignment for proximity effect testing
    // Can be customized based on requirements
    
    if (IsCornerShot(x, y, size)) {
        // Corners typically need less dose due to proximity from two edges
        return 2;  // Will use modulationTable[2]
    } else if (IsEdgeShot(x, y, size)) {
        // Edges need intermediate dose
        return 1;  // Will use modulationTable[1]
    } else {
        // Interior needs full dose
        return 0;  // Will use modulationTable[0]
    }
}