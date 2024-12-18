import re
from sfparser import loadSidAndFixData, loadStarAndFixData
from globalVars import ATS_DATA, FIXES
from Constants import ACTIVE_RUNWAYS


class Route:
    def __init__(self, route: str, depAD: str, arrAD: str = None):
        self.route = route
        self.initial = True
        self.fixes = []
        self.depAD = depAD
        self.arrAD = arrAD
        self.initialiseFixesFromRoute()

    def initialiseFixesFromRoute(self):
        global FIXES
        fixAirways = self.route.split(" ")

        if self.depAD.startswith("EG"):
            try:
                if fixAirways[0].endswith("/" + ACTIVE_RUNWAYS[self.depAD]):
                    try:
                        data = loadSidAndFixData(self.depAD)
                        sidName = fixAirways[0].split("/")[0]
                        self.fixes = data[0][sidName][ACTIVE_RUNWAYS[self.depAD]].split(" ")
                        FIXES.update(data[1])
                    except KeyError:
                        pass
                    fixAirways.pop(0)
            except KeyError:
                pass

        addToEnd = []

        if self.arrAD is not None and self.arrAD.startswith("EG"):
            try:
                if (m := re.match(r"([A-Z]{3,5}\d[A-Z])", fixAirways[-1])):
                    starData, extraFixes = loadStarAndFixData(self.arrAD)
                    FIXES.update(extraFixes)
                    addToEnd.extend(starData[m.group(1)][ACTIVE_RUNWAYS[self.arrAD]].split(" "))
                    addToEnd.pop(0)
            except KeyError:
                pass

        prevWpt = None
        prevRoute = None

        for fix in fixAirways:
            if "/" in fix:
                fix = fix.split("/")[0]  # Remove level / speed restriction

            try:
                FIXES[fix]

                if prevWpt is not None and prevRoute is not None:
                    atsData = ATS_DATA[prevRoute]

                    try:
                        prevIndex = atsData.index(prevWpt)
                        currentIndex = atsData.index(fix)
                    except ValueError:  # one of the fixes isn't in the route!!
                        self.fixes.append(fix)
                        prevWpt = fix
                        prevRoute = None
                        continue

                    if prevIndex < currentIndex:
                        for i in range(prevIndex + 1, currentIndex):
                            self.fixes.append(atsData[i])
                    else:
                        for i in range(prevIndex - 1, currentIndex, -1):
                            self.fixes.append(atsData[i])

                    prevWpt = None
                    prevRoute = None

                prevWpt = fix
                self.fixes.append(fix)
            except KeyError:
                if fix in ATS_DATA.keys():
                    prevRoute = fix
                else:
                    prevRoute = None

        self.fixes.extend(addToEnd)

        # for i in range(0, len(fixAirways), 2):
        #     initialFix = fixAirways[i]

        #     self.fixes.append(initialFix)

        #     # TODO: add airway fixes for usable directs

    def removeFirstFix(self):
        self.fixes.pop(0)

    def __str__(self):
        return self.route

    @classmethod
    def duplicate(cls, route, depAD, arrAD=None):
        return cls(route.route, depAD, arrAD)


if __name__ == "__main__":
    r = Route("LIFFY1N LIFFY L975 WAL DCT POL/N0272F180 P18 NATEB")
    print(r.fixes)
