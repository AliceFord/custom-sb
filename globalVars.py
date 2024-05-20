from sfparser import parseFixes, parseADs, parseATS
from taxiCoordGen import getAllGroundCoords, standDataParser

import pyttsx3

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Plane

FIXES = parseFixes() | parseADs()
GROUND_POINTS = getAllGroundCoords()
STANDS = standDataParser()
ATS_DATA = parseATS()

otherControllerSocks = []

planes: 'Plane' = []
planeSocks = []
window = None
timeMultiplier: float = 1

allocatedSquawks = []
allocatedCallsigns = []

messagesToSpeak = []
currentSpeakingAC = ""
