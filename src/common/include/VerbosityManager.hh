// VerbosityManager.hh - Centralized logging control for performance
#ifndef VERBOSITYMANAGER_HH
#define VERBOSITYMANAGER_HH

#include "G4ios.hh"

class VerbosityManager {
public:
    enum Level {
        SILENT = 0,
        ERRORS = 1,
        WARNINGS = 2,
        INFO = 3,
        DEBUG = 4,
        VERBOSE = 5
    };

    static VerbosityManager* Instance();
    
    void SetVerbosityLevel(Level level) { fVerbosityLevel = level; }
    Level GetVerbosityLevel() const { return fVerbosityLevel; }
    
    // Conditional logging methods
    bool ShouldPrint(Level level) const { return level <= fVerbosityLevel; }
    
    // Convenience methods for common log levels
    bool PrintErrors() const { return ShouldPrint(ERRORS); }
    bool PrintWarnings() const { return ShouldPrint(WARNINGS); }
    bool PrintInfo() const { return ShouldPrint(INFO); }
    bool PrintDebug() const { return ShouldPrint(DEBUG); }
    bool PrintVerbose() const { return ShouldPrint(VERBOSE); }
    
    // Progress reporting control
    void SetProgressInterval(G4int interval) { fProgressInterval = interval; }
    G4int GetProgressInterval() const { return fProgressInterval; }
    bool ShouldReportProgress(G4int eventNumber) const {
        return PrintInfo() && (eventNumber % fProgressInterval == 0);
    }
    
private:
    VerbosityManager() : fVerbosityLevel(INFO), fProgressInterval(10000) {}
    static VerbosityManager* fInstance;
    Level fVerbosityLevel;
    G4int fProgressInterval;
};

// Convenience macros for conditional logging
#define LOG_ERROR(msg) \
    if (VerbosityManager::Instance()->PrintErrors()) { G4cout << "[ERROR] " << msg << G4endl; }

#define LOG_WARNING(msg) \
    if (VerbosityManager::Instance()->PrintWarnings()) { G4cout << "[WARNING] " << msg << G4endl; }

#define LOG_INFO(msg) \
    if (VerbosityManager::Instance()->PrintInfo()) { G4cout << "[INFO] " << msg << G4endl; }

#define LOG_DEBUG(msg) \
    if (VerbosityManager::Instance()->PrintDebug()) { G4cout << "[DEBUG] " << msg << G4endl; }

#define LOG_VERBOSE(msg) \
    if (VerbosityManager::Instance()->PrintVerbose()) { G4cout << "[VERBOSE] " << msg << G4endl; }

#endif // VERBOSITYMANAGER_HH