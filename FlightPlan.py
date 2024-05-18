from __future__ import annotations
from Route import Route


class FlightPlan:
    def __init__(self, flightRules: str, aircraftType: str, enrouteSpeed: int, departure: str, offBlockTime: int,
                 enrouteTime: int, cruiseAltitude: int, destination: str, route: Route):
        self.flightRules = flightRules
        self.aircraftType = aircraftType
        self.enrouteSpeed = enrouteSpeed
        self.departure = departure
        self.offBlockTime = offBlockTime
        self.enrouteTime = enrouteTime
        self.cruiseAltitude = cruiseAltitude
        self.destination = destination
        self.route = route

    def __str__(self):
        return f":*A:{self.flightRules}:{self.aircraftType}:{self.enrouteSpeed}:{self.departure}:{self.offBlockTime}:{self.enrouteTime}:{self.cruiseAltitude}:{self.destination}:01:00:0:0::/v/:{self.route}"

    @staticmethod
    def duplicate(flightPlan: FlightPlan):
        return FlightPlan(flightPlan.flightRules, flightPlan.aircraftType, flightPlan.enrouteSpeed, flightPlan.departure, flightPlan.offBlockTime, flightPlan.enrouteTime, flightPlan.cruiseAltitude, flightPlan.destination, Route.duplicate(flightPlan.route, flightPlan.departure))

    @staticmethod
    def arrivalPlan(dest: str, route: Route):
        return FlightPlan("I", "A20N", 250, "EDDF", 1130, 1130, 36000, dest, Route(route, "EDDF"))
