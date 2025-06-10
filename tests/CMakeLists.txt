# Unit tests for EBL Simulation

# Find testing framework (optional - using Geant4's built-in testing)
enable_testing()

# Test executable for material properties
add_executable(test_materials test_materials.cc)
target_link_libraries(test_materials
    PRIVATE
        ebl_geometry
        ebl_common
        ${Geant4_LIBRARIES}
)
target_include_directories(test_materials PRIVATE ${CMAKE_SOURCE_DIR}/src)

# Test executable for PSF calculations
add_executable(test_psf test_psf.cc)
target_link_libraries(test_psf
    PRIVATE
        ebl_actions
        ebl_common
        ${Geant4_LIBRARIES}
)
target_include_directories(test_psf PRIVATE ${CMAKE_SOURCE_DIR}/src)

# Add tests
add_test(NAME MaterialTest COMMAND test_materials)
add_test(NAME PSFTest COMMAND test_psf)

# Set working directory for tests
set_tests_properties(MaterialTest PSFTest
    PROPERTIES WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)