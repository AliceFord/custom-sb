import random
import threading
import time
import numpy as np
import pygad.nn
import pygad.gann
import pygad

from Constants import RADAR_UPDATE_RATE
from PlaneMode import PlaneMode
import util
import main

"""
general setup:
all planes stuck at 4000ft
NN accepts 4 inputs per plane: lat, lon, speed hdg
7 planes, so 28 inputs
NN outputs heading and speed for plane 1


28 input nodes
x hidden nodes
2 output nodes (softmax, scale hdg by 360, speed * 40 +180 )

+ve reward of 10 for two planes on final 4 miles apart
-ve reward of 5 for two planes less than 3 miles seperated each cycle
-ve reward of 1 for plane outside RMA each cycle
"""

# https://pygad.readthedocs.io/en/latest/gacnn.html setup

def fitnessFunc(gaInstance, solution, solIdx):
    global GACNNInstance

    # start main in a thread
    # every radar update, run NN with every plane
    # send new hdg and speed to planes

    # sock = util.ControllerSocket.StartController("EGLL_F_APP")
    # sock.setblocking(False)

    # # start main in thread with threading
    thr = threading.Thread(target=main.main)
    thr.daemon = True
    thr.start()

    time.sleep(2)

    # data = [[51.47876, -0.15752, 220, 269], [51.61132, -0.29702, 220, 125], [51.32494, -0.29139, 220, 85], [51.37144, 0.04752, 220, 345], [51.67808, 0.24878, 220, 241.96740542246403], [51.18761, -0.58149, 220, 35.633855432841415], [51.10887, -0.67151, 220, 35.67900254992156]]
    # data = np.array([np.array(data).flatten()])
    # print(data)
    # predictions = pygad.nn.predict(last_layer=GANNInstance.population_networks[solIdx], data_inputs=data, problem_type="regression")
    # print(predictions[0])
    # quit()

    for _ in range(360):  # 30 mins real time
        data = []
        for plane in main.planes[:7]:
            data.append([plane.lat, plane.lon, plane.speed, plane.heading])

        for i, plane in enumerate(main.planes[:7]):
            currentData = np.array([np.roll(np.array(data).flatten(), -i * 4)])

            predictions = pygad.nn.predict(last_layer=GANNInstance.population_networks[solIdx], data_inputs=currentData, problem_type="regression")
            hdg = predictions[0][0] * 360
            speed = predictions[0][1] * 40 + 180

            if 0 < hdg - plane.heading < 180 or hdg - plane.heading < -180:
                turnDir = "r"
            else:
                turnDir = "l"

            plane.mode = PlaneMode.HEADING
            plane.targetHeading = hdg
            plane.turnDir = turnDir
            plane.targetSpeed = speed

            time.sleep(RADAR_UPDATE_RATE)

    

    # predictions = GACNNInstance.population_networks[solIdx].predict(data_inputs=dataInputs)

    print(predictions)

    quit()


def callbackGeneration(gaInstance: pygad.GA):
    global GANNInstance
    populationMatrices = pygad.gann.population_as_matrices(population_networks=GANNInstance.population_networks, population_vectors=gaInstance.population)

    GANNInstance.update_population_trained_weights(population_trained_weights=populationMatrices)

    print("Generation = {generation}".format(generation=gaInstance.generations_completed))
    print("Fitness    = {fitness}".format(fitness=gaInstance.best_solution()[1]))


# inputLayer = pygad.cnn.Input2D(input_shape=(7, 4))
# convLayer = pygad.cnn.Conv2D(num_filters=7, kernel_size=3, previous_layer=inputLayer, activation_function="relu")
# poolingLayer = pygad.cnn.AveragePooling2D(previous_layer=convLayer, pool_size=7, stride=2)
# flattenLayer = pygad.cnn.Flatten(previous_layer=poolingLayer)
# denseLayer = pygad.cnn.Dense(num_neurons=2, previous_layer=flattenLayer, activation_function="softmax")
# model = pygad.cnn.Model(last_layer=convLayer)

# GACNNInstance = pygad.gacnn.GACNN(model=model, num_solutions=10)

# populationVectors = pygad.gacnn.population_as_vectors(population_networks=GACNNInstance.population_networks)
# initialPopulation = populationVectors.copy()

# gaInstance = pygad.GA(num_generations=50,
#                         num_parents_mating=2,
#                         initial_population=initialPopulation,
#                         fitness_func=fitnessFunc,
#                         mutation_percent_genes=5,
#                         on_generation=callbackGeneration)

# gaInstance.run()

np.random.seed(4)
random.seed(4)

GANNInstance = pygad.gann.GANN(num_solutions=10,
                             num_neurons_input=28,
                             num_neurons_hidden_layers=[14, 14, 14],
                             num_neurons_output=2,
                             hidden_activations=["None", "None", "None"],
                             output_activation="sigmoid")

populationVectors = pygad.gann.population_as_vectors(population_networks=GANNInstance.population_networks)
initialPopulation = populationVectors.copy()

init_range_low = -4
init_range_high = 4

gaInstance = pygad.GA(num_generations=50,
                      num_parents_mating=2,
                      initial_population=initialPopulation,
                    #   sol_per_pop=10,
                    #   num_genes=GANNInstance.num_solutions,
                      fitness_func=fitnessFunc,
                      mutation_percent_genes=5,
                      init_range_low=init_range_low,
                      init_range_high=init_range_high,
                      parent_selection_type="sss",
                      crossover_type="single_point",
                      mutation_type="random",
                      keep_parents=2,
                      on_generation=callbackGeneration,
                      random_seed=1)

gaInstance.run()