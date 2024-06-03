from dataclasses import dataclass
import time
import pygame
import random
import math
import os
from prettytable import PrettyTable
from util import haversine




class Bot:
    def __init__(self,name : str,threshold : tuple, runway_heading :int):
        self.planes = []
        self.landing_order = []
        self.thd = threshold
        self.rhed = runway_heading
        self.VECTOR_FOR = 5 # nm - in the rma


    def update_landing_order(self) -> bool:
        for plane in self.planes:
            if plane not in self.landing_order:
                new_dist = self.get_distance_to_td(plane)
                for i in range(len(self.landing_order) - 1):
                    plane1_distance = self.get_distance_to_td(
                        self.landing_order[i])
                    plane2_distance = self.get_distance_to_td(
                        self.landing_order[i + 1])

                    if plane2_distance - plane1_distance > 8 * 50:  # 8 nm gap
                        if plane1_distance < new_dist < plane2_distance:
                            self.landing_order.insert(i + 1, plane)
                            return True
                else:  # at the back lol
                    self.landing_order.append(plane)
                    return False

    def accept_plane(self, plane) -> None:
        self.planes.append(plane)
        self.update_landing_order()  
        print("BOTATC: LANDING ORDER")
        for p in self.landing_order:
            print(p.callsign)

    def get_distance_to_td(self, plane) -> float:
        return 10
        if plane.base and not plane.ils:
            return (abs(self.runway_pos[1] - plane.y) + 550)
        if plane.ils:
            return plane.x
        rad = math.radians(plane.h - 90)
        dx = 550 - plane.x
        dy = dx * math.tan(rad)
        turn_y = plane.y + dy

        dx = 550 - plane.x
        dy = turn_y - plane.y
        distance_to_base = (dx**2 + dy**2) ** 0.5

        distance_on_base = abs(self.runway_pos[1] - turn_y)

        distance_down_ILS = 550

        return distance_to_base + distance_on_base + distance_down_ILS

    def find_itx_heading(self, plane)-> int:
        print("Getting heading")
        order = self.landing_order.index(plane)
        plane_before = self.landing_order[order-1]

        current_distance = self.get_distance_to_td(plane)
        proc_distance = self.get_distance_to_td(plane_before)
        # should never be negative... (hopefully)
        diff = (current_distance - proc_distance) / 50
        print(diff)
        if not (math.isclose(diff, self.VECTOR_FOR, abs_tol=0.1) or math.isclose(plane.x, 550, abs_tol=3*50) or plane.base or plane.ils):
            test_plane = Plane(-1, plane.x, plane.y, h=plane.h)
            print("new plane")
            if diff > self.VECTOR_FOR:  # too far - get moar planes in
                print("Too far")
                if plane.y > self.runway_pos[1] and plane.x < 550 or plane.y < self.runway_pos[1] and plane.x > 550:
                    print("left")
                    for _ in range(17):
                        test_plane.h -= 5
                        new_distance = self.get_distance_to_td(test_plane)
                        new_diff = (new_distance - proc_distance) / 50
                        if new_diff < self.VECTOR_FOR:
                            return test_plane.h + 5  # new heading to turn to
                else:
                    print("right")
                    for _ in range(17):
                        test_plane.h += 5
                        new_distance = self.get_distance_to_td(test_plane)
                        new_diff = (new_distance - proc_distance) / 50
                        if new_diff < self.VECTOR_FOR:
                            return test_plane.h - 5  # new heading to turn to
            else:  # too close
                if plane.y > self.runway_pos[1] and plane.x < 550 or plane.y < self.runway_pos[1] and plane.x > 550:
                    print("Right")
                    for _ in range(17):
                        test_plane.h += 5
                        new_distance = self.get_distance_to_td(test_plane)
                        new_diff = (new_distance - proc_distance)/50
                        if new_diff > self.VECTOR_FOR:
                            return test_plane.h  # new heading to turn to
                else:
                    print("left")
                    for _ in range(17):
                        test_plane.h -= 5
                        new_distance = self.get_distance_to_td(test_plane)
                        new_diff = (new_distance - proc_distance)/50
                        if new_diff > self.VECTOR_FOR:
                            return test_plane.h  # new heading to turn to
        return plane.h

    def vector(self):
        ...


#@dataclass
class Plane:
    def __init__(self, cs, x, y, d=-1, h=None):
        self.cs = cs
        self.x = x
        self.y = y
        self.d = d
        if h == None:
            self.h = 90 if x < 550 else 270
        else:
            self.h = h
        self.s = 180
        self.base = False
        self.ils = False
        self.landed = False