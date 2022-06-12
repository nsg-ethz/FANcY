import itertools
import multiprocessing
import os
import subprocess
import time
import fcntl
import glob

from fancy.utils import call_in_path, run_cmd

# this has to be a parameter
START_SIM_INDEX = 10000


def build_ns3(sim_path):
    """Builds ns3. We always run it before every experiment.

    Args:
        sim_path (str): path to ns3 simulator
    """
    call_in_path("./waf build", sim_path)


def run_ns3_simulation(path, cmd, num, finished_file):
    """Runs one ns3 simulation. And saves command in finished file. With that we
    can check what has finished or not. 

    Args:
        path(str): path to simulator.
        cmd(str): ns3 command.
        num(int): Simulation number `num`. Useful to know how advanced you are.
        finished_file(str): file where the finished command is saved.
    """

    print("Start Test {}".format(num))
    print(cmd)

    # runs cmd
    call_in_path(cmd, path)

    # atomic saving that this finished
    print("Finish Test {}".format(num))
    print(cmd)

    # atomic write to file to to indicate that its finished
    with open(finished_file, "a") as g:
        fcntl.flock(g, fcntl.LOCK_EX)
        g.write(cmd + "\n")
        fcntl.flock(g, fcntl.LOCK_UN)


def dict_product(d):
    """
    Intersects all the values of a dictionary keeping the keys
    d = {
        "A": [0, 1, 2],
        "B": [3, 4]
        }
    runs = [
        {"A": [0], "B": [3]},
        {"A": [0], "B": [4]},
        {"A": [1], "B": [3]},
        {"A": [1], "B": [4]},
        {"A": [2], "B": [3]},
        {"A": [2], "B": [4]},
    ]
    Args:
        d: settings dictionary

    Returns:

    """

    runs = []
    keys = d.keys()
    for element in itertools.product(*d.values()):
        runs.append(dict(zip(keys, element)))
    return runs


def run_ns3_from_file(path_to_ns3, cores, run_file):

    # load file
    cmds = [x.strip() for x in open(run_file, "r").readlines()]

    print("NS3 path: {}".format(path_to_ns3))
    print("Num cpus: {}".format(cores))
    print("Cmds file: {}".format(run_file))
    print("Number of cmds: {}".format(len(cmds)))

    pool = multiprocessing.Pool(cores)

    build_ns3(path_to_ns3)
    print("The build is done!")

    now = time.time()

    finished_runs = run_file.replace(".txt", "") + "_finished.txt"

    os.system("rm {}".format(finished_runs))

    print("will run {} ns3 simulations".format(len(cmds)))
    for num, cmd in enumerate(cmds):
        pool.apply_async(run_ns3_simulation,
                         (path_to_ns3, cmd, num, finished_runs), {})
    pool.close()
    pool.join()

    print("Total running time was {} seconds".format(time.time() - now))


def merge_cmd_files(file_list, out_file):
    """_summary_

    Args:
        file_list (_type_): _description_
        out_file (_type_): _description_

    Returns:
        _type_: _description_
    """

    files_list = " ".join(file_list)
    cmd = "cat {} > {}".format(files_list, out_file)
    # merge files
    run_cmd(cmd)

# file that explores .infos or something like that?


def find_not_ran_simulations(cmds_file, out_path):

    # load file
    cmds = [x.strip() for x in open(cmds_file, "r").readlines()]
    not_run = []

    for cmd in cmds:
        fingerprint = cmd.split("OutDirBase=")[-1].split("/")[-1][:-1]

        try:
            out = subprocess.check_output(
                "ls {}/{}*".format(out_path, fingerprint),
                shell=True).split()
        except subprocess.CalledProcessError:
            out = []

        if len(out) != 3:
            not_run.append(cmd)

    # save
    with open(cmds_file + ".diff", "w") as f:
        for cmd in not_run:
            f.write(cmd + "\n")

    return not_run


def find_not_ran_simulations_fast(cmds_file, out_path):

    # load file
    cmds = [x.strip() for x in open(cmds_file, "r").readlines()]
    not_run = []

    finished_runs = glob.glob(out_path + "/" + "*json")

    finished_runs = [x.split("/")[-1].split("_s1.json")[0]
                     for x in finished_runs]

    finished_runs = set(finished_runs)

    for cmd in cmds:
        fingerprint = cmd.split("OutDirBase=")[-1].split("/")[-1][:-1]

        if fingerprint not in finished_runs:
            not_run.append(cmd)

    # save
    with open(cmds_file + ".diff", "w") as f:
        for cmd in not_run:
            f.write(cmd + "\n")

    return not_run
