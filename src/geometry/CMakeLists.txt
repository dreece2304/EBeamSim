# Geometry module - detector construction
add_library(ebl_geometry STATIC
    src/DetectorConstruction.cc
    src/DetectorMessenger.cc
)

target_include_directories(ebl_geometry
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/src  # For cross-module includes
)

target_link_libraries(ebl_geometry
    PUBLIC
        ${Geant4_LIBRARIES}
        ebl_common
)

# Set properties
set_target_properties(ebl_geometry PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Install library
install(TARGETS ebl_geometry
    EXPORT EBeamSimTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/geometry
    FILES_MATCHING PATTERN "*.hh"
)