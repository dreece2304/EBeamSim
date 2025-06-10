// DetectorConstruction.cc
#include "DetectorConstruction.hh"
#include "DetectorMessenger.hh"
#include "EBLConstants.hh"

#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4SystemOfUnits.hh"
#include "G4VisAttributes.hh"
#include "G4UnitsTable.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"

#include <sstream>
#include <algorithm>

// Helper function to parse composition string - ADD THIS FUNCTION
namespace {
    void parseComposition(const G4String& composition,
        std::map<G4String, G4int>& elements) {
        elements.clear();

        // Remove spaces
        G4String cleanComp = composition;
        cleanComp.erase(std::remove(cleanComp.begin(), cleanComp.end(), ' '),
            cleanComp.end());

        // Split by comma
        size_t pos = 0;
        while (pos < cleanComp.length()) {
            size_t colonPos = cleanComp.find(':', pos);
            if (colonPos == std::string::npos) break;

            size_t commaPos = cleanComp.find(',', colonPos);
            if (commaPos == std::string::npos) {
                commaPos = cleanComp.length();
            }

            G4String element = cleanComp.substr(pos, colonPos - pos);
            G4String countStr = cleanComp.substr(colonPos + 1, commaPos - colonPos - 1);

            // Convert string to int safely
            G4int count = std::atoi(countStr.c_str());
            elements[element] = count;

            pos = commaPos + 1;
        }
    }
}

DetectorConstruction::DetectorConstruction()
    : G4VUserDetectorConstruction(),
    fScoringVolume(nullptr),
    fWorldVolume(nullptr),
    fResistRegion(nullptr),
    fActualResistThickness(EBL::Resist::DEFAULT_THICKNESS),
    fResistDensity(EBL::Resist::DEFAULT_DENSITY),
    fResistVisualizationThickness(30.0 * nm),
    fParametersChanged(false),
    fMessenger(nullptr)
{
    // Default resist composition - Alucone from XPS
    fResistElements["Al"] = 1;
    fResistElements["C"] = 5;
    fResistElements["H"] = 4;
    fResistElements["O"] = 2;

    // Create messenger for UI commands
    fMessenger = new DetectorMessenger(this);
}

DetectorConstruction::~DetectorConstruction()
{
    delete fMessenger;
}

G4VPhysicalVolume* DetectorConstruction::Construct()
{
    // Get nist material manager
    G4NistManager* nist = G4NistManager::Instance();

    // World material - vacuum
    G4Material* world_mat = nist->FindOrBuildMaterial("G4_Galactic");

    // World volume
    G4double world_size = EBL::Geometry::WORLD_SIZE;

    G4Box* solidWorld = new G4Box("World",
        0.5 * world_size, 0.5 * world_size, 0.5 * world_size);

    fWorldVolume = new G4LogicalVolume(solidWorld, world_mat, "World");

    G4VPhysicalVolume* physWorld = new G4PVPlacement(
        0,                     // no rotation
        G4ThreeVector(),       // at (0,0,0)
        fWorldVolume,          // logical volume
        "World",               // name
        0,                     // mother volume
        false,                 // no boolean operation
        0,                     // copy number
        true);                 // overlaps checking

    // Substrate - Silicon
    G4Material* substrate_mat = nist->FindOrBuildMaterial("G4_Si");

    G4double substrate_thickness = EBL::Geometry::SUBSTRATE_THICKNESS;
    G4double substrate_xy = 100.0 * mm;  // Large lateral size

    G4Box* solidSubstrate = new G4Box("Substrate",
        0.5 * substrate_xy, 0.5 * substrate_xy, 0.5 * substrate_thickness);

    G4LogicalVolume* logicSubstrate = new G4LogicalVolume(
        solidSubstrate, substrate_mat, "Substrate");

    // Position substrate so its top surface is at z=0
    new G4PVPlacement(0,
        G4ThreeVector(0, 0, -0.5 * substrate_thickness),
        logicSubstrate,
        "Substrate",
        fWorldVolume,
        false,
        0,
        true);

    // CREATE SUBSTRATE REGION - ADD THIS
    G4Region* substrateRegion = new G4Region("SubstrateRegion");
    logicSubstrate->SetRegion(substrateRegion);
    substrateRegion->AddRootLogicalVolume(logicSubstrate);

    // Resist layer - create custom material
    G4Material* resist_mat = CreateResistMaterial();

    // Use actual thickness for physics, but could visualize differently
    G4double resist_thickness = fActualResistThickness;
    G4double resist_xy = substrate_xy;  // Same lateral size as substrate

    G4Box* solidResist = new G4Box("Resist",
        0.5 * resist_xy, 0.5 * resist_xy, 0.5 * resist_thickness);

    G4LogicalVolume* logicResist = new G4LogicalVolume(
        solidResist, resist_mat, "Resist");

    // Position resist on top of substrate (bottom at z=0)
    new G4PVPlacement(0,
        G4ThreeVector(0, 0, 0.5 * resist_thickness),
        logicResist,
        "Resist",
        fWorldVolume,
        false,
        0,
        true);

    // Set resist as the scoring volume
    fScoringVolume = logicResist;

    // Create a region for the resist with special production cuts
    fResistRegion = new G4Region("ResistRegion");
    logicResist->SetRegion(fResistRegion);
    fResistRegion->AddRootLogicalVolume(logicResist);

    // Visualization attributes
    fWorldVolume->SetVisAttributes(G4VisAttributes::GetInvisible());

    G4VisAttributes* substrateVis = new G4VisAttributes(G4Colour(0.5, 0.5, 0.5, 0.8));
    substrateVis->SetForceSolid(true);
    logicSubstrate->SetVisAttributes(substrateVis);

    G4VisAttributes* resistVis = new G4VisAttributes(G4Colour(1.0, 0.8, 0.0, 0.5));
    resistVis->SetForceSolid(true);
    logicResist->SetVisAttributes(resistVis);

    // Print geometry info
    G4cout << "\n=== Detector Construction ===" << G4endl;
    G4cout << "Substrate: Silicon, " << G4BestUnit(substrate_thickness, "Length") << " thick" << G4endl;
    G4cout << "Resist: " << resist_mat->GetName() << ", "
        << G4BestUnit(resist_thickness, "Length") << " thick" << G4endl;
    G4cout << "Resist density: " << G4BestUnit(resist_mat->GetDensity(), "Volumic Mass") << G4endl;
    G4cout << "===========================\n" << G4endl;

    return physWorld;
}

void DetectorConstruction::ConstructSDandField()
{
    // Add sensitive detectors or fields if needed
}

G4Material* DetectorConstruction::CreateResistMaterial()
{
    G4NistManager* nist = G4NistManager::Instance();

    // Create unique name based on composition
    std::stringstream ss;
    ss << "Resist_";
    for (const auto& elem : fResistElements) {
        ss << elem.first << elem.second << "_";
    }
    G4String materialName = ss.str();

    // Check if material already exists
    G4Material* existingMat = G4Material::GetMaterial(materialName, false);
    if (existingMat) {
        G4cout << "Using existing material: " << materialName << G4endl;
        return existingMat;
    }

    // Calculate total atoms for stoichiometry
    G4int totalAtoms = 0;
    for (const auto& elem : fResistElements) {
        totalAtoms += elem.second;
    }

    if (totalAtoms == 0) {
        G4cerr << "Error: No elements defined for resist!" << G4endl;
        // Return default PMMA
        return nist->FindOrBuildMaterial("G4_PLEXIGLASS");
    }

    // Create new material
    G4Material* resist = new G4Material(materialName, fResistDensity,
        fResistElements.size());

    // Add elements
    for (const auto& elem : fResistElements) {
        G4Element* element = nist->FindOrBuildElement(elem.first);
        if (element) {
            G4double fraction = G4double(elem.second) / G4double(totalAtoms);
            resist->AddElement(element, fraction);
        }
        else {
            G4cerr << "Warning: Element " << elem.first << " not found!" << G4endl;
        }
    }

    G4cout << "\nCreated resist material: " << materialName << G4endl;
    G4cout << "Composition: ";
    for (const auto& elem : fResistElements) {
        G4cout << elem.first << ":" << elem.second << " ";
    }
    G4cout << "\nDensity: " << G4BestUnit(fResistDensity, "Volumic Mass") << G4endl;

    return resist;
}

void DetectorConstruction::SetResistThickness(G4double thickness)
{
    fActualResistThickness = thickness;
    fParametersChanged = true;

    G4cout << "Resist thickness set to " << G4BestUnit(thickness, "Length") << G4endl;
    G4cout << "Call /det/update to apply changes" << G4endl;
}

void DetectorConstruction::SetResistDensity(G4double density)
{
    fResistDensity = density;
    fParametersChanged = true;

    G4cout << "Resist density set to " << G4BestUnit(density, "Volumic Mass") << G4endl;
}

void DetectorConstruction::SetResistVisualizationThickness(G4double thickness)
{
    fResistVisualizationThickness = thickness;
    G4cout << "Resist visualization thickness set to "
        << G4BestUnit(thickness, "Length") << G4endl;
}

void DetectorConstruction::AddResistElement(G4String element, G4int count)
{
    fResistElements[element] = count;
    fParametersChanged = true;
}

void DetectorConstruction::ClearResistElements()
{
    fResistElements.clear();
    fParametersChanged = true;
}

void DetectorConstruction::SetResistComposition(G4String composition)
{
    // Use the parseComposition helper function
    parseComposition(composition, fResistElements);
    fParametersChanged = true;

    G4cout << "Resist composition updated: ";
    for (const auto& elem : fResistElements) {
        G4cout << elem.first << ":" << elem.second << " ";
    }
    G4cout << G4endl;
}