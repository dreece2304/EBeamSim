# PowerShell script to create the complete EBL project structure
# Usage: .\create_ebl_project.ps1 -ProjectPath "C:\Users\dreec\Geant4Projects\EBLSimulation"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectPath
)

Write-Host "Creating EBL Simulation project structure at: $ProjectPath" -ForegroundColor Green

# Create main directory
New-Item -ItemType Directory -Force -Path $ProjectPath

# Create directory structure
$directories = @(
    "cmake",
    "apps/ebl_sim",
    "apps/ebl_analysis",
    "src/common/include",
    "src/common/src",
    "src/geometry/include",
    "src/geometry/src",
    "src/physics/include",
    "src/physics/src",
    "src/beam/include",
    "src/beam/src",
    "src/actions/include",
    "src/actions/src",
    "config/materials",
    "config/beam",
    "macros/init",
    "macros/runs",
    "macros/benchmarks",
    "scripts/gui",
    "scripts/analysis",
    "scripts/utils",
    "tests",
    "docs",
    "data/output"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path "$ProjectPath\$dir"
}

Write-Host "Directory structure created!" -ForegroundColor Green

# Create main CMakeLists.txt
$mainCMake = @'
cmake_minimum_required(VERSION 3.16)
project(EBLSimulation VERSION 1.0.0 LANGUAGES CXX)

# Project options
option(BUILD_TESTING "Build unit tests" OFF)
option(BUILD_ANALYSIS "Build analysis tools" OFF)
option(USE_PYTHON "Enable Python bindings" OFF)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Add CMake module path
list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)

# Include helper modules
include(CompilerSettings)
include(GNUInstallDirs)

# Find Geant4
set(Geant4_DIR "C:/Users/dreec/Geant4Projects/program_files/lib/cmake/Geant4" CACHE PATH "Geant4 installation directory")
find_package(Geant4 REQUIRED ui_all vis_all)

if(NOT Geant4_FOUND)
    message(FATAL_ERROR "Geant4 not found! Please set Geant4_DIR correctly.")
endif()

# Include Geant4 use file
include(${Geant4_USE_FILE})

# Set global include directory
include_directories(${Geant4_INCLUDE_DIRS})

# Enable testing if requested
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# Add subdirectories for modular components
add_subdirectory(src/common)
add_subdirectory(src/geometry)
add_subdirectory(src/physics)
add_subdirectory(src/beam)
add_subdirectory(src/actions)

# Add applications
add_subdirectory(apps/ebl_sim)

if(BUILD_ANALYSIS)
    add_subdirectory(apps/ebl_analysis)
endif()

# Install configuration files
install(DIRECTORY config/ DESTINATION ${CMAKE_INSTALL_DATADIR}/ebl_sim/config)
install(DIRECTORY macros/ DESTINATION ${CMAKE_INSTALL_DATADIR}/ebl_sim/macros)

# Create data output directory
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/data/output)

# Print configuration summary
message(STATUS "====================================")
message(STATUS "EBL Simulation Configuration:")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  Geant4: ${Geant4_VERSION}")
message(STATUS "  Build testing: ${BUILD_TESTING}")
message(STATUS "  Build analysis: ${BUILD_ANALYSIS}")
message(STATUS "====================================")
'@
Set-Content -Path "$ProjectPath\CMakeLists.txt" -Value $mainCMake

# Create CompilerSettings.cmake
$compilerSettings = @'
# Compiler settings for different platforms

if(MSVC)
    # Visual Studio settings
    set_property(GLOBAL PROPERTY USE_FOLDERS ON)
    add_compile_options(/W3 /wd4251 /wd4996)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
    
    # Set proper flags
    set(CMAKE_CXX_FLAGS_RELEASE "/MD /O2 /Ob2 /DNDEBUG")
    set(CMAKE_CXX_FLAGS_DEBUG "/MDd /Zi /Ob0 /Od /RTC1")
elseif(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    # GCC/Clang settings
    add_compile_options(-Wall -Wextra -Wpedantic)
    
    # Debug/Release flags
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
endif()

# Position independent code
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
'@
Set-Content -Path "$ProjectPath\cmake\CompilerSettings.cmake" -Value $compilerSettings

# Create module CMakeLists.txt files
$moduleCMakeTemplate = @'
# MODULE_NAME module
add_library(ebl_MODULE_NAME STATIC
    # Add source files here
)

target_include_directories(ebl_MODULE_NAME
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
)

target_link_libraries(ebl_MODULE_NAME
    PUBLIC
        ${Geant4_LIBRARIES}
        ebl_common
)

set_target_properties(ebl_MODULE_NAME PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
)
'@

# Create CMakeLists.txt for each module
$modules = @("common", "geometry", "physics", "beam", "actions")
foreach ($module in $modules) {
    $content = $moduleCMakeTemplate -replace "MODULE_NAME", $module
    Set-Content -Path "$ProjectPath\src\$module\CMakeLists.txt" -Value $content
}

# Create app CMakeLists.txt
$appCMake = @'
# EBL Simulation Application

add_executable(ebl_sim main.cc)

target_link_libraries(ebl_sim
    PRIVATE
        ebl_geometry
        ebl_physics
        ebl_beam
        ebl_actions
        ebl_common
        ${Geant4_LIBRARIES}
)

# Set properties
set_target_properties(ebl_sim PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    VS_DEBUGGER_ENVIRONMENT "PATH=${Geant4_DIR}/../../bin;%PATH%"
)

# Copy macros to output directory
add_custom_command(TARGET ebl_sim POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${PROJECT_SOURCE_DIR}/macros
        $<TARGET_FILE_DIR:ebl_sim>/macros
)

# Install
install(TARGETS ebl_sim DESTINATION bin)
'@
Set-Content -Path "$ProjectPath\apps\ebl_sim\CMakeLists.txt" -Value $appCMake

# Create placeholder main.cc
$mainCC = @'
// main.cc - EBL Simulation Application
#include <iostream>

int main(int argc, char** argv) {
    std::cout << "EBL Simulation v1.0.0" << std::endl;
    std::cout << "TODO: Add your existing main.cc content here" << std::endl;
    return 0;
}
'@
Set-Content -Path "$ProjectPath\apps\ebl_sim\main.cc" -Value $mainCC

# Create material configuration example
$aluconeConfig = @'
{
    "name": "Alucone",
    "density": 1.35,
    "density_unit": "g/cm3",
    "composition": {
        "Al": 1,
        "C": 5,
        "H": 4,
        "O": 2
    },
    "description": "Alucone resist from TMA + butyne-1,4-diol MLD process"
}
'@
Set-Content -Path "$ProjectPath\config\materials\alucone.json" -Value $aluconeConfig

# Create test macro
$testMacro = @'
# Quick test macro
/run/verbose 1
/event/verbose 0
/tracking/verbose 0

/run/initialize

# Set resist properties
/det/setResistComposition "Al:1,C:5,H:4,O:2"
/det/setResistThickness 30 nm
/det/setResistDensity 1.35 g/cm3
/det/update

# Configure beam
/gun/particle e-
/gun/energy 30 keV
/gun/position 0 0 50 nm
/gun/direction 0 0 -1
/gun/beamSize 1 nm

# Run
/run/beamOn 1000
'@
Set-Content -Path "$ProjectPath\macros\runs\test.mac" -Value $testMacro

# Create README
$readme = @'
# EBL Simulation Project

## Structure
- `apps/` - Applications (main executables)
- `src/` - Source code organized by module
  - `common/` - Shared utilities and constants
  - `geometry/` - Detector construction
  - `physics/` - Physics lists
  - `beam/` - Primary particle generation
  - `actions/` - User actions
- `config/` - Configuration files
- `macros/` - Geant4 macro files
- `scripts/` - Python scripts and tools
- `tests/` - Unit tests
- `docs/` - Documentation

## Building
```bash
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

## Running
```bash
./bin/ebl_sim -m macros/runs/test.mac
```
'@
Set-Content -Path "$ProjectPath\README.md" -Value $readme

# Create .gitignore
$gitignore = @'
# Build directories
build/
out/
cmake-build-*/
.vs/

# Output data
data/output/*
*.csv
*.dat
*.root

# IDE files
*.user
*.suo
*.sln
*.vcxproj*
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
.venv/
'@
Set-Content -Path "$ProjectPath\.gitignore" -Value $gitignore

Write-Host "`nProject structure created successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Copy your existing source files to the appropriate directories"
Write-Host "2. Update the CMakeLists.txt files to include your actual source files"
Write-Host "3. Open the project in Visual Studio: File -> Open -> Folder -> $ProjectPath"
Write-Host "4. Build the project"

Write-Host "`nFile mapping guide:" -ForegroundColor Cyan
Write-Host "  DetectorConstruction.* -> src/geometry/"
Write-Host "  PhysicsList.* -> src/physics/"
Write-Host "  PrimaryGenerator*.* -> src/beam/"
Write-Host "  *Action.* -> src/actions/"
Write-Host "  main.cc (from ebl_sim.cc) -> apps/ebl_sim/main.cc"