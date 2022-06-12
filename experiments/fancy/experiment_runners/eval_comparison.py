import datetime
import os

from fancy.experiment_runners.utils import dict_product, START_SIM_INDEX
from fancy.file_loader import load_prefixes_file, load_zooming_speed


def create_tests(fixed_parameters, variable_parameters, out_dir,
                 computed_parameters_path):

    runs = []

    for fixed_parameter in fixed_parameters:
        sim_index = START_SIM_INDEX
        for variable_parameter in dict_product(variable_parameters):

            parameters = fixed_parameter.copy()
            parameters.update(variable_parameter)
            trace = parameters.pop("Traces")

            sim_index += 1

            params = [trace,
                      parameters["NumTopEntriesSystem"],
                      parameters["TreeDepth"],
                      parameters["LayerSplit"],
                      parameters["CounterWidth"],
                      parameters["Seed"],
                      parameters["FailDropRate"],
                      sim_index]

            parameters["InDirBase"] += trace + "/" + trace

            # find zooming speed
            zooming_speed_file = computed_parameters_path + "{}_{}_{}_{}_{}_1.speed".format(
                trace, parameters["TreeDepth"], 30, parameters["TraceSlice"], parameters["NumTopEntriesTraffic"])

            # set zooming speed
            speed = int(load_zooming_speed(zooming_speed_file))
            parameters["ProbingTimeZoomingMs"] = speed

            # Get allowed prefixes

            # Check if Allowed prefixes file exist
            # always get it for 100% loss rate, the parameter is fixed in the name
            allowed_prefixes_file_max_loss = computed_parameters_path + "{}_{}_{}_{}_{}_{}_1.allowed".format(trace,
                                                                                                             parameters[
                                                                                                                 "TreeDepth"],
                                                                                                             parameters[
                                                                                                                 "SendDuration"],
                                                                                                             parameters[
                                                                                                                 "TraceSlice"],
                                                                                                             parameters[
                                                                                                                 "ProbingTimeZoomingMs"],
                                                                                                             parameters[
                                                                                                                 "NumTopEntriesTraffic"])

            parameters["AllowedToFail"] = allowed_prefixes_file_max_loss

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
        traces_path, computed_parameters, split=0):

    # set path to traces
    TRACES_PATH = traces_path
    variable_parameters["InDirBase"] = [TRACES_PATH]

    if not os.path.isdir(out_dir_runs):
        os.system("mkdir -p {}".format(out_dir_runs))

    runs = create_tests(
        fixed_parameters, variable_parameters, out_dir_runs,
        computed_parameters)

    cmds = []
    # build commands
    for run in runs:
        # we started the zooming and traffic at second 2. Lets try to keep it like this so to get the results as similar as possible.
        cmd = './waf --run  "main --DebugFlag=false --PcapEnabled=False --StartSystemSec=2 --TrafficStart=2 --EnableSaveDrops=false --SoftDetectionEnabled=false --CheckPortStateEnable=false --TrafficType=PcapReplayTraffic --SwitchType=Fancy --PacketHashType=DstPrefixHash --SwitchDelay=0'

        for parameter, value in run.items():
            cmd += " --{}={}".format(parameter, value)

        cmd += '"'
        cmds.append(cmd)

    # split runs if needed
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
