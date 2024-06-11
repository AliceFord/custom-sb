from copy import copy
import neat
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
import main
from Constants import ACTIVE_RUNWAYS,RADAR_UPDATE_RATE
from globalVars import FIXES
from sfparser import loadRunwayData
from PlaneMode import PlaneMode
import math
from shapely.geometry import Point,Polygon
import util
import time
import pickle
from Trainer_Plane import Plane
import random
from prettytable import PrettyTable

ROUTES = [["NOVMA","OCK"],
          ["ODVIK","BIG"],
          ["BRAIN","LAM"],
          ["COWLY","BNN"]]

table = PrettyTable()

# Add column names
table.field_names = ["Latitude", "Longitude", "Altitude", "Speed", "Heading","TargetHeading","Mode"]


class Bot:
    def __init__(self,airport):
        self.airport = airport
        self.planes = []

        self.RMA = [(51.726111111111, -0.54972222222222),
                    (51.655833333333, -0.32583333333333),
                    (51.646111111111, 0.15166666666667),
                    (51.505277777778, 0.055277777777778),
                    (51.330875, 0.034811111111111),
                    (51.305, -0.44722222222222),
                    (51.4775, -0.46138888888889),
                    (51.624755555556, -0.51378083333333),
                    (51.726111111111, -0.54972222222222)]
        self.RMA_POLYGON = Polygon(self.RMA)

        self.simulating = True
        self.start_time = None
        self.seen_planes = 1
        self.active_planes = []


    def train_ai(self,genome,config): # put in main.py??

        net1 = neat.nn.FeedForwardNetwork.create(genome,config)
        start_time = time.time()
        route = random.choice(ROUTES)
        lat,lon = FIXES[route[0]]
        head = util.headingFromTo((lat,lon),FIXES[route[-1]])
        self.active_planes.append(Plane("TRN101",1000,8000,head,250,lat,lon,0,PlaneMode.HEADING,route[-1]))
        while self.simulating:
            table.clear_rows()
            # run the sim and see
            if time.time() - start_time > 80 / 100:
                route = random.choice(ROUTES)
                lat,lon = FIXES[route[0]]
                head = util.headingFromTo((lat,lon),FIXES[route[-1]])
                self.active_planes.append(Plane("TRN101",1000,8000,head,250,lat,lon,0,PlaneMode.HEADING,route[-1]))

                
                self.seen_planes += 1
                start_time = time.time()

            for plane in self.active_planes:
                table.add_row([plane.lat, plane.lon, plane.altitude, plane.speed, plane.heading,plane.targetHeading,plane.mode])
                if plane.distance_travelled > 5:
                    input_nodes = [-1] * 57

                    input_nodes[0] = plane.lat
                    input_nodes[1] = plane.lon
                    input_nodes[2] = plane.altitude
                    input_nodes[3] = plane.speed
                    input_nodes[4] = plane.heading
                    input_nodes[5] = self.airport[0]
                    input_nodes[6] = self.airport[1]
                    for i,p in enumerate(self.active_planes):
                        if i >= 10:
                            break
                        if p != plane:
                            offset = (i*5) + 7
                            input_nodes[offset] = p.lat
                            input_nodes[offset + 1] = p.lon
                            input_nodes[offset + 2] = p.altitude
                            input_nodes[offset + 3] = p.speed
                            input_nodes[offset + 4] = p.heading

                    output = net1.activate(tuple(input_nodes)) # pop in the thingys
                    given_inst = False
                    
                    if given_inst:
                        plane.instructions += 1

                    heading = output[:73]
                    heading_desc = heading.index(max(heading))
                    if plane.targetHeading != heading_desc * 5:
                        given_inst = True
                    plane.targetHeading = heading_desc * 5

                    altitude = output[73:79]
                    altitude_desc = altitude.index(max(altitude))
                    if plane.altitude < (altitude_desc * 1000) + 1000:
                        plane.climbed = True
                    if plane.targetAltitude != (altitude_desc * 1000) + 1000:
                        given_inst = True
                    plane.targetAltitude = (altitude_desc * 1000) + 1000

                    if given_inst and not self.RMA_POLYGON.contains(Point(plane.lat,plane.lon)):
                        plane.vectored_out_rma = True

                    speed = output[79:105]
                    speed_desc = speed.index(max(speed))
                    if plane.speed < (speed_desc * 5) + 125:
                        plane.sped_up = True
                    plane.targetSpeed = (speed_desc * 5) + 125
                    
                    if output[-1] >= 0.75: # CL/APP
                        runwayData = loadRunwayData("EGLL")["27R"] # TODO get better
                        plane.clearedILS = runwayData
                        plane.mode = PlaneMode.ILS

                    if plane.mode == PlaneMode.HEADING:
                        if not plane.left_rma and not self.RMA_POLYGON.contains(Point(plane.lat,plane.lon)):
                            plane.left_rma = True

                    landed = False
                    distances = [30]
                    if math.isclose((util.haversine(plane.lat,plane.lon,self.airport[0],self.airport[1]) / 1.852),0.1,abs_tol=0.1) and plane.altitude < 300 and plane.mode == PlaneMode.ILS:
                        self.planes.append(plane)
                        landed = True
                    for p in self.active_planes:
                        if p != plane:
                            if landed and p.mode == PlaneMode.ILS:
                                distances.append(abs(util.haversine(p.lat,p.lon,self.airport[0],self.airport[1])))


                            if abs(util.haversine(p.lat,p.lon,plane.lat,plane.lon) / 1.852) < 2.5 and abs(p.altitude - plane.altitude) < 1000:
                                plane.close_calls += 1

                        if landed:
                            plane.dist_from_behind = min(distances)
                            self.active_planes.pop(self.active_planes.index(plane))

                        if util.haversine(plane.lat,plane.lon,self.airport[0],self.airport[1]) / 1.852 >= 60 and plane.heading != 0:
                            self.simulating = False
                            genome.fitness -= 100

            
            for plane in self.active_planes:
                plane.calculatePosition()
                
            os.system("cls" if os.name == "nt" else "clear")
            print(table)

            if self.seen_planes >= 24:
                self.simulating = False
            
            time.sleep(5/100)
            

        self.planes.extend(self.active_planes.copy())
        self.calc_fitness(genome)

    def calc_fitness(self,genome):
        #genome.fitness += 1 # TODO : tune this
        for plane in self.planes:
            if plane.intercept_dist != None:
                if plane.intercept_dist < 8:
                    genome.fitness -= 10
                else:
                    diff = abs(plane.intercept_dist - 12)
                    genome.fitness += calc_score(diff) * 10
                    genome.fitness += round(diff,1) * 5

                if math.isclose(plane.altitude_at_intercept,math.tan(math.radians(3)) * plane.intercept_dist * 6076, abs_tol=500):
                    genome.fitness += 20
                else:
                    genome.fitness -= abs(plane.altitude_at_intercept-math.tan(math.radians(3)) * plane.intercept_dist * 6076 ) / 500

            if plane.left_rma:
                genome.fitness -= 100

            if plane.vectored_out_rma:
                genome.fitness -= 75

            if plane.sped_up:
                genome.fitness -= 25

            if plane.climbed:
                genome.fitness -= 35

            if plane.dist_from_behind != None:
                if plane.dist_from_behind < 3:
                    genome.fitness -= 100
                elif plane.dist_from_behind == 3: # hhhm not likely
                    genome.fitness += 100
                else:
                    genome.fitness += min(1/(plane.dist_from_behind - 3),150)


            genome.fitness -= plane.close_calls * 100
            genome.fitness += (13 - plane.instructions)* 0.1
            if plane.distance_travelled >= 60:
                genome.fitness -= 150
            genome.fitness += 1/(60 - plane.distance_travelled)

            


def calc_score(number,mean=12,stddev = 1):
    exponent = -((number - mean) ** 2) / (2 * stddev ** 2)
    score = math.exp(exponent)
    return score
            



def eval_genomes(genomes,config):
    
    for i, (genomes_id1,genome1) in enumerate(genomes):
        genome1.fitness = 0
        bot = Bot((51.477697222222, -0.43554333333333))
        bot.train_ai(genome1,config)
        print(f"GENONE {i + 1} DONE")



def run_neat(config):
    # p = neat.Checkpointer.restore_checkpoint("neat-checkpoint-2")
    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)
    p.add_reporter(neat.Checkpointer(1))


    winner = p.run(eval_genomes,50)

    with open("best.pickle","wb") as f:
        pickle.dump(winner,f)




if __name__ == "__main__":
    
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir,"config.txt")

    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_path)
    
    run_neat(config)