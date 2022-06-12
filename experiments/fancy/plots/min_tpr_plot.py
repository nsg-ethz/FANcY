from logging import warning

#from fancy.visualizations import *
from fancy.plots.synthetic_prefix_sizes_info import get_prefix_sizes_zooming

import pickle
import warnings

import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt


def set_rc_params():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.style.use(['science', 'ieee'])
    mpl.rcParams['xtick.labelsize'] = 8
    mpl.rcParams['ytick.labelsize'] = 8
    mpl.rcParams['legend.fontsize'] = 6
    mpl.rcParams['axes.labelsize'] = 8
    #mpl.rcParams['axes.linewidth'] = 1
    mpl.rcParams['figure.figsize'] = (2.5, 1.66)
    mpl.rcParams['axes.prop_cycle'] = (mpl.cycler(
        'color', ['k', 'r', 'b', 'g', 'm']) + mpl.cycler('ls', ['-', '--', ':', '-.', '--']))


# standard params
#zooming_speeds = [10, 50, 100, 200]
#loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

def compute_min_tpr_line(
        input_dir, min_tpr=0.95, burst_size=1, switch_delay=10000,
        zooming_speeds=[10, 50, 100, 200],
        loss_rates=[1, 0.75, 0.5, 0.1, 0.01, 0.001]):
    """Parses the output files and creates a data structure so we can easily plot.

    Args:
        input_dir (_type_): _description_
        min_tpr (float, optional): _description_. Defaults to 0.95.
        burst_size (int, optional): _description_. Defaults to 1.
        switch_delay (int, optional): _description_. Defaults to 10000.
        zooming_speeds (list, optional): _description_. Defaults to [10, 50, 100, 200].
        loss_rates (list, optional): _description_. Defaults to [1, 0.75, 0.5, 0.1, 0.01, 0.001].

    Returns:
        _type_: _description_
    """
    # here it should always be this, however might want to change it???
    prefix_sizes = get_prefix_sizes_zooming()[burst_size]
    data = {}
    for zooming_speed in zooming_speeds:
        data[zooming_speed] = []
        input_file = "{}/fancy_zooming_{}_{}.pickle".format(
            input_dir, zooming_speed, switch_delay)
        info = pickle.load(open(input_file, "rb"))

        for loss in loss_rates:
            for i, prefix_size in enumerate(prefix_sizes):
                _info = info[(prefix_size, loss)]
                if _info["tpr"] >= min_tpr:
                    data[zooming_speed].append((loss, i + 1, prefix_size))
                    break
    return data


def plot_min_tpr_line(
        input_dir, out_file, min_tpr=0.95, burst_size=1, switch_delay=10000,
        zooming_speeds=[10, 50, 100, 200],
        loss_rates=[1, 0.75, 0.5, 0.1, 0.01, 0.001]):
    """Plots one min_tpr_plot for a specific burst size and switch delay.

    The function assumes that inputs will be at eval_zooming_{}_pre.
    That files inside will be named: fancy_zooming_{zooming_speed}_{switch_delay}.pickle.
    And generates outputs of the form min_tpr_{burst_size}_{switch_delay}

    Args:
        input_dir (str): input directory to all the pickle files.
        out_file (str): directory where to save the plots.
        min_tpr (float, optional): _description_. Defaults to 0.95.
        burst_size (int, optional): _description_. Defaults to 1.
        switch_delay (int, optional): _description_. Defaults to 10000.
        zooming_speeds (list, optional): _description_. Defaults to [10, 50, 100, 200].
        loss_rates (list, optional): _description_. Defaults to [1, 0.75, 0.5, 0.1, 0.01, 0.001].
    """

    # set rc params
    set_rc_params()

    # ignore warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        data = compute_min_tpr_line(
            input_dir, min_tpr, burst_size, switch_delay, zooming_speeds,
            loss_rates)

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        # loss rate from 1 to 0.001
        ax.set_xlim(1, 0.001)

        markers = ["^", "v", "o", "+"]
        i = 0
        for zooming_speed, points in sorted(data.items(), key=lambda x: x[0]):
            _x = [x[0] for x in points]
            _y = [x[1] for x in points]
            ax.plot(
                _x, _y, linewidth=1, marker=markers[i],
                markersize=2, label="Zooming {} ms".format(zooming_speed))
            i += 1

        ax.set_xlabel('Loss Rate (\%)')
        ax.set_ylabel('Entry Size Rank')

        ax.set_xticks([1, 0.75, 0.5, 0.1, 0.001])
        ax.set_xticklabels([100, 75, 50, 10, 0.1])

        ax.legend(loc=0)

        fig.tight_layout()
        plt.savefig(out_file)


def plot_all_min_tpr_line(input_dir_base, out_dir_base, min_tpr=0.95):
    """Helper function to plot many different min_tpr_line plots.

    The function assumes that inputs will be at eval_zooming_{}_pre.
    That files inside will be named: fancy_zooming_{zooming_speed}_{switch_delay}.pickle.
    And generates outputs of the form min_tpr_{burst_size}_{switch_delay}

    Args:
        input_dir_base (_type_): _description_
        out_dir_base (_type_): _description_
        min_tpr (float, optional): _description_. Defaults to 0.95.
    """
    #burst_sizes = [1, 10]
    #switch_delays = [1000, 5000, 10000]
    burst_sizes = [1]
    switch_delays = [10000]
    zooming_speeds = [10, 50, 100, 200]
    loss_rates = [1, 0.75, 0.5, 0.1, 0.01, 0.001]

    os.system("mkdir -p {}".format(out_dir_base))
    for burst_size in burst_sizes:
        for switch_delay in switch_delays:
            _input_dir = "{}/eval_zooming_{}_pre/".format(
                input_dir_base, burst_size)
            _out_dir = "{}/min_tpr_{}_{}.pdf".format(
                out_dir_base, burst_size, switch_delay)
            plot_min_tpr_line(
                _input_dir, _out_dir, min_tpr, burst_size, switch_delay,
                zooming_speeds, loss_rates)


def crop_and_copy(dst="/Users/edgar/p4-offloading/paper/current/figures/"):
    import os
    # figure 7
    figure_7 = "/Users/edgar/p4-offloading/experiments/output_files/sigcomm2022/min_tpr/min_tpr_1_10000.pdf"
    os.system("pdfcrop {}".format(figure_7))
    # crop
    # send to paper figures
    crop_name = figure_7.replace(".pdf", "-crop.pdf")
    os.system("cp {} {}".format(crop_name, dst))
