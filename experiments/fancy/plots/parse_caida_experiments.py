from fancy.visualizations import *
from collections import OrderedDict

import glob
import pickle

# Some default parameters
# table 3
used_traces = ['equinix-nyc.dirA.20180419',
               'equinix-chicago.dirB.20140619', 'equinix-nyc.dirB.20180816']

# not used
num_top_prefixes_nya = 6459

# all done with 50ms 200ms and switch delay 10ms
loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
zooming_speed = 200
switch_delay = 10000


def get_output_files_in_dict(input_dir, trace, loss):
    """Given a trace returns a dictionary with all the experiments found inside

    Args:
        input_dir ([type]): [description]
        trace ([type]): [description]

    Returns:
        [type]: [description]
    """
    info_to_files = {}

    all_files = glob.glob(input_dir + "/*info")
    for file in all_files:
        # skip file
        if trace not in file:
            continue

        _str = file.split(trace)[-1].split("_")
        _, _, loss_rate, zooming, _, _, _, prefix_rank = _str
        loss_rate = float(loss_rate)
        zooming_speed = int(zooming)
        prefix_rank = int(prefix_rank.split(".")[0])

        # we do 1 by 1, to avoid problems
        if loss_rate != loss:
            continue

        if (zooming_speed, loss_rate, prefix_rank) not in info_to_files:
            info_to_files[(zooming_speed, loss_rate, prefix_rank)] = [file]
        else:
            info_to_files[(zooming_speed, loss_rate, prefix_rank)].append(file)

    return info_to_files


def precompute_all_caida_sections(
        base_input, path_to_trace_inputs, output_dir,
        zooming_speed, switch_delay, loss_rates, slice,
        traces=used_traces):

    # makes output dir
    os.system("mkdir -p {}".format(output_dir))

    # multiprocessing pool
    pool = multiprocessing.Pool(6)
    for trace in traces:
        for loss_rate in loss_rates:
            input_path = "{}/eval_caida_{}/".format(base_input, trace)
            # get all the files for the subexperiments
            info_to_all_files = get_output_files_in_dict(
                input_path, trace, loss_rate)
            output_file = "{}/fancy_caida_{}_{}_{}_{}.pickle".format(
                output_dir, trace, zooming_speed, switch_delay, loss_rate)
            print("Precomputing for trace {}, zooming speed {} switch delay {} loss {}".format(
                trace, zooming_speed, switch_delay, loss_rate))

            # try with pool
            pool.apply_async(
                get_stats_for_caida_prefix_by_prefix_experiment,
                (info_to_all_files, path_to_trace_inputs, trace, slice,
                 loss_rate, zooming_speed, output_file),
                {}
            )
            # get_stats_for_caida_prefix_by_prefix_experiment(
            #    info_to_all_files, path_to_trace_inputs, trace, slice,
            #    loss_rate, zooming_speed, output_file)


def load_top_prefixes_dict(top_file):
    """
    Loads top prefixes file (can be global or in the specific trace we run.
    Saves the prefixes in a ordered dictionary. The ordered dictionary allows as
    to get given ranked prefix with list(d.items)[rank].
    Args:
        top_file:

    Returns:
    """
    top_prefixes = OrderedDict()
    with open(top_file, "r") as f:
        i = 1
        for line in f:
            prefix, bytes, packets = line.split()
            top_prefixes[prefix] = [i, int(bytes), int(packets)]
            i += 1

    return top_prefixes


def read_flows_dist(dist_file, max=10000):

    prefixes = OrderedDict()
    current_prefix = ""
    rank = 1
    with open(dist_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                if rank == max + 1:
                    return prefixes
                current_prefix = line.split()[1]
                prefixes[current_prefix] = {
                    'packets': [],
                    'bytes': [],
                    'durations': [],
                    "rtts": [],
                    "rank": rank}
                rank += 1
            elif not line.strip():
                continue
            else:
                start_time, packets, duration, bytes, rtt, proto = line.split()
                prefixes[current_prefix]["packets"].append(int(packets))
                prefixes[current_prefix]["bytes"].append(int(bytes))
                prefixes[current_prefix]["durations"].append(float(duration))
                prefixes[current_prefix]["rtts"].append(float(rtt))
    return prefixes


def caida_compute_table_elements(
        input_dir, path_to_trace_inputs, trace, switch_delay, zooming_speed,
        loss_rates, num_top_prefixes=500):

    trace_base = "{}/{}/{}".format(
        path_to_trace_inputs,
        trace, trace)
    dist_file = trace_base + "_" + str(0) + ".dist"
    top_file = trace_base + ".top"

    # put them in the right format
    flow_dist = read_flows_dist(dist_file)
    flow_dist = sorted(flow_dist.items(), key=lambda x: x[1]["rank"])

    top_prefixes = load_top_prefixes_dict(top_file)
    top_prefixes = set(list(top_prefixes.keys())[:num_top_prefixes])

    all_information = {}

    for loss_rate in loss_rates:
        all_information[loss_rate] = {
            "baseline_tpr": [],
            "baseline_bytes": [],
            "layer0_tpr": [],
            "layer0_bytes": [],
            "tpr": [],
            "tpr_1k": [],
            "tpr_5k": [],
            "bytes_share": [],
            "bytes_share_dedicated": [],
            "bytes_share_zooming": [],
            "pkts_share": [],
            "avg_detection_speed": [],
            "avg_detection_speed_1k": [],
            "avg_detection_speed_5k": [],
            "tpr_dedicated": [],
            "tpr_zooming": [],
            "top_entries_count": 0}

        all_bytes = 0
        all_packets = 0

        input_file = "{}/fancy_caida_{}_{}_{}_{}.pickle".format(
            input_dir, trace, zooming_speed, switch_delay, loss_rate)
        data = pickle.load(open(input_file, "rb"))

        for rank, prefix_info in sorted(data.items(), key=lambda x: x[0]):

            prefix = flow_dist[rank - 1][0]
            total_bytes = sum(flow_dist[rank - 1][1]["packets"])
            total_packets = sum(flow_dist[rank - 1][1]["bytes"])

            # sum for the total
            all_bytes += total_bytes
            all_packets += total_packets

            # bool
            is_top_prefix = prefix in top_prefixes

            # fancy prefix info
            fancy_prefix_info = prefix_info["fancy"]

            # get dedicated baseline info
            dedicated_baseline_info = prefix_info["dedicated"]
            all_information[loss_rate]["baseline_tpr"].append(
                dedicated_baseline_info["tpr"])
            all_information[loss_rate]["baseline_bytes"].append(
                total_bytes * dedicated_baseline_info["tpr"])

            # layer 0 info
            # TODO ALSO COUNT TOP ENTRIES AS THE BASELINE TPR
            layer0_baseline_info = prefix_info["layer0"]
            if not is_top_prefix:
                all_information[loss_rate]["layer0_tpr"].append(
                    layer0_baseline_info["tpr"])
                all_information[loss_rate]["layer0_bytes"].append(
                    total_bytes * layer0_baseline_info["tpr"])
            # we add the info from top prefixes to do the UNION
            else:
                all_information[loss_rate]["layer0_tpr"].append(
                    dedicated_baseline_info["tpr"])
                all_information[loss_rate]["layer0_bytes"].append(
                    total_bytes * dedicated_baseline_info["tpr"])

            # filling the info
            all_information[loss_rate]["tpr"].append(fancy_prefix_info["tpr"])
            all_information[loss_rate]["bytes_share"].append(
                total_bytes * fancy_prefix_info["tpr"])
            all_information[loss_rate]["pkts_share"].append(
                total_packets * fancy_prefix_info["tpr"])

            # only if there is detection times
            if fancy_prefix_info["avg_detection_times"] != -1:
                all_information[loss_rate]["avg_detection_speed"].append(
                    fancy_prefix_info["avg_detection_times"])

            # top prefix tpr
            if is_top_prefix:
                all_information[loss_rate]["top_entries_count"] += 1
                all_information[loss_rate]["tpr_dedicated"].append(
                    fancy_prefix_info["tpr"])
                all_information[loss_rate]["bytes_share_dedicated"].append(
                    total_bytes * fancy_prefix_info["tpr"])

            else:
                all_information[loss_rate]["tpr_zooming"].append(
                    fancy_prefix_info["tpr"])
                all_information[loss_rate]["bytes_share_zooming"].append(
                    total_bytes * fancy_prefix_info["tpr"])

            # per rank stats
            if rank <= 1000:
                all_information[loss_rate]["tpr_1k"].append(
                    fancy_prefix_info["tpr"])
                if fancy_prefix_info["avg_detection_times"] != -1:
                    all_information[loss_rate]["avg_detection_speed_1k"].append(
                        fancy_prefix_info["avg_detection_times"])

            if rank <= 5000:
                all_information[loss_rate]["tpr_5k"].append(
                    fancy_prefix_info["tpr"])
                if fancy_prefix_info["avg_detection_times"] != -1:
                    all_information[loss_rate]["avg_detection_speed_5k"].append(
                        fancy_prefix_info["avg_detection_times"])

        # aggregate data
        # baseline info
        all_information[loss_rate]["baseline_tpr"] = np.mean(
            all_information[loss_rate]["baseline_tpr"])
        all_information[loss_rate]["baseline_bytes"] = sum(
            all_information[loss_rate]["baseline_bytes"]) / all_bytes

        # baseline info
        all_information[loss_rate]["layer0_tpr"] = np.mean(
            all_information[loss_rate]["layer0_tpr"])
        all_information[loss_rate]["layer0_bytes"] = sum(
            all_information[loss_rate]["layer0_bytes"]) / all_bytes

        # fancy info
        all_information[loss_rate]["tpr"] = np.mean(
            all_information[loss_rate]["tpr"])
        all_information[loss_rate]["tpr_1k"] = np.mean(
            all_information[loss_rate]["tpr_1k"])
        all_information[loss_rate]["tpr_5k"] = np.mean(
            all_information[loss_rate]["tpr_5k"])
        all_information[loss_rate]["tpr_dedicated"] = np.mean(
            all_information[loss_rate]["tpr_dedicated"])
        all_information[loss_rate]["tpr_zooming"] = np.mean(
            all_information[loss_rate]["tpr_zooming"])

        all_information[loss_rate]["bytes_share"] = sum(
            all_information[loss_rate]["bytes_share"]) / all_bytes

        all_information[loss_rate]["bytes_share_dedicated"] = sum(
            all_information[loss_rate]["bytes_share_dedicated"]) / all_bytes
        all_information[loss_rate]["bytes_share_zooming"] = sum(
            all_information[loss_rate]["bytes_share_zooming"]) / all_bytes
        all_information[loss_rate]["pkts_share"] = sum(
            all_information[loss_rate]["pkts_share"]) / all_packets
        all_information[loss_rate]["avg_detection_speed"] = np.mean(
            all_information[loss_rate]["avg_detection_speed"])
        all_information[loss_rate]["avg_detection_speed_1k"] = np.mean(
            all_information[loss_rate]["avg_detection_speed_1k"])
        all_information[loss_rate]["avg_detection_speed_5k"] = np.mean(
            all_information[loss_rate]["avg_detection_speed_5k"])

    return all_information


def caida_compute_table(
        input_dir, path_to_trace_inputs,
        output_file,
        traces, switch_delay, zooming_speed, loss_rates, num_top_prefixes=500):

    table = {}
    for trace in traces:
        data = caida_compute_table_elements(
            input_dir, path_to_trace_inputs, trace, switch_delay,
            zooming_speed, loss_rates, num_top_prefixes=500)

        table[trace] = data

    if output_file:
        pickle.dump(table, open(output_file, "wb"))

    return table

    # table 3 extended version


def print_caida_table(input_file, output_file):
    """Prints and saves the caida table from a precomputed pickle file.

    Args:
        input_file (_type_): _description_
        output_file (_type_): _description_
    """

    # loads the table info
    table = pickle.load(open(input_file, "rb"))

    # table heading
    heading = "{:>8} {:>14} {:>14} {:>16} {:>15} {:>8} {:>7} {:>7} {:>12} {:>22} {:>22} {:>11} {:>22} {:>24} {:>24} {:>15} {:>14} {:>20}"

    # output string
    out_str = ""

    for trace, data in table.items():
        # print heading
        headers = [""] + list(data[1].keys())
        out_str += "Avg trace {}".format(trace) + "\n"
        heading_str = heading.format(*headers)
        out_str += heading_str + "\n"
        for loss, run_info in data.items():
            headers = [loss] + [round(x, 3) for x in list(run_info.values())]
            heading_str = heading.format(*headers)
            out_str += heading_str + "\n"
        out_str += "\n"

    # print the average table
    out_str += "Average of all traces\n"
    # print heading
    headers = [""] + list(list(table.values())[0][1].keys())
    heading_str = heading.format(*headers)
    out_str += heading_str + "\n"

    table_list = list(table.items())
    # it is just a sample
    trace, data = table_list[0]

    for loss in loss_rates:
        # average all the data values with other runs
        avg_values = []
        for i in range(len(table_list)):
            avg_values.append(list(table_list[i][1][loss].values()))

        # ipdb.set_trace()
        avg = [sum(i) for i in zip(*avg_values)]
        avg = [x / len(table_list) for x in avg]

        headers = [loss] + [round(x, 3) for x in avg]
        # ipdb.set_trace()
        heading_str = heading.format(*headers)
        out_str += heading_str + "\n"

    out_str += "\n"

    # print table
    print(out_str)

    # save table
    if output_file:
        with open(output_file, "w") as fp:
            fp.write(out_str)


# reduced version, only shwos the columns of table 3
def print_caida_table_reduced(input_file, output_file):
    """Prints and saves the caida table from a precomputed pickle file.

    Args:
        input_file (_type_): _description_
        output_file (_type_): _description_
    """

    # loads the table info
    table = pickle.load(open(input_file, "rb"))

    # table heading
    heading = "{:>8} {:>12} {:>8} {:>22} {:>15} {:>24}"
    columns = ["bytes_share", "tpr", "tpr_dedicated",
               "tpr_zooming", "avg_detection_speed"]
    # output string
    out_str = ""

    for trace, data in table.items():
        # print heading
        headers = [""] + columns
        out_str += "Avg trace {}".format(trace) + "\n"
        heading_str = heading.format(*headers)
        out_str += heading_str + "\n"
        for loss, run_info in data.items():
            headers = [loss] + [round(run_info[x], 3) for x in columns]
            heading_str = heading.format(*headers)
            out_str += heading_str + "\n"
        out_str += "\n"

    # print the average table
    out_str += "Average of all traces\n"
    # print heading
    headers = [""] + columns
    heading_str = heading.format(*headers)
    out_str += heading_str + "\n"

    table_list = list(table.items())
    # it is just a sample
    trace, data = table_list[0]

    for loss in loss_rates:
        # average all the data values with other runs
        avg_values = []
        # ipdb.set_trace()
        # iterate all the traces
        for i in range(len(table_list)):
            # filtered columns
            values = [table_list[i][1][loss][x] for x in columns]
            avg_values.append(values)

        # ipdb.set_trace()
        avg = [sum(i) for i in zip(*avg_values)]
        avg = [x / len(table_list) for x in avg]

        headers = [loss] + [round(x, 3) for x in avg]
        # ipdb.set_trace()
        heading_str = heading.format(*headers)
        out_str += heading_str + "\n"

    out_str += "\n"

    # print table
    print(out_str)

    # save table
    if output_file:
        with open(output_file, "w") as fp:
            fp.write(out_str)
