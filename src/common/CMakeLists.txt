# Common module - shared utilities and constants
add_library(ebl_common STATIC
    src/DataManager.cc
)

# Generate export header
include(GenerateExportHeader)
generate_export_header(ebl_common
    EXPORT_FILE_NAME ${CMAKE_CURRENT_BINARY_DIR}/include/ebl_common_export.h
)

target_include_directories(ebl_common
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${Geant4_INCLUDE_DIRS}
)

target_link_libraries(ebl_common
    PUBLIC
        ${Geant4_LIBRARIES}
)

# Set properties
set_target_properties(ebl_common PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    FOLDER "Libraries"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Install library
install(TARGETS ebl_common
    EXPORT EBeamSimTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Install headers
install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/common
    FILES_MATCHING PATTERN "*.hh" PATTERN "*.h"
)

# Install generated export header
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/include/ebl_common_export.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ebl_sim/common
)