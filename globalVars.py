from sfparser import parseFixes
from taxiCoordGen import getAllGroundCoords, standDataParser

FIXES = parseFixes()
GROUND_POINTS = getAllGroundCoords()
STANDS = standDataParser()

planes = []
planeSocks = []
window = None
timeMultiplier: float = 1

TURN_RATE = 2  # deg / sec
TAXI_SPEED = 15  # knots
PUSH_SPEED = 5  # knots

allocatedSquawks = []
allocatedCallsigns = []

CCAMS_SQUAWKS = list(range(1410,1478)) + list(range(2001,2078)) + list(range(2201,2278)) + list(range(2701,2738))  # realistically way way more

ACTIVE_AERODROME = "EGSS"
ACTIVE_RUNWAY = "22"
ACTIVE_CONTROLLER = "EGSS_APP"
MASTER_CONTROLLER = "LON_S_CTR"
MASTER_CONTROLLER_FREQ = "29430"
# ACTIVE_CONTROLLER = "LON_S_CTR"
# MASTER_CONTROLLER = "EGLL_N_APP"
# MASTER_CONTROLLER_FREQ = "19730"