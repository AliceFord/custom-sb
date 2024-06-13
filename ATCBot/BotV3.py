from copy import copy
import threading
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

ROUTES = [["NOVMA","OCK"],
          ["ODVIK","BIG"],
          ["BRAIN","LAM"],
          ["COWLY","BNN"]]



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

        thr = threading.Thread(target=main.main)
        thr.daemon = True
        thr.start()

        time.sleep(2)  # WE GO LOLZ


        # net1 = neat.nn.FeedForwardNetwork.create(genome,config)
        net = neat.nn.FeedForwardNetwork.create(winner,config)

        while self.simulating:
            # run the sim and see

            for plane in main.planes:
                dists = [(p,abs(util.haversine(p.lat,p.lon,plane.lat,plane.lon))) for p in main.planes]
                dists = sorted(dists, key=lambda x: x[-1])
                inputs = [[p.lat,p.lon,p.altitude,p.speed,p.heading] for p,d in dists if p != plane]
                inputs = [i for li in inputs for i in li]

                input_nodes = [-1] * 57

                input_nodes[0] = plane.lat
                input_nodes[1] = plane.lon
                input_nodes[2] = plane.altitude
                input_nodes[3] = plane.speed
                input_nodes[4] = plane.heading
                input_nodes[5] = self.airport[0]
                input_nodes[6] = self.airport[1]
                input_nodes[7:] = inputs[:50]

                input_nodes.extend([-1] *( 57 - len(input_nodes)))

                output = net.activate(tuple(input_nodes)) # pop in the thingys
                
                heading = output[:73]
                heading_desc = heading.index(max(heading))
                hdg = heading_desc * 5
                # if 0 < hdg - plane.heading < 180 or hdg - plane.heading < -180:
                #     turnDir = "r"
                # else:
                #     turnDir = "l"
                # plane.turnDir = turnDir
                plane.targetHeading = hdg

                altitude = output[73:79]
                altitude_desc = altitude.index(max(altitude))
                plane.targetAltitude = (altitude_desc * 1000) + 1000

                speed = output[79:105]
                speed_desc = speed.index(max(speed))
                plane.targetSpeed = (speed_desc * 5) + 125
                
                clapp = output[-2:]
                clapp_desc = clapp.index(max(clapp))

                if clapp_desc == 1: # CL/APP
                    runwayData = loadRunwayData("EGLL")["27R"] # TODO get better
                    plane.clearedILS = runwayData
                    plane.mode = PlaneMode.ILS

                landed = False
                distances = [30]
                if math.isclose((util.haversine(plane.lat,plane.lon,self.airport[0],self.airport[1]) / 1.852),0.1,abs_tol=0.1) and plane.altitude < 300 and plane.mode == PlaneMode.ILS:
                    self.planes.append(plane)
                    landed = True
                for p in main.planes:
                    if p != plane:
                        if landed and p.mode == PlaneMode.ILS:
                            distances.append(abs(util.haversine(p.lat,p.lon,self.airport[0],self.airport[1])))

                    if landed:
                        try:
                            main.planes.pop(main.planes.index(plane))
                        except Exception as e:
                            print(e)


            time.sleep(5/100)



def eval_genomes(genomes,config):
    
    for i, (genomes_id1,genome1) in enumerate(genomes):
        genome1.fitness = 0
        bot = Bot((51.477697222222, -0.43554333333333))
        bot.train_ai(genome1,config)
        print(f"GENOME {i + 1} DONE")



def run_neat(config):
    global winner
    # p = neat.Checkpointer.restore_checkpoint("ATCBot/best.pickle")
    # p = neat.Population(config)
    # p.add_reporter(neat.StdOutReporter(True))
    # stats = neat.StatisticsReporter()
    # p.add_reporter(stats)
    # p.add_reporter(neat.Checkpointer(1))


    # winner = p.run(eval_genomes,29)

    with open("ATCBot/best.pickle","rb") as f:
        winner = pickle.load(f)

    bot = Bot((51.477697222222, -0.43554333333333))
    bot.train_ai(winner, config)

    

    # with open("best.pickle","wb") as f:
    #     pickle.dump(winner,f)




if __name__ == "__main__":
    
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir,"config.txt")

    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_path)
    
    run_neat(config)