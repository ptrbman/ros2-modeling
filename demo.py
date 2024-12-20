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
import time


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


# Case study has following parameters:
# - cameras: No. of cameras
# - prob: probability of each camera being used (load)
# - mcamera: which camera should be monitored
# - subcription: if True, subscription is used of fusion (otherwise Timer)
#
def case_study(cameras, prob, mcamera, subscription, fusion_period=500):

    CAMERAWCET = 20
    CAMERAPER = 1000
    OBJDETWCET = 50
    FUSIONSUBWCET = 90
    FUSIONSUB = 10
    FUSIONTIMERWCET = 90
    ACTUATORWCET = 50
    
    if mcamera >= cameras:
        return None

    if subscription:
        name = "casestudy" + str(cameras) + "_" + str(mcamera) + "_sub"
    else:
        name = "casestudy" + str(cameras) + "_" + str(mcamera) + "_tmr"

    system = System(name)

    for i in range(cameras):
        system.add_probalisticdatagenerator("CAMERA" + str(i), CAMERAPER, CAMERAWCET, 0, prob, i == mcamera)
        system.add_subscriber("OBJDET" + str(i), "CAMERA" + str(i), OBJDETWCET, [], [], "pd")

    if subscription:
        if 0 == mcamera:
            system.add_subscriber("FUSION", "OBJDET0", FUSIONSUBWCET, ["OBJDET" + str(i) for i in range(1,cameras)], [FUSIONSUB]*(cameras-1), "pd")
        else:
            system.add_subscriber("FUSION", "OBJDET0", FUSIONSUBWCET, ["OBJDET" + str(i) for i in range(1,cameras)], [FUSIONSUB]*(cameras-1), "FUSIONxOBJDET" + str(mcamera) + "_data")
    else:
        system.add_timer("FUSION", fusion_period, 0, FUSIONTIMERWCET, ["OBJDET" + str(i) for i in range(cameras)], [FUSIONSUB]*cameras, "FUSIONxOBJDET" + str(mcamera) + "_data")
    system.add_subscriber("ACTUATOR", "FUSION", ACTUATORWCET, [], [], "pd")
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




# Let's do the same but generate for each camera?
# def case_study(cameras, prob, mcamera, subscription, fusion_period=500):
def test_system(max_cameras, mcamera, subscription, upper_limit, fusion_period):
    print("test_system(", mcamera, subscription, upper_limit, fusion_period, ")")
    results = []
    probs = [25, 50, 75, 100]
    for cameras in range(1,max_cameras+1):
        for prob in probs:
            print("\t", cameras, prob)
            system = case_study(cameras, prob, mcamera, subscription, fusion_period)
            print(system)
            if system:
                #print("\trunning system")
                THRESHOLD = 850
                PERCENTAGE = 0.05

                start = time.time()
                formula, data = system.measure_load(THRESHOLD, PERCENTAGE, upper_limit)
                end = time.time()
                t = end - start
                results.append((cameras, prob, data, formula, t))
            else:
                print("\tsystem could not be created")
                results.append((cameras, prob, "n/a", "", 0.0))

    # print("#Cams\tLoad\tResult")
    # print("============================")
    # for (c, p, r, f) in results:
    #     print(c, "\t", p, "\t", r)


    # Uncomment these lines to generate the table presented in the paper.
    #
    i = 0
    result = []
    rows = len(probs)
    cols = 3
    header = []
    result.append("\\begin{table}")
    result.append("\\centering")
    result.append("\\begin{tabular}{|" + '|'.join('c'*cols*4) + '|}')

    result.append("\\hline")
    for _ in range(cols):
        header.append("\\#Cams & Load & $\\leq 850$ & Time")
    result.append(' & '.join(header) + "\\\\")
    result.append("\\hline")
    while i*cols*rows < len(results):
        # Create one block (i.e., row x cols)
        lines = []
        for _ in range(rows):
            lines.append([])
        for col in range(cols):
            for row in range(rows):
                (c, p, r, f, t) = results[i*cols*rows + col*rows + row]
                #print(col, "x", row, " --> ", c, p, r)
                if r:
                    if not r == "n/a":
                        r = "Yes"
                else:
                    r = "No"

                fmt = str(c) + " & " + str(p) + "\\% & " + r + " & " + "{:.2f}".format(t)
                lines[row].append(fmt)
                #print("NEWLINE: ", row, "--->", lines[row])
        i += 1
        for l in lines:
            result.append(' & '.join(l) + "\\\\")
        result.append("\\hline")
    result.append("\\end{tabular}")
    if subscription:
        result.append("\\caption{Use case monitoring " + str(mcamera+1) + ", with subscription-based fusion analysing " + str(upper_limit) + " time steps.}")
    else:
        result.append("\\caption{Use case monitoring " + str(mcamera+1) + ", with timer-based fusion (period of " + str(fusion_period) + ") analysing " + str(upper_limit) + " time steps.}")
    result.append("\\end{table}")
    latex = '\n'.join(result)
    return latex


# Correspoding to the first study
def first_study():
    all = []
    max_cameras = 12
    for mcamera in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
        for sub in [False]:
            for upper_limit in [10000]:
                for fusion_period in [500]:
                    latex = test_system(max_cameras, mcamera, sub, upper_limit, fusion_period)
                    all.append(latex)    

    return "\n\n\n".join(all)

# Ten-fold time steps
def ten_fold():
    all = []
    max_cameras = 6
    for mcamera in [0, 1, 2, 3, 4, 5, 6, 7]:
        for sub in [False]:
            for upper_limit in [100000]:
                for fusion_period in [500]:
                    latex = test_system(max_cameras, mcamera, sub, upper_limit, fusion_period)
                    all.append(latex)    

    return "\n\n\n".join(all)

# Subscription fusion
def subscription():
    all = []
    max_cameras = 6
    for mcamera in [0, 1]:
        for sub in [True]:
            for upper_limit in [10000]:
                for fusion_period in [500]:
                    latex = test_system(max_cameras, mcamera, sub, upper_limit, fusion_period)
                    all.append(latex)    

    return "\n\n\n".join(all)

# Fusion periods
def fusion_study():
    all = []
    max_cameras = 6
    for mcamera in [0, 1]:
        for sub in [False]:
            for upper_limit in [10000]:
                for fusion_period in [250, 750]:
                    latex = test_system(max_cameras, mcamera, sub, upper_limit, fusion_period)
                    all.append(latex)    

    return "\n\n\n".join(all)

#example()
#validation()

latex = first_study()
fout = open("results_first_study.txt", 'w')
fout.write(latex)
fout.close()

latex = ten_fold()
fout = open("results_ten_fold.txt", 'w')
fout.write(latex)
fout.close()

latex = subscription()
fout = open("results_subscription.txt", 'w')
fout.write(latex)
fout.close()

latex = fusion_study()
fout = open("results_fusion_study.txt", 'w')
fout.write(latex)
fout.close()

