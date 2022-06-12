from fancy.frequencies_and_opportunities import speeds_to_ms_decimals
from fancy.file_loader import *
import _pickle as pickle
import os.path
import multiprocessing
import random
import copy
import itertools

"""
Zooming speed
"""


def get_best_zooming_speed(
        detectable_file, prefixes_to_consider, zooming_speeds,
        max_zooming_allowed=0, window=3, threshold=50):

    if not type(max_zooming_allowed) == Decimal:
        max_zooming_allowed = Decimal(max_zooming_allowed) / 1000

    zooming_speeds = speeds_to_ms_decimals(zooming_speeds)

    # crop the list
    if max_zooming_allowed in zooming_speeds:
        zooming_speeds = zooming_speeds[: zooming_speeds.index(
            max_zooming_allowed) + 1]

    speeds_to_detectable_prefixes = load_speed_to_detectable_from_caches(
        detectable_file,
        zooming_speeds)

    if prefixes_to_consider:
        speeds_to_detectable_prefixes = get_detectable_prefixes_subset(
            speeds_to_detectable_prefixes, prefixes_to_consider)

    # explore the curve
    prefixes_lens = [len(x['weak'])
                     for x in speeds_to_detectable_prefixes.values()]

    for i, (speed, _prefixes) in enumerate(speeds_to_detectable_prefixes.items()):
        prefixes = _prefixes['weak']
        if i >= (window):

            # averaged gain
            increases = []
            for j in range(window):
                increases.append(
                    prefixes_lens[i - j] - prefixes_lens[i - (j + 1)])

            averaged_gain = sum(increases) / len(increases)
            #print(speed, increases, averaged_gain, len(prefixes))

            if averaged_gain < threshold:
                return speed

    # returns 400ms if we are here ? why not max speed directly?
    return list(speeds_to_detectable_prefixes.keys())[-1]


"""
SYSTEM PERFORMANCE COMPUTATIONS (output of functions from here will be used as input to plotting scripts)
"""


def get_list_top_prefixes(top_prefixes_file, top_num=2500):
    """
    Returns X top prefixes
    Args:
        top_prefixes_file:
        top_num:

    Returns:

    """
    top_prefixes = load_top_prefixes_dict(top_prefixes_file)

    return list(top_prefixes.keys())[:top_num]


def generate_specific_detectable_prefixes_file(
        speed_to_detectable_prefixes_file, zooming_speeds, output_file,
        restict_top=0, top_file=None):
    """
    Generates file with a list of detectable prefixes at a given speed. We can also do at all speeds (as "our detectable thing")
    Args:
        speed_to_detectable_prefixes_file:
        zooming_speeds:
        output_file:
        restict_top:
        top_file:

    Returns:

    """

    if type(zooming_speeds[0]) != Decimal:
        zooming_speeds = [Decimal(x) / Decimal(1000) for x in zooming_speeds]

    speeds_to_detectable_prefixes = load_speed_to_detectable_from_caches(
        speed_to_detectable_prefixes_file, zooming_speeds)

    if restict_top:
        top_subset = get_list_top_prefixes(top_file, restict_top)
        speed_to_detectable_prefixes = get_detectable_prefixes_subset(
            speeds_to_detectable_prefixes, top_subset)

    prefixes_intersect = get_detectable_prefixes_intersect(
        speed_to_detectable_prefixes, zooming_speeds)

    # print(list(prefixes_intersect['weak'])[0])

    with open(output_file, "w") as f:
        for prefix in prefixes_intersect['weak']:
            f.write(prefix + "\n")


def get_detectable_prefixes_intersect(speed_to_detectable_prefixes, speeds):
    """
    Returns all the prefixes that could be detected (intersection) at a set of zooming speeds)
    Args:
        speed_to_detectable_prefixes:
        speeds:

    Returns:

    """

    detectable_intersect = {'weak': set(), 'strong': set()}

    for speed, prefixes in speed_to_detectable_prefixes.items():
        if speed in speeds:
            detectable_intersect['weak'].update(prefixes['weak'])
            detectable_intersect['strong'].update(prefixes['strong'])

    return detectable_intersect


def get_detectable_prefixes_subset(detectable_prefixes, prefix_subset):
    """
    From a detectable prefixes dict we only keep a subset. For example, this can be done if we only want to look at
    the top X prefixes, thus we run this function to just keep them.
    Args:
        detectable_prefixes:
        prefix_subset:

    Returns:

    """

    new_detectable_prefixes = copy.deepcopy(detectable_prefixes)

    for k in detectable_prefixes:
        new_detectable_prefixes[k]['weak'] = set(
            new_detectable_prefixes[k]['weak']).intersection(prefix_subset)
        new_detectable_prefixes[k]['strong'] = set(
            new_detectable_prefixes[k]['strong']).intersection(prefix_subset)

    return new_detectable_prefixes


def filter_speeds_to_detectable(speed_to_detectable_prefixes, speeds):
    """

    Args:
        speed_to_detectable_prefixes:
        speeds:

    Returns:

    """

    new_speed_to_detectable_prefixes = OrderedDict()
    if set(speeds_to_ms_decimals(speeds)).intersection(
            set(speed_to_detectable_prefixes.keys())) == set(
            speeds_to_ms_decimals(speeds)):
        for speed in speeds_to_ms_decimals(speeds):
            new_speed_to_detectable_prefixes[speed] = speed_to_detectable_prefixes[speed]
    return new_speed_to_detectable_prefixes


def load_speed_to_detectable_from_caches(detectable_file, speeds):

    if os.path.isfile(detectable_file):
        speed_to_detectable_prefixes = pickle.load(open(detectable_file, "rb"))
        # if the same speeds can be found in the cached
        if speeds:
            new_speed_to_detectable_prefixes = filter_speeds_to_detectable(
                speed_to_detectable_prefixes, speeds)
        else:
            return speed_to_detectable_prefixes

    return new_speed_to_detectable_prefixes


def get_detectable_prefixes_per_speed(
        raw_zooming_opportunities, min_weak_opportunities=1,
        min_strong_opportunities=1):
    """
    Returns a list of prefixes that can be detected at each zooming speed.
    Args:
        raw_zooming_opportunities:
        min_weak_opportunities:
        min_strong_opportunities:

    Returns:

    """

    speed_to_detectable_prefixes = OrderedDict()

    for y in raw_zooming_opportunities[0]["zooming_opportunities"]:
        speed = y[0]
        speed_to_detectable_prefixes[speed] = {'weak': [], 'strong': []}

    for zooming_opportunity in raw_zooming_opportunities:
        _zooming_opportunities = zooming_opportunity["zooming_opportunities"]
        prefix = zooming_opportunity["prefix"]

        for speed, weak_op, strong_op in _zooming_opportunities:

            if weak_op >= min_weak_opportunities:
                speed_to_detectable_prefixes[speed]["weak"].append(prefix)

            if strong_op >= min_strong_opportunities:
                speed_to_detectable_prefixes[speed]["strong"].append(prefix)

    return speed_to_detectable_prefixes


def get_prefixes_accumulated_share(top_prefixes, prefixes_list):
    """
    Retuns the sum of bytes and packets of a list of prefixes from a traffic slice
    Args:
        top_prefixes_file:
        prefixes_list:

    Returns:

    """

    #top_prefixes = load_top_prefixes_dict(top_prefixes_file)
    sum_bytes = 0
    sum_packets = 0

    for prefix in prefixes_list:
        sum_bytes += top_prefixes[prefix][1]
        sum_packets += top_prefixes[prefix][2]

    return sum_bytes, sum_packets


def get_all_prefixes_from_detectable(detectable_dict):
    """
    List of all detectable prefixes, summing all the zooming speeds
    Args:
        detectable_dict:

    Returns:

    """

    detectable_weak = set()
    detectable_strong = set()
    for k, v in detectable_dict.items():
        detectable_weak.update(v['weak'])
        detectable_strong.update(v['strong'])

    return detectable_weak, detectable_strong


def get_n_combinations(l, n):
    return list(itertools.combinations(l, n))


# Need to do a small optimization here
def get_best_tree_combination(
        detectable_prefixes_dict, n, max_combinations=100000):
    """
    Get the best combination of trees, however right now this decides whats best by just
    looking at percentage of detected prefixes at a given speed and thus it does not take into account
    the zooming speed.
    Args:
        detectable_prefixes_dict:
        n:
        max_combinations:

    Returns:

    """

    random.seed(1)
    memory_limit = 5000
    compress_factor = 1000

    tree_combinations = get_n_combinations(
        list(detectable_prefixes_dict.keys()), n)

    # limit combinations
    random.shuffle(tree_combinations)
    tree_combinations = tree_combinations[:max_combinations]

    best_options = []
    for combination in tree_combinations:
        prefixes = get_detectable_prefixes_intersect(
            detectable_prefixes_dict, combination)['weak']
        best_options.append((len(prefixes), prefixes, combination))

        if len(best_options) >= memory_limit:
            best_options.sort(key=lambda x: (x[0], -sum(x[2])))
            best_options = best_options[-compress_factor:]

    best_options.sort(key=lambda x: (x[0], -sum(x[2])))

    return best_options[-1]


"""
Prefixes Share CDFs
"""


def top_prefixes_cdf(
        in_file, out_file,
        steps=[1, 5, 10, 100, 250, 500, 1000, 2000, 2500, 5000, 10000, 50000,
               100000]):
    """
    Computes the cdf of number of bytes given N top prefixes

    Args:
        in_file: top prefixes file
        out_file:
        steps:

    Returns:

    """
    top_prefixes = load_top_prefixes_list(in_file)

    # compute total bytes and packets
    total_packets = 0
    total_bytes = 0
    for prefix in top_prefixes:
        total_packets += prefix[3]
        total_bytes += prefix[2]

    max_len = len(top_prefixes)

    steps = steps.copy()

    steps.append(max_len)
    steps = sorted(steps)
    steps = steps[:steps.index(max_len) + 1]

    # this does the same more optimally (above)
    #steps2 = []
    # uses max_len prefixes to edit the step list
    # for step in steps:
    #    if step < max_len:
    #        steps2.append(step)
    #    if step > max_len:
    #        break
    # if steps2[-1] != max_len:
    #    steps2.append(max_len)
    #steps = steps2

    out = open(out_file, "w")
    header = "{:<8} {:<8} {:<8} {:<10}\n".format(
        "topN", "bytes", "pkts", "pkt_diff")
    out.write(header)
    out.write(len(header) * "-" + "\n")

    story = []

    for j, s in enumerate(steps):
        top_n_packets = 0
        top_n_bytes = 0
        for i in range(s):
            top_n_packets += top_prefixes[i][3]
            top_n_bytes += top_prefixes[i][2]

        p_bytes = float(top_n_bytes) / total_bytes
        p_packets = float(top_n_packets) / total_packets
        story.append((p_bytes, p_packets))
        if j == 0:
            p_diff = p_packets
        else:
            p_diff = p_packets - story[j - 1][1]

        out.write("{:<8} {:<8f} {:<8f} {:<10f}\n".format(
            s, p_bytes, p_packets, p_diff))


def top_prefixes_cdf_many(traces_path, traces, slices, num_processes=10):
    """
    Computes top prefixes shares
    Args:
        traces_path:
        traces:
        slices:

    Returns:

    """

    pool = multiprocessing.Pool(num_processes)
    base_path = traces_path + "{}/{}.{}"
    for trace in traces:

        # global top
        src_name = base_path.format(trace, trace, "top")
        dst_name = base_path.format(trace, trace, "cdf")
        pool.apply(top_prefixes_cdf, (src_name, dst_name), {})

        # slices
        for slice in range(slices):
            src_name = base_path.format(
                trace, trace + "_{}".format(slice), "top")
            dst_name = base_path.format(
                trace, trace + "_{}".format(slice), "cdf")
            pool.apply(top_prefixes_cdf, (src_name, dst_name), {})
