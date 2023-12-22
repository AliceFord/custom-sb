from sfparser import parseFixes

FIXES = parseFixes()

planes = []
planeSocks = []
window = None
timeMultiplier: float = 1

TURN_RATE = 2  # deg / sec

allocatedSquawks = []
allocatedCallsigns = []

CCAMS_SQUAWKS = list(range(1410,1478)) + list(range(2001,2078)) + list(range(2201,2278)) + list(range(2701,2738))  # realistically way way more

ACTIVE_AERODROME = "EGKK"
ACTIVE_RUNWAY = "26L"
ACTIVE_CONTROLLER = "EGKK_APP"
MASTER_CONTROLLER = "LON_S_CTR"
MASTER_CONTROLLER_FREQ = "29430"
# ACTIVE_CONTROLLER = "LON_S_CTR"
# MASTER_CONTROLLER = "EGLL_N_APP"
# MASTER_CONTROLLER_FREQ = "19730"