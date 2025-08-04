# Beam module - primary particle generation
add_library(ebl_beam STATIC
    src/PrimaryGeneratorAction.cc
    src/PrimaryGeneratorMessenger.cc
    src/PatternGenerator.cc
    src/SquarePatternGenerator.cc
    src/PatternMessenger.cc
)

target_include_directories(ebl_beam
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/src  # For cross-module includes
)

target_link_libraries(ebl_beam
    PUBLIC
        ${Geant4_LIBRARIES}
        ebl_common
        ebl_geometry  # Needs DetectorConstruction
)

# Set properties
set_target_properties(ebl_beam PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Install library
install(TARGETS ebl_beam
    EXPORT EBeamSimTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/beam
    FILES_MATCHING PATTERN "*.hh"
)