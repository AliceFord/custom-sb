from dataclasses import dataclass
import time
import pygame
import random
import math
import os,sys
from pyproj import Geod, Proj, transform
from shapely.geometry import LineString
from PlaneMode import PlaneMode
from prettytable import PrettyTable
from util import haversine, EsSocket, ControllerSocket, headingFromTo
from Constants import KM_TO_NM, TURN_RATE
from math import sin, cos, atan2,degrees,radians,tan, asin, sqrt,isclose
from Plane import Plane



class Bot:
    def __init__(self,name : str,threshold : tuple, runway_heading :int):
        self.planes = []
        self.landing_order = []
        self.thd = threshold
        self.rhed = runway_heading
        self.VECTOR_FOR = 5 # nm - in the rma

        self.base_start = self.get_coordinates_pbd(self.thd[0], self.thd[1], (self.rhed + 180)%360, 11)
        self.default_base_len_north = self.get_coordinates_pbd(self.base_start[0],self.base_start[1],(self.rhed + 90)%360,2)
        self.default_base_len_south = self.get_coordinates_pbd(self.base_start[0],self.base_start[1],(self.rhed - 90)%360,2)

        self.init_pygame()
        self.font = pygame.font.Font(None,36)
        self.table_font = pygame.font.Font(None, 15)
        self.start_time = time.time()


        print(self.thd)
        print(self.base_start)
        print(self.default_base_len_north)
        print(self.default_base_len_south)
        print(haversine(self.default_base_len_north[0],self.default_base_len_north[1],self.default_base_len_south[0],self.default_base_len_south[1])/KM_TO_NM)

    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800,800))
        #self.update_pygame()

    def draw_plane(self,plane : Plane):
        x,y = self.convert_coords(plane.lat,plane.lon)
        pygame.draw.circle(self.screen,(255,0,0),(x,y),5)
        print(f"Drawn {plane.callsign} at {x},{y}")
        end_x = x + cos(radians(90 - plane.targetHeading)) * 500 
        end_y = y - sin(radians(90 - plane.targetHeading)) * 500
        pygame.draw.line(self.screen, (255, 0, 0), (x, y), (end_x, end_y), 1)
        pygame.draw.circle(self.screen,(200,200,0), self.convert_coords(plane.base_intercept[0],plane.base_intercept[1]),2)
        

    def update_pygame(self):

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.screen.fill((0,0,0))
        time_left = 5 - ((time.time() - self.start_time)) % 5
        timer = self.font.render(str(int(time_left)),True,(255,255,255))
        self.screen.blit(timer, (self.screen.get_width() - timer.get_width(), 0))

        table = PrettyTable(["Callsign","DTTD","Base Length"])



        for plane in self.planes:
            table.add_row([plane.callsign,self.get_distance_to_td(plane),haversine(plane.base_intercept[0],plane.base_intercept[1],self.base_start[0],self.base_start[1])/KM_TO_NM])
            self.draw_plane(plane)
        
        table_lines = str(table).split('\n')
        for i, line in enumerate(table_lines):
            table_line_text = self.table_font.render(line, True, (255, 255, 255))
            self.screen.blit(table_line_text, (0, i * table_line_text.get_height()))
        pygame.draw.line(self.screen,(255,255,255), self.convert_coords(self.thd[0],self.thd[1]),self.convert_coords(self.base_start[0],self.base_start[1]),2)
        pygame.display.flip()

    def convert_coords(self,lat,lon):
        min_lat,max_lat = 50.977795,52.164555833333
        min_lon,max_lon = 0.89348333333333,-1.4849486111111,
        x = ((lon - min_lon) / (max_lon - min_lon)) * self.screen.get_width()
        y = ((lat - min_lat) / (max_lat - min_lat)) * self.screen.get_height()

        return self.screen.get_width() - x,self.screen.get_height() - y

    def update_landing_order(self) -> bool:
        for plane in self.planes:
            if plane not in self.landing_order:
                if len(self.landing_order) < 2:
                    self.landing_order.append(plane)
                    return False
                new_dist = self.get_distance_to_td(plane)
                for i in range(len(self.landing_order) - 1):
                    plane1_distance = self.get_distance_to_td(
                        self.landing_order[i])
                    plane2_distance = self.get_distance_to_td(
                        self.landing_order[i + 1])

                    if plane2_distance - plane1_distance > self.VECTOR_FOR - 2:
                        if plane1_distance < new_dist < plane2_distance:
                            self.landing_order.insert(i + 1, plane)
                            return True
                else:  # at the back lol
                    self.landing_order.append(plane)
                    return False

    def accept_plane(self, plane) -> None:
        self.planes.append(plane)
        self.update_landing_order()  
        plane.mode = PlaneMode.HEADING
        for p in self.landing_order:
            print(p.callsign)
            print(self.get_distance_to_td(p))
        
        #$CQEGLL_N_APP:@94835:SC:QFA8P:H180

    def get_distance_to_td(self, plane) -> float:
        if plane.ils:
            return haversine(plane.lat,plane.lon,self.thd[0],self.thd[1]) / KM_TO_NM
        if plane.base:
             return (haversine(plane.lat,plane.lon,self.base_start[0],self.base_start[1]) + haversine(self.base_start[0],self.base_start[1],self.thd[0],self.thd[1]))/KM_TO_NM
        
        if plane.base_intercept == (None,None): # set 2 nm base
            if plane.lat > self.thd[0]: # north
                plane.base_intercept = self.default_base_len_north
            else:
                plane.base_intercept = self.default_base_len_south

        return (haversine(plane.lat,plane.lon,plane.base_intercept[0],plane.base_intercept[1]) + haversine(plane.base_intercept[0],plane.base_intercept[1], self.base_start[0],self.base_start[1]) + haversine(self.base_start[0],self.base_start[1],self.thd[0],self.thd[1]))/KM_TO_NM

    

    def get_coordinates_pbd(self,lat, lon, bearing, distance_nautical_miles):
        
        distance_km = distance_nautical_miles * 1.852

        
        distance_rad = distance_km / 6371.01  # Earth's radius in km

        
        bearing_rad = radians(bearing)
        lat1_rad = radians(lat)
        lon1_rad = radians(lon)

        lat2_rad = asin(math.sin(lat1_rad) * cos(distance_rad) +
                            cos(lat1_rad) * sin(distance_rad) * cos(bearing_rad))

        lon2_rad = lon1_rad + atan2(sin(bearing_rad) * sin(distance_rad) * cos(lat1_rad),
                                        cos(distance_rad) - sin(lat1_rad) * sin(lat2_rad))

        
        lat2_deg = degrees(lat2_rad)
        lon2_deg = degrees(lon2_rad)

        return lat2_deg, lon2_deg
    
    def vector(self):
        for i,plane in enumerate(self.landing_order):
            if not plane.base:
                if plane.lat > self.thd[0]: # north
                    targetHeading = (self.rhed + 90)%360
                else:
                    targetHeading = (self.rhed - 90)%360
            elif plane.base:
                    targetHeading = self.rhed
                
                
            turn_angle = ((plane.heading - targetHeading)%360)
            turn_rate_rad = radians(TURN_RATE*3600)
            turn_radius = plane.speed / turn_rate_rad
            angle_rad = radians(turn_angle)
            distance = turn_radius * tan(angle_rad / 2) # d = r * tan(θ / 2)
            print(distance)
            if haversine(plane.lat,plane.lon,plane.base_intercept[0],plane.base_intercept[1])/KM_TO_NM < distance + 0.1 and not plane.base:
                plane.base = True
                plane.targetHeading = targetHeading
            
            if plane.base and not plane.ils and haversine(plane.lat,plane.lon,self.base_start[0],self.base_start[1])/KM_TO_NM < distance + 0.1:
                plane.ils = True
                plane.targetHeading = targetHeading

            print(plane.callsign)
            if i != 0 and not (plane.base or plane.ils): # first plane, or planes on base/ils (dont' take them off lol)
                
                prev_dist = self.get_distance_to_td(self.landing_order[i-1])
                self_distance = self.get_distance_to_td(plane)
                diff = self_distance - prev_dist
                if isclose(diff,self.VECTOR_FOR,abs_tol=0.2):
                    plane.targetHeading = headingFromTo((plane.lat,plane.lon),plane.base_intercept)
                else:
                    diff = self.VECTOR_FOR - diff
                    current_base_length = haversine(plane.base_intercept[0],plane.base_intercept[1],self.base_start[0],self.base_start[1])

                    if plane.lat > self.thd[0]: # north
                        base_len = diff+current_base_length
                        if diff+current_base_length < 1:
                            base_len = 1
                        plane.base_intercept = self.get_coordinates_pbd(self.base_start[0],self.base_start[1],(self.rhed + 90)%360,base_len)

                    else:
                        base_len = diff+current_base_length
                        if diff+current_base_length < 1:
                            base_len = 1
                        plane.base_intercept = self.get_coordinates_pbd(self.base_start[0],self.base_start[1],(self.rhed - 90)%360,diff+base_len)
            plane.targetHeading = headingFromTo((plane.lat,plane.lon),plane.base_intercept)
          

        self.update_pygame()





if __name__ == "__main__":
    bob = Bot("EGLL",(51.477692222222, -0.43244666666667), 269)