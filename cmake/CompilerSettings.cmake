# Compiler settings for different platforms

if(MSVC)
    # Visual Studio settings
    set_property(GLOBAL PROPERTY USE_FOLDERS ON)

    # Compiler warnings
    add_compile_options(/W3)           # Warning level 3
    add_compile_options(/wd4251)       # Disable DLL interface warnings
    add_compile_options(/wd4996)       # Disable deprecated warnings

    # Use multi-threaded DLL runtime
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")

    # Set optimization flags
    set(CMAKE_CXX_FLAGS_RELEASE "/MD /O2 /Ob2 /DNDEBUG")
    set(CMAKE_CXX_FLAGS_DEBUG "/MDd /Zi /Ob0 /Od /RTC1")
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/MD /Zi /O2 /Ob1 /DNDEBUG")

    # Enable parallel compilation
    add_compile_options(/MP)

    # Set bigobj flag for large object files
    add_compile_options(/bigobj)

elseif(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    # GCC/Clang settings
    add_compile_options(-Wall -Wextra -Wpedantic)
    add_compile_options(-Wno-unused-parameter)
    add_compile_options(-Wno-sign-compare)

    # Debug/Release flags
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG")
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g -DNDEBUG")

    # Enable colored output
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        add_compile_options(-fcolor-diagnostics)
    elseif(CMAKE_COMPILER_IS_GNUCXX)
        if(CMAKE_CXX_COMPILER_VERSION VERSION_GREATER 4.9)
            add_compile_options(-fdiagnostics-color=always)
        endif()
    endif()
endif()

# Position independent code (needed for shared libraries)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# RPATH settings for installed binaries
if(NOT WIN32)
    set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
    set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")
endif()

# Export compile commands for IDEs
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)