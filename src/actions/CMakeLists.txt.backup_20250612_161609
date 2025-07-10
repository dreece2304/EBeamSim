# Actions module - user actions
add_library(ebl_actions STATIC
    src/ActionInitialization.cc
    src/RunAction.cc
    src/EventAction.cc
    src/SteppingAction.cc
)

target_include_directories(ebl_actions
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/src  # For cross-module includes
)

target_link_libraries(ebl_actions
    PUBLIC
        ${Geant4_LIBRARIES}
        ebl_common
        ebl_geometry
        ebl_beam
)

# Set properties
set_target_properties(ebl_actions PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Install library
install(TARGETS ebl_actions
    EXPORT EBeamSimTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/actions
    FILES_MATCHING PATTERN "*.hh"
)