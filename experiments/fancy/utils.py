import os
import random
import subprocess
import time
from collections import namedtuple
from contextlib import contextmanager
import psutil
import glob

import ipaddr
import ipaddress
import math

from fancy.logger import log

import sys
from collections import OrderedDict
from threading import Thread

"""
Dictionary that limits size
"""

from fancy.file_loader import load_sim_info_file


def get_experiment_runtime(experiment_dir):
    """Sums the runtimes for all experiments in a directory

    Args:
        experiment_dir (str): path to experiments
    """

    experiments_info = glob.glob(experiment_dir + "/" + "*info")
    total_run_time = 0
    for experiment in experiments_info:
        info = load_sim_info_file(experiment)
        runtime = float(info["RealSimulationTime"])
        total_run_time += runtime

    return total_run_time


def get_expected_runtime(experiment_dir, number_cpus):
    """Returns the approximate time to run an 
       experiment with one cpu and X cpus

    Args:
        experiment_dir (str): path to experiments
        number_cpus (int): number of cpus
    """

    runtime = get_experiment_runtime(experiment_dir)
    print("Time to run experiments with 1 CPU: {} minutes".format(runtime / 60))
    print("Time to run experiments with {} CPU: {} minutes".format(
        number_cpus, runtime / (60 * number_cpus)))


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class KThread(Thread):
    """A subclass of threading.Thread, with a kill()
  method."""

    def __init__(self, *args, **keywords):
        Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the
    trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


import multiprocessing.pool


class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)

# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.


class NoDaemonPool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess


"""
util functions
"""


def merge_pcaps(global_dir, output_file):
    """
    Merges all the pcap from a given directory and saves them at output_file
    Args:
        burst_dir: Directory where we can find all the pcap files
        output_file: Output pcap file name

    Returns: None

    """
    cmd_base = "mergecap -F libpcap -w %s " % (output_file) + " %s"

    with cwd(global_dir):
        print(os.getcwd())
        out = subprocess.check_output(
            "find . -type f -name '*pcap'", shell=True)
        out = out.replace("\n", " ")
        cmd = cmd_base % out
        subprocess.call(cmd, shell=True)


def merge_context_files(burst_dir):
    """
    Merges all the context files from a sub_test directories in a burst
    Args:
        burst_dir: burst path
    Returns: None

    """
    sub_dir_base = "cat sub_test_*/%s > %s"
    files_to_merge = ["failed_prefixes.txt", "prefixes_real.txt",
                      "prefixes_to_loss.txt", "prefixes_to_out_of_order.txt"]

    with cwd(burst_dir):
        for f in files_to_merge:
            try:
                subprocess.call(sub_dir_base % (f, f), shell=True)
            except Exception as e:
                print(e)
                print("Failed merging %s" % f)


def find_files_in_dir(dir, regex=".*pcap"):
    """

    Args:
        dir:
        pattern:

    Returns:

    """
    with cwd(dir):
        out = subprocess.check_output(
            'find "$PWD" -type f -regex "%s"' % regex, shell=True).split("\n")
        out = [x.strip() for x in out if x]
    return out


def weighted_choice(*args):

    choices = args  # [("e",weight_e),('m',weight_m)]

    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w

    assert False, "Shouldn't get here"


def call_in_path(cmd, path, quiet=True):
    with cwd(path):
        if not quiet:
            print(cmd, path)
            return
        subprocess.run(cmd, shell=True)


def call_in_path_out(cmd, path, outfile, quiet=True):
    with cwd(path):
        if not quiet:
            print(cmd, path)
            return
        with open(outfile, "w") as f:
            subprocess.run(cmd, shell=True, stdout=f, stderr=f)


"""
Command execution support
"""


def run_cmd(cmd):
    log.debug(cmd)
    subprocess.call(cmd, shell=True)


def run_check(cmd):
    log.debug(cmd)
    return subprocess.check_output(cmd, shell=True)


@contextmanager
def cwd(path):
    """
    Conext that changes current path for some piece of code and returns to the previous
    path once the we leave the context.
    Args:
        path: path to switch to

    Returns:

    """
    oldpwd = os.getcwd()
    os.chdir(os.path.expanduser(path))
    try:
        yield
    finally:
        os.chdir(oldpwd)


"""
Decorators
"""


def time_profiler(function):
    def wrapper(*args, **kwargs):
        now = time.time()
        r = function(*args, **kwargs)
        print("Function {0} was executed in {1} seconds".format(
            function.__name__, time.time() - now))
        return r
    return wrapper


"""
ip handling
"""


def ipv6_to_ipv4(ipv6):

    hashed = hash(ipv6) & 0xfffffff
    ip = ipaddr.IPv4Address(hashed)
    return ip.compressed


def ipv4_prefix(ip, prefix_len=24):
    ip_net = ipaddr.IPv4Network(ip + "/" + str(prefix_len))
    return ip_net.network.compressed


def from_prefix_to_mask(cidr):
    """
    Converts from prefix length to mask version x.x.x.x. I.e 24 -> 255.255.255.0
    Args:
        cidr: Prefix length

    Returns:

    """
    cidr = int(cidr)
    mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
    return (str((0xff000000 & mask) >> 24) + '.' +
            str((0x00ff0000 & mask) >> 16) + '.' +
            str((0x0000ff00 & mask) >> 8) + '.' +
            str((0x000000ff & mask)))


class IterIPv4Network(ipaddress.IPv4Network):

    def __init__(self, addr, *args, **kwargs):
        super(IterIPv4Network, self).__init__(addr, *args, **kwargs)

    def __add__(self, offset):
        """Add numeric offset to the IP."""
        new_base_addr = int(self.network_address) + (offset * self.size())
        return self.__class__((new_base_addr, str(self.netmask)))

    def size(self):
        """Return network size."""
        start = int(self.network_address)
        return int(self.broadcast_address) + 1 - start


def generate_prefix_pool(prefix_base):
    import itertools as it
    base = IterIPv4Network(prefix_base)
    for i in it.count():
        try:
            yield (base + (i + 1)).compressed
        except ipaddress.AddressValueError:
            return


"""
input files loaders: single link simulations
"""


def load_prefixes_rtts(flows_per_prefix_file, rtt_position=3):
    log.debug(__name__)

    rtt_per_prefix = {}
    with open(flows_per_prefix_file, "r") as flows_file:
        for line in flows_file:

            # remove blank lines
            if not line.strip():
                continue

            # finds prefixes
            if line.startswith("#"):
                line = line.strip().strip("#").strip()
                rtt_per_prefix[line] = []
                current_prefix = line

            else:
                rtt = float(line.strip().split()[rtt_position])
                rtt_per_prefix[current_prefix].append(rtt)

    return rtt_per_prefix


def load_flows_per_prefix(flows_per_prefix_file):
    log.debug(__name__)

    flows_per_prefix = {}
    with open(flows_per_prefix_file, "r") as flows_file:
        for line in flows_file:
            # remove blank lines
            if not line.strip():
                continue

            # finds prefixes
            if line.startswith("#"):
                line = line.strip().strip("#").strip()
                flows_per_prefix[line] = []
                current_prefix = line

            else:
                flow = line.strip().split()
                flows_per_prefix[current_prefix].append(flow)

    return flows_per_prefix


def load_prefix_stats(prefix_stats_file, header=["nflows", "nbytes"]):
    log.debug(__name__)

    prefixes_stats = {}
    total_nbytes = 0
    total_nflows = 0
    header = namedtuple('prefix_data', header)
    with open(prefix_stats_file, "r") as f:
        for line in f:
            line = line.strip().split()
            prefix = line[0]
            values = [int(x) for x in line[1:]]
            prefix_stats = header(*values)._asdict()
            total_nbytes += prefix_stats['nbytes']
            total_nflows += prefix_stats['nflows']
            prefixes_stats[prefix] = prefix_stats

    return prefixes_stats, total_nbytes, total_nflows


def check_memory():
    """

    Returns: returns memory used by this process

    """
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1000000000


def fix_out_dir_base_path(src_string, dst_string):

    info_files = glob.glob("*.info")

    for _file in info_files:
        f = open(_file, "r")
        content = f.read()
        f.close()

        content = content.replace(src_string, dst_string)

        f = open(_file, "w")
        f.write(content)
        f.close()


def crop_pdf(file_name, dst="."):
    """Crops a pdf, using pdfcrop. Thus it must be installed.
    To install: 
    sudo apt update
    sudo apt install texlive-extra-utils

    The output cropped file has -crop added to the original name.

    Args:
        file_name (str): input figure to crop
        dst (str):  output path where to save it
    """
    # crop
    os.system("pdfcrop {}".format(file_name))
    # send to paper figures
    crop_name = file_name.replace(".pdf", "-crop.pdf")
    os.system("cp {} {}".format(crop_name, dst))


def crop_pdfs(path_to_pdfs):
    """Crops all the pdfs in the directory

    Args:
        path_to_figures (_type_): _description_
    """

    pdfs = glob.glob(f"{path_to_pdfs}/*pdf")
    for pdf in pdfs:
        # crops the pdf
        crop_pdf(pdf)


######
# Misc
######


class StatsCDF():

    @staticmethod
    def takes_spread_elements(sequence, num, extra=10):
        """

        Args:
            sequence:
            num:
            extra:

        Returns:

        """

        length = float(len(sequence))

        extra_sequence1 = sequence[0:int(math.ceil(1 * length / num))]
        extra_sequence2 = sequence[int(math.ceil(
            (num - 1) * length / num)) + 1:int(math.ceil(num * length / num))]

        for i in range(0, extra):
            yield extra_sequence1[int(math.ceil(i * len(extra_sequence1) / extra))]

        length -= (len(extra_sequence1) + len(extra_sequence2))
        for i in range(1, int(num)):
            yield sequence[int(math.ceil(i * length / num))]

        for i in range(0, extra):
            yield extra_sequence2[int(math.ceil(i * len(extra_sequence2) / extra))]

        # add last element
        yield extra_sequence2[-1]

    def get_cdf_points(self, column, num_points_in_cdf, extra=10):
        """

        Args:
            column:
            num_points_in_cdf:
            extra:

        Returns:

        """

        try:
            data = getattr(self, column)
        except AttributeError:
            log.error('Attribute %s does not exist' % (column))
            return

        if num_points_in_cdf > len(data):
            log.error("Not enough data to process that")
            return

        data = sorted(data)
        return self.takes_spread_elements(data, num_points_in_cdf, extra)

    @staticmethod
    def save_compressed_cdf(filename, compressed_cdf):
        """

        Args:
            filename:
            compressed_cdf:

        Returns:

        """

        with open(filename, "w") as f:
            for element in compressed_cdf:
                f.write("%s\n" % element)
