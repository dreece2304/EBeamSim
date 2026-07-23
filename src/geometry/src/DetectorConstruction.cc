// DetectorConstruction.cc - Complete file with material validation
#include "DetectorConstruction.hh"
#include "DetectorMessenger.hh"
#include "EBLConstants.hh"
#include "EBLParsing.hh"
#include "../../physics/include/PhysicsList.hh"

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
#include "G4UserLimits.hh"

#include <sstream>
#include <algorithm>
#include <cstdlib>

// Helper function to parse composition string (logic shared with unit tests)
namespace {
    void reportBadToken(const std::string& token) {
        G4Exception("DetectorConstruction::parseComposition",
                    "DC003", JustWarning,
                    ("Ignoring malformed composition token: " + token).c_str());
    }

    void parseComposition(const G4String& composition,
        std::map<G4String, G4double>& elements) {
        std::map<std::string, double> parsed;
        EBL::ParseComposition(composition, parsed, &reportBadToken);

        elements.clear();
        for (const auto& elem : parsed) {
            elements[G4String(elem.first)] = elem.second;
        }
    }
}

DetectorConstruction::DetectorConstruction()
    : G4VUserDetectorConstruction(),
    fScoringVolume(nullptr),
    fWorldVolume(nullptr),
    fResistLogical(nullptr),
    fResistPhysical(nullptr),
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
    G4double substrate_xy = EBL::Geometry::SUBSTRATE_XY;

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

    // CREATE SUBSTRATE REGION for region-specific cuts
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

    // Store the resist logical volume for later material updates
    fResistLogical = logicResist;

    // Position resist on top of substrate (bottom at z=0)
    fResistPhysical = new G4PVPlacement(0,
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

    // CRITICAL: Apply step limits for accurate trajectory tracking
    // The step limit must be applied to ALL volumes the particle traverses,
    // including the world/vacuum, otherwise electrons can skip through boundaries
    G4double maxStepResist = EBL::Physics::MAX_STEP_SIZE;  // 2 nm - fine for energy deposition

    // Resist - finest step limit for accurate energy deposition tracking
    G4UserLimits* resistLimits = new G4UserLimits(maxStepResist);
    logicResist->SetUserLimits(resistLimits);
    G4cout << "Resist step limit: " << maxStepResist/nm << " nm" << G4endl;

    // Substrate - coarse steps OK (we only care about resist for figure)
    G4double maxStepSubstrate = 500.0 * nm;
    G4UserLimits* substrateLimits = new G4UserLimits(maxStepSubstrate);
    logicSubstrate->SetUserLimits(substrateLimits);
    G4cout << "Substrate step limit: " << maxStepSubstrate/nm << " nm" << G4endl;

    // World/vacuum - just needs to catch resist boundary, doesn't need to be as fine
    G4double maxStepWorld = 10.0 * nm;
    G4UserLimits* worldLimits = new G4UserLimits(maxStepWorld);
    fWorldVolume->SetUserLimits(worldLimits);
    G4cout << "World step limit: " << maxStepWorld/nm << " nm" << G4endl;

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
        return existingMat;
    }

    // Validate composition
    G4double totalAtoms = 0.0;
    for (const auto& elem : fResistElements) {
        totalAtoms += elem.second;
    }

    if (totalAtoms <= 0.0) {
        G4Exception("DetectorConstruction::CreateResistMaterial",
                    "DC001", FatalException,
                    "No elements defined for resist material!");
    }

    // Create new material
    G4Material* resist = new G4Material(materialName, fResistDensity,
        static_cast<G4int>(fResistElements.size()));

    // Calculate molecular weight for mass fractions
    G4double molecularWeight = 0.0;
    for (const auto& elem : fResistElements) {
        G4Element* element = nist->FindOrBuildElement(elem.first);
        if (!element) {
            G4Exception("DetectorConstruction::CreateResistMaterial",
                        "DC002", FatalException,
                        ("Element " + elem.first + " not found!").c_str());
        }
        molecularWeight += element->GetA() * elem.second;
    }

    // Add elements with proper mass fractions
    for (const auto& elem : fResistElements) {
        G4Element* element = nist->FindOrBuildElement(elem.first);
        G4double massFraction = (element->GetA() * elem.second) / molecularWeight;
        resist->AddElement(element, massFraction);
    }

    // Concise material summary
    G4cout << "Resist: ";
    bool first = true;
    for (const auto& elem : fResistElements) {
        if (!first) G4cout << ",";
        G4cout << elem.first << elem.second;
        first = false;
    }
    G4cout << " @ " << fResistDensity/(g/cm3) << " g/cm3, "
           << fActualResistThickness/nm << " nm" << G4endl;

    return resist;
}

void DetectorConstruction::SetResistThickness(G4double thickness)
{
    fActualResistThickness = thickness;
    fParametersChanged = true;
}

void DetectorConstruction::SetResistDensity(G4double density)
{
    fResistDensity = density;
    fParametersChanged = true;
}

void DetectorConstruction::SetResistVisualizationThickness(G4double thickness)
{
    fResistVisualizationThickness = thickness;
}

void DetectorConstruction::AddResistElement(G4String element, G4double count)
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
    parseComposition(composition, fResistElements);
    fParametersChanged = true;
}

void DetectorConstruction::UpdateMaterial()
{
    if (!fResistLogical) {
        return;
    }

    G4bool changed = false;

    // Material swap
    G4Material* newResistMaterial = CreateResistMaterial();
    if (fResistLogical->GetMaterial() != newResistMaterial) {
        fResistLogical->SetMaterial(newResistMaterial);
        changed = true;
    }

    // Thickness: mutate the existing solid in place (a full re-Construct would
    // double-register ResistRegion in the region store)
    auto* resistBox = dynamic_cast<G4Box*>(fResistLogical->GetSolid());
    if (resistBox) {
        const G4double targetHalfZ = 0.5 * fActualResistThickness;
        if (std::abs(resistBox->GetZHalfLength() - targetHalfZ) > 1.0e-6 * nm) {
            resistBox->SetZHalfLength(targetHalfZ);
            if (fResistPhysical) {
                // Keep the resist bottom at z=0 (on top of the substrate)
                fResistPhysical->SetTranslation(G4ThreeVector(0, 0, targetHalfZ));
            }
            changed = true;
            G4cout << "Resist geometry updated: thickness = "
                   << fActualResistThickness / nm << " nm" << G4endl;
        }
    }

    if (changed) {
        auto* runManager = G4RunManager::GetRunManager();
        runManager->GeometryHasBeenModified();

        // Reconfigure physics for new material (important for high-Z)
        auto* physicsList = dynamic_cast<PhysicsList*>(
            const_cast<G4VUserPhysicsList*>(runManager->GetUserPhysicsList()));
        if (physicsList) {
            physicsList->ReconfigureForMaterial();
        }
    }
}