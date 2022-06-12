import datetime
import os
import subprocess

from fancy.experiment_runners.utils import dict_product, START_SIM_INDEX


def create_tests(fixed_parameters, variable_parameters, out_dir_base):

    # Check if Allowed prefixes file exist
    runs = []

    for fixed_parameter in fixed_parameters:
        sim_index = START_SIM_INDEX
        for variable_parameter in dict_product(variable_parameters):

            parameters = fixed_parameter.copy()
            parameters.update(variable_parameter)
            trace = parameters.pop("Traces")

            sim_index += 1

            params = ["fancy",
                      trace,
                      parameters["Seed"],
                      parameters["FailDropRate"],
                      parameters["ProbingTimeZoomingMs"],
                      parameters["NumDrops"],
                      sim_index]

            parameters["InDirBase"] += trace + "/" + trace

            out_file = ""
            for param in params:
                out_file += str(param) + "_"
            out_file = out_file[:-1]

            date = datetime.datetime.now()
            date_str = "{}-{}-{}-{}".format(date.year,
                                            date.month, date.day, date.hour)

            out_file = out_dir_base + "/" + "eval_caida_{}".format(
                trace) + "/" + date_str + "-" + out_file
            # In case we add a double // by mistake
            out_file = out_file.replace("//", "/")

            parameters["OutDirBase"] = out_file
            runs.append(parameters)

    return runs


# for one test
def generate_ns3_runs(
        output_file, out_dir_runs, fixed_parameters, variable_parameters,
        traces_path, split=0):

    # set path to traces
    TRACES_PATH = traces_path
    variable_parameters["InDirBase"] = [TRACES_PATH]

    # parameters
    fail_time = 2
    traffic_start = 1

    caida_traces = variable_parameters["Traces"]

    # create main dir
    if not os.path.isdir(out_dir_runs):
        os.system("mkdir -p {}".format(out_dir_runs))

    # creates path for the outputs
    for caida_trace in caida_traces:
        out_dir_run = out_dir_runs + "/" + "eval_caida_{}".format(caida_trace)
        if not os.path.isdir(out_dir_run):
            os.system("mkdir -p {}".format(out_dir_run))

    runs = create_tests(fixed_parameters, variable_parameters, out_dir_runs)

    # sort them by bandwidth
    runs = sorted(runs, key=lambda x: x["Seed"])

    # one run per prefix
    prefixes_to_explore = range(1, 10001)

    cmds = []
    # build commands
    for run in runs:
        dist_file = run["InDirBase"] + "_" + str(run["TraceSlice"]) + ".dist"
        max_prefixes = int(
            subprocess.check_output(
                "less {} | grep '#' | wc -l ".format(dist_file),
                shell=True))

        prefixes_to_explore = range(1, min(10001, max_prefixes + 1))

        for prefix_num in prefixes_to_explore:
            cmd = './waf --run  "main --DebugFlag=false --PcapEnabled=False --FailTime={} --TrafficStart={} --EnableSaveDrops=false --SoftDetectionEnabled=true --CheckPortStateEnable=false --TrafficType=HybridTraceTraffic --SwitchType=Fancy --EnableNat=true --NumReceivers=5 --NumSendersPerRtt=1 --PacketHashType=DstPrefixHash --FailSpecificTopIndex={}'.format(
                fail_time, traffic_start, prefix_num)

            # modif y the out dir and add something else
            _run = run.copy()
            _run["OutDirBase"] = _run["OutDirBase"] + \
                "_prefix_{}".format(prefix_num)

            for parameter, value in _run.items():
                cmd += " --{}={}".format(parameter, value)

            cmd += '"'
            cmds.append(cmd)

    if split:
        # split commands
        cmds = [cmds[i::split] for i in range(split)]

        # save
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
