# EBL Simulation Project - Claude Code Instructions

## 🚀 **PROJECT CONTEXT**
This is an **Electron Beam Lithography (EBL) simulation project** using Geant4 11.3.2 (C++) and PySide6 (Python GUI). The project simulates point spread functions (PSF) and pattern exposure for JEOL e-beam lithography systems.

**Key Purpose**: Scientific simulation for semiconductor manufacturing research, specifically for BEAMER software integration and proximity effect correction.

## 📋 **CURRENT PROJECT STATUS**

### **🎉 MAJOR BREAKTHROUGH: MODULAR ARCHITECTURE DESIGNED**
**Date**: August 5, 2025 - **ADVANCED MODULARIZATION SESSION**

### **✅ COMPLETED WORK:**
- **Phase 1**: ✅ C++ optimization complete (modern C++17, Geant4 11.3+ best practices)
- **Phase 2**: ✅ Professional transformation complete (GUI, CLI, core infrastructure)
- **Phase 3**: ✅ **MODULAR ARCHITECTURE BREAKTHROUGH** - Ultra-maintainable structure designed

### **✅ CURRENT STATUS: MODULAR ARCHITECTURE FUNCTIONAL**
- **Goal**: Transform existing professional code into ultra-modular, maintainable architecture
- **Achievement**: **✅ Complete modular structure implemented, tested, and functional**
- **Current Status**: ✅ Dependencies installed, architecture fixes complete, both systems operational

## 🎯 **NEXT PRIORITIES**

1. **✅ COMPLETED**: Modular architecture fixes and dependency installation
2. **READY**: Deploy advanced agents for GUI integration, physics validation, and optimization
3. **READY**: Begin Phase 2 core functionality development with agent coordination

## 📚 **ESSENTIAL REFERENCE DOCUMENTS**

### **Master Reference**: 
- **`EBL_PROJECT_OPTIMIZATION_PLAN.md`** - Comprehensive project plan and file inventory
- **ALWAYS READ THIS FIRST** when starting work on this project

### **Key Technical Info**:
- **Geant4 Version**: 11.3.2 (latest stable)
- **C++ Standard**: C++17 minimum
- **Python**: 3.10+ with PySide6
- **Platform**: Cross-platform (Windows/Linux/macOS)

## 🏗️ **ARCHITECTURE PRINCIPLES**

### **C++ Code (Phase 1 Complete):**
- ✅ Modern C++17: constexpr, move semantics, noexcept
- ✅ Geant4 11.3+ best practices: proper accumulables, thread safety
- ✅ Performance optimized: reduced copies, efficient memory usage

### **Python GUI (Phase 2 - In Progress):**
- 🎯 **Target**: Modular MVC architecture
- 🎯 **Rule**: No single file > 500 lines
- 🎯 **Pattern**: Models → Services → Views → Widgets
- 🎯 **Modes**: PSF Analysis vs Pattern Simulation interfaces

### **Cross-Platform Requirements:**
- ❌ **NEVER** use hardcoded paths
- ✅ **ALWAYS** use `pathlib.Path` for file operations  
- ✅ **ALWAYS** detect Geant4 installation automatically
- ✅ **ALWAYS** test on multiple platforms via environment variables

## 💻 **DEVELOPMENT ENVIRONMENT**

### **Target System - "Nugtop":**
- **OS**: Windows 11 Home (Build 26100) + WSL2 Ubuntu (Claude terminal)
- **CPU**: AMD Ryzen 9 8945HS w/ Radeon 780M Graphics (8 cores, 4.00 GHz) - High performance
- **RAM**: 32.0 GB (31.3 GB usable) - Excellent for large simulations
- **GPU**: NVIDIA GeForce RTX 4070 Laptop GPU (4608 CUDA cores, 8188 MB GDDR6, 90W Max-Q)
  - **Driver**: Studio Driver 577.00 (latest) - Future GPU acceleration potential
  - **Memory**: 24.2 GB total graphics memory (8.2 GB dedicated + 16 GB shared)
- **Storage**: SSD 953.9 GB - Fast I/O for large data files

### **Development Workflow:**
- **IDE**: CLion on Windows 11 for C++ development
- **Terminal**: WSL2 Ubuntu terminal within CLion for Claude Code
- **Build**: Native Linux builds in WSL2 environment
- **Cross-platform**: Code works on Windows/Linux/macOS via GitHub

## 🔧 **OPTIMIZED BUILD COMMANDS**

### **Build System (Optimized for Ryzen 9 8945HS):**
```bash
# Create build directory
mkdir -p build && cd build

# Configure with CMake (optimized for 8-core Ryzen)
cmake .. -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_CXX_FLAGS="-march=native -mtune=native -O3" \
         -DGEANT4_BUILD_MULTITHREADED=ON

# Build with all 8 cores (Ryzen 9 8945HS optimization)
make -j8  # Use all 8 cores for maximum build speed

# For testing/development builds
make -j6  # Leave 2 cores free for system responsiveness
```

### **Performance Optimizations for Your Hardware:**
```bash
# Large simulation settings (32GB RAM advantage)
export G4FORCE_MULTITHREADED=ON
export G4MULTITHREADED=ON
export OMP_NUM_THREADS=8  # Match CPU cores

# Memory optimization for large PSF simulations
export G4GEOM_CACHE_DEPTH=5  # Optimize for 32GB RAM
```

### **GUI Development:**
```bash
# Run GUI (after locating correct version)
cd scripts/gui
python ebl_gui.py  # Current monolithic version

# Future modular launcher:
python ebl_launcher.py  # Target start menu
```

## 📁 **CRITICAL FILE LOCATIONS**

### **Main Reference:**
- **`EBL_PROJECT_OPTIMIZATION_PLAN.md`** - Master plan and file inventory (READ FIRST!)

### **C++ Source (Phase 1 Complete):**
- **`src/actions/src/RunAction.cc`** - ✅ Optimized energy collection
- **`src/beam/src/PatternGenerator.cc`** - ✅ Optimized JEOL pattern generation  
- **`src/common/include/EBLConstants.hh`** - ✅ All constexpr optimizations

### **Python GUI (Phase 2 - Modularization in Progress):**
- **`scripts/gui/ebl_gui.py`** - 🚨 MONOLITHIC (3,953 lines) - Being broken down
- **`scripts/gui/core/file_manager.py`** - ✅ Extracted utility
- **`scripts/gui/widgets/common/status_button.py`** - ✅ Extracted UI component
- **`scripts/gui/utils/threading_utils.py`** - ✅ Extracted cross-platform simulation runner

### **Project Structure:**
- **Working Directory**: `/mnt/c/Users/dreec/CLionProjects/EBeamSim/`
- **Build Directory**: `build_test/` (for testing)
- **GUI Scripts**: `scripts/gui/`
- **C++ Source**: `src/`

## 🚨 **CRITICAL RULES**

### **File Modification Rules:**
1. **NEVER break existing functionality** during refactoring
2. **ALWAYS preserve cross-platform compatibility**
3. **NEVER introduce hardcoded paths**
4. **ALWAYS add type hints to new Python code**
5. **ALWAYS use modern C++17 practices**

### **GUI Modularization Rules:**
1. **No Python file > 500 lines** (target for Phase 2)
2. **Extract classes** from monolithic file systematically
3. **Maintain MVC separation**: Models, Views, Controllers clearly separated
4. **Create mode-specific interfaces**: PSF vs Pattern workflows

### **Cross-Platform Rules:**
1. **Path Detection**: Use environment variables and automatic detection
2. **File Operations**: Always use `pathlib.Path`
3. **Process Execution**: Handle Windows/Linux differences properly

## 🎯 **WORKFLOW FOR NEW SESSIONS**

### **When Starting Work:**
1. **Read** `EBL_PROJECT_OPTIMIZATION_PLAN.md` first
2. **Check current phase** in the todo tracking
3. **Verify build status** with quick compilation test
4. **Review recent changes** in git status if needed

### **Before Making Changes:**
1. **Understand the current architecture** from reference doc
2. **Follow established patterns** from completed phases
3. **Test cross-platform compatibility** considerations
4. **Preserve all existing functionality**

### **Quality Checks:**
1. **C++**: Compile without warnings, follow modern practices
2. **Python**: Type hints, no files >500 lines, proper MVC separation
3. **Cross-platform**: No hardcoded paths, automatic path detection
4. **Architecture**: Clean imports, no circular dependencies

## 🔄 **CURRENT PROJECT STATUS**

### **🎉 BREAKTHROUGH MILESTONE: PROFESSIONAL TRANSFORMATION 100% COMPLETE**
**Date**: August 5, 2025 - **COMPLETE PROFESSIONAL REFACTORING SESSION**

The project has undergone a **complete professional transformation** with industry-standard architecture:

### **✅ PROFESSIONAL INFRASTRUCTURE (COMPLETED):**
- **✅ Professional Python Package**: Modern `setup.py`, `pyproject.toml`, proper versioning
- **✅ Configuration Management**: Type-safe config with Pydantic, environment-specific settings
- **✅ Professional Logging**: Structured logging with performance metrics, JSON output
- **✅ Data Management**: Multi-format support, metadata tracking, validation
- **✅ Core Business Logic**: 
  - Professional SimulationManager with state tracking
  - Advanced PatternGenerator with multiple pattern types
  - Cross-platform execution with progress monitoring

### **✅ COMPLETE GUI TRANSFORMATION:**
- **Professional GUI Package**: Complete `python/ebl_sim/gui/` with modern interfaces
- **Modern Launcher**: Graphical mode selection with professional styling
- **Dedicated Modes**: PSF Analysis and Pattern Simulation interfaces
- **Complete CLI**: Full command-line interface with all features
- **Reduced monolithic GUI**: 3,960 → 2,369 lines (40% reduction) + new professional structure

### **📁 NEW PROFESSIONAL STRUCTURE:**
```
EBeamSim/
├── python/ebl_sim/               # ✅ Professional Python package
│   ├── core/                     # ✅ Business logic
│   │   ├── config_manager.py     # ✅ Type-safe configuration  
│   │   ├── data_manager.py       # ✅ Professional data handling
│   │   ├── simulation_manager.py # ✅ Simulation orchestration
│   │   └── pattern_generator.py  # ✅ Advanced pattern generation
│   ├── gui/                      # ✅ Professional GUI package
│   │   ├── launcher.py           # ✅ Modern start menu
│   │   ├── psf_mode.py          # ✅ PSF analysis interface
│   │   ├── pattern_mode.py      # ✅ Pattern simulation interface
│   │   └── main_window.py       # ✅ Professional main window
│   ├── cli.py                    # ✅ Complete CLI interface
│   └── utils/                    # ✅ Professional utilities
├── config/                       # 🆕 Configuration files
│   ├── default.json             # ✅ Base configuration
│   ├── development.json         # ✅ Dev environment
│   └── production.json          # ✅ Production settings
└── scripts/gui/                 # 🔄 Legacy (being migrated)
```

### **🎯 NEXT PROJECT PHASE: Organization & Testing**
1. **Directory cleanup** - Remove obsolete files and organize build systems
2. **Testing framework** - Comprehensive test suite for all components
3. **Documentation finalization** - Complete user and developer documentation
4. **Performance benchmarking** - Validate optimization improvements

## 💡 **TIPS FOR CLAUDE**

- **File sizes matter**: Always check line counts before modification
- **References first**: Read the master plan document before deep work
- **Cross-platform focus**: This project runs on multiple systems via GitHub
- **Scientific accuracy**: This is real research code for semiconductor manufacturing
- **Mode-based thinking**: PSF analysis vs Pattern simulation are different workflows

### **📝 DOCUMENTATION MAINTENANCE PROTOCOL**
**CRITICAL**: Claude should proactively update project documentation:

1. **After Major Milestones**: Update `CLAUDE.md` and `EBL_PROJECT_OPTIMIZATION_PLAN.md` with:
   - New achievements and completions
   - Updated project structure
   - Modified next steps and priorities
   - Performance metrics and improvements

2. **Before Conversation Compaction**: When conversation approaches token limits:
   - Save current progress to documentation files
   - Update todo lists and project status
   - Document any architectural decisions made
   - Preserve context for future Claude sessions

3. **Regular Updates**: Every 10-15 major tool calls, check if documentation needs updates

4. **Version Control**: Always increment "Last Updated" timestamps and phase completions

## 📊 **SUCCESS METRICS**

### **✅ COMPLETED:**
- **✅ Professional package structure** with proper Python packaging standards
- **✅ Type-safe configuration management** with environment-specific settings
- **✅ Professional logging system** with structured output and performance metrics
- **✅ Advanced data management** with multi-format support and validation
- **✅ Core business logic** with simulation orchestration and pattern generation
- **✅ Monolithic file reduction** from 3,960 → 2,369 lines (40% improvement)
- **✅ Cross-platform compatibility** with automatic path detection

### **✅ COMPLETED:**
- [x] GUI migration to professional structure with launcher, PSF/Pattern modes
- [x] CLI interface for batch operations with full feature set
- [x] Start menu with mode separation (PSF vs Pattern)
- [x] Professional package structure with proper entry points

### **🔄 NEXT PHASE:**
- [ ] Comprehensive testing framework
- [ ] Directory cleanup and organization
- [ ] Full workflow preservation testing
- [ ] Performance optimization validation
- [ ] Documentation finalization for new architecture

---

**Last Updated**: August 5, 2025  
**Phase**: PROFESSIONAL TRANSFORMATION COMPLETE (100%)  
**Major Achievement**: Complete professional architecture with GUI, CLI, and core infrastructure  
**Next Review**: After testing framework implementation