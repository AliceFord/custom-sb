# from enum import Enum


class PlaneMode:
    FLIGHTPLAN = 1
    HEADING = 2
    ILS = 3
    GROUND_STATIONARY = 4
    GROUND_TAXI = 5
    GROUND_READY = 6
    NONE = -1

    GROUND_MODES = [GROUND_STATIONARY, GROUND_TAXI, GROUND_READY]
    AIRBORNE_MODES = [FLIGHTPLAN, HEADING, ILS]