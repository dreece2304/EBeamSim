// VerbosityManager.cc - Implementation
#include "VerbosityManager.hh"

VerbosityManager* VerbosityManager::fInstance = nullptr;

VerbosityManager* VerbosityManager::Instance() {
    if (!fInstance) {
        fInstance = new VerbosityManager();
    }
    return fInstance;
}