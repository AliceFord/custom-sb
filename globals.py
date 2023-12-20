from sfparser import parseFixes

FIXES = parseFixes()

planes = []
planeSocks = []
window = None
timeMultiplier: float = 1

TURN_RATE = 2  # deg / sec