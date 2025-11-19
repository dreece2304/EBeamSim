"""
Application Constants for EBL Simulation GUI
Centralizes all magic numbers and configuration values
"""

# =============================================================================
# OUTPUT AND LOGGING
# =============================================================================
MAX_GUI_OUTPUT_LINES = 5000  # Maximum lines in output log before auto-truncation
MAX_GUI_LINES_FOR_FILTERING = 3000  # Start filtering output for large simulations

# =============================================================================
# SIMULATION THRESHOLDS
# =============================================================================
LARGE_SIMULATION_THRESHOLD = 100000  # Events threshold for optimization warnings
VERY_LARGE_SIMULATION_THRESHOLD = 1000000  # Threshold for aggressive filtering
HUGE_SIMULATION_THRESHOLD = 10000000  # 10M events - warn about very long runtime

# Minimum events for good statistics
MIN_EVENTS_RECOMMENDED = 1000
MIN_EVENTS_FOR_TESTING = 10000
MIN_EVENTS_FOR_PRODUCTION = 100000

# =============================================================================
# PROGRESS TRACKING
# =============================================================================
PROGRESS_ESTIMATION_FACTOR = 8000  # Factor for estimating progress from energy reports
PROGRESS_UPDATE_INTERVAL = 1.0  # Seconds between progress updates

# Progress reporting thresholds (percentage) based on simulation size
PROGRESS_REPORT_THRESHOLD_HUGE = 0.5  # >2M events: report every 0.5%
PROGRESS_REPORT_THRESHOLD_LARGE = 1.0  # >500k events: report every 1%
PROGRESS_REPORT_THRESHOLD_MEDIUM = 2.0  # >50k events: report every 2%
PROGRESS_REPORT_THRESHOLD_SMALL = 5.0  # <50k events: report every 5%

# Simulation size breakpoints for adaptive thresholds
SIMULATION_SIZE_HUGE = 2000000  # 2M events
SIMULATION_SIZE_LARGE = 500000  # 500k events
SIMULATION_SIZE_MEDIUM = 50000  # 50k events

# =============================================================================
# BEAM PARAMETERS (Typical ranges for validation)
# =============================================================================
# Energy (keV)
BEAM_ENERGY_MIN = 10.0
BEAM_ENERGY_MAX = 300.0
BEAM_ENERGY_TYPICAL_MIN = 50.0
BEAM_ENERGY_TYPICAL_MAX = 125.0

# Beam size (nm FWHM)
BEAM_SIZE_MIN = 0.5
BEAM_SIZE_MAX = 100.0
BEAM_SIZE_TYPICAL_MIN = 2.0
BEAM_SIZE_TYPICAL_MAX = 10.0

# =============================================================================
# MATERIAL PARAMETERS (Typical ranges for validation)
# =============================================================================
# Resist thickness (nm)
RESIST_THICKNESS_MIN = 5.0
RESIST_THICKNESS_MAX = 500.0
RESIST_THICKNESS_TYPICAL_MIN = 10.0
RESIST_THICKNESS_TYPICAL_MAX = 100.0

# Material density (g/cm³)
MATERIAL_DENSITY_MIN = 0.5
MATERIAL_DENSITY_MAX = 5.0
MATERIAL_DENSITY_TYPICAL_MIN = 1.0
MATERIAL_DENSITY_TYPICAL_MAX = 2.5

# =============================================================================
# UI SETTINGS
# =============================================================================
# Thread wait timeouts (milliseconds)
THREAD_WAIT_TIMEOUT = 5000  # 5 seconds for graceful shutdown
THREAD_TERMINATE_TIMEOUT = 2000  # 2 seconds before forced termination

# Progress bar
PROGRESS_BAR_MAX_WIDTH = 200  # pixels

# Status bar message timeout (milliseconds)
STATUS_MESSAGE_TIMEOUT = 3000  # 3 seconds

# =============================================================================
# FILE OPERATIONS
# =============================================================================
# Recent files
MAX_RECENT_FILES = 10

# File size limits
MAX_LOG_FILE_SIZE_MB = 100

# =============================================================================
# DEFAULT VALUES
# =============================================================================
# Beam defaults
DEFAULT_BEAM_ENERGY = 100.0  # keV
DEFAULT_BEAM_SIZE = 5.0  # nm FWHM
DEFAULT_BEAM_POS_Z = 100.0  # nm above sample
DEFAULT_BEAM_DIR_Z = -1.0  # Pointing downward

# Material defaults
DEFAULT_RESIST_THICKNESS = 30.0  # nm
DEFAULT_RESIST_DENSITY = 1.35  # g/cm³

# Simulation defaults
DEFAULT_EVENTS_QUICK_TEST = 10000
DEFAULT_EVENTS_STANDARD = 100000
DEFAULT_EVENTS_HIGH_QUALITY = 1000000

# =============================================================================
# PHYSICS SETTINGS
# =============================================================================
MIN_TRACKING_ENERGY_EV = 10  # Minimum tracking energy in eV
