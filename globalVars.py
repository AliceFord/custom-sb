from sfparser import parseFixes, parseADs
from taxiCoordGen import getAllGroundCoords, standDataParser

# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from main import Plane

FIXES = parseFixes() | parseADs()
GROUND_POINTS = getAllGroundCoords()
STANDS = standDataParser()

otherControllerSocks = []

planes = []
planeSocks = []
window = None
timeMultiplier: float = 1

allocatedSquawks = []
allocatedCallsigns = []
