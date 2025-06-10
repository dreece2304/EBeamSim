# Physics module - physics lists and processes
add_library(ebl_physics STATIC
    src/PhysicsList.cc
    src/PhysicsMessenger.cc
)

target_include_directories(ebl_physics
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/src  # For cross-module includes
)

target_link_libraries(ebl_physics
    PUBLIC
        ${Geant4_LIBRARIES}
        ebl_common
)

# Set properties
set_target_properties(ebl_physics PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Install library
install(TARGETS ebl_physics
    EXPORT EBeamSimTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/physics
    FILES_MATCHING PATTERN "*.hh"
)