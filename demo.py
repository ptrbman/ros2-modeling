# Copyright (c) 2024 Peter Backeman
# All rights reserved.
#
# This software is provided "as is," without warranty of any kind, express or implied,
# including but not limited to the warranties of merchantability, fitness for a particular purpose,
# and noninfringement. In no event shall the authors or copyright holders be liable for any claim,
# damages, or other liability, whether in an action of contract, tort, or otherwise, arising from,
# out of, or in connection with the software or the use or other dealings in the software.


###
## This script allows to generate a ROS system and check the maxmimum reaction time
##
## Usage: At the bottom of the script, three functions are called, example, validation and use_case.
##
## Comments:
## No component can be named pd
## Component names not case-sensitive


from system import System
from grapher import Grapher



# Call this to create the ss validation case
def validation_ss():
    system = System("ss")
    system.add_datagenerator("SENSOR1", 360, 10, 0, True)
    system.add_datagenerator("SENSOR2", 360, 20, 0, False)
    system.add_subscriber("FILTER1", "SENSOR1", 10, [], [], "pd")
    system.add_subscriber("FILTER2", "SENSOR2", 20, [], [], "pd")
    system.add_subscriber("FUSION1", "SENSOR1", 30, ["SENSOR2"], [30], "pd")
    system.add_subscriber("FILTER3", "FUSION1", 30, [], [], "pd")
    system.add_subscriber("ACTUATOR1", "FILTER3", 30, [], [], "pd")
    system.monitor("ACTUATOR1", 360)
    return system


# Call this to create the st validation case
def validation_st():
    system = System("st")
    system.add_datagenerator("SENSOR1", 420, 10, 0, True, 6)
    system.add_datagenerator("SENSOR2", 420, 20, 0, False, 5)
    system.add_subscriber("FILTER1", "SENSOR1", 10, [], [], "pd")
    system.add_subscriber("FILTER2", "SENSOR2", 20, [], [], "pd")
    system.add_subscriber("FUSION1", "SENSOR1", 30, ["SENSOR2"], [30], "pd")
    system.add_subscriber("FILTER3", "FUSION1", 30, [], [], "pd")
    system.add_timer("ACTUATOR1", 840, 0, 30, ["FILTER3"], [30], "ACTUATOR1xFILTER3_data", 4, [-3])
    system.monitor("ACTUATOR1", 420)
    return system


# Call this to create the ts validation case
def validation_ts():
    system = System("ts")
    system.add_datagenerator("SENSOR1", 420, 10, 0, True, 6)
    system.add_datagenerator("SENSOR2", 420, 20, 0, False, 5)
    system.add_subscriber("FILTER1", "SENSOR1", 10, [], [], "pd")
    system.add_subscriber("FILTER2", "SENSOR2", 20, [], [], "pd")
    system.add_timer("FUSION1", 840, 0, 30, ["FILTER1", "FILTER2"], [30, 30], "FILTER1_data")
    system.add_subscriber("FILTER3", "FUSION1", 30, [], [], "pd")
    system.add_subscriber("ACTUATOR1", "FILTER3", 30, [], [], "pd")
    system.monitor("ACTUATOR1", 420)
    return system


# Call this to create the tt validation case
def validation_tt():
    system = System("tt")
    system.add_datagenerator("SENSOR1", 480, 10, 0, True, 6)
    system.add_datagenerator("SENSOR2", 480, 20, 0, False, 5)
    system.add_subscriber("FILTER1", "SENSOR1", 10, [], [], "pd")
    system.add_subscriber("FILTER2", "SENSOR2", 20, [], [], "pd")
    system.add_timer("FUSION1", 960, 0, 30, ["FILTER1", "FILTER2"], [30, 30], "FILTER1_data", 4, [-2, -3])
    system.add_subscriber("FILTER3", "FUSION1", 30, [], [], "pd")
    system.add_timer("ACTUATOR1", 960, 0, 30, ["FILTER3"], [30], "ACTUATOR1xFILTER3_data", 3, [-3])
    system.monitor("ACTUATOR1", 480)
    return system

def validation():
    names = ["ss", "st", "ts", "tt"]
    systems = [validation_ss(), validation_st(), validation_ts(), validation_tt()]
    for name, system in zip(names, systems):
        mrt, _, graph = system.max_reaction_time()
        print(name, "\t", mrt)
        # print('\n'.join(graph))



def prio_inversion():
    system = System("prio_inv")
    system.add_datagenerator("Sensor1", 150, 50, 0, False)
    system.add_subscriber("Filter", "Sensor1", 30, [], [], "pd")
    system.add_datagenerator("Sensor2", 150, 30, 50, True)
    system.add_subscriber("Actuator", "Filter", 10, ["Sensor2"], [10], "ActuatorxSensor2_data")
    system.monitor("Actuator", 0)
    return system


def case_study(cameras, prob):
    system = System("casestudy" + str(cameras))

    for i in range(cameras):
        system.add_probalisticdatagenerator("CAMERA" + str(i), 1000, 20, 0, prob, i == 0) # Monitor first camera
        system.add_subscriber("OBJDET" + str(i), "CAMERA" + str(i), 50, [], [], "pd")

    system.add_timer("FUSION", 500, 0, 30, ["OBJDET" + str(i) for i in range(cameras)], [10]*cameras, "FUSIONxOBJDET0_data") # What about priorities???
    system.add_subscriber("ACTUATOR", "FUSION", 50, [], [], "pd")
    system.monitor("ACTUATOR", 0)

    return system

def example():
    system = prio_inversion()

    print(system)
    print("//=====================\\\\")
    print("   DETERMINSTIC HOSTS")
    print("\\\\=====================//")
    system.deterministic_hosts(True)
    mrt, trace, graph = system.max_reaction_time()
    print("Max reaction time: ", str(mrt))
    print("\n\n\nGraph:")
    print('\n'.join(graph))

    print("//=====================\\\\")
    print(" NON-DETERMINSTIC HOSTS")
    print("\\\\=====================//")
    system.deterministic_hosts(False)
    mrt, trace, graph = system.max_reaction_time()
    print("Max reaction time: ", str(mrt))
    print("\n\n\nGraph:")
    print('\n'.join(graph))





def use_case():
    results = []
    probs = [25, 50, 75, 100]
    for i in range(1,17):
        for prob in probs:
            system = case_study(i, prob)
            print(system)
            THRESHOLD = 850
            PERCENTAGE = 0.05
            formula, data = system.measure_load(THRESHOLD, PERCENTAGE)
            print(formula, "\t", data)
            results.append((i, prob, data, formula))


        # results.append((i, mrt))


    print("#Cams\tLoad\tResult")
    print("============================")
    for (c, p, r, f) in results:
        print(c, "\t", p, "\t", r)


    # Uncomment these lines to generate the table presented in the paper.
    #
    # i = 0
    # result = []
    # rows = len(probs)
    # cols = 4
    # header = []

    # result.append("\\begin{tabular}{|" + '|'.join('c'*cols*3) + '|}')

    # result.append("\\hline")
    # for _ in range(cols):
    #     header.append("\\#Cams & Load & $\leq 850$")
    # result.append(' & '.join(header) + "\\\\")
    # result.append("\\hline")
    # while i*cols*rows < len(results):
    #     # Create one block (i.e., row x cols)
    #     lines = []
    #     for _ in range(rows):
    #         lines.append([])
    #     for col in range(cols):
    #         for row in range(rows):
    #             (c, p, r, f) = results[i*cols*rows + col*rows + row]
    #             print(col, "x", row, " --> ", c, p, r)
    #             if r:
    #                 r = "Yes"
    #             else:
    #                 r = "No"

    #             fmt = str(c) + " & " + str(p) + "\\% & " + r
    #             lines[row].append(fmt)
    #             print("NEWLINE: ", row, "--->", lines[row])
    #     i += 1
    #     for l in lines:
    #         result.append(' & '.join(l) + "\\\\")
    #     result.append("\\hline")
    # result.append("\\end{tabular}")
    # print("\n\n\n\n")
    # print('\n'.join(result))


example()
# validation()
# use_case()
