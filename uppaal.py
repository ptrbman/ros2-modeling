# Copyright (c) 2024 Peter Backeman
# All rights reserved.
#
# This software is provided "as is," without warranty of any kind, express or implied,
# including but not limited to the warranties of merchantability, fitness for a particular purpose,
# and noninfringement. In no event shall the authors or copyright holders be liable for any claim,
# damages, or other liability, whether in an action of contract, tort, or otherwise, arising from,
# out of, or in connection with the software or the use or other dealings in the software.


## Provides functions to perform various UPPAAL tasks.

import subprocess
import itertools
import re

# Class containing static functions for interacting with UPPAAL
class UPPAAL():
    def run_uppaal(modelfile, queryfile, extra_args = []):
        try:
            output = subprocess.check_output(
                [
                    "./verifyta"
                ] + extra_args + [
                    modelfile,
                    queryfile
                ],
                text=True,
            )

            return output
        except Exception:
            # We assume that any error is due to overflow in scheduling queue.
            return "Overflow"

    def write_sup_query(queryfile):
        fout = open(queryfile, 'w')
        fout.write("sup{monitor.measure}: monitor.x[lm]\n")
        fout.close()


    def write_measure_load_query(queryfile, load_threshold, percentage):
        fout = open(queryfile, 'w')
        formula = "Pr [<=10000] (<> monitor.measure && monitor.x[lm] >= " + str(load_threshold) + ") <= " + str(percentage)
        fout.write(formula + "\n")
        fout.close()
        return formula


    def parse_sup_query(output):
        lines = output.split("\n")
        for l in lines:
            if "sup:" in l:
                return int(l[5:-1])

    def write_random_trace_query(queryfile, upper_limit):
        fout = open(queryfile, 'w')
        fout.write("E<> global == " + str(upper_limit) + "\n")
        fout.close()



    # Also retursn final data...
    def parse_random_trace_query(output):

        #
        #  Current idea:
        #  - We register whenever a task starts executing (host.takenext->host.executing)
        #  - We register whenever a task finished executing (host.executing->host.done)
        #       then we also store which jobs was done (host.job)
        #  - Also register when data-sources are firing
        def parse_state(s, v, t):
            actions = []
            # string = ""
            string = "<<<STATE>>>\n"
            string += s[2:-2] + "\n"
            for l in s[2:-2].split(" "):
                string += "  " + l + "\n"
            string += str(v) + "\n"
            string += str(t) + "\n"

            values = {}
            for vv in v.split(" "):
                split = vv.strip().split("=")
                values[split[0]] = split[1]

            for tt in t:
                fire_pattern = r"(\w+)\.monitored_fire->\1\.wait"
                match = re.search(fire_pattern, tt)
                if match:
                    source_id = values[match.group(1) + ".id"]
                    actions.append((values['global'], "FIRE", source_id, values["PAYLOAD"]))

                fire_pattern = r"(\w+)\.fire->\1\.wait"
                match = re.search(fire_pattern, tt)
                if match:
                    source_id = values[match.group(1) + ".id"]
                    actions.append((values['global'], "FIRE", source_id, "-1")) # Here -1 is hard-coded


                window_pattern = r"check->host\.takenext"
                match = re.search(window_pattern, tt)
                if match:
                    actions.append((values['global'], "WINDOW", "", ""))


                start_pattern = r"host\.takenext->host\.executing"
                match = re.search(start_pattern, tt)
                if match:
                    actions.append((values['global'], "START", "", ""))


                done_pattern = r"host\.executing->host\.done"
                match = re.search(done_pattern, tt)
                if match:
                    actions.append((values['global'], "DONE", values['host.job'], values['host.data']))

                measure_pattern = r"monitor\.i->monitor\.measure"
                match = re.search(measure_pattern, tt)
                if match:
                    lm = values["lm"]
                    payload = values["monitor_payload[" + values["lm"] + "]"]
                    actions.append((values['global'], "MONITOR", payload, ''))

            return actions

        i = 0
        lines = output.split("\n")
        actions = []
        while i < len(lines):
            l = lines[i].strip()
            if "State:" == l:
                state_line = lines[i+1]
                value_line = lines[i+2]
                transition_lines = []
                j = i+5
                while j < len(lines) and not lines[j].strip() == "":
                    transition_lines.append(lines[j].strip())
                    j += 1

                new_actions = parse_state(state_line, value_line, transition_lines)
                actions += new_actions

                i = j
            i += 1

        return actions

    def check_overload(output):
        for l in output.split("\n"):
            if "Overflow" in l: # todo: 20 hard-coded here
                return True

        return False

    def parse_load_query(output):
        print(output)
        satisfied = None
        lines = output.split("\n")
        idx = 0
        while "Verifying formula" not in lines[idx]:
            idx += 1

        print("!!!", lines[idx])
        l1 = lines[idx] # "Verifying formula 1 ..."
        l2 = lines[idx+1].strip() # Formula is/NOT satisfied
        l3 = lines[idx+2] # (x/y runs) H1: ...
        l4 = lines[idx+3] # with confidence
        #
        if "Formula is NOT satisfied" in l2:
            satisfied = False
        elif "Formula is satisfied" in l2:
            satisfied = True


        return satisfied


    # Finds upper bound on reaction time
    def sup(modelfile):
        queryfile = modelfile + ".q"
        UPPAAL.write_sup_query(queryfile)
        output = UPPAAL.run_uppaal(modelfile, queryfile)
        return UPPAAL.parse_sup_query(output)

    # Gets a trace satisfying query
    def get_trace(modelfile, query):
        queryfile = modelfile + ".q"
        f = open(queryfile, 'w')
        f.write(query + '\n')
        f.close()
        output = UPPAAL.run_uppaal(modelfile, queryfile, ['-t', '1'])
        return UPPAAL.parse_random_trace_query(output)


    # Gets a random trace until time upper_limit
    def random_trace(modelfile, upper_limit):
        queryfile = modelfile + ".q"
        UPPAAL.write_random_trace_query(queryfile, upper_limit)
        output = UPPAAL.run_uppaal(modelfile, queryfile, ['-t', '1'])
        return UPPAAL.parse_random_trace_query(output)


    # Used for use case, checks if the system is under load_threshold, with percentage chance
    def measure_load(modelfile, load_threshold, percentage):
        queryfile = modelfile + ".q"
        formula = UPPAAL.write_measure_load_query(queryfile, load_threshold, percentage)
        output = UPPAAL.run_uppaal(modelfile, queryfile)
        if UPPAAL.check_overload(output):
            return formula, "Overload"

        data = UPPAAL.parse_load_query(output)
        return formula, data
