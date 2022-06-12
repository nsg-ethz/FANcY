import os
import copy

from configuration import *
from fancy.experiment_runners.utils import merge_cmd_files, run_ns3_from_file

# Create all the experiment runs for ns3
from fancy.experiment_runners.eval_dedicated import generate_ns3_runs as generate_ns3_runs_dedicated
from fancy.experiment_runners.eval_zooming import generate_ns3_runs as generate_ns3_runs_zooming
from fancy.experiment_runners.eval_uniform import generate_ns3_runs as generate_ns3_runs_uniform
from fancy.experiment_runners.eval_caida import generate_ns3_runs as generate_ns3_runs_caida
from fancy.experiment_runners.eval_comparison import generate_ns3_runs as generate_ns3_runs_camparison

# speedup types and runtime with 64 cores
# ALL -> ~1 week
# SEMI -> ~3.5 days
# FAST -> ~1.5 days (33h)


# figure 5
def generate_cmds_eval_dedicated(cmds_file, runs_output_dir):

    # get variables
    from fancy.experiment_runners.sigcomm2022.eval_dedicated import variable_parameters_dedicated_all
    from fancy.experiment_runners.sigcomm2022.eval_dedicated import fixed_parameters

    # there is no speed up here, this is fast enough
    generate_ns3_runs_dedicated(
        cmds_file, runs_output_dir, fixed_parameters,
        variable_parameters_dedicated_all)


# figure 6 and 7a
def generate_cmds_eval_zooming_1(cmds_file, runs_output_dir):

    # get variables
    from fancy.experiment_runners.sigcomm2022.eval_zooming import fixed_parameters
    from fancy.experiment_runners.sigcomm2022.eval_zooming import variable_parameters_zooming_1_all

    generate_ns3_runs_zooming(cmds_file, runs_output_dir, fixed_parameters,
                              variable_parameters_zooming_1_all)


# figure 7b
def generate_cmds_eval_zooming_100(cmds_file, runs_output_dir, speed_up="ALL"):

    # get variables
    from fancy.experiment_runners.sigcomm2022.eval_zooming import fixed_parameters
    from fancy.experiment_runners.sigcomm2022.eval_zooming import variable_parameters_zooming_100_all
    from fancy.experiment_runners.sigcomm2022.eval_zooming import variable_parameters_zooming_100_fast

    # default all
    variable_parameters_zooming_100 = copy.deepcopy(
        variable_parameters_zooming_100_all)
    if speed_up == "ALL":
        variable_parameters_zooming_100 = copy.deepcopy(
            variable_parameters_zooming_100_all)
    elif speed_up == "FAST":
        variable_parameters_zooming_100 = copy.deepcopy(
            variable_parameters_zooming_100_fast)

    generate_ns3_runs_zooming(cmds_file, runs_output_dir, fixed_parameters,
                              variable_parameters_zooming_100)


# uniform table
def generate_cmds_eval_uniform(cmds_file, runs_output_dir):

    # get variables
    from fancy.experiment_runners.sigcomm2022.eval_uniform import variable_parameters_uniform_all
    from fancy.experiment_runners.sigcomm2022.eval_uniform import fixed_parameters

    # there is no speed up here, this is fast enough
    generate_ns3_runs_uniform(
        cmds_file, runs_output_dir, fixed_parameters,
        variable_parameters_uniform_all)


# table 3 and baselines
def generate_cmds_eval_caida(
        cmds_file, runs_output_dir, input_traces_path, speed_up="ALL"):

    # get variables
    from fancy.experiment_runners.sigcomm2022.eval_caida import variable_parameters_caida_all, variable_parameters_caida_fast
    from fancy.experiment_runners.sigcomm2022.eval_caida import fixed_parameters

    variable_parameters_caida = copy.deepcopy(
        variable_parameters_caida_all)
    if speed_up == "ALL":
        variable_parameters_caida = copy.deepcopy(
            variable_parameters_caida_all)
    elif speed_up == "FAST":
        variable_parameters_caida = copy.deepcopy(
            variable_parameters_caida_fast)

    generate_ns3_runs_caida(
        cmds_file, runs_output_dir, fixed_parameters,
        variable_parameters_caida, input_traces_path)


# figure 11
def generate_cmds_eval_comparison(
        cmds_file, runs_output_dir, input_traces_path, computed_parameters,
        speed_up="ALL"):

    from fancy.experiment_runners.sigcomm2022.eval_comparison import fixed_parameters
    from fancy.experiment_runners.sigcomm2022.eval_comparison import variable_parameters_comparison_all, variable_parameters_comparison_fast

    variable_parameters_comparison = copy.deepcopy(
        variable_parameters_comparison_all)
    if speed_up == "ALL":
        variable_parameters_comparison = copy.deepcopy(
            variable_parameters_comparison_all)
    elif speed_up == "FAST":
        variable_parameters_comparison = copy.deepcopy(
            variable_parameters_comparison_fast)

    generate_ns3_runs_camparison(
        cmds_file, runs_output_dir, fixed_parameters,
        variable_parameters_comparison, input_traces_path, computed_parameters)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--ns3_path', help="Path to the ns3 simulator source code",
        type=str, required=False, default=NS3_PATH)
    parser.add_argument(
        '--cpus', help="Number of cpus to use",
        type=int, required=False, default=64)
    parser.add_argument(
        '--cmds_dir', help="Path to experiment cmds",
        type=str, required=False, default="./cmds")
    parser.add_argument(
        '--input_dir', help="Path to inputs",
        type=str, required=False, default=DATA_INPUTS_PATH)
    parser.add_argument(
        '--output_dir', help="Path to experiment's outputs",
        type=str, required=False, default=EXPERIMENT_OUTPUTS)
    parser.add_argument(
        '--run_type', help="Type of run. Options:  {ALL, FAST}",
        type=str, required=False, default="ALL")
    args = parser.parse_args()

    # creates cmds directory
    if not os.path.isdir(args.cmds_dir):
        os.system("mkdir -p {}".format(args.cmds_dir))

    # creates cmds directory
    if not os.path.isdir(args.output_dir):
        os.system("mkdir -p {}".format(args.output_dir))

    print("""
Generating ns3 commands...
==========================

Commands directory: {}
Experiments inputs: {}
Experiments outputs: {}""".format(args.cmds_dir, args.input_dir, args.output_dir))

    # generates all the experiments commands.
    generate_cmds_eval_dedicated(
        f"{args.cmds_dir}/eval_dedicated.txt", args.output_dir +
        "/eval_dedicated/")
    generate_cmds_eval_zooming_1(
        f"{args.cmds_dir}/eval_zooming_1.txt", args.output_dir +
        "/eval_zooming_1/")
    generate_cmds_eval_zooming_100(
        f"{args.cmds_dir}/eval_zooming_100.txt", args.output_dir +
        "/eval_zooming_100/", args.run_type)

    generate_cmds_eval_uniform(
        f"{args.cmds_dir}/eval_uniform.txt", args.output_dir + "/eval_uniform/")

    generate_cmds_eval_caida(
        f"{args.cmds_dir}/eval_caida.txt", args.output_dir + "/eval_caida/",
        args.input_dir, args.run_type)

    generate_cmds_eval_comparison(
        f"{args.cmds_dir}/eval_comparison.txt", args.output_dir +
        "/eval_comparison/", args.input_dir, args.input_dir + "/zooming_info/",
        args.run_type)

    print("All commands have been generated!")

    # Running experiments
    # Merge all commands into 1 file so we can run it all at the same time
    cmds_files = [
        f"{args.cmds_dir}/eval_dedicated.txt",
        f"{args.cmds_dir}/eval_zooming_1.txt",
        f"{args.cmds_dir}/eval_zooming_100.txt",
        f"{args.cmds_dir}/eval_uniform.txt",
        f"{args.cmds_dir}/eval_caida.txt",
        f"{args.cmds_dir}/eval_comparison.txt"
    ]

    # merge
    all_cmds = f"{args.cmds_dir}/all_cmds.txt"
    print("Merging commands into {}".format(all_cmds))
    merge_cmd_files(cmds_files, all_cmds)

    # run all
    print("Running ns3 simulations")
    run_ns3_from_file(args.ns3_path, int(args.cpus), all_cmds)
