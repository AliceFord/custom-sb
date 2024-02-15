from sfparser import loadSidAndFixData
from globalVars import FIXES
from Constants import ACTIVE_RUNWAY, ACTIVE_AERODROME


class Route:
    def __init__(self, route: str):
        self.route = route
        self.initial = True
        self.fixes = []
        self.initialiseFixesFromRoute()

    def initialiseFixesFromRoute(self):
        fixAirways = self.route.split(" ")

        if fixAirways[0].endswith("/" + ACTIVE_RUNWAY):
            try:
                data = loadSidAndFixData(ACTIVE_AERODROME)
                sidName = fixAirways[0].split("/")[0]
                self.fixes = data[0][sidName][ACTIVE_RUNWAY].split(" ")
                FIXES.update(data[1])
            except KeyError:
                pass
            fixAirways.pop(0)

        for fix in fixAirways:
            try:
                FIXES[fix]
                self.fixes.append(fix)
            except KeyError:
                pass

        # for i in range(0, len(fixAirways), 2):
        #     initialFix = fixAirways[i]

        #     self.fixes.append(initialFix)

        #     # TODO: add airway fixes for usable directs

    def removeFirstFix(self):
        self.fixes.pop(0)

    def __str__(self):
        return self.route

    @classmethod
    def duplicate(cls, route):
        return cls(route.route)
