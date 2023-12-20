from sfparser import loadSidAndFixData
from globals import *

class Route:
    def __init__(self, route: str):
        self.route = route
        self.initial = True
        self.fixes = []
        self.initialiseFixesFromRoute()

    def initialiseFixesFromRoute(self):
        fixAirways = self.route.split(" ")

        if len(fixAirways) == 2:  # TODO: BUILD A BETTER PARSER!
            if fixAirways[1] == "AMDUT1G":
                self.fixes = ["AMDUT", "SFD", "WILLO"]
                return
            elif fixAirways[1] == "VASUX1G":
                self.fixes = ["VASUX", "TELTU", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "SIRIC1G":
                self.fixes = ["SIRIC", "NIGIT", "MID", "TUFOZ", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "TELTU1G":
                self.fixes = ["TELTU", "SFD", "TIMBA"]
                return
            elif fixAirways[1] == "ABSAV1G":
                self.fixes = ["ABSAV", "AVANT", "GWC", "HOLLY", "WILLO"]
                return
            elif fixAirways[1] == "KIDLI1G":
                self.fixes = ["KIDLI", "MID", "TUFOZ", "HOLLY", "WILLO"]
                return
            
        if fixAirways[0].endswith("/26L"):  # TODO: choose runway
            data = loadSidAndFixData("EGKK")  # TODO: choose airport
            sidName = fixAirways[0].split("/")[0]
            self.fixes = data[0][sidName]["26L"].split(" ")  # TODO: choose runway
            FIXES.update(data[1])
            fixAirways.pop(0)
        
        for i in range(0, len(fixAirways), 2):
            initialFix = fixAirways[i]
            # airway = fixAirways[i + 1]
            # finalFix = fixAirways[i + 2]

            self.fixes.append(initialFix)

            # TODO: add airway fixes for usable directs

    def removeFirstFix(self):
        self.fixes.pop(0)

    def __str__(self):
        return self.route
    
    @staticmethod
    def duplicate(route):
        return Route(route.route)
