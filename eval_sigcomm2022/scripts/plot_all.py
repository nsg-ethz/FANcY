"""
Given an input directory and an output one, this script plots everything.
"""
import os
import glob
# import needed constants
from configuration import PLOT_OUTPUTS, PRECOMPUTED_OUTPUTS


# plotter imports
from fancy.plots.plot_netseer import plot_netseer_memory_requirements
from fancy.plots.plot_heatmaps import plot_heatmap, get_prefix_sizes_dedicated_counters, get_prefix_sizes_zooming
from fancy.plots.min_tpr_plot import plot_min_tpr_line
from fancy.plots.uniform_drops import print_uniform_random_drops_table
from fancy.plots.parse_caida_experiments import print_caida_table, print_caida_table_reduced
from fancy.plots.plot_comparison import plot_comparison
from fancy.plots.plot_tofino import plot_tofino_dedicated_zooming

# Plotting calls
# Table 2
# Possible info of how to get it?
# Problem is, it is based on some speed experiments I did on the tofino using the C API.


def figure2(output_file):
    """Plots the net seer memory needed plot. Data is computed on the fly, thus
    input not required.

    Args:
        src_path(_type_): _description_
        output_file(_type_): _description_
    """
    print("Plotting figure2 at {}".format(output_file))

    switch_descriptions = {
        "tofino1": (64, 100, 36),
        "tofino2": (64, 200, 60),
        "tofino3": (64, 400, 96)
    }

    # plots
    plot_netseer_memory_requirements(
        output_file, switch_descriptions, 1024, 13)


def figure5(inputs_path, output_file):
    """

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """
    print("Plotting figure5 at {}".format(output_file))

    # specific parameters for figure 5
    zooming_speed = 50
    switch_delay = 10000
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
    input_file = f"{inputs_path}/eval_dedicated_pre/fancy_dedicated_{zooming_speed}_{switch_delay}.pickle"

    # checks if input folder exists
    if not os.path.isdir(f"{inputs_path}/eval_dedicated_pre/"):
        print("Not plotting: Missing folder " +
              f"{inputs_path}/eval_dedicated_pre/")
        return

    prefix_sizes = get_prefix_sizes_dedicated_counters()
    plot_heatmap(prefix_sizes, loss_rates, input_file, output_file,
                 1, y_label=True, bw_label=True)


def figure6(inputs_path, output_file):
    """

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """
    print("Plotting figure6 at {}".format(output_file))

    # params
    min_tpr = 0.95
    switch_delay = 10000
    zooming_speeds = [10, 50, 100, 200]
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

    burst_size = 1
    input_dir = f"{inputs_path}/eval_zooming_{burst_size}_pre/"

    # checks if input folder exists
    if not os.path.isdir(input_dir):
        print("Not plotting: Missing folder " + input_dir)
        return

    # plot
    plot_min_tpr_line(input_dir, output_file, min_tpr=min_tpr,
                      burst_size=burst_size, zooming_speeds=zooming_speeds,
                      loss_rates=loss_rates, switch_delay=switch_delay)


def figure7a(inputs_path, output_file):
    """_summary_

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """

    print("Plotting figure7a at {}".format(output_file))

    # specific parameters for figure 7a
    zooming_speed = 200
    switch_delay = 10000
    input_file = f"{inputs_path}/eval_zooming_1_pre/fancy_zooming_{zooming_speed}_{switch_delay}.pickle"

    # checks if input folder exists
    if not os.path.isdir(f"{inputs_path}/eval_zooming_1_pre/"):
        print("Not plotting: Missing folder " +
              f"{inputs_path}/eval_zooming_1_pre/")
        return

    prefix_sizes = get_prefix_sizes_zooming()
    num_prefixes = 1
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
    plot_heatmap(prefix_sizes, loss_rates, input_file, output_file,
                 num_prefixes, y_label=True, bw_label=True)


def figure7b(inputs_path, output_file):
    """_summary_

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """

    print("Plotting figure7b at {}".format(output_file))

    # specific parameters for figure 7b
    zooming_speed = 200
    switch_delay = 10000
    input_file = f"{inputs_path}/eval_zooming_100_pre/fancy_zooming_{zooming_speed}_{switch_delay}.pickle"
    # checks if input folder exists
    if not os.path.isdir(f"{inputs_path}/eval_zooming_100_pre/"):
        print("Not plotting: Missing folder " +
              f"{inputs_path}/eval_zooming_100_pre/")
        return

    prefix_sizes = get_prefix_sizes_zooming()
    num_prefixes = 100
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
    plot_heatmap(prefix_sizes, loss_rates, input_file, output_file,
                 num_prefixes, y_label=False, bw_label=True)


def uniform_loss(inputs_path, output_file):
    """Prints and saves the unifom random loss table

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """
    print("Plotting uniform random drops table at {}".format(output_file))

    # prints and saves the table
    input_file = f"{inputs_path}/eval_uniform_pre/fancy_uniform.pickle"

    # checks if input folder exists
    if not os.path.isdir(f"{inputs_path}/eval_uniform_pre/"):
        print("Not plotting: Missing folder " +
              f"{inputs_path}/eval_uniform_pre/")
        return

    print_uniform_random_drops_table(input_file, output_file)


def table3(inputs_path, output_file):
    """Prints and saves table 3 full and reduced versions

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """

    print("Printing and saving table3 {}".format(output_file))

    input_file = f"{inputs_path}/eval_caida_pre/table.pickle"

    # checks if input folder exists
    if not os.path.isdir(f"{inputs_path}/eval_caida_pre/"):
        print("Not plotting: Missing folder " +
              f"{inputs_path}/eval_caida_pre/")
        return

    output_file_1 = output_file + ".txt"
    print_caida_table(input_file, output_file_1)

    output_file_2 = output_file + "_reduced.txt"
    print_caida_table_reduced(input_file, output_file_2)


# tofino figure
def figure8(inputs_path, output_file):
    """Plots figure 8 (tofino case study)

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """

    print("Plotting figure 8 at {}".format(output_file))

    bw = 50000
    ips_setup = [("11.0.2.2", 31000)]
    loss_rates = [1, 0.1, 0.01]

    input_dir = f"{inputs_path}/eval_tofino/"

    # checks if input folder exists
    if not os.path.isdir(input_dir):
        print("Not plotting: Missing folder " +
              input_dir)
        return

    # Guess the zooming speed
    zooming_outputs = f"{inputs_path}/eval_tofino/zooming_outputs/"
    file = glob.glob(f"{zooming_outputs}/*.txt")[0]
    zooming_speed = float(file.split(".txt")[0].split("_")[-1])

    # plot
    plot_tofino_dedicated_zooming(
        input_dir, ips_setup, bw, loss_rates, zooming_speed, output_file)


# appendix figure
def figure11(inputs_path, output_file):
    """Plots figure 11 (design comparison)

    Args:
        inputs_path (_type_): _description_
        output_file (_type_): _description_
    """

    print("Plotting figure 11a and b at {}".format(output_file))

    input_dir = f"{inputs_path}/eval_comparison_pre/"

    # checks if input folder exists
    if not os.path.isdir(input_dir):
        print("Not plotting: Missing folder " +
              input_dir)
        return

    trace = 'equinix-nyc.dirB.20190117'

    # a
    plot_comparison(input_dir, output_file + "a.pdf", 10, trace, True)

    # b
    plot_comparison(input_dir, output_file + "b.pdf", 50, trace, True)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--input_dir', help="Path to inputs (precomputed values)",
        type=str, required=False, default=PRECOMPUTED_OUTPUTS)
    parser.add_argument(
        '--output_dir', help="Path to experiment's outputs",
        type=str, required=False, default=PLOT_OUTPUTS)
    args = parser.parse_args()

    # creates plots directory
    if not os.path.isdir(args.output_dir):
        os.system("mkdir -p {}".format(args.output_dir))

    # figure 2
    figure2(args.output_dir + "/figure2.pdf")

    # figure 5
    figure5(args.input_dir, args.output_dir + "/figure5.pdf")

    # figure 6
    figure6(args.input_dir, args.output_dir + "/figure6.pdf")

    # figure 7a
    figure7a(args.input_dir, args.output_dir + "/figure7a.pdf")
#
    # figure 7b
    figure7b(args.input_dir, args.output_dir + "/figure7b.pdf")
#
    # uniform packet loss
    uniform_loss(args.input_dir,
                 args.output_dir + "/uniform_random_drops.txt")

    # table 3
    table3(args.input_dir, args.output_dir + "/table3")

    # figure 8 (Tofino case study)
    figure8(args.input_dir, args.output_dir + "/figure8.pdf")

    # figure 11
    # NOTE: the x axis can be improved
    figure11(args.input_dir, args.output_dir + "/figure11")
