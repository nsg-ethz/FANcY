import datetime
import os

from fancy.experiment_runners.utils import dict_product, START_SIM_INDEX


def create_tests(fixed_parameters, variable_parameters, out_dir):

    # Check if Allowed prefixes file exist
    runs = []

    for fixed_parameter in fixed_parameters:
        sim_index = START_SIM_INDEX
        for variable_parameter in dict_product(variable_parameters):

            parameters = fixed_parameter.copy()
            parameters.update(variable_parameter)

            sim_index += 1

            if "SendRate|FlowsPerSec" in parameters:
                t = parameters.pop("SendRate|FlowsPerSec")
                rate = t[0]
                # to keep the sending rate per prefix constant we increase the sending rate times the prefixes per sec.
                digits = ''.join(c for c in rate if c.isdigit())
                digits = int(digits) * parameters["SyntheticNumPrefixes"]
                unit = ''.join(c for c in rate if not c.isdigit())

                rate = "{}{}".format(digits, unit)

                parameters["SendRate"] = rate

                parameters["FlowsPerSec"] = t[1]

                params = ["fancy",
                          parameters["Seed"],
                          parameters["FailDropRate"],
                          parameters["ProbingTimeZoomingMs"],
                          parameters["SendRate"],
                          parameters["FlowsPerSec"],
                          parameters["SyntheticNumPrefixes"],
                          sim_index]
            else:
                params = ["fancy",
                          parameters["Seed"],
                          parameters["FailDropRate"],
                          parameters["ProbingTimeZoomingMs"],
                          parameters["SendRate"],
                          parameters["FlowsPerSec"],
                          parameters["SyntheticNumPrefixes"],
                          sim_index]

            out_file = ""
            for param in params:
                out_file += str(param) + "_"
            out_file = out_file[:-1]

            date = datetime.datetime.now()
            date_str = "{}-{}-{}-{}".format(date.year,
                                            date.month, date.day, date.hour)

            out_file = out_dir + "/" + date_str + "-" + out_file
            # In case we add a double // by mistake
            out_file.replace("//", "/")

            parameters["OutDirBase"] = out_file
            runs.append(parameters)

    return runs


def generate_ns3_runs(
        output_file, out_dir_runs, fixed_parameters, variable_parameters,
        split=0):

    # parameters
    fail_time = 2
    traffic_start = 1
    input_dir = "inputs_sigcomm2022/tests/test"

    # creates path for the outputs
    if not os.path.isdir(out_dir_runs):
        os.system("mkdir -p {}".format(out_dir_runs))

    runs = create_tests(fixed_parameters, variable_parameters, out_dir_runs)

    # sort them by bandwidth
    #runs = sorted(runs, key= lambda x: len(x["SendRate"]))
    runs = sorted(runs, key=lambda x: int(x["Seed"]))

    cmds = []
    # build commands
    for run in runs:
        cmd = './waf --run  "main --DebugFlag=false --PcapEnabled=False --FailTime={} --TrafficStart={} --InDirBase={} --EnableSaveDrops=false --SoftDetectionEnabled=false --CheckPortStateEnable=false --TrafficType=StatefulSyntheticTraffic --SwitchType=Fancy --EnableNat=true --NumReceivers=10 --NumSendersPerRtt=10 --PacketHashType=DstPrefixHash --NumDrops={}'.format(
            fail_time, traffic_start, input_dir, run["SyntheticNumPrefixes"])

        for parameter, value in run.items():
            cmd += " --{}={}".format(parameter, value)

        cmd += '"'
        cmds.append(cmd)

    # split commands
    if split:
        cmds = [cmds[i::split] for i in range(split)]
        for i, sub_cmds in enumerate(cmds):
            _output_file = output_file.split(".")
            _output_file = _output_file[0] + "_{}.".format(i) + _output_file[1]
            with open(_output_file, "w") as f:
                for cmd in sub_cmds:
                    f.write(cmd + "\n")
    else:
        # save
        with open(output_file, "w") as f:
            for cmd in cmds:
                f.write(cmd + "\n")
