# special import so it works well in servers and my laptop
import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt

from collections import OrderedDict
from scipy.interpolate import interp1d
import numpy as np
import glob
import json

"""
Old Plots
"""


def filter_files(input_folder, filter_conf):

    file_names = glob.glob(input_folder + "/*.json")

    to_keep = []
    file_conf = {}
    for name in file_names:
        tmp = name.replace(".json", "").split("/")[-1].split("_")[:-1]

        file_conf["algorithm"] = tmp[0]
        file_conf["bw"] = int(tmp[1])
        file_conf["duration"] = int(tmp[2])
        file_conf["num_flows"] = int(tmp[3])
        file_conf["num_drop"] = int(tmp[4])
        file_conf["seed"] = int(tmp[5])
        file_conf["tree_depth"] = int(tmp[6])
        file_conf["layer_split"] = int(tmp[7])
        file_conf["proving_time"] = int(tmp[8])
        file_conf["max_collision"] = int(tmp[9])
        file_conf["cost"] = int(tmp[10])
        file_conf["boost"] = int(tmp[11])

        # intersect the keys
        values_to_check = set(
            filter_conf.keys()).intersection(
            set(file_conf.keys()))
        # if they are all the same
        if all(file_conf[x] == filter_conf[x] for x in values_to_check):
            to_keep.append((file_conf, name))

    return to_keep


def parse_metric_rates(input_folder, filter_conf):

    file_names = sorted(
        filter_files(input_folder, filter_conf),
        key=lambda x: x[0]['num_flows'])

    num_drop = filter_conf['num_drop']

    parsed = []
    for file_data, file_name in file_names:
        num_flows = file_data['num_flows']
        data = json.load(open(file_name, "r"))

        reroutes = data['reroutes']
        failures_detected = 0
        non_failures_detected = 0

        if not reroutes:
            parsed.append((num_flows, 0, 1, 0))
            continue

        for reroute in reroutes:
            type = reroute['flow'].split()[-1]
            if type == '1':
                failures_detected += 1
            elif type == '0':
                non_failures_detected += 1

        tpr = failures_detected / num_drop
        fnr = (num_drop - failures_detected) / num_drop
        if (num_drop == num_flows):
            tnr = 0
        else:
            tnr = non_failures_detected / (num_flows - num_drop)

        parsed.append((num_flows, tpr, fnr, tnr))

    labels = [str(x[0]) for x in parsed]
    tpr = [x[1] for x in parsed]
    fnr = [x[2] for x in parsed]
    tnr = [x[3] for x in parsed]

    return labels, tpr, fnr, tnr


def parse_detection_times(input_folder, filter_conf):

    file_names = sorted(
        filter_files(input_folder, filter_conf),
        key=lambda x: x[0]['num_flows'])

    parsed = []
    for file_data, file_name in file_names:
        num_flows = file_data['num_flows']
        data = json.load(open(file_name, "r"))

        failures = data['failures']
        detection_times = []
        if not failures:
            parsed.append((num_flows, [0]))
            continue
        for failure in failures:
            detection_times.append(failure['timestamp'] - 2)

        parsed.append((num_flows, detection_times))

    times = [x[1] for x in parsed]
    return times


def plot_tp_fn_rate(ax, input_folder, filter_conf, decorate=False):

    labels, tpr, fnr, tnr = parse_metric_rates(input_folder, filter_conf)

    num_drop = filter_conf['num_drop']
    tree_depth = filter_conf['tree_depth']
    layer_split = filter_conf['layer_split']
    proving_time = filter_conf['proving_time']
    max_collision = filter_conf['max_collision']

    x = np.arange(len(labels))  # the label locations
    width = 0.2  # the width of the bars

    TPR = ax.bar(x - 1.5 * (width), tpr, width, label='TPR')
    FNR = ax.bar(x - width / 2, fnr, width, label='FNR')
    TNR = ax.bar(x + width / 2, tnr, width, label='TNR')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    if decorate:
        ax.set_ylabel('Rates')
        ax.set_title('Num Failures={} Tree Depth={} Split={} ZoomSpeed={} MaxCollisions={}'.format(
            num_drop, tree_depth, layer_split, proving_time, max_collision))
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend(loc=2)

    return


def plot_histogram(ax, input_folder, filter_conf, decorate=False):

    times = parse_detection_times(input_folder, filter_conf)
    times = sorted(times[-1])

    if len(times) >= 2:
        time_diff = times[-1] - times[0]
    else:
        time_diff = 1

    bins = int(time_diff / (filter_conf["proving_time"] / 1000))
    ax.hist(times, bins=bins)

    return


def plot_detection_times(ax, input_folder, filter_conf, decorate=False):

    times = parse_detection_times(input_folder, filter_conf)

    num_drop = filter_conf['num_drop']
    tree_depth = filter_conf['tree_depth']
    layer_split = filter_conf['layer_split']
    proving_time = filter_conf['proving_time']
    max_collision = filter_conf['max_collision']

    ax.violinplot(times, showmeans=True, showmedians=True)

    if decorate:
        ax.set_ylabel('Time')
        ax.set_title('Num Failures={} Tree Depth={} Split={} ZoomSpeed={} MaxCollisions={}'.format(
            num_drop, tree_depth, layer_split, proving_time, max_collision))

    return


# [send_rate, duration, num_flow, num_drop, seed, tree_depth, layer_splt, proving_time, max_collision
num_flows = [200, 1000, 5000, 10000, 50000]
num_drops = [100, 200]
#seeds = [1]
#tree_depths = [3, 4, 5]
#layer_splits = [2, 3]
#proving_times = [5, 10]
#max_collisions = [2, 5]
#runs = []

"""
Old plots (dont use)
"""


def plot_violin_rates_histo_vs_num_drops(
        input_folder, output_folder, num_drops, algorithms, costs, boost, seed,
        tree_depth, layer_split, proving_time, max_collision):
    """
    Num drops and algorithms are lists. So for each num_drop we put all the algorithms consecutively
    :param num_drops:
    :param algorithms:
    :param seed:
    :param tree_depth:
    :param layer_split:
    :param proving_time:
    :param max_collision:
    :return:
    """

    grid_height = len(num_drops) * len(algorithms) * len(costs)
    fig, axes = plt.subplots(grid_height, 3, figsize=(20, 10))
    i = 0

    for cost in costs:
        for algorithm in algorithms:
            for num_drop in num_drops:
                conf = {}
                conf['num_drop'] = num_drop
                conf['algorithm'] = algorithm
                conf['seed'] = seed
                conf['tree_depth'] = tree_depth
                conf['layer_split'] = layer_split
                conf['proving_time'] = proving_time
                conf['max_collision'] = max_collision
                conf['cost'] = cost
                conf['boost'] = boost

                if grid_height == 1:
                    # Violin plot
                    plot_detection_times(axes[0], input_folder, conf)
                    # Performance plot
                    plot_tp_fn_rate(axes[1], input_folder, conf)
                    # histogram
                    plot_histogram(axes[2], input_folder, conf)
                else:
                    # Violin plot
                    plot_detection_times(axes[i, 0], input_folder, conf)
                    # Performance plot
                    plot_tp_fn_rate(axes[i, 1], input_folder, conf)
                    # histogram
                    plot_histogram(axes[i, 2], input_folder, conf)

                i += 1

    fig.tight_layout()
    name = output_folder + "{}_{}_{}_{}_{}".format(
        tree_depth, layer_split, proving_time, max_collision, seed)
    plt.savefig(name)
    plt.close(fig)


def plot_everything_grid(out_dir):

    #num_flows = [200,1000, 5000, 10000, 50000]
    num_drops = [100, 200]
    seeds = [1]
    tree_depths = [3, 4, 5]
    layer_splits = [2, 3]
    proving_times = [5, 10]
    max_collisions = [2, 5]
    pipelines = []

    for tree_depth in tree_depths:
        for seed in seeds:
            for layer_split in layer_splits:
                for proving_time in proving_times:
                    for max_collision in max_collisions:
                        fig, axes = plt.subplots(2, 3, figsize=(20, 10))
                        for i, num_drop in enumerate(num_drops):

                            # Violin plot
                            plot_detection_times(
                                axes[i, 0],
                                num_drop, seed, tree_depth, layer_split,
                                proving_time, max_collision)

                            # Performance plot
                            plot_tp_fn_rate(
                                axes[i, 1],
                                num_drop, seed, tree_depth, layer_split,
                                proving_time, max_collision)

                            # histogram
                            plot_histogram(
                                axes[i, 2],
                                num_drop, seed, tree_depth, layer_split,
                                proving_time, max_collision)

                        fig.tight_layout()
                        name = "figures/_{}_{}_{}_{}".format(
                            tree_depth, layer_split, proving_time, max_collision)
                        # plt.show()
                        plt.savefig(name)
                        plt.close(fig)

# old plot


def plot_zooming_opportunities(axes, zooming_opportunities):
    """

    Args:
        axes:
        zooming_opportunities:

    Returns:

    """

    #fig, ax = plt.subplots(len(zooming_opportunities), 1)

    titles = [
        "Total Zooming Opportunities", "Detected Zooming Opportunities",
        "Not Detected Zooming Opportunities"]

    for i, zooming_opportunity in enumerate(zooming_opportunities):

        if len(zooming_opportunities) == 1:
            axis = axes
        else:
            axis = axes[i]

        if zooming_opportunity:

            x, y, z = [
                float(x[0]) for x in zooming_opportunity], [
                x[1] for x in zooming_opportunity], [
                x[2] for x in zooming_opportunity]

            x_sm = np.array(x)
            y_sm = np.array(y)
            z_sm = np.array(z)

            f1 = interp1d(x_sm, y_sm, kind='cubic')
            f2 = interp1d(x_sm, z_sm, kind='cubic')

            x_smooth = np.linspace(
                x_sm.min(),
                x_sm.max(),
                len(x_sm) * 3, endpoint=True)

            axis.plot(x_smooth, f1(x_smooth), label="weak opportunities")
            axis.plot(x_smooth, f2(x_smooth), label="strong opportunities")

        axis.set_title(titles[i])
        axis.set_xlabel('zooming speed')
        axis.set_ylabel('Zooming opportunities')
        axis.legend(loc=2)

    # fig.tight_layout()
    # plt.savefig(save_name)


"""
New Plots
"""

# the one we use


def plot_zooming_opportunities_absolute(
        axes, zooming_opportunities, mark_maxs=2, show_strong=False):
    """

    Args:
        axes:
        zooming_opportunities:

    Returns:

    """

    colors = ["#7aa0c4", "#ca82e1", "#8bcd50",
              "#df9f53", "#64b9a1", "#745ea6", "#db7e76"]

    i = 0
    for name, x, y in zooming_opportunities:

        weak_y = y['weak']
        strong_y = y['strong']

        axes.plot(
            x, weak_y, color=colors[i],
            linewidth=2, label="W:{}".format(name))
        i += 1
        if show_strong:
            axes.plot(
                x, strong_y, color=colors[i],
                linewidth=2, label="S:{}".format(name))
            i += 1

    # we do this in two times the same for since the y limit will be re-ajusted all the time and then
    # the vertical bars are not well positioned.

    # y max
    axes.set_ylim(bottom=0)
    i = 0
    for name, x, y in zooming_opportunities:

        weak_y = y['weak']
        strong_y = y['strong']

        ymax = axes.get_ybound()[1]

        # find max weak and max strong

        best_weaks = sorted(
            zip(x, weak_y),
            key=lambda x: x[1],
            reverse=True)[
            : mark_maxs]
        for best_weak in best_weaks:
            #label="weak max {}".format(best_weak[0])
            axes.axvline(
                best_weak[0],
                ymax=best_weak[1] / ymax, color=colors[i])
        i += 1

        if show_strong:
            best_strongs = sorted(
                zip(x, strong_y),
                key=lambda x: x[1],
                reverse=True)[
                : mark_maxs]
            for best_strong in best_strongs:
                # label="strong max {}".format(best_strong[0])
                axes.axvline(
                    best_strong[0],
                    ymax=best_strong[1] / ymax, color=colors[i])

            i += 1

    axes.set_xlabel('Zooming Speed (s)')
    axes.set_ylabel('Percentage of prefixes detectable')
    axes.legend(loc=0)

# cdf function  used in the old plots


def plot_detection_time_cdf(axes, detection_times_cdf):
    """

    Args:
        axes:
        detection_times_cdf:

    Returns:

    """

    # detection_times_cdf = cdf_x, normal_cdf_y, packets_cdf_y, bytes_cdf_y, avg, median

    # Find X limit
    l = [x for x in detection_times_cdf[0] if x != 1000000]
    x_limit = 0
    if len(l):
        x_limit = max(l)

    if detection_times_cdf[0][-1] == 1000000:
        x_limit += 1
    axes.set_xlim([0, float(x_limit)])

    axes.plot(
        detection_times_cdf[0],
        detection_times_cdf[1],
        color='red', linewidth=2, label="Prefix Count")
    axes.plot(
        detection_times_cdf[0],
        detection_times_cdf[2],
        color='green', linewidth=1, label="Packet Count")
    axes.plot(
        detection_times_cdf[0],
        detection_times_cdf[3],
        color='blue', linewidth=1, label="Byte Count")

    axes.set_title("Detection Time CDF(total/packets/bytes)")
    axes.set_xlabel('Detection time (s)')
    axes.set_ylabel('CDF')
    axes.legend(loc=2)

# metrics function  used in the old plots


def plot_performance_metrics(axes, performances):
    """

    Args:
        axes:
        performances:

    Returns:

    """

    # plot_performance_metrics(performance_ax, (tpr, fpr, tnr, fnr))

    metrics = ["TPR", "FPR", "TNR", "FNR"]
    metrics_values = [x * 100 for x in performances]

    axes.set_title("Prefix detection Metrics")
    axes.set_ylabel('Scores')

    x = np.arange(len(metrics))
    axes.bar(x, metrics_values, color=(
        'red', 'orange', 'green', 'blue'), width=0.5)
    axes.set_xticks(x)
    axes.set_xticklabels(metrics)

# shares function  used in the old plots


def plot_performance_shares(axes, shares):
    """

    Args:
        axes:
        shares:

    Returns:

    """

    # plot_performance_shares(shares_ax, shares)
    # "global": {"packets":
    #               {"total": global_packets_total_count_detected / global_packets_total_count,
    #                "top_entry": global_packets_top_count_detected / global_packets_total_count,
    #                "zoomed": global_packets_zoomed_count_detected / global_packets_total_count},
    #           "bytes":
    #               {"total": global_bytes_total_count_detected / global_bytes_total_count,
    #                "top_entry": global_bytes_top_count_detected / global_bytes_total_count,
    #                "zoomed": global_bytes_zoomed_count_detected / global_bytes_total_count}},
    # "slice": {"packets":
    #              {"total": slice_packets_total_count_detected / slice_packets_total_count,
    #               "top_entry": slice_packets_top_count_detected / slice_packets_total_count,
    #               "zoomed": slice_packets_zoomed_count_detected / slice_packets_total_count},
    #          "bytes":
    #              {"total": slice_bytes_total_count_detected / slice_bytes_total_count,
    #               "top_entry": slice_bytes_top_count_detected / slice_bytes_total_count,
    #               "zoomed": slice_bytes_zoomed_count_detected / slice_bytes_total_count}}
    # }

    labels = ['Global Bytes', 'Global Packets', "Slice Bytes", "Slice Packets"]
    total_values = [
        shares["global"]["bytes"]["total"],
        shares["global"]["packets"]["total"],
        shares["slice"]["bytes"]["total"],
        shares["global"]["packets"]["total"]]
    top_values = [shares["global"]["bytes"]["top_entry"],
                  shares["global"]["packets"]["top_entry"],
                  shares["slice"]["bytes"]["top_entry"],
                  shares["global"]["packets"]["top_entry"]]
    bottom_values = [
        shares["global"]["bytes"]["zoomed"],
        shares["global"]["packets"]["zoomed"],
        shares["slice"]["bytes"]["zoomed"],
        shares["global"]["packets"]["zoomed"]]

    x = np.arange(len(labels))  # the label locations
    width = 0.2  # the width of the bars

    total = axes.bar(x - (width * 1.5), total_values, width, label='Total')
    tops = axes.bar(x + width / 2, top_values, width, label='Top Entries')
    bottom = axes.bar(x + width / 2, bottom_values,
                      width, label='Zoomed Entries')

    axes.set_ylabel('Detection %')
    axes.set_title('Detection Shares by prefix type')
    axes.set_xticks(x)
    axes.set_xticklabels(labels)
    axes.legend(loc=2)


def bar_plot(ax, data, x_lables=None, colors=None, total_width=0.8,
             single_width=1, legend=True, xy_lables=None, title=None,
             autolable=False, custom_annotations=None):
    """Draws a bar plot with multiple bars per data point.

    Parameters
    ----------
    ax : matplotlib.pyplot.axis
        The axis we want to draw our plot on.

    data: dictionary
        A dictionary containing the data we want to plot. Keys are the names of the
        data, the items is a list of the values.

        Example:
        data = {
            "x":[1,2,3],
            "y":[1,2,3],
            "z":[1,2,3],
        }

    colors : array-like, optional
        A list of colors which are used for the bars. If None, the colors
        will be the standard matplotlib color cyle. (default: None)

    total_width : float, optional, default: 0.8
        The width of a bar group. 0.8 means that 80% of the x-axis is covered
        by bars and 20% will be spaces between the bars.

    single_width: float, optional, default: 1
        The relative width of a single bar within a group. 1 means the bars
        will touch eachother within a group, values less than 1 will make
        these bars thinner.

    legend: bool, optional, default: True
        If this is set to true, a legend will be added to the axis.
    """

    # Check if colors where provided, otherwhise use the default color cycle
    if colors is None:
        colors = ['#1f77b4',
                  '#ff7f0e',
                  '#2ca02c',
                  '#d62728',
                  '#9467bd',
                  '#8c564b',
                  '#e377c2',
                  '#7f7f7f',
                  '#bcbd22',
                  '#17becf']
        #colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    # Number of bars per group
    n_bars = len(data)

    # The width of a single bar
    bar_width = total_width / n_bars

    # List containing handles for the drawn bars, used for the legend
    bars = []

    data_max = []
    for value in data.values():
        data_max += value
    data_max = max(data_max)

    # Iterate over all data
    for i, (name, values) in enumerate(data.items()):
        # The offset in x direction of that bar
        x_offset = (i - n_bars / 2) * bar_width + bar_width / 2

        # Draw a bar for every value of that type
        #import ipdb; ipdb.set_trace()
        for x, y in enumerate(values):
            bar = ax.bar(
                x + x_offset, y, width=bar_width * single_width,
                color=colors[i % len(colors)])

            if autolable:
                height = bar[0].get_height()
                height = round(height, 4)

                height_str = "{}".format(height)

                if custom_annotations:
                    if name in custom_annotations:
                        height_str = custom_annotations[name][x]

                # calculate y position with respect the previous one
                if i == 0:
                    offset = 0
                else:
                    difference_percentage = (
                        list(data.items())[i - 1][1][x] - y) / data_max
                    if abs(difference_percentage) < 0.04:
                        if difference_percentage > 0:
                            offset = -6
                        elif difference_percentage <= 0:
                            offset = 6
                    else:
                        offset = 0

                ax.annotate(height_str,
                            xy=(bar[0].get_x() + bar[0].get_width() / 2, height),
                            xytext=(0, offset),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=6, fontweight='bold')

        # Add a handle to the last drawn bar, which we'll need for the legend
        bars.append(bar[0])

    #ax.tick_params(top='off', right='off')

    if x_lables:
        x = np.arange(len(x_lables))
        ax.set_xticks(x)
        ax.set_xticklabels(x_lables)

    if xy_lables:
        ax.set_xlabel(xy_lables[0])
        ax.set_ylabel(xy_lables[1])

    if title:
        ax.set_title(title)

    # Draw legend if we need
    if legend:
        ax.legend(bars, data.keys(), fontsize=5, loc=2)

    return bars, data.keys()


"""
Plot to compare different systems
"""


def plot_systems_comparison(systems_data, out_path, info):
    """

    Args:
        systems_data:
        out_path:
        memory_usage:

    Returns:

    """

    num_systems = len(systems_data)

    fig = plt.figure(figsize=(16, 10))

    if "zooming_speed" not in info:
        info["zooming_speed"] = "Estimated by function"

    fig.suptitle('System Comparison (Only Entries/ Only Tree/ Hybrid): Zooming Speed: {} - Memory usage: {}'.format(
        info["zooming_speed"], info["memory_usage"]))

    for i, (system_name, system_performance) in enumerate(systems_data):

        sorted_by_failures = sorted(
            system_performance.items(),
            key=lambda x: int(x[0]))

        # Plot Mean and Median
        system_a = fig.add_subplot(3, num_systems, 1 + i)

        data = OrderedDict()
        data["median(avg)"] = []
        data["mean(avg)"] = []
        data["percentile95(avg)"] = []
        data["percentile95(median)"] = []

        for f_size, values in sorted_by_failures:
            data["mean(avg)"].append(values['avg_avg_detection'])
            data["percentile95(median)"].append(
                values['percentile_95_of_medians'])
            data["median(avg)"].append(values['avg_median_detection'])
            data["percentile95(avg)"].append(values['avg_95_detection'])

        # x labels (failure size)
        x_lables = [x[0] for x in sorted_by_failures]

        title = "Entries={} - Tree={}/{}/{} - #Runs={}".format(
            system_name["NumTopEntriesSystem"],
            system_name["TreeDepth"],
            system_name["LayerSplit"],
            system_name["CounterWidth"],
            sorted_by_failures[0][1]["num_runs"])

        xy_lables = ("Failure Burst Size", "Detection Time (s)")
        bar_plot(
            system_a, data, x_lables, colors=None, total_width=0.8,
            single_width=1, legend=(i == 0),
            xy_lables=xy_lables, title=title, autolable=True)

        # Plot Performances
        system_b = fig.add_subplot(3, num_systems, 1 + len(systems_data) + i)

        data = OrderedDict()
        data["TPR"] = []
        data["FPR"] = []
        custom_annotations = {"FPR": []}

        for f_size, values in sorted_by_failures:
            data["TPR"].append(values['avg_tpr'])
            data["FPR"].append(values['avg_fpr'])
            custom_annotations["FPR"].append("{}({})".format(
                round(values['avg_fpr'], 4), values['avg_fp']))

        xy_lables = ("Failure Burst Size", "Performance (%)")
        bar_plot(system_b, data, x_lables, colors=None, total_width=0.8,
                 single_width=1, xy_lables=xy_lables, legend=(i == 0),
                 autolable=True, custom_annotations=custom_annotations)

        # Plot Shares
        system_c = fig.add_subplot(
            3, num_systems, 1 + len(systems_data) * 2 + i)

        data = OrderedDict()
        data["Zoomed"] = []
        data["Top entry"] = []
        data["Total"] = []

        for f_size, values in sorted_by_failures:
            data["Total"].append(values['avg_slice_bytes']['total'])
            data["Top entry"].append(values['avg_slice_bytes']['top_entry'])
            data["Zoomed"].append(values['avg_slice_bytes']['zoomed'])

        xy_lables = ("Failure Burst Size", "Detection Share Bytes (%)")
        bar_plot(
            system_c, data, x_lables, colors=None, total_width=0.8,
            single_width=1, xy_lables=xy_lables, legend=(i == 0),
            autolable=True)

        #labels = ['Global Bytes', 'Global Packets', "Slice Bytes", "Slice Packets"]

    # fig.tight_layout()
    plt.savefig(out_path + "_image.pdf")
