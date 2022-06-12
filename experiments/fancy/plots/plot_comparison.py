import multiprocessing
import copy
import pickle

from fancy.system_performance_lib import get_stats_for_experiment_spec

import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt


"""
Figure 11 appendix (old section 1)
"""


def set_rc_params():
    # reset
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.style.use(['science', 'scatter', 'grid'])
    mpl.rcParams['xtick.labelsize'] = 11
    mpl.rcParams['ytick.labelsize'] = 11
    mpl.rcParams['legend.fontsize'] = 6
    mpl.rcParams['axes.labelsize'] = 12
    mpl.rcParams['lines.markersize'] = 6
    mpl.rcParams['figure.figsize'] = (5.5, 2.65)
    mpl.rcParams['axes.prop_cycle'] = (mpl.cycler(
        'marker', ['o', 's', '^', 'v', '<', '>', 'd', 'h']) + mpl.cycler(
        'color',
        ['0C5DA5', '00B945', 'FF9500', 'FF2C00', '845B97', '474747', '9e9e9e',
         'b']) + mpl.cycler('ls', [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ']))


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


# previously called precompute_section1
def precompute_comparison(
        input_dir, output_dir, systems, num_top_entries_traffic,
        number_of_failures, traces_path, traces, slice=0):

    if not os.path.isdir(output_dir):
        os.system("mkdir -p {}".format(output_dir))

    pool = multiprocessing.Pool(16)
    for trace in traces:
        for num_top_prefixes in num_top_entries_traffic:
            for num_failures in number_of_failures:

                for system_name, system_spec in systems.items():

                    specs = copy.deepcopy(system_spec)

                    specs["NumTopEntriesTraffic"] = str(num_top_prefixes)
                    specs["NumTopFails"] = str(num_failures)
                    specs["InDirBase"] = "{}/{}/{}".format(traces_path,
                                                           trace, trace)

                    # make sure the path has only / and not // otherwise it does not match
                    specs["InDirBase"] = specs["InDirBase"].replace("//", "/")

                    specs["TraceSlice"] = str(slice)
                    # those experiments used 100% loss rate!
                    # thus we do not even filter by this
                    #specs["FailDropRate"] = "1.0"

                    output_file = "{}/{}_{}_{}_{}.pickle".format(
                        output_dir, trace, system_name, num_top_prefixes, num_failures)

                    print(output_file)

                    # get_stats_for_experiment_spec(
                    #    input_dir, specs, output_file)
                    pool.apply_async(
                        get_stats_for_experiment_spec,
                        (input_dir, specs, output_file),
                        {})
                    # break

    pool.close()
    pool.join()


def plot_comparison(input_dir, out_name, num_failures,
                    trace='equinix-nyc.dirB.20190117', set_custom_ticks=False):

    # max prefixes we set in the inputs file
    num_prefixes = 1000000

    # set rc params
    set_rc_params()

    fig = plt.figure()

    ax_time_vs_tp = fig.add_subplot(1, 2, 1)
    ax_bytes_vs_fp = fig.add_subplot(1, 2, 2)

    system_names = list(systems.keys())

    # put names better
    system_names = ["{}/{}/{} ({})".format(*(x.split("_")))
                    for x in system_names]

    # params we look at
    system_median_detections = []
    system_avg_tpr = []
    system_bytes = []
    system_fp = []

    # getting systems data to plot
    for system_name, _ in systems.items():
        input_file = "{}/{}_{}_{}_{}.pickle".format(
            input_dir, trace, system_name, num_prefixes, num_failures)
        performance_info = pickle.load(open(input_file, "rb"))

        # getting data
        system_median_detections.append(
            performance_info["avg_median_detection"])
        system_avg_tpr.append(performance_info["avg_tpr"])
        system_bytes.append(performance_info["avg_slice_bytes"]['total'])
        system_fp.append(performance_info['avg_fp'])

    #ax_prefixes.set_title("Detectable Prefixes CDF")
    ax_time_vs_tp.set_xlabel('True Positive Rate')
    ax_time_vs_tp.set_ylabel('Median Detection')

    #ax_bytes.set_title("Detectable bytes CDF")
    ax_bytes_vs_fp.set_xlabel('False Positives')
    ax_bytes_vs_fp.set_ylabel('Detected Bytes')

    #ax_prefixes.set_xlim([min(all_prefixes), max(all_prefixes)])
    #ax_prefixes.set_ylim(bottom=0, top=1.04)

    # min(all_prefixes)
    #ax_bytes.set_xlim([min(all_prefixes), max(all_prefixes)])
    #ax_bytes.set_ylim(bottom=0, top=1.04)

    # plot ax_time_vs_tp
    for i in range(len(system_names)):

        label1 = system_names[i]
        #label1 = None
        #label2 = None
        # if i < 4:
        #    label1 = system_names[i]
        # elif i>= 4:
        #    label2 = system_names[i]

        ax_time_vs_tp.plot(
            system_avg_tpr[i],
            system_median_detections[i],
            label=label1)
        ax_bytes_vs_fp.plot(system_fp[i], system_bytes[i], label=label1)

    # this is manual ticking for nyc
    # this only works for those results
    if set_custom_ticks:
        if num_failures == 10:
            ax_time_vs_tp.set_xlim(0.92, 1.005)
            ax_time_vs_tp.set_xticks([0.92, 0.95, 0.975, 1])
            ax_time_vs_tp.set_xticklabels(
                ["0.92", "0.95", "0.975", "1"],
                fontweight='normal')

            ax_bytes_vs_fp.set_xlim(0, 6.75)
            ax_bytes_vs_fp.set_xticks([0, 2.5, 4.5, 6.5])

        elif num_failures == 50:
            ax_time_vs_tp.set_xlim(0.6, 1.01)
            ax_time_vs_tp.set_xticks([0.6, 0.7, 0.8, 0.9, 1])

            ax_bytes_vs_fp.set_xlim(0.5, 32)
            ax_bytes_vs_fp.set_xticks([1, 10, 20, 30])

            ax_bytes_vs_fp.set_ylim

    # ipdb.set_trace()

    # manually set xticks
    #ax_prefixes.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9])
    #ax_prefixes.set_xticklabels([10, 30, 50, 70, 90], fontweight='normal')
#
    #ax_bytes.set_xticks([0.96, 0.97, 0.98, 0.99, 1])
    #ax_bytes.set_xticklabels([96, 97, 98, 99, 100], fontweight='normal')

    # ipdb.set_trace()

    #ax_prefixes.grid(linestyle='--', axis='y')
    #ax_bytes.grid(linestyle='--', axis='y')

    # fig.subplots_adjust(top=0.9, left=0.1, right=0.9,
    #                    bottom=0.12)  # create some space below the plots by increasing the bottom-value

    #ax_prefixes.legend(bbox_to_anchor=(1.04, 1.04), loc="upper center", ncol=3, mode="expand")

    # fig.subplots_adjust(bottom=0.01)

    #lgd = fig.legend(bbox_to_anchor=(0.5, -0.01), loc="upper center", ncol=4)
    ax_bytes_vs_fp.legend(
        bbox_to_anchor=(1.02, 0.5),
        loc="center left", ncol=1)

    #ax_time_vs_tp.legend(bbox_to_anchor=(-0.2, 1.04), loc="lower left", ncol=4)

    # ax_time_vs_tp.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
    #          ncol=2, mode="expand", borderaxespad=0.)
#
    # ax_bytes_vs_fp.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
    # ncol=2, mode="expand", borderaxespad=0.)

    #leg1= ax_time_vs_tp.legend(loc = 'upper center', bbox_to_anchor=(1.05, 1.05), ncol=4)
    # leg1.get_frame().set_edgecolor('black')
    #[x.set_linewidth(6.0) for x in leg1.get_lines()]
    #leg2= ax_bytes.legend(loc=0)
    #[x.set_linewidth(6.0) for x in leg2.get_lines()]
    # leg2.get_frame().set_edgecolor('black')

    fig.tight_layout()
    plt.savefig(out_name)
