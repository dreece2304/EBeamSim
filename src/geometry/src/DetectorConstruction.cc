// DetectorConstruction.cc
#include "DetectorConstruction.hh"
#include "DetectorMessenger.hh"
#include "EBLConstants.hh"

#include "G4RunManager.hh"
#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4Region.hh"
#include "G4ProductionCuts.hh"
#include "G4MaterialPropertiesTable.hh"
#include "G4VisAttributes.hh"
#include "G4PhysicalConstants.hh"

#include <sstream>
#include <algorithm>
#include <map>
#include <regex>

DetectorConstruction::DetectorConstruction()
    : G4VUserDetectorConstruction(),
    fScoringVolume(nullptr),
    fWorldVolume(nullptr),
    fResistRegion(nullptr),
    fActualResistThickness(EBL::Resist::DEFAULT_THICKNESS),
    fResistDensity(EBL::Resist::DEFAULT_DENSITY),
    fResistVisualizationThickness(EBL::Resist::DEFAULT_THICKNESS),
    fParametersChanged(true),
    fMessenger(nullptr)
{
    // Initialize with default Alucone composition
    SetResistComposition(EBL::Resist::ALUCONE_COMPOSITION);

    // Create messenger for UI commands
    fMessenger = new DetectorMessenger(this);
}

DetectorConstruction::~DetectorConstruction()
{
    delete fMessenger;
}

G4VPhysicalVolume* DetectorConstruction::Construct()
{
    // Get NIST material manager
    G4NistManager* nist = G4NistManager::Instance();

    // Option to switch on/off checking of volumes overlaps
    G4bool checkOverlaps = true;

    // World - must be large enough to contain backscattered electrons
    G4double world_size = EBL::Geometry::WORLD_SIZE;

    // Create vacuum for the world volume
    // Use G4_Galactic which is an ultra-high vacuum in Geant4
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");

    G4Box* solidWorld = new G4Box("World", 0.5 * world_size, 0.5 * world_size, 0.5 * world_size);

    fWorldVolume = new G4LogicalVolume(solidWorld, vacuum, "World");

    G4VPhysicalVolume* physWorld =
        new G4PVPlacement(nullptr,              // no rotation
            G4ThreeVector(),      // at (0,0,0)
            fWorldVolume,         // its logical volume
            "World",              // its name
            nullptr,              // its mother volume
            false,                // no boolean operation
            0,                    // copy number
            checkOverlaps);       // check overlaps

    // Substrate (silicon) - MUST be thick enough to stop all electrons!
    // For 100 keV electrons, range in Si is ~100 µm
    // We want substrate thick enough to capture all backscattered electrons
    G4Material* si_mat = nist->FindOrBuildMaterial("G4_Si");

    // Calculate substrate thickness based on beam energy
    // Rule of thumb: 2x the electron range for the beam energy
    // For 100 keV in Si: range ~ 100 µm, so use 200 µm substrate
    G4double substrate_thickness = 200.0 * micrometer;  // Thick enough to stop all electrons
    G4double substrate_xy = 0.8 * world_size;  // Large lateral size

    G4Box* solidSubstrate =
        new G4Box("Substrate", 0.5 * substrate_xy, 0.5 * substrate_xy, 0.5 * substrate_thickness);

    G4LogicalVolume* logicSubstrate =
        new G4LogicalVolume(solidSubstrate, si_mat, "Substrate");

    // Position substrate so its top surface is at z=0
    G4double substrate_z_pos = -0.5 * substrate_thickness;

    new G4PVPlacement(nullptr,                // no rotation
        G4ThreeVector(0, 0, substrate_z_pos), // position
        logicSubstrate,         // its logical volume
        "Substrate",            // its name
        fWorldVolume,           // its mother volume
        false,                  // no boolean operation
        0,                      // copy number
        checkOverlaps);         // check overlaps

    // Resist layer (on top of substrate)
    G4Material* resist_mat = CreateResistMaterial();

    G4Box* solidResist =
        new G4Box("Resist", 0.5 * substrate_xy, 0.5 * substrate_xy, 0.5 * fActualResistThickness);

    G4LogicalVolume* logicResist =
        new G4LogicalVolume(solidResist, resist_mat, "Resist");

    // Resist sits directly on substrate (top of substrate is at z=0)
    G4double resist_z_pos = 0.5 * fActualResistThickness;

    new G4PVPlacement(nullptr,               // no rotation
        G4ThreeVector(0, 0, resist_z_pos), // position
        logicResist,           // its logical volume
        "Resist",              // its name
        fWorldVolume,          // its mother volume
        false,                 // no boolean operation
        0,                     // copy number
        checkOverlaps);        // check overlaps

    // Set visualization attributes
    G4VisAttributes* grayVisAtt = new G4VisAttributes(G4Colour(0.5, 0.5, 0.5));
    G4VisAttributes* blueVisAtt = new G4VisAttributes(G4Colour(0.0, 0.0, 1.0, 0.3));
    G4VisAttributes* cyanVisAtt = new G4VisAttributes(G4Colour(0.0, 1.0, 1.0, 0.5));

    logicSubstrate->SetVisAttributes(grayVisAtt);
    logicResist->SetVisAttributes(cyanVisAtt);
    fWorldVolume->SetVisAttributes(G4VisAttributes::GetInvisible());

    // Set scoring volume - this is where we record energy deposition
    fScoringVolume = logicResist;

    // Create region for resist with custom production cuts
    fResistRegion = new G4Region("ResistRegion");
    fResistRegion->AddRootLogicalVolume(logicResist);

    // Print geometry information
    G4cout << "\n=== Detector Construction ===" << G4endl;
    G4cout << "World size: " << G4BestUnit(world_size, "Length") << G4endl;
    G4cout << "Substrate: " << G4BestUnit(substrate_thickness, "Length")
        << " thick Si" << G4endl;
    G4cout << "  Bottom at z=" << G4BestUnit(substrate_z_pos - 0.5 * substrate_thickness, "Length") << G4endl;
    G4cout << "  Top at z=" << G4BestUnit(0.0, "Length") << " (reference)" << G4endl;
    G4cout << "Resist: " << G4BestUnit(fActualResistThickness, "Length")
        << " thick" << G4endl;
    G4cout << "  Bottom at z=" << G4BestUnit(0.0, "Length") << G4endl;
    G4cout << "  Top at z=" << G4BestUnit(fActualResistThickness, "Length") << G4endl;
    G4cout << "Recommended beam start: z="
        << G4BestUnit(fActualResistThickness + 100 * nanometer, "Length") << G4endl;
    G4cout << "===========================\n" << G4endl;

    return physWorld;
}

void DetectorConstruction::ConstructSDandField()
{
    // Create region-specific production cuts for the resist
    // These cuts determine the minimum range for secondary particle production
    // CRITICAL for PSF accuracy - must be very small!
    G4ProductionCuts* resistCuts = new G4ProductionCuts();
    resistCuts->SetProductionCut(0.1 * nanometer, "gamma");     // Very fine
    resistCuts->SetProductionCut(0.1 * nanometer, "e-");        // Critical for PSF
    resistCuts->SetProductionCut(0.1 * nanometer, "e+");        // Critical for PSF
    resistCuts->SetProductionCut(0.1 * nanometer, "proton");    // Just in case

    fResistRegion->SetProductionCuts(resistCuts);

    G4cout << "Set production cuts for resist region: "
        << G4BestUnit(0.1 * nanometer, "Length") << G4endl;
}

G4Material* DetectorConstruction::CreateResistMaterial()
{
    G4NistManager* nistManager = G4NistManager::Instance();
    G4Material* resistMaterial = nullptr;

    // Only rebuild the material if parameters have changed
    if (fParametersChanged) {
        // Reset flag
        fParametersChanged = false;

        // Check if we have valid elements
        if (fResistElements.empty()) {
            G4cerr << "ERROR: No resist elements defined! Using default PMMA." << G4endl;
            // Default to PMMA
            fResistElements["C"] = 5;
            fResistElements["H"] = 8;
            fResistElements["O"] = 2;
        }

        // Create a unique name for the custom material
        std::ostringstream nameStr;
        nameStr << "Resist_" << G4Threading::G4GetThreadId();
        G4String name = nameStr.str();

        // Create material with specified density
        G4int numElements = static_cast<G4int>(fResistElements.size());
        G4cout << "Creating resist material with " << numElements << " elements" << G4endl;
        resistMaterial = new G4Material(name, fResistDensity, numElements);

        // Define elements from NIST database
        std::map<G4String, G4Element*> elements;
        elements["H"] = nistManager->FindOrBuildElement("H");
        elements["C"] = nistManager->FindOrBuildElement("C");
        elements["O"] = nistManager->FindOrBuildElement("O");
        elements["Si"] = nistManager->FindOrBuildElement("Si");
        elements["Al"] = nistManager->FindOrBuildElement("Al");

        // Add elements to material based on specified composition
        G4int totalCount = 0;
        for (const auto& pair : fResistElements) {
            totalCount += pair.second;
        }

        G4cout << "Total atom count: " << totalCount << G4endl;

        for (const auto& pair : fResistElements) {
            G4String elementSymbol = pair.first;
            G4int count = pair.second;
            G4double fraction = G4double(count) / G4double(totalCount);

            if (elements.find(elementSymbol) != elements.end()) {
                resistMaterial->AddElement(elements[elementSymbol], fraction);
                G4cout << "  Added " << elementSymbol << " with fraction " << fraction << G4endl;
            }
            else {
                G4Exception("DetectorConstruction::CreateResistMaterial", "InvalidElement",
                    FatalException, ("Element " + elementSymbol + " not found").c_str());
            }
        }

        // Print final material info
        G4cout << "Created resist material:" << G4endl;
        G4cout << "  Name: " << resistMaterial->GetName() << G4endl;
        G4cout << "  Density: " << resistMaterial->GetDensity() / (g / cm3) << " g/cm3" << G4endl;
        G4cout << "  Number of elements: " << resistMaterial->GetNumberOfElements() << G4endl;
        G4cout << "  Composition: ";
        for (const auto& pair : fResistElements) {
            G4cout << pair.first << ":" << pair.second << " ";
        }
        G4cout << G4endl;

        // Verify material is valid
        if (resistMaterial->GetNumberOfElements() == 0) {
            G4Exception("DetectorConstruction::CreateResistMaterial", "NoElements",
                FatalException, "Resist material has no elements!");
        }
    }
    else {
        // Reuse existing material
        resistMaterial = G4Material::GetMaterial("Resist_" + G4String(std::to_string(G4Threading::G4GetThreadId())));

        if (!resistMaterial) {
            // Fall back to creating new material if not found
            fParametersChanged = true;
            return CreateResistMaterial();
        }
    }

    return resistMaterial;
}

void DetectorConstruction::SetResistThickness(G4double thickness)
{
    fActualResistThickness = thickness;
    fResistVisualizationThickness = thickness;
    fParametersChanged = true;

    G4RunManager::GetRunManager()->GeometryHasBeenModified();
    G4cout << "Resist thickness set to " << thickness / nanometer << " nm" << G4endl;
}

void DetectorConstruction::SetResistDensity(G4double density)
{
    fResistDensity = density;
    fParametersChanged = true;

    G4RunManager::GetRunManager()->GeometryHasBeenModified();
    G4cout << "Resist density set to " << density / (g / cm3) << " g/cm3" << G4endl;
}

void DetectorConstruction::SetResistVisualizationThickness(G4double thickness)
{
    fResistVisualizationThickness = thickness;
    G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::AddResistElement(G4String element, G4int count)
{
    fResistElements[element] = count;
    fParametersChanged = true;

    G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::ClearResistElements()
{
    fResistElements.clear();
    fParametersChanged = true;

    G4RunManager::GetRunManager()->GeometryHasBeenModified();
}

void DetectorConstruction::SetResistComposition(G4String composition)
{
    // Parse composition string of form "C:7,H:14,O:2,Al:1"
    ClearResistElements();

    G4cout << "SetResistComposition received: '" << composition << "'" << G4endl;

    // Remove any outer quotes that might have been passed
    if (composition.length() >= 2) {
        if ((composition[0] == '"' && composition[composition.length() - 1] == '"') ||
            (composition[0] == '\'' && composition[composition.length() - 1] == '\'')) {
            composition = composition.substr(1, composition.length() - 2);
            G4cout << "Removed outer quotes, now: '" << composition << "'" << G4endl;
        }
    }

    // Split by commas
    std::vector<G4String> elements;
    std::istringstream f(composition);
    G4String s;
    while (std::getline(f, s, ',')) {
        elements.push_back(s);
    }

    G4cout << "Found " << elements.size() << " element specifications" << G4endl;

    // Helper lambda to sanitize strings
    auto sanitize = [](G4String str) -> G4String {
        // Remove leading/trailing whitespace and quotes
        size_t start = str.find_first_not_of(" \t\n\r\"'");
        size_t end = str.find_last_not_of(" \t\n\r\"'");

        if (start == G4String::npos || end == G4String::npos) {
            return "";
        }

        return str.substr(start, end - start + 1);
        };

    // Process each element:count pair
    for (const auto& element : elements) {
        size_t colonPos = element.find(':');
        if (colonPos != G4String::npos) {
            G4String symbolRaw = element.substr(0, colonPos);
            G4String countStr = element.substr(colonPos + 1);

            // Sanitize both parts
            G4String symbol = sanitize(symbolRaw);
            countStr = sanitize(countStr);

            G4cout << "  Processing: '" << symbolRaw << "' -> '" << symbol << "'" << G4endl;

            try {
                G4int count = std::stoi(countStr);

                // Validate element symbol
                if (symbol.empty()) {
                    G4cerr << "  ERROR: Empty element symbol after sanitization" << G4endl;
                    continue;
                }

                // Check if it's a valid element
                G4NistManager* nist = G4NistManager::Instance();
                G4Element* testElement = nist->FindOrBuildElement(symbol, false); // false = don't warn
                if (!testElement) {
                    G4cerr << "  ERROR: Unknown element '" << symbol << "'" << G4endl;
                    continue;
                }

                AddResistElement(symbol, count);
                G4cout << "  Successfully added element: " << symbol << " count: " << count << G4endl;
            }
            catch (const std::exception& e) {
                G4cerr << "  ERROR parsing count for " << symbol << ": " << e.what() << G4endl;
            }
        }
        else {
            G4cerr << "  ERROR: Invalid element specification (no colon): '" << element << "'" << G4endl;
        }
    }

    // Verify we have elements
    if (fResistElements.empty()) {
        G4cerr << "ERROR: No valid elements parsed from composition string!" << G4endl;
        G4cerr << "Using default PMMA composition as fallback" << G4endl;
        // Set a default to prevent crashes
        AddResistElement("C", 5);
        AddResistElement("H", 8);
        AddResistElement("O", 2);
    }

    G4cout << "Final resist composition set with " << fResistElements.size() << " elements" << G4endl;
}