# EBL Project Context - Quick Reference

## 🚀 **QUICK START GUIDE FOR CLAUDE**

### **Project Type**: Scientific Simulation (Electron Beam Lithography)
### **Languages**: C++ (Geant4) + Python (PySide6)
### **Status**: Phase 2 - GUI Modularization (In Progress)

## 📋 **IMMEDIATE CONTEXT**

**Current Task**: Extracting plotting widgets from 3,953-line monolithic GUI file
**Goal**: Create modular architecture with <500 line files
**Priority**: Maintain cross-platform compatibility (GitHub workflow)

## 🎯 **KEY OBJECTIVES**
1. Break down monolithic `scripts/gui/ebl_gui.py` (3,953 lines)
2. Create start menu with PSF vs Pattern mode selection  
3. Maintain all existing functionality
4. Zero hardcoded paths (cross-platform requirement)

## 📁 **CRITICAL FILES TO KNOW**
- **`EBL_PROJECT_OPTIMIZATION_PLAN.md`** - Master reference (READ FIRST)
- **`CLAUDE.md`** - Main Claude instructions
- **`scripts/gui/ebl_gui.py`** - Monolithic file being modularized
- **`src/`** - C++ source (Phase 1 complete, optimized)

## 🚨 **ESSENTIAL RULES**
- No hardcoded paths (cross-platform requirement)
- No Python files >500 lines (Phase 2 target)
- Preserve all existing functionality during refactoring
- Use modern C++17 and type-hinted Python

## 🔄 **WORKFLOW**
1. Read master plan document first
2. Check current phase status
3. Follow established modular patterns
4. Test cross-platform compatibility