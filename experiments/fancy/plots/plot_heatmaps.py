from fancy.system_performance_lib import get_stats_for_heatmap
from fancy.plots.synthetic_prefix_sizes_info import format_prefix_sizes, get_prefix_sizes_zooming, get_prefix_sizes_dedicated_counters

import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt


import seaborn as sns
import pandas as pd
import pickle

"""
Plots for figure 5, 7a and b
"""
# mpl.style.use(['modified_style.style'])


def set_rc_params():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams['xtick.labelsize'] = 11
    mpl.rcParams['ytick.labelsize'] = 11
    mpl.rcParams['legend.fontsize'] = 9
    mpl.rcParams['axes.labelsize'] = 13
    mpl.rcParams['figure.figsize'] = (6.4, 4.8)
    mpl.rcParams['font.serif'] = 'Times New Roman'
    mpl.rcParams['font.family'] = 'serif'
    mpl.rcParams['text.usetex'] = True


# Default parameters
LOSS_RATES = [1, 0.75, 0.5, 0.1, 0.01, 0.001]
ZOOMING_SPEEDS = [10, 50, 100, 200]
SWITCH_DELAYS = [1000, 5000, 10000]


def precompute_dedicated_counters_heatmap(
        input_path, output_dir, num_prefixes=1, zooming_speeds=ZOOMING_SPEEDS,
        switch_delays=SWITCH_DELAYS, loss_rates=LOSS_RATES):
    prefix_sizes = get_prefix_sizes_dedicated_counters()
    os.system("mkdir -p {}".format(output_dir))
    for zooming_speed in zooming_speeds:
        for switch_delay in switch_delays:
            specs = {
                "ProbingTimeTopEntriesMs": ("%6.6f" % zooming_speed).strip(),
                "NumPrefixes": str(num_prefixes),
                "SwitchDelay": str(switch_delay)
            }
            output_file = "{}/fancy_dedicated_{}_{}.pickle".format(
                output_dir, zooming_speed, switch_delay)
            get_stats_for_heatmap(
                input_path, specs, prefix_sizes[num_prefixes],
                loss_rates, output_file, num_prefixes)


def precompute_zooming_heatmap(
        input_path, output_dir, num_prefixes=1, zooming_speeds=ZOOMING_SPEEDS,
        switch_delays=SWITCH_DELAYS, loss_rates=LOSS_RATES):
    prefix_sizes = get_prefix_sizes_zooming()
    os.system("mkdir -p {}".format(output_dir))
    for zooming_speed in zooming_speeds:
        for switch_delay in switch_delays:
            specs = {
                "ProbingTimeZoomingMs": ("%6.6f" % zooming_speed).strip(),
                "NumPrefixes": str(num_prefixes),
                "SwitchDelay": str(switch_delay)
            }
            output_file = "{}/fancy_zooming_{}_{}.pickle".format(
                output_dir, zooming_speed, switch_delay)
            get_stats_for_heatmap(
                input_path, specs, prefix_sizes[num_prefixes],
                loss_rates, output_file, num_prefixes)


##########
# PLOTTING
##########

def plot_heatmap(
        prefix_sizes, loss_rates, input_file, output_file=None, num_prefixes=1,
        y_label=True, bw_label=False):

    # set rc params
    set_rc_params()

    fig = plt.figure()

    ax_tpr = fig.add_subplot(1, 2, 1)
    ax_times = fig.add_subplot(1, 2, 2)

    info = pickle.load(open(input_file, "rb"))

    num_rows = len(prefix_sizes[num_prefixes])

    prefix_sizes_formatted = format_prefix_sizes(prefix_sizes, bw_label)

    _prefix_sizes = []
    _loss_rates = []
    _values_tpr = []
    _values_avg_detection_times = []

    for i, prefix_size in enumerate(prefix_sizes[num_prefixes]):
        # append it multiple times
        for loss in loss_rates:
            _value_tpr = info[(prefix_size, loss)]["tpr"]
            _value_avg_detection_time = info[(prefix_size, loss)][
                "avg_detection_times"]
            if _value_avg_detection_time == -1:
                _value_avg_detection_time = 30  # np.nan
            _loss_rates.append(loss)
            _prefix_sizes.append(prefix_sizes_formatted[num_prefixes][i])
            # values
            _values_tpr.append(_value_tpr)
            _values_avg_detection_times.append(_value_avg_detection_time)

    prefix_size_name = "Entry Size (total throughput and flows/s)"
    loss_rate_name = "Loss Rate (\%)"

    # transform values
    __loss_rates = []
    for loss in _loss_rates:
        if loss * 100 >= 1:
            __loss_rates.append(int(round(loss * 100, 2)))
        else:
            __loss_rates.append(round(loss * 100, 2))
    _loss_rates = __loss_rates[:]

    _values_tpr = [round(x, 2) for x in _values_tpr]
    _values_avg_detection_times = [round(x, 2)
                                   for x in _values_avg_detection_times]

    # ipdb.set_trace()

    data_frame_tpr = {prefix_size_name: _prefix_sizes,
                      loss_rate_name: _loss_rates, "value": _values_tpr}
    data_frame_times = {prefix_size_name: _prefix_sizes,
                        loss_rate_name: _loss_rates,
                        "value": _values_avg_detection_times}

    df1 = pd.DataFrame(data_frame_tpr)
    result = df1.pivot(index=prefix_size_name,
                       columns=loss_rate_name, values='value')
    result.index = pd.CategoricalIndex(
        result.index, categories=prefix_sizes_formatted[num_prefixes])
    result.sort_index(level=0, inplace=True, ascending=False)
    result = result.loc[:, _loss_rates[:len(loss_rates)]]
    # ax_tpr.set_facecolor("black")
    sns.heatmap(result, ax=ax_tpr, cmap=sns.cm.rocket,
                linewidth=0.5, annot=True, annot_kws={"fontsize": 9})

    df2 = pd.DataFrame(data_frame_times)
    result = df2.pivot(index=prefix_size_name,
                       columns=loss_rate_name, values='value')
    result.index = pd.CategoricalIndex(
        result.index, categories=prefix_sizes_formatted[num_prefixes])
    result.sort_index(level=0, inplace=True, ascending=False)
    result = result.loc[:, _loss_rates[:len(loss_rates)]]
    sns.heatmap(result, ax=ax_times, cmap=sns.cm.rocket_r,
                linewidth=0.25, annot=True, annot_kws={"fontsize": 9})

    ax_tpr.set_xticklabels(ax_tpr.get_xticklabels(), rotation=30)
    ax_times.set_xticklabels(ax_times.get_xticklabels(), rotation=30)

    # remove from ax_times the y axis info
    ax_times.get_yaxis().set_ticks([])
    ax_times.set_ylabel("")

    if y_label:
        #ax_tpr.set_ylabel("Pkts/s and Flows/s")
        ax_tpr.set_ylabel("Entry Size (total throughput and flows/s)")
    else:  # force the remval of the label
        ax_tpr.set_ylabel("")

    #ax_tpr.text(-0.1, 1.1, "pkts/s flows/s")

    ax_tpr.set_title("Avg TPR")
    ax_times.set_title("Avg Detection Time(s)")

    fig.tight_layout()
    if output_file:
        plt.savefig(output_file)


###################
# Plotting helpers
###################

def plot_dedicated_counters_all(
        in_base_path, out_base, num_prefixes=1, y_label=True, bw_label=False,
        zooming_speeds=ZOOMING_SPEEDS, switch_delays=SWITCH_DELAYS,
        loss_rates=LOSS_RATES):

    prefix_sizes = get_prefix_sizes_dedicated_counters()

    os.system("mkdir -p {}".format(out_base))
    #switch_delays = [1000, 5000, 10000]
    #zooming_speeds = [50, 100]
    for zooming_speed in zooming_speeds:
        for switch_delay in switch_delays:
            in_file = in_base_path + "fancy_dedicated_{}_{}.pickle".format(
                zooming_speed,
                switch_delay)
            out_file = out_base + "fancy_heatmap_dedicated_{}_{}.pdf".format(
                zooming_speed,
                switch_delay)
            # original plot_heatmap
            plot_heatmap(prefix_sizes, loss_rates, in_file, out_file,
                         num_prefixes, y_label, bw_label)


def plot_zooming_all(
        in_base_path="", out_base="", num_prefixes=1, y_label=True,
        bw_label=False, zooming_speeds=ZOOMING_SPEEDS,
        switch_delays=SWITCH_DELAYS, loss_rates=LOSS_RATES):

    prefix_sizes = get_prefix_sizes_zooming()

    os.system("mkdir -p {}".format(out_base))
    #switch_delays = [1000, 5000, 10000]
    #zooming_speeds = [100, 200]

    for zooming_speed in zooming_speeds:
        for switch_delay in switch_delays:
            in_file = in_base_path + "fancy_zooming_{}_{}.pickle".format(
                zooming_speed,
                switch_delay)
            out_file = out_base + "fancy_heatmap_zooming_{}_{}_{}.pdf".format(
                zooming_speed,
                switch_delay,
                num_prefixes)
            # original function plot_heatmap
            plot_heatmap(prefix_sizes, loss_rates, in_file, out_file,
                         num_prefixes, y_label, bw_label)
