cmake_minimum_required(VERSION 3.16)
project(EBeamSim VERSION 1.0.0 LANGUAGES CXX)

# Project options
option(BUILD_TESTING "Build unit tests" OFF)
option(BUILD_ANALYSIS "Build analysis tools" OFF)
option(USE_PYTHON "Enable Python bindings" OFF)
option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Add CMake module path
list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)

# Include helper modules
include(CompilerSettings)
include(GNUInstallDirs)

# Visual Studio specific settings
if(MSVC)
    set_property(GLOBAL PROPERTY USE_FOLDERS ON)
endif()

# Help CMake find Geant4 on Windows
if(WIN32)
    set(Geant4_DIR "C:/Users/dreec/Geant4Projects/program_files/lib/cmake/Geant4" CACHE PATH "Geant4 installation directory")
endif()

# Find Geant4
find_package(Geant4 REQUIRED ui_all vis_all)

if(NOT Geant4_FOUND)
    message(FATAL_ERROR "Geant4 not found! Please set Geant4_DIR correctly.")
endif()

# Include Geant4 use file
include(${Geant4_USE_FILE})

# Set output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Enable testing if requested
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# Add subdirectories for modular components
# Order matters due to dependencies
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
install(DIRECTORY config/ 
    DESTINATION ${CMAKE_INSTALL_DATADIR}/ebl_sim/config
    FILES_MATCHING PATTERN "*.json" PATTERN "*.yaml"
)

install(DIRECTORY macros/ 
    DESTINATION ${CMAKE_INSTALL_DATADIR}/ebl_sim/macros
    FILES_MATCHING PATTERN "*.mac"
)

# Create data output directory in build tree
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/data/output)

# Package configuration
include(CMakePackageConfigHelpers)

# Export targets
install(EXPORT EBeamSimTargets
    FILE EBeamSimTargets.cmake
    NAMESPACE EBL::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/EBeamSim
)

# Create package version file
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/EBeamSimConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

# Create package config file
configure_file(cmake/EBeamSim.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/EBeamSimConfig.cmake"
    @ONLY
)

# Install package files
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/EBeamSimConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/EBeamSimConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/EBeamSim
)

# Print configuration summary
message(STATUS "====================================")
message(STATUS "EBL Simulation Configuration:")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "  Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Geant4 version: ${Geant4_VERSION}")
message(STATUS "  Geant4 dir: ${Geant4_DIR}")
message(STATUS "Options:")
message(STATUS "  Build testing: ${BUILD_TESTING}")
message(STATUS "  Build analysis: ${BUILD_ANALYSIS}")
message(STATUS "  Python bindings: ${USE_PYTHON}")
message(STATUS "====================================")