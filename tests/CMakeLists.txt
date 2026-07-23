# Unit tests for pure-logic simulation helpers (no Geant4 runtime required)

add_executable(test_parsing test_parsing.cc)
target_include_directories(test_parsing PRIVATE ${PROJECT_SOURCE_DIR}/src/common/include)
target_compile_features(test_parsing PRIVATE cxx_std_17)

add_test(NAME parsing_and_binning COMMAND test_parsing)
