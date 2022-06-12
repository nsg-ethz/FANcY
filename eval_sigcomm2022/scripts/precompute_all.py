import os

from configuration import *
from fancy.experiment_runners.utils import merge_cmd_files, run_ns3_from_file

# Create all the experiment runs for ns3
from fancy.plots.plot_heatmaps import precompute_dedicated_counters_heatmap, precompute_zooming_heatmap
from fancy.plots.uniform_drops import precompute_uniform_drops
from fancy.plots.parse_caida_experiments import precompute_all_caida_sections, caida_compute_table
from fancy.plots.plot_comparison import precompute_comparison


# figure 5
def precompute_dedicated_eval(input_dir, output_dir_base):
    """precompute dedicated entries evaluation

    Args:
        input_dir (_type_): _description_
        output_dir (_type_): _description_
    """

    # fixed output name
    output_dir = f"{output_dir_base}/eval_dedicated_pre/"

    # plot parameters
    num_prefixes = 1
    zooming_speeds = [50]
    switch_delays = [10000]
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

    # precompute
    precompute_dedicated_counters_heatmap(
        input_dir, output_dir, num_prefixes, zooming_speeds, switch_delays, loss_rates)


# figure 6 and 7a
def precompute_zooming_1_eval(input_dir, output_dir_base):
    """precompute inputs for zooming heatmaps

    Args:
        input_dir (_type_): _description_
        output_dir (_type_): _description_
    """

    # fixed output name
    output_dir = f"{output_dir_base}/eval_zooming_1_pre/"

    # plot parameters
    num_prefixes = 1
    zooming_speeds = [10, 50, 100, 200]
    switch_delays = [10000]
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

    # precompute
    precompute_zooming_heatmap(
        input_dir, output_dir, num_prefixes, zooming_speeds, switch_delays,
        loss_rates)


# figure 7b
def precompute_zooming_100_eval(input_dir, output_dir_base):
    """precompute inputs for zooming heatmaps

    Args:
        input_dir (_type_): _description_
        output_dir (_type_): _description_
    """

    # fixed output name
    output_dir = f"{output_dir_base}/eval_zooming_100_pre/"

    # plot parameters
    num_prefixes = 100
    zooming_speeds = [200]
    switch_delays = [10000]
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

    # precompute
    precompute_zooming_heatmap(
        input_dir, output_dir, num_prefixes, zooming_speeds, switch_delays,
        loss_rates)


# uniform loss
def precompute_uniform_loss_eval(input_dir, output_dir_base):
    """_summary_

    Args:
        input_dir (_type_): _description_
        output_dir_base (_type_): _description_
    """

    # fixed output name
    output_dir = f"{output_dir_base}/eval_uniform_pre/"

    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
    zooming_speeds = [200]
    switch_delays = [10000]
    num_prefixes = [1000, 10000]

    precompute_uniform_drops(
        input_dir, output_dir, loss_rates, zooming_speeds, switch_delays,
        num_prefixes)


# table 3
def precompute_caida_eval(input_dir, input_traces_path, output_dir_base):
    """Precomputes caida ouputs and pre-generates table3

    Args:
        input_dir (_type_): input directory where all the caida experiments are
        input_traces_path (str): path to traces and inputs
        output_dir_base (_type_): precomputed outputs
    """

    # fixed output name
    output_dir = f"{output_dir_base}/eval_caida_pre/"

    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
    zooming_speed = 200
    switch_delay = 10000
    slice = 0
    traces = ['equinix-nyc.dirA.20180419',
              'equinix-chicago.dirB.20140619', 'equinix-nyc.dirB.20180816']

    print("Precompute caida eval")
    # precompute caida sections. This is a bit slow.
    precompute_all_caida_sections(
        input_dir, input_traces_path, output_dir, zooming_speed,
        switch_delay, loss_rates, slice, traces)

    print("Precompute caida table")
    # compute for the table
    caida_compute_table(
        output_dir, input_traces_path, output_dir + "/table.pickle", traces,
        switch_delay, zooming_speed, loss_rates)


# figure 11 appendix
def precompute_comparison_eval(input_dir, input_traces_path, output_dir_base):
    """Precompute eval comparison. Figure 11, appendix.

    Args:
        input_dir (_type_): _description_
        input_traces_path (_type_): _description_
        output_dir_base (_type_): _description_
    """

    # params
    # system name to parameters
    systems = {
        "3_3_205_1MB": {"NumTopEntriesSystem": '0', "TreeDepth": '3', "LayerSplit": '3', "CounterWidth": '205',
                        "TreeEnabled": '1'},
        "3_2_190_500KB": {"NumTopEntriesSystem": '0', "TreeDepth": '3', "LayerSplit": '2', "CounterWidth": '190',
                          "TreeEnabled": '1'},
        "3_3_100_500KB": {"NumTopEntriesSystem": '0', "TreeDepth": '3', "LayerSplit": '3', "CounterWidth": '100',
                          "TreeEnabled": '1'},
        "4_3_32_500KB": {"NumTopEntriesSystem": '0', "TreeDepth": '4', "LayerSplit": '3', "CounterWidth": '32',
                         "TreeEnabled": '1'},
        "3_2_100_250KB": {"NumTopEntriesSystem": '0', "TreeDepth": '3', "LayerSplit": '2', "CounterWidth": '100',
                          "TreeEnabled": '1'},
        "4_2_44_250KB": {"NumTopEntriesSystem": '0', "TreeDepth": '4', "LayerSplit": '2', "CounterWidth": '44',
                         "TreeEnabled": '1'},
        "3_1_110_125KB": {"NumTopEntriesSystem": '0', "TreeDepth": '3', "LayerSplit": '1', "CounterWidth": '110',
                          "TreeEnabled": '1'},
        "4_2_28_125KB": {"NumTopEntriesSystem": '0', "TreeDepth": '4', "LayerSplit": '2', "CounterWidth": '28',
                         "TreeEnabled": '1'}
    }

    traces = ['equinix-nyc.dirB.20190117']
    num_top_entries_traffic = [1000000]
    number_of_failures = [10, 50]

    # fixed output name
    output_dir = f"{output_dir_base}/eval_comparison_pre/"

    precompute_comparison(
        input_dir, output_dir, systems, num_top_entries_traffic,
        number_of_failures, input_traces_path, traces)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--cpus', help="Number of cpus to use",
        type=int, required=False, default=64)
    parser.add_argument(
        '--input_dir', help="Path to inputs",
        type=str, required=False, default=EXPERIMENT_OUTPUTS)
    parser.add_argument(
        '--data_inputs', help="Path to inputs",
        type=str, required=False, default=DATA_INPUTS_PATH)
    parser.add_argument(
        '--output_dir', help="Path to experiment's outputs",
        type=str, required=False, default=PRECOMPUTED_OUTPUTS)
    parser.add_argument(
        '--run_type', help="Type of run. Options:  {ALL, FAST}",
        type=str, required=False, default="ALL")
    args = parser.parse_args()

    # creates cmds directory
    if not os.path.isdir(args.output_dir):
        os.system("mkdir -p {}".format(args.output_dir))

    print("""
Precomputing all simulation outputs....
=======================================

Simulation outputs: {}
Precompute outputs: {}""".format(args.input_dir, args.output_dir))

    # parses all the simulation data and precomputes it for plotting
    precompute_dedicated_eval(
        args.input_dir + "/eval_dedicated/", args.output_dir)

    precompute_zooming_1_eval(
        args.input_dir + "/eval_zooming_1/", args.output_dir)

    precompute_zooming_100_eval(
        args.input_dir + "/eval_zooming_100/", args.output_dir)

    precompute_uniform_loss_eval(
        args.input_dir + "/eval_uniform/", args.output_dir)

    precompute_caida_eval(args.input_dir + "/eval_caida/",
                          args.data_inputs, args.output_dir)

    precompute_comparison_eval(
        args.input_dir + "/eval_comparison/", args.data_inputs, args.output_dir)
