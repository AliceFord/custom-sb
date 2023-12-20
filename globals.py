from sfparser import parseFixes

FIXES = parseFixes()

planes = []
planeSocks = []
window = None
timeMultiplier: float = 1

TURN_RATE = 2  # deg / sec

allocatedSquawks = []

CCAMS_SQUAWKS = list(range(1410,1478)) + list(range(2001,2078)) + list(range(2201,2278)) + list(range(2701,2738))  # realistically way way more

ACTIVE_AERODROME = "EGLL"
ACTIVE_RUNWAY = "27L"
ACTIVE_CONTROLLER = "EGLL_N_APP"
