from collections import OrderedDict
from decimal import Decimal
from deprecated import deprecated

import json
import struct
import pickle

"""
Output Loaders 
"""

def load_sim_info_file(info_file):

    """
    Loads the simulation info file and builds
    a dictionary. This file has all the information
    about a given run
    Args:
        info_file:

    Returns:

    """

    sim_info = OrderedDict()
    with open(info_file, "r") as f:
        for line in f:
            field, value = line.strip().split("=")
            sim_info[field] = value

    return sim_info


def save_sim_info_file(info, info_file):

    """
    Saves a run info into a file
    Args:
        info:
        info_file:

    Returns:

    """
    with open(info_file, "w") as f:
        for parameter, value in info.items():
            f.write("{}={}\n".format(parameter, value))


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
            i +=1

    return top_prefixes


# to fix something i did
def fix_infos():
    import glob
    infos = glob.glob("*.info")
    for f in infos:
        d = load_sim_info_file(f)
        if "resubmission" not in d["OutDirBase"]:
            d["OutDirBase"] = d["OutDirBase"].replace("fancy_outputs/", "fancy_outputs/resubmission/")
    save_sim_info_file(d, f)


def load_prefixes_file(prefixes_file):

    """
    Load a file with flat prefixes
    Args:
        prefixes_file:

    Returns:

    """

    prefixes = []
    with open(prefixes_file, "r") as f:
        for line in f:
            prefixes.append(line.strip())

    return prefixes

def load_zooming_speed(zooming_speed_file):

    """
    Loads the best zooming speed
    Args:
        zooming_speed_file:

    Returns:

    """

    with open(zooming_speed_file, "r") as f:
        speed =  float(f.read().strip())

    return speed

def load_trace_ts(trace_ts):
    """
    Gets the first and last ts from a given trace. Start/end ts files
    only exist for processed pcaps.
    Args:
        trace_ts:

    Returns:

    """
    lines = open(trace_ts, "r").readlines()
    return Decimal(lines[0]), Decimal(lines[1])


def load_simulation_out(sim_out):
    """
    Loads the output of a simulation run. This is basically
    a json-formatted dictionary
    Args:
        sim_out:

    Returns:

    """
    with open(sim_out, "r") as f:
        sim = json.load(f)


    for k,v in sim.items():
        if v == None:
            sim[k] = []

    return sim


def load_failed_prefixes(failed_file):
    """
    Loads list of prefixes that failed. Failed prefixes files have 2 columns.
    One with the prefix and one with the type. That means if they are a top, or non
    top prefix. This info might lose its meaning at some point.
    Args:
        failed_file:

    Returns:

    """
    failed_prefixes = OrderedDict()
    with open(failed_file, "r") as f:
        for line in f:
            prefix, type = line.split()
            failed_prefixes[prefix] = type

    return failed_prefixes


def load_prefixes_ts_raw(in_file):

    _in_file = open(in_file, "rb")
    prefixes_ts = {}

    prefix_len = struct.unpack("I", _in_file.read(4))[0]
    for _ in range(prefix_len):
        prefix = struct.unpack("BBBB", _in_file.read(4))
        prefix = '{0:d}.{1:d}.{2:d}.0'.format(prefix[0],
                                              prefix[1],
                                              prefix[2],
                                              prefix[3])

        ts_len = struct.unpack("I", _in_file.read(4))[0]
        prefixes_ts[prefix] = [(Decimal(struct.unpack("Q", _in_file.read(8))[0])/1000000000) for _ in range(ts_len)]
        #prefixes_ts[prefix] = [(int(struct.unpack("Q", _in_file.read(8))[0])) for _ in range(ts_len)]

    return prefixes_ts


@deprecated(reason="Deprecated in favour of load_prefixes_ts_raw, "
                   "which is more efficient but assumes data to be stored in binary format")
def load_prefixes_ts(prefixes_ts):
    """
    Loads a pickle file with a dicitonary prefix: [ts...]
    Args:
        prefixes_ts:

    Returns:

    """
    with open(prefixes_ts, "rb") as f:
        ts = pickle.load(f)

    return ts


@deprecated(reason="load_top_prefixes uses an Ordered dict that can do this already")
def load_top_prefixes_list(top_file):
    """
    Loads the top prefixes and stores them in a list.
    Args:
        top_file:

    Returns:

    """
    top_prefixes = []
    with open(top_file, "r") as f:
        i = 0
        for line in f:
            prefix, bytes, packets = line.split()
            top_prefixes.append((prefix, i, int(bytes), int(packets)))
            i +=1

    return top_prefixes