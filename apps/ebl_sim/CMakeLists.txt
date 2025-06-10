# EBL Simulation Application

# Add executable
add_executable(ebl_sim main.cc)

# Include directories for cross-module headers
target_include_directories(ebl_sim PRIVATE
    ${CMAKE_SOURCE_DIR}/src
)

# Link libraries
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
    FOLDER "Applications"
)

# Visual Studio specific settings
if(MSVC)
    set_property(TARGET ebl_sim PROPERTY VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
    
    # Set debugger environment to include Geant4 bin directory
    set(GEANT4_BIN_DIR "${Geant4_DIR}/../../bin")
    file(TO_NATIVE_PATH "${GEANT4_BIN_DIR}" GEANT4_BIN_DIR_NATIVE)
    set_property(TARGET ebl_sim PROPERTY VS_DEBUGGER_ENVIRONMENT "PATH=${GEANT4_BIN_DIR_NATIVE};$ENV{PATH}")
endif()

# Copy macros to binary directory
add_custom_command(TARGET ebl_sim POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:ebl_sim>/macros
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_SOURCE_DIR}/macros
        $<TARGET_FILE_DIR:ebl_sim>/macros
    COMMENT "Copying macro files to output directory"
)

# Create output directory
add_custom_command(TARGET ebl_sim POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:ebl_sim>/output
    COMMENT "Creating output directory"
)

# Install executable
install(TARGETS ebl_sim
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install macros with the executable
install(DIRECTORY ${CMAKE_SOURCE_DIR}/macros
    DESTINATION ${CMAKE_INSTALL_BINDIR}
)