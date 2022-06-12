from fancy.file_loader import *
from fancy.frequencies_and_opportunities import get_prefix_packet_frequency, prefix_zooming_performance, STRONG_BIN, WEAK_BIN
import ipdb
import numpy as np
import os.path
import glob
import subprocess

all_traces = [
    'equinix-chicago.dirA.20160121', 'equinix-chicago.dirB.20140619',
    'equinix-nyc.dirA.20180419', 'equinix-chicago.dirB.20131219',
    'equinix-chicago.dirB.20160121', 'equinix-sanjose.dirA.20131024',
    'equinix-nyc.dirB.20190117', 'equinix-nyc.dirB.20180816',
    'equinix-chicago.dirB.20101029', 'equinix-sanjose.dirA.20110324']


id_to_trace = {1: 'equinix-chicago.dirB.20101029',
               2: 'equinix-sanjose.dirA.20110324',
               3: 'equinix-sanjose.dirA.20131024',
               4: 'equinix-chicago.dirB.20131219',
               5: 'equinix-chicago.dirB.20140619',
               6: 'equinix-chicago.dirA.20160121',
               7: 'equinix-chicago.dirB.20160121',
               8: 'equinix-nyc.dirA.20180419',
               9: 'equinix-nyc.dirB.20180816',
               10: 'equinix-nyc.dirB.20190117'}

trace_to_id = {y: x for x, y in id_to_trace.items()}

new_traces = ['equinix-nyc.dirB.20190117', 'equinix-nyc.dirB.20180816',
              'equinix-chicago.dirB.20101029', 'equinix-sanjose.dirA.20110324']


traces1 = ['equinix-chicago.dirA.20160121',
           'equinix-chicago.dirB.20140619', 'equinix-nyc.dirA.20180419']
traces2 = ['equinix-chicago.dirB.20131219',
           'equinix-chicago.dirB.20160121', 'equinix-sanjose.dirA.20131024']

traces3 = ['equinix-nyc.dirB.20190117', 'equinix-nyc.dirB.20180816']
traces4 = ['equinix-sanjose.dirA.20110324', 'equinix-chicago.dirB.20101029']

traces_boilover = ['equinix-chicago.dirA.20160121']
traces_samichlaus = ['equinix-nyc.dirA.20180419']
traces_arak = ['equinix-chicago.dirB.20101029',
               'equinix-sanjose.dirA.20131024']
traces_west = ['equinix-nyc.dirB.20190117', 'equinix-nyc.dirB.20180816']
traces_orval = ['equinix-chicago.dirB.20140619',
                'equinix-chicago.dirB.20131219',
                'equinix-chicago.dirB.20160121',
                'equinix-sanjose.dirA.20131024']

traces_orval_help = ['equinix-sanjose.dirA.20131024',
                     'equinix-nyc.dirB.20180816']

last_trace = ['equinix-sanjose.dirA.20110324']

TOP_PREFIX_TYPE = 1

all_traces = [
    'equinix-chicago.dirA.20160121', 'equinix-chicago.dirB.20140619',
    'equinix-nyc.dirA.20180419', 'equinix-chicago.dirB.20131219',
    'equinix-chicago.dirB.20160121', 'equinix-sanjose.dirA.20131024',
    'equinix-nyc.dirB.20190117', 'equinix-nyc.dirB.20180816',
    'equinix-chicago.dirB.20101029', 'equinix-sanjose.dirA.20110324']

# latest runs
traces_arak = ['equinix-chicago.dirA.20160121',
               'equinix-chicago.dirB.20140619', ]
traces_west = ['equinix-chicago.dirB.20160121',
               'equinix-sanjose.dirA.20131024', 'equinix-nyc.dirB.20190117']
traces_orval = [
    'equinix-nyc.dirA.20180419', 'equinix-chicago.dirB.20101029',
    'equinix-sanjose.dirA.20110324', 'equinix-nyc.dirB.20180816',
    'equinix-chicago.dirB.20131219']

traces_west = ['equinix-nyc.dirB.20190117']
traces_orval = ['equinix-nyc.dirB.20180816']


"""
Test Infos (outputs) Utils
"""


def get_specific_tests_info(path_to_infos, desired_features):
    """
    Fins all the test infos that have some matching desires features
    Args:
        path_to_infos:
        desired_features:

    Returns:

    """

    # transform desired features

    matching_infos = []
    infos = glob.glob(path_to_infos + "/*.info")
    for info in infos:
        sim_info = load_sim_info_file(info)
        match = set(sim_info.items()).intersection(
            set(desired_features.items())) == desired_features.items()

        if match:
            matching_infos.append(info)

    return matching_infos


def find_duplicated_test_infos(path_to_infos):
    """

    Args:
        path_to_infos:

    Returns:

    """

    duplicated_candidates = {}
    infos = glob.glob(path_to_infos + "/*.info")
    for info in infos:
        _sim_info = load_sim_info_file(info)
        # remove temporal elements
        sim_info = _sim_info.copy()
        sim_info.pop('RealSimulationTime', None)
        sim_info.pop('ExperimentEpoch', None)
        sim_info.pop('OutDirBase', None)

        _key = str(sorted(sim_info.items()))

        if _key not in duplicated_candidates:
            duplicated_candidates[_key] = [info]
        else:
            duplicated_candidates[_key].append(info)

    # filter and only keep the duplicated groups
    duplicated_test_infos = []
    for k, v in duplicated_candidates.items():
        if len(v) > 1:
            duplicated_test_infos.append(v)

    return duplicated_test_infos


def remove_command(cmd):

    print(cmd)
    os.system("rm {}".format(cmd))


def clean_duplicated_test_infos(path_to_infos):
    """

    Args:
        path_to_infos:

    Returns:

    """

    files_to_remove = find_duplicated_test_infos(path_to_infos)

    # find the oldest experiment and keep that one
    for experiments in files_to_remove:
        oldest_file = sorted(
            [(int(load_sim_info_file(x)['ExperimentEpoch']),
              x) for x in experiments],
            key=lambda x: x[0],
            reverse=True)

        # iterate the files to remove
        # print(oldest_file)
        for file_to_remove in oldest_file[1:]:
            info_name = file_to_remove[1]
            base_name = info_name.replace(".info", "")

            remove_command(info_name)
            remove_command(base_name + "-failed_prefixes.txt")
            remove_command(base_name + "_s1.json")


"""
Extract information from system runs
"""


def get_run_performance(
        sim_out, failed_prefixes, num_total_prefixes, global_top_prefixes,
        num_top_prefixes_system):

    total_failed_prefixes = len(failed_prefixes)

    # count truly detected prefixes
    truly_detected = 0

    for prefix in failed_prefixes:
        id, _type = get_prefix_type(
            prefix, global_top_prefixes, num_top_prefixes_system)
        if get_prefix_detection_time(
                prefix, _type, id, sim_out["failures"]) != -1:
            truly_detected += 1

    # compute TPR
    tpr = truly_detected / (total_failed_prefixes)
    tp = truly_detected

    # compute FPR
    falsy_detected = 0
    for reroute in sim_out["reroutes"]:
        rerouted_prefix = reroute["flow"].split()[1]
        if rerouted_prefix not in failed_prefixes:
            falsy_detected += 1
    fpr = falsy_detected / (num_total_prefixes - total_failed_prefixes)
    fp = falsy_detected

    # compute TNR
    tnr = 1 - fpr

    # compute FNR
    fnr = 1 - tpr

    print("TRP: {}, FPR: {}, TNR : {}, FNR: {}".format(tpr, fpr, tnr, fnr))

    return tpr, fpr, tnr, fnr, tp, fp


def get_list_cdf(element_list):

    cdf_x = sorted([float(x) for x in element_list])
    normal_cdf_y = np.arange(1, len(cdf_x) + 1) / float(len(cdf_x))
    return cdf_x, normal_cdf_y


def get_detection_times_cdf_info(detection_times_data):
    """
    Returns three CDFS.
    1) Absolute number CDF
    2) Weighted by packets CDF
    3) Weighted by bytes CDF

    It takes into account non detected prefixes

    Args:
        detection_times_data:

    Returns:

    """

    INF = 1000000

    # replace detection time -1 with INF
    # also count bytes and packets
    total_packets = 0
    total_bytes = 0
    for prefix, data in detection_times_data.items():
        if data["detection_time"] == -1:
            data["detection_time"] = INF

        total_packets += data["packets"]
        total_bytes += data["bytes"]

    # here we substract the first packet!
    sorted_detections = sorted(detection_times_data.items(), key=lambda x: (
        Decimal(x[1]["detection_time"]) - x[1]["first_packet"]))

    # get sorted and raw detection time
    detection_times = []
    for prefix, data in sorted_detections:
        if data["detection_time"] != INF:
            detection_time = (
                Decimal(data["detection_time"]) - data["first_packet"])
        else:
            detection_time = INF
        detection_times.append((prefix, detection_time))

    # 1) Normal CDF Info
    cdf_x = [x[1] for x in detection_times]
    normal_cdf_y = np.arange(1, len(cdf_x) + 1) / float(len(cdf_x))

    prefix_to_info = {}

    # 2) Per Packet CDF Info & # 3) Per Byte CDF Info
    packets_cdf_y = []
    bytes_cdf_y = []
    packets_cumulative_y = 0
    bytes_cumulative_y = 0
    for prefix, detect_t in detection_times:

        bytes = detection_times_data[prefix]["bytes"]
        packets = detection_times_data[prefix]["packets"]

        prefix_to_info[prefix] = {
            'detection_time': float(detect_t),
            'bytes': bytes, 'packets': packets,
            'first_packet':
            float(detection_times_data[prefix]['first_packet']),
            'prefix_type': detection_times_data[prefix]['prefix_type'],
            "fzo": float(detection_times_data[prefix]['fzo']),
            'wzo': detection_times_data[prefix]['wzo']}

        packets_cumulative_y += packets
        bytes_cumulative_y += bytes

        packets_cdf_y.append(packets_cumulative_y / float(total_packets))
        bytes_cdf_y.append(bytes_cumulative_y / float(total_bytes))

    # 4 Extra Info/Stats
    filtered_detection_times = [float(x[1])
                                for x in detection_times if x[1] != INF]

    # Maybe not the best, but if its an empty list we set the avg to 0...
    if not filtered_detection_times:
        avg = 0
        median = 0
        percentile95 = 0
    else:
        avg = np.average(filtered_detection_times)
        median = np.median(filtered_detection_times)
        percentile95 = np.percentile(filtered_detection_times, 95)

    return filtered_detection_times, prefix_to_info, cdf_x, normal_cdf_y, packets_cdf_y, bytes_cdf_y, avg, median, percentile95


def get_detection_shares_info(
        sim_out, failed_prefixes, slice_top_prefixes, global_top_prefixes,
        num_top_prefixes_system):

    # count all the detected bytes and packets split in between dedicated entries and tree
    global_packets_total_count = 0
    global_packets_total_count_detected = 0
    global_packets_top_count_detected = 0
    global_packets_zoomed_count_detected = 0

    global_bytes_total_count = 0
    global_bytes_total_count_detected = 0
    global_bytes_top_count_detected = 0
    global_bytes_zoomed_count_detected = 0

    slice_packets_total_count = 0
    slice_packets_total_count_detected = 0
    slice_packets_top_count_detected = 0
    slice_packets_zoomed_count_detected = 0

    slice_bytes_total_count = 0
    slice_bytes_total_count_detected = 0
    slice_bytes_top_count_detected = 0
    slice_bytes_zoomed_count_detected = 0

    global_packets_per_prefix = {}
    global_bytes_per_prefix = {}

    slice_packets_per_prefix = {}
    slice_bytes_per_prefix = {}

    for prefix in failed_prefixes:
        id, _type = get_prefix_type(
            prefix, global_top_prefixes, num_top_prefixes_system)

        global_top, global_bytes, global_packets = global_top_prefixes[prefix]
        slice_top, slice_bytes, slice_packets = slice_top_prefixes[prefix]

        # max counts
        global_packets_total_count += global_packets
        global_bytes_total_count += global_bytes

        slice_packets_total_count += slice_packets
        slice_bytes_total_count += slice_bytes

        # if detected
        if get_prefix_detection_time(
                prefix, _type, id, sim_out["failures"]) != -1:

            global_packets_total_count_detected += global_packets
            global_bytes_total_count_detected += global_bytes

            slice_packets_total_count_detected += slice_packets
            slice_bytes_total_count_detected += slice_bytes

            global_packets_per_prefix[prefix] = global_packets
            global_bytes_per_prefix[prefix] = global_bytes

            slice_packets_per_prefix[prefix] = slice_packets
            slice_bytes_per_prefix[prefix] = slice_bytes

            # if prefix has a dedicated entry
            if _type == 1:
                global_packets_top_count_detected += global_packets
                global_bytes_top_count_detected += global_bytes

                slice_packets_top_count_detected += slice_packets
                slice_bytes_top_count_detected += slice_bytes
            # if prefix has to be detected by zooming
            elif _type == 0:
                global_packets_zoomed_count_detected += global_packets
                global_bytes_zoomed_count_detected += global_bytes

                slice_packets_zoomed_count_detected += slice_packets
                slice_bytes_zoomed_count_detected += slice_bytes

    # total bytes can be inferred from the shares if we do the sum of packets or bytes at the per_prefix cell
    return {"global": {"packets":
                       {"total": global_packets_total_count_detected / global_packets_total_count, "top_entry": global_packets_top_count_detected / global_packets_total_count, "zoomed": global_packets_zoomed_count_detected / global_packets_total_count, "per_prefix": global_packets_per_prefix},
                       "bytes":
                           {"total": global_bytes_total_count_detected / global_bytes_total_count, "top_entry": global_bytes_top_count_detected / global_bytes_total_count, "zoomed": global_bytes_zoomed_count_detected / global_bytes_total_count, "per_prefix": global_bytes_per_prefix}},
            "slice": {"packets":
                      {"total": slice_packets_total_count_detected / slice_packets_total_count, "top_entry": slice_packets_top_count_detected / slice_packets_total_count, "zoomed": slice_packets_zoomed_count_detected / slice_packets_total_count, "per_prefix": slice_packets_per_prefix},
                      "bytes":
                          {"total": slice_bytes_total_count_detected / slice_bytes_total_count, "top_entry": slice_bytes_top_count_detected / slice_bytes_total_count, "zoomed": slice_bytes_zoomed_count_detected / slice_bytes_total_count, "per_prefix": slice_bytes_per_prefix}}
            }


def get_prefix_type(prefix, global_top_prefixes, num_top_prefixes_system):
    """
    Returns prefix id and prefix type 1 for top prefixes
    Args:
        prefix:
        global_top_prefixes:
        num_top_prefixes_system:

    Returns:

    """

    global_top, _, _ = global_top_prefixes[prefix]
    # we do id - 1 because in the ns3 implementation IDs start from 0, maybe I should
    # modify that?
    if global_top - 1 >= num_top_prefixes_system:
        id = num_top_prefixes_system
        _type = 0
    else:
        id = global_top - 1
        _type = 1

    return id, _type


def get_prefix_detection_time(prefix, prefix_type, id, fail_info):
    """
    Returns the prefix detection time in this simulation. If not detected
    returns -1.
    Args:
        prefix:
        prefix_type:
        id:
        fail_info:

    Returns:

    """

    # top prefixes
    if prefix_type == TOP_PREFIX_TYPE:
        for fail in fail_info:
            if id == fail['id']:
                return fail['timestamp']

    #  detected with the zooming
    else:
        for fail in fail_info:
            if fail['bloom_count'] > 0:
                if any(x.split()[1] == prefix for x in fail['flows']):
                    return fail['timestamp']

    return -1


"""
Getting SYSTEM stats
"""


def get_prefixes_detection_times(
        sim_out, failed_prefixes, prefixes_ts, global_top_prefixes,
        slice_top_prefixes, start_ts, end_ts, num_top_prefixes, depth,
        zooming_speed):

    prefixes_detection_times = {}

    failure_info = sim_out["failures"]

    SIMULATION_SEND_START = 2

    # Useless but keep it here
    cached_prefixes_packet_frequency = {}

    for prefix in failed_prefixes:

        global_top, global_bytes, global_packets = global_top_prefixes[prefix]
        slice_top, slice_bytes, slice_packets = slice_top_prefixes[prefix]

        # get metadata
        id, _type = get_prefix_type(
            prefix, global_top_prefixes, num_top_prefixes)
        # get detection time
        detection_time = get_prefix_detection_time(
            prefix, _type, id, failure_info)

        prefix_ts = prefixes_ts.get(prefix, None)
        if prefix_ts:
            if type(prefix_ts) == dict:
                prefix_ts = prefix_ts['ts']

        # for this specific prefix
        first_ts = prefix_ts[0] - start_ts

        # First zooming opportunity info
        cached_frequencies = cached_prefixes_packet_frequency.get(prefix, None)
        packet_frequency, num_packets = get_prefix_packet_frequency(
            prefix_ts, start_ts, end_ts, zooming_speed, cached_frequencies)

        # gets the performance for a specific frequency and tree set up
        weak_total_bins, \
            weak_max_consecutive_bins, \
            weak_zooming_opportunities, \
            weak_first_zooming_opportunity, \
            strong_total_bins, \
            strong_max_consecutive_bins, \
            strong_zooming_opportunities, \
            strong_first_zooming_opportunity = prefix_zooming_performance(packet_frequency, depth, WEAK_BIN, STRONG_BIN)

        if weak_first_zooming_opportunity != -1:
            weak_first_zooming_opportunity -= start_ts

        if strong_first_zooming_opportunity != -1:
            strong_first_zooming_opportunity -= start_ts

        """
        Collect info for the plots
        """
        prefixes_detection_times[prefix] = {
            "failure_time": 0,
            "detection_time": max(
                detection_time - SIMULATION_SEND_START, -1),
            "first_packet": first_ts, "bytes": slice_bytes,
            "packets": slice_packets, 'prefix_type': _type,
            "fzo": weak_first_zooming_opportunity,
            'wzo': weak_zooming_opportunities}

    return prefixes_detection_times


# call it precompute a system output compilation
def get_stats_for_experiment_spec(
        input_path, experiment_spec, output_file=None):

    # for a given set of traces, fixed system , seeds, duration, etc. We do:
    # One file for each: top_entries, fail_drop, num_top_fails.
    # For each we do: averaged TP, averaged FP, absolute FP, list of detection times, means, medians, percentiles, etc
    experiment_runs = get_specific_tests_info(input_path, experiment_spec)

    # common info
    if not experiment_runs:
        print("No experiments found for spec: {}".format(experiment_spec))
        print("Make sure the traces input path {} is the same used to run the simulations, \
              since that is being used to match experiments".format(
            experiment_spec["InDirBase"]))

    sim_info = load_sim_info_file(experiment_runs[0])
    inputs_dir_base = sim_info["InDirBase"]

    experiment_slice = experiment_spec["TraceSlice"]

    # load
    # This uses the top prefixes and ranks to compute how big the prefixes are etc.
    # It also takes the real starting time of each prefix so to compute a more realistic
    # detection time.
    slice_top_prefixes = load_top_prefixes_dict(
        inputs_dir_base + "_{}.top".format(experiment_slice))
    global_top_prefixes = load_top_prefixes_dict(inputs_dir_base + ".top")

    trace_ts = load_trace_ts(
        inputs_dir_base + "_{}.info".format(experiment_slice))
    prefixes_ts = load_prefixes_ts_raw(
        inputs_dir_base + "_{}.ts".format(experiment_slice))

    start_ts = trace_ts[0]
    end_ts = start_ts + Decimal(sim_info["SendDuration"])

    all_detection_times = []
    all_prefixes_info = []
    avg_detections = []
    median_detections = []
    percentile_95_detections = []

    tprs = []
    fprs = []
    tps = []
    fps = []
    avg_slice_bytes = {'total': [], "top_entry": [], "zoomed": []}

    for run_info in experiment_runs:
        print(run_info)

        sim_info = load_sim_info_file(run_info)
        outputs_dir_base = sim_info["OutDirBase"]
        num_top_prefixes = int(sim_info["NumTopEntriesSystem"])

        failed_prefixes = load_failed_prefixes(
            outputs_dir_base + "-failed_prefixes.txt")
        sim_out = load_simulation_out(outputs_dir_base + "_s1.json")

        # Get Detection times and a lot of info
        res = get_prefixes_detection_times(
            sim_out, failed_prefixes, prefixes_ts, global_top_prefixes,
            slice_top_prefixes, start_ts, end_ts, num_top_prefixes,
            int(sim_info["TreeDepth"]),
            Decimal(sim_info["ProbingTimeZoomingMs"]) / 1000)

        # process detection times
        detection_times, prefix_to_info, * \
            cdfs, avg_detection, median_detection, percentile_95 = get_detection_times_cdf_info(res)

        # Here we start to collect stats
        all_detection_times.append(detection_times)
        all_prefixes_info.append(prefix_to_info)

        avg_detections.append(avg_detection)
        median_detections.append(median_detection)
        percentile_95_detections.append(percentile_95)

        # Get Performances
        tpr, fpr, tnr, fnr, tp, fp = get_run_performance(
            sim_out, failed_prefixes, len(slice_top_prefixes),
            global_top_prefixes, num_top_prefixes)
        tprs.append(tpr)
        fprs.append(fpr)
        tps.append(tp)
        fps.append(fp)

        # Get Shares
        detection_shares = get_detection_shares_info(
            sim_out, failed_prefixes, slice_top_prefixes, global_top_prefixes,
            num_top_prefixes)

        # stats for this given slice, not using global sizes
        avg_slice_bytes['total'].append(
            detection_shares['slice']['bytes']['total'])
        avg_slice_bytes['top_entry'].append(
            detection_shares['slice']['bytes']['top_entry'])
        avg_slice_bytes['zoomed'].append(
            detection_shares['slice']['bytes']['zoomed'])

    # Collected stats from this set of runs
    N = len(experiment_runs)

    # average of the average of detection times over N runs
    avg_avg_detection = sum(avg_detections) / N

    # average of the medians over N runs
    avg_median_detection = sum(median_detections) / N

    # Percentiles
    # percentile 95 of medians
    percentile_95_of_medians = np.percentile(median_detections, 95)
    # average of 95th percentiles (this is very high usually)
    avg_95_detection = sum(percentile_95_detections) / N

    avg_tpr = sum(tprs) / N
    avg_fpr = sum(fprs) / N
    avg_tp = sum(tps) / N
    avg_fp = sum(fps) / N

    avg_slice_bytes['total'] = sum(avg_slice_bytes['total']) / N
    avg_slice_bytes['top_entry'] = sum(avg_slice_bytes['top_entry']) / N
    avg_slice_bytes['zoomed'] = sum(avg_slice_bytes['zoomed']) / N

    experiment_performance = {
        'all_prefixes_info': all_prefixes_info,
        'all_detection_times': all_detection_times,
        'flat_all_detection_times': sorted([item for sublist in all_detection_times for item in sublist]),
        'avg_avg_detection': avg_avg_detection,
        'avg_median_detection': avg_median_detection,
        'medians': median_detections,
        'means': avg_detections,
        'avg_tpr': avg_tpr,
        'avg_fpr': avg_fpr,
        'avg_tp': avg_tp,
        'avg_fp': avg_fp,
        'tprs': tprs,
        'fprs': fprs,
        'tps': tps,
        'fps': fps,
        'avg_slice_bytes': avg_slice_bytes,
        'avg_95_detection': avg_95_detection,
        'percentile_95_of_medians': percentile_95_of_medians,
        'num_runs': len(experiment_runs),
        'experiment_runs': experiment_runs
    }

    # Pickle if there is a file to pickle too
    if output_file:
        pickle.dump(experiment_performance, open(output_file, "wb"))

    return experiment_performance


def get_loss_rates(sim_out):
    """Gets the loss rate for each detection

    Args:
        sim_out ([type]): [description]
    Returns:
        [type]: [description]
    """

    prefixes_loss_rates = []
    failure_info = sim_out["failures"]

    for failure in failure_info:
        if failure["flows"] and failure["hash_path"]:  # tree
            loss_rate = 1 - (failure["remote_counter"] /
                             failure["local_counter"])
        elif not failure["hash_path"]:  # dedicated counter only
            loss_rate = 1 - (failure["remote_counter"] /
                             failure["local_counter"])
        else:  # invalid weird thing
            continue
        prefixes_loss_rates.append(loss_rate)

    return prefixes_loss_rates

# used for caida eval experiments sigcomm2022
# this asumes only one prefixed failed at the moment
# to make it for multiple has to be extended


def get_prefixes_soft_failure_info(
        sim_out, failure_time=2, soft_layers=2, dedicated_id=501):
    """Sigcomm function to get soft failures info.
    Soft failures are not detected by fancy itself but by dedicated counter
    entries or partial tree steps.

    Args:
        sim_out ([type]): [description] failure_time (int, optional):
        [description]. Defaults to 2.
    """

    dedicated_entry_info = ()
    hash_tree_info = {}

    failure_info = sim_out["soft_failures"]

    elements_found = 0
    elements_to_find = soft_layers + 1

    for failure in failure_info:
        if elements_found == elements_to_find:
            break
        if failure["id"] == dedicated_id:
            ts = failure["timestamp"]
            detection_time = ts - failure_time
            # bug problem
            try:
                loss_rate = 1 - (failure["remote_counter"] /
                                 failure["local_counter"])
            except:
                loss_rate = 1
            if not dedicated_entry_info:
                elements_found += 1
                dedicated_entry_info = (detection_time, loss_rate)

        elif failure["id"] == dedicated_id - 1:
            # just in case there is the weird thing with no real flow
            if failure["flows"]:
                depth = failure["depth"]
                ts = failure["timestamp"]
                detection_time = ts - failure_time
                # bug
                try:
                    loss_rate = 1 - (failure["remote_counter"] /
                                     failure["local_counter"])
                except:
                    loss_rate = 1
                # we add it
                if not depth in hash_tree_info:
                    hash_tree_info[depth] = (detection_time, loss_rate)
                    elements_found += 1

    return dedicated_entry_info, hash_tree_info


def get_prefixes_detection_times_synthetic(sim_out, failure_time=2):
    """Used for resubmission experiments eval 2. Way simpler than the other experiments.

    Args:
        sim_out ([type]): [description]
        failure_time (int, optional): [description]. Defaults to 2.

    Returns:
        [type]: [description]
    """

    prefixes_detection_times = {}

    failure_info = sim_out["failures"]

    for failure in failure_info:
        # we asume there is no collision here, but if there is both are failed prefixes.
        # NOTE this needs to be reviewed, what if multiple prefixes?
        # tree
        if failure["flows"]:
            for prefix in failure["flows"]:
                _prefix = prefix.split()[1]
                prefixes_detection_times[_prefix] = failure["timestamp"] - failure_time
        else:  # dedicated entries
            # removes some weird event were we detections without failure["flow"] but they go to tree.
            # if not failure["hash_path"]:
            prefixes_detection_times[failure["id"]
                                     ] = failure["timestamp"] - failure_time

    return prefixes_detection_times


# call it precompute a system output compilation // EVAL 2
def get_stats_for_synthetic_experiment_spec(
        input_path, experiment_spec, output_file=None,
        variable_feature="SendRate"):

    # for a given set of traces, fixed system , seeds, duration, etc. We do:

    # One file for each: top_entries, fail_drop, num_top_fails.

    # For each we do: averaged TP, averaged FP, absolute FP, list of detection times, means, medians, percentiles, etc

    experiment_runs = get_specific_tests_info(input_path, experiment_spec)

    #experiment_runs = pickle.load(open("runs.pickle", "rb"))

    # common info
    sim_info = load_sim_info_file(experiment_runs[0])
    inputs_dir_base = sim_info["InDirBase"]

    # check type of simulation to synthesise some parameters that we do not have
    if sim_info["TrafficType"] != "StatefulSyntheticTraffic":
        raise Exception("The test is not Stateful synthetic test")

    experiment_performance = {}

    for run_info in experiment_runs:
        print(run_info)
        sim_info = load_sim_info_file(run_info)
        outputs_dir_base = sim_info["OutDirBase"]
        sim_out = load_simulation_out(outputs_dir_base + "_s1.json")

        # Get Detection times and a lot of info
        prefix_to_detection_time = get_prefixes_detection_times_synthetic(
            sim_out, float(sim_info["FailTime"]))

        detection_times = list(prefix_to_detection_time.values())

        if not detection_times:
            experiment_performance[sim_info[variable_feature]] = {
                "detection_times": [],
                "tpr": 0,
                "avg_detection": -1,
                "median_detection": -1,
                "95_percentile_detection": -1,
                "99_percentile_detection": -1
            }
        else:
            experiment_performance[sim_info[variable_feature]] = {
                "detection_times": detection_times,
                "tpr": float(len(detection_times)) / int(sim_info["NumDrops"]),
                "avg_detection": np.mean(detection_times),
                "median_detection": np.median(detection_times),
                "95_percentile_detection": np.percentile(detection_times, 95),
                "99_percentile_detection": np.percentile(detection_times, 99)
            }

    # Pickle if there is a file to pickle too
    if output_file:
        pickle.dump(experiment_performance, open(output_file, "wb"))
    return experiment_performance

# call it precompute a system output compilation // EVAL 1


def get_stats_for_hybrid_experiment_spec(
        input_path, experiment_spec, output_file=None,
        variable_feature="SendRate"):

    # for a given set of traces, fixed system , seeds, duration, etc. We do:

    # One file for each: top_entries, fail_drop, num_top_fails.

    # For each we do: averaged TP, averaged FP, absolute FP, list of detection times, means, medians, percentiles, etc

    experiment_runs = get_specific_tests_info(input_path, experiment_spec)

    #experiment_runs = pickle.load(open("runs.pickle", "rb"))

    # common info
    sim_info = load_sim_info_file(experiment_runs[0])
    inputs_dir_base = sim_info["InDirBase"]

    experiment_performance = {}

    for run_info in experiment_runs:
        print(run_info)
        sim_info = load_sim_info_file(run_info)
        outputs_dir_base = sim_info["OutDirBase"]
        sim_out = load_simulation_out(outputs_dir_base + "_s1.json")

        # Get Detection times and a lot of info
        prefix_to_detection_time = get_prefixes_detection_times_synthetic(
            sim_out, float(sim_info["FailTime"]))

        detection_times = list(prefix_to_detection_time.values())

        _variable = sim_info[variable_feature]

        if _variable not in experiment_performance:
            if not detection_times:
                experiment_performance[sim_info[variable_feature]] = {
                    "detection_times": [],
                    "tpr": [0],
                    # "avg_detection": -1,
                    # "median_detection": -1,
                    # "95_percentile_detection": -1,
                    # "99_percentile_detection": -1
                }
            else:
                experiment_performance[sim_info[variable_feature]] = {
                    "detection_times": detection_times,
                    "tpr": [float(len(detection_times)) / int(sim_info["NumDrops"])],
                    # "avg_detection": np.mean(detection_times),
                    # "median_detection": np.median(detection_times),
                    # "95_percentile_detection": np.percentile(detection_times, 95),
                    # "99_percentile_detection": np.percentile(detection_times, 99)
                }
        else:
            if not detection_times:
                experiment_performance[sim_info[variable_feature]][
                    "detection_times"].append([])
                experiment_performance[sim_info[variable_feature]]["tpr"].append(
                    0)
            else:
                experiment_performance[sim_info[variable_feature]][
                    "detection_times"].append(detection_times)
                experiment_performance[sim_info[variable_feature]]["tpr"].append(
                    float(len(detection_times)) / int(sim_info["NumDrops"]))

    # Pickle if there is a file to pickle too
    if output_file:
        pickle.dump(experiment_performance, open(output_file, "wb"))
    return experiment_performance


# call it precompute a system output compilation // EVAL 1 heatmap attempt
def get_stats_for_heatmap(
        input_path, experiment_spec, prefix_sizes, loss_rates,
        output_file=None, send_rate_scale=1):

    experiment_performance = {}

    for send_rate, flows_per_sec in prefix_sizes:
        for loss_rate in loss_rates:

            print("Experiment: {} {} {}".format(
                send_rate, flows_per_sec, loss_rate))
            specs = experiment_spec.copy()

            rate = send_rate
            digits = ''.join(c for c in rate if c.isdigit())
            digits = int(int(digits) * send_rate_scale)
            unit = ''.join(c for c in rate if not c.isdigit())
            _rate = "{}{}".format(digits, unit)

            _specs = {
                "SendRate": _rate,
                "FlowsPerSec": str(flows_per_sec),
                "FailDropRate": ("%6.6f" % loss_rate).strip()
            }

            specs.update(_specs)
            experiment_runs = get_specific_tests_info(input_path, specs)

            sub_experiment_performance = {"avg_detection_times": [],
                                          "tpr": [], "avg_loss_rate": []}

            for run_info in experiment_runs:
                # print(run_info)
                sim_info = load_sim_info_file(run_info)
                outputs_dir_base = sim_info["OutDirBase"]
                sim_out = load_simulation_out(outputs_dir_base + "_s1.json")

                # Get Detection times and a lot of info
                prefix_to_detection_time = get_prefixes_detection_times_synthetic(
                    sim_out, float(sim_info["FailTime"]))
                detection_times = list(prefix_to_detection_time.values())

                # get loss rates
                detected_loss_rates = get_loss_rates(sim_out)

                if not detection_times:
                    # sub_experiment_performance["detection_times"].append([0])
                    sub_experiment_performance["tpr"].append(0)
                else:
                    sub_experiment_performance["avg_detection_times"].append(
                        np.mean(detection_times))

                    # to fix when this extra prefix appears
                    # I had this problem where a non failed prefix appears, this should be investigated.
                    if len(detection_times) > int(sim_info["NumDrops"]):
                        num_drops = len(detection_times)
                    else:
                        num_drops = int(sim_info["NumDrops"])
                    sub_experiment_performance["tpr"].append(
                        float(len(detection_times)) / num_drops)

                    # add loss rates
                    sub_experiment_performance["avg_loss_rate"].append(
                        np.mean(detected_loss_rates))

            # get avg of avg detection times
            if not sub_experiment_performance["avg_detection_times"]:
                # which should be plotted as terrible
                sub_experiment_performance["avg_detection_times"] = -1
            else:
                sub_experiment_performance["avg_detection_times"] = np.mean(
                    sub_experiment_performance["avg_detection_times"])

            # get avg of avg loss rates
            if not sub_experiment_performance["avg_loss_rate"]:
                sub_experiment_performance["avg_loss_rate"] = -1
            else:
                sub_experiment_performance["avg_loss_rate"] = np.mean(
                    sub_experiment_performance["avg_loss_rate"])

            sub_experiment_performance["tpr"] = np.mean(
                sub_experiment_performance["tpr"])
            print(sub_experiment_performance)

            experiment_performance[(
                (send_rate, flows_per_sec), loss_rate)] = sub_experiment_performance

    # Pickle if there is a file to pickle too
    if output_file:
        pickle.dump(experiment_performance, open(output_file, "wb"))
    return experiment_performance


def get_stats_for_caida_prefix_by_prefix_experiment(
        info_to_files, path_to_trace_inputs, trace, slice, loss_rate,
        zooming_speed, output_file):

    # base path to traces
    trace_base = "{}/{}/{}".format(path_to_trace_inputs, trace, trace)

    # load dist just to get the number of prefixes
    dist_file = trace_base + "_" + str(slice) + ".dist"
    max_prefixes = int(
        subprocess.check_output(
            "less {} | grep '#' | wc -l ".format(dist_file),
            shell=True))
    prefixes_to_explore = range(1, min(10001, max_prefixes + 1))

    experiment_performance = {}

    # Warning, this might only work with a tree of size 3.
    soft_layers = 2

    for rank in prefixes_to_explore:
        # file naming to do it faster than using `get_specific_tests_info` which
        # might be to slow when there are so many files like in these tests.
        experiment_runs = info_to_files[(zooming_speed, loss_rate, rank)]

        # all performances with extended measurements
        experiment_performance[rank] = {"fancy":
                                        {
                                            "avg_detection_times": [],
                                            "tpr": [],
                                            "avg_loss_rate": [],
                                        },
                                        "dedicated":
                                        {
                                            "avg_detection_times": [],
                                            "tpr": [],
                                            "avg_loss_rate": [],
                                        },
                                        "layer0":
                                        {
                                            "avg_detection_times": [],
                                            "tpr": [],
                                            "avg_loss_rate": [],
                                        },
                                        "layer1":
                                        {
                                            "avg_detection_times": [],
                                            "tpr": [],
                                            "avg_loss_rate": [],
                                        },
                                        }
        for run_info in experiment_runs:
            # print(run_info)
            sim_info = load_sim_info_file(run_info)
            #outputs_dir_base = sim_info["OutDirBase"]
            sim_out = load_simulation_out(
                run_info.replace(".info", "_s1.json"))

            # Get Detection times and a lot of info
            prefix_to_detection_time = get_prefixes_detection_times_synthetic(
                sim_out, float(sim_info["FailTime"]))
            detected_loss_rates = get_loss_rates(sim_out)
            detection_times = list(prefix_to_detection_time.values())

            # fix for the weird bug
            if detection_times and not detected_loss_rates:
                print(rank)
                ipdb.set_trace()
                # add it was detected but we dont add times or loss
                # hopefull not 3 will fail in the same
                # experiment_performance[rank]["fancy"]["tpr"].append(1)
                # experiment_performance[rank]["dedicated"]["tpr"].append(1)
                # experiment_performance[rank]["layer0"]["tpr"].append(1)
                # experiment_performance[rank]["layer1"]["tpr"].append(1)
                # print(rank)
                continue

            # get soft failures data
            soft_info = get_prefixes_soft_failure_info(
                sim_out, float(sim_info["FailTime"]),
                soft_layers=soft_layers)

            dedicated_soft_info, hash_tree_info = soft_info

            if not detection_times:
                experiment_performance[rank]["fancy"]["tpr"].append(0)
            else:
                experiment_performance[rank]["fancy"]["avg_detection_times"].append(
                    np.mean(detection_times))
                experiment_performance[rank]["fancy"]["tpr"].append(
                    float(len(detection_times)) / int(sim_info["NumDrops"]))
                experiment_performance[rank]["fancy"]["avg_loss_rate"].append(
                    np.mean(detected_loss_rates))

            # for debugging now
            if len(detection_times) > 1:
                print("Detected more than 1 prefix ?")
                pass

                # so far not needed lets see
                # if len(detection_times) > int(sim_info["NumDrops"]):
                #    num_drops = len(detection_times)
                # else:
                #    num_drops = int(sim_info["NumDrops"])
                #experiment_performance[rank]["fancy"]["tpr"].append(float(len(detection_times)) / num_drops)

            # add dedicated info
            if not dedicated_soft_info:
                experiment_performance[rank]["dedicated"]["tpr"].append(0)
            else:
                detection_time, _loss_rate = dedicated_soft_info
                experiment_performance[rank]["dedicated"][
                    "avg_detection_times"].append(detection_time)
                experiment_performance[rank]["dedicated"]["tpr"].append(1)
                experiment_performance[rank]["dedicated"]["avg_loss_rate"].append(
                    _loss_rate)

            # add layers info
            for layer in range(soft_layers):
                layer_info = hash_tree_info.get(layer + 1, None)
                layer_name = "layer{}".format(layer)
                if not layer_info:
                    experiment_performance[rank][layer_name]["tpr"].append(0)
                else:
                    detection_time, _loss_rate = layer_info
                    experiment_performance[rank][layer_name][
                        "avg_detection_times"].append(detection_time)
                    experiment_performance[rank][layer_name]["tpr"].append(1)
                    experiment_performance[rank][layer_name]["avg_loss_rate"].append(
                        _loss_rate)

        # aggregate for all
        for _type in ["fancy", "dedicated", "layer0", "layer1"]:

            if not experiment_performance[rank][_type]["avg_detection_times"]:
                # which should be plotted as terrible
                experiment_performance[rank][_type]["avg_detection_times"] = -1
            else:
                experiment_performance[rank][_type]["avg_detection_times"] = np.mean(
                    experiment_performance[rank][_type]["avg_detection_times"])

            # get avg of avg loss rates
            if not experiment_performance[rank][_type]["avg_loss_rate"]:
                experiment_performance[rank][_type]["avg_loss_rate"] = -1
            else:
                experiment_performance[rank][_type]["avg_loss_rate"] = np.mean(
                    experiment_performance[rank][_type]["avg_loss_rate"])

            if not experiment_performance[rank][_type]["tpr"]:
                experiment_performance[rank][_type]["tpr"] = float(0)
            else:
                experiment_performance[rank][_type]["tpr"] = np.mean(
                    experiment_performance[rank][_type]["tpr"])

    if output_file:
        pickle.dump(experiment_performance, open(output_file, "wb"))
    return experiment_performance
