from fancy.utils import cwd

import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import shutil


def set_rc_params():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.style.use(['science', 'ieee'])
    mpl.rcParams['xtick.labelsize'] = 8
    mpl.rcParams['ytick.labelsize'] = 8
    mpl.rcParams['legend.fontsize'] = 6
    mpl.rcParams['axes.labelsize'] = 8
    mpl.rcParams['figure.figsize'] = (3, 2)

# not sure why I added this
#mpl.rcParams['font.serif'] = 'Times New Roman'
#mpl.rcParams['font.family'] = 'serif'
#mpl.rcParams['text.usetex'] = True


mpl.rcParams['axes.prop_cycle'] = (mpl.cycler(
    'color', ['k', 'r', 'b', 'g', 'm']) + mpl.cycler('ls', ['-', '--', ':', '-.', '--']))

# name; ports, bw, total_memory
switch_descriptions = {
    "tofino1": (64, 100, 36),
    "tofino2": (64, 200, 60),
    "tofino3": (64, 400, 96)
}

"""
How do we do the calculations

In the paper they say that for each packet they store at least the 5-tuple. That
is 13 Bytes per packet. For an array of 1000 cells and a switch with 64 ports
they need:

13 * 6 * 1000 = 823KB of memory. Which matches what they say in the paper of
~800KB. Which can support a max delay of 62us (as our computations below show).

Note: I do believe they need 15 bytes at least... they need to somehow save the
packet ID in the ring otherwise how do they know its the wrong ID? Lets do both
calculations. 

For 1000 packets are transferred at the following rates:

1500B → 8.333M: 8.3K (1ms) → 8.3 packets 1 us

750 → 16.666M:  16.6k (1ms) → 16.6 packets 1 us for example 62us (1000 packets) 

64 → 195M: 195k (1ms) → 195 packets 1 us
"""

###
# Operational region net seer plot
###

# Traffic to latency operational plot


def max_rtt(buffer_size, bw=100000000000, pkt_size=1024):

    pkts_per_sec = bw / (8 * pkt_size)
    max_latency = buffer_size / pkts_per_sec
    return max_latency


def max_link_delay(buffer_size, bw=100000000000, pkt_size=1024):
    return max_rtt(buffer_size, bw, pkt_size) / 2


def get_max_bw(link_delay, buffer_size, bw_steps=10000, pkt_size=1024):
    bws = []
    for i in range(1, bw_steps + 1):
        # bandwidth in gbps
        bw = (100 * i) / bw_steps * 1000000000
        bws.append(bw)
    max_bw = 0
    for bw in bws:
        if link_delay < max_link_delay(buffer_size, bw, pkt_size):
            max_bw = bw

    return max_bw


def netseer_limits(link_delays, buffer_size=1000, avg_pkt_size=1024):
    netseer_bw_limits = []
    for link_delay in link_delays:
        bw = get_max_bw(link_delay, buffer_size=buffer_size,
                        pkt_size=avg_pkt_size, bw_steps=1000)
        netseer_bw_limits.append((link_delay, bw))

        if link_delay == 100 / 1000000:
            print(bw)

    return netseer_bw_limits


def get_netseer_limits_basic_lines(buffer_size=1000, avg_pkt_size=1024):
    """Gets the operational line of netseer up to 100gbps. 

    Args:
        buffer_size (int, optional): _description_. Defaults to 1000.
        avg_pkt_size (int, optional): _description_. Defaults to 1024.
    """

    link_delays = np.logspace(-6, -1, 1000)  # from 1us to 100ms
    data_points = netseer_limits(link_delays, 1000, 1024)

    # divide bw to 100Gbps
    data_points = [(x, y / 1000000000) for (x, y) in data_points]

    x = [x[0] for x in data_points]
    y = [x[1] for x in data_points]

    return x, y


def save_netseer_limits_basic_lines(
        output_file, buffer_size=1000, avg_pkt_size=1024):
    """Saves in csv the line so we can plot it. 

    Args:
        output_file (str): output csv file
        buffer_size (int, optional): _description_. Defaults to 1000.
        avg_pkt_size (int, optional): _description_. Defaults to 1024.
    """
    x, y = get_netseer_limits_basic_lines(buffer_size, avg_pkt_size)

    f = open(output_file, "w")
    f.write("x,y\n")
    for xx, yy in zip(x, y):
        f.write("{},{}\n".format(xx, yy))
    f.close()


def plot_netseer_limits_basic_lines(buffer_size=1000, avg_pkt_size=1024):
    """Plots the operational region of netseer as delay increases, for a given
    fixed memory use and average packet level size. 
    """

    # set rc params
    set_rc_params()

    x, y = get_netseer_limits_basic_lines(buffer_size, avg_pkt_size)

    # return x,y

    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.set_xscale("log")

    ax.plot(x, y)

    #d = scipy.zeros(len(y))
    #ax.fill_between(xs, ys, where=ys>=d, interpolate=True, color='blue')
    #ax.fill_between(xs, ys, where=ys<=d, interpolate=True, color='red')

    # ax.margins(0)

    plt.tight_layout()
    plt.show()


def plot_netseer_operational_latex(
        output_file, buffer_size=1000, avg_pkt_size=1024):
    """Prints the operational netseer region using latex and pdflatex

    Args:
        output_file (_type_): _description_
        buffer_size (int, optional): _description_. Defaults to 1000.
        avg_pkt_size (int, optional): _description_. Defaults to 1024.

    Returns:
        _type_: _description_
    """
    # latex standalone file
    doc = r"""
\documentclass{standalone}
\usepackage[english]{babel}

% tikz
\usepackage{tikz}
\usepackage{pgfplots}

\usetikzlibrary{tikzmark, calc,shapes,arrows,decorations.markings}
\usepgfplotslibrary{fillbetween, groupplots, statistics}

% colors
\usepackage{xcolor}
\definecolor{cLightRed}{HTML}{E74C3C}
\definecolor{cRed}{HTML}{C0392B}
\definecolor{cBlue}{HTML}{2980B9}
\definecolor{cLightBlue}{HTML}{3498DB}
\definecolor{cDarkBlue}{HTML}{10334A}
\definecolor{cGreen}{HTML}{27AE60}
\definecolor{cLightGreen}{HTML}{2ECC71}
\definecolor{cViolet}{HTML}{8E44AD}
\definecolor{cLightViolet}{HTML}{9B59B6}
\definecolor{cOrange}{HTML}{D35400}
\definecolor{cLightOrange}{HTML}{E67E22}
\definecolor{cYellow}{HTML}{F39C12}
\definecolor{cLightYellow}{HTML}{F1C40F}

\tikzset{cross/.style={cross out, draw, 
         minimum size=2*(#1-\pgflinewidth), 
         inner sep=0pt, outer sep=0pt}}

\begin{document}
\begin{tikzpicture}
    \begin{axis}[
    axis on top=true,
    xmode=log,
    xlabel={Link Latency},
    ylabel={Traffic (Gbps)},
    xmin=0.00001,
    ymin=0,
    xmax=0.1,
    ymax=105,
    axis y line=left,
    axis x line=bottom,
    xtick={0.00001, 0.0001, 0.001, 0.01, 0.1},
    xticklabels={10$\mu$s, 100$\mu$s, 1ms, 10ms, 0.1s},
    ytick={0, 20, 40, 60, 80, 100},
    yticklabels={0, 20, 40, 60, 80,  100},
    height=5cm,
    width={\linewidth},
    ]
    \draw[draw=red!25, fill=red!25] (axis cs:0.000001, 0) rectangle (axis cs:0.1, 100);
    \addplot+[mark=none,  thick, cGreen, fill=cGreen!30] table[x=x, y=y, col sep=comma] {netseer.csv} \closedcycle;
    \draw (axis cs:0.00001, 35) node[right] {\small{Operational}};
    \draw (axis cs:0.0008, 65) node[right] {\small{Not Operational}};
    \draw (axis cs:0.001, 20) node[cross, cRed!25] {};
\end{axis}
\end{tikzpicture}
\end{document}"""

    with tempfile.TemporaryDirectory() as tmpdirname:

        # runs commands in that directory
        with cwd(tmpdirname):
            # create netseer.csv
            save_netseer_limits_basic_lines(
                "netseer.csv", buffer_size, avg_pkt_size)

            # save tex file
            with open("netseer.tex", "w") as fp:
                fp.write(doc)

            # compile the document
            os.system("pdflatex netseer.tex")

            # move pdf to output_file
            cur_name = "netseer.pdf"
            shutil.copy(cur_name, output_file)


###
# Required memory plots
###
"""
INFO ABOUT TOFINO MEMORY

Tofino 1: 15MB per pipe. We know they allocate 48/80 to registers thus 9MB per
pipe. And ~0.75 per stage.

Tofino 2: Has 25MB per pipe. Following same logic -> 15MB per pipe and 0.75 per
stage! so the same. 

Tofino 3: 20MB per pipe (but has 8 pipes, but still double speed). If we follow
the same logic than tofino 1, they allocate 12MB per pipe. They dont say how
many stages though, I assume 20 as well.
"""

# required memory plot


def needed_bucket_ring_size(link_delay, bandwidth, pkt_size):
    """
    Computes the amount of buckets needed to not overwrite the buffer
    Args:
        link_delay ([type]): [description]
        bandwidth ([type]): bandwidth in gb
        pkt_size ([type]): [description]
    """

    # transform bandwidth to bytes per second
    # banswidth comes in Gigabytes
    byte_rate = (bandwidth * 1000000000) / 8

    # two times rtt
    rtt = link_delay * 2
    # total bytes in flight
    rtt_trasmitted_bytes = byte_rate * rtt
    # number of buckets to be able to hold that amount in flight
    bucket_size = rtt_trasmitted_bytes / pkt_size

    return bucket_size


def bucket_size_to_memory(bucket_size, cell_cost, switch_ports):
    return bucket_size * cell_cost * switch_ports


def tofino_memory(block_size=128, blocks_mau=48, stages=1):
    # block size in KBit.
    # returns MBs
    return ((block_size / 8) * blocks_mau * stages) / 1000


def find_memory_intersect(data, memory):
    """_summary_

    Args:
        data (_type_): _description_
        memory (_type_): _description_

    Returns:
        _type_: _description_
    """
    for i, (delay, data_mem) in enumerate(data):
        if data_mem <= memory and memory <= data[i + 1][1]:
            # get closer
            if abs(memory - data_mem) < abs(memory - data[i + 1][1]):
                return delay, data_mem
            else:
                return data[i + 1]

    # if nothing was found
    return -1, -1


"""
Plots net seer memory requirements (Figure 2 Sigcomm 2022)
"""


def plot_netseer_memory_requirements(
        out_name, switches, packet_size=1024, cell_cost=13):
    """
    Computes and prints the needed memory for netseer to be operational
    at different delays and bandwidths
    Args:
        bandwidths (list, optional): [description]. Defaults to [10, 40, 100].
        num_ports (int, optional): [description]. Defaults to 64.
        cell_cost (int, optional): [description]. Defaults to 13.
    """

    # set rc params
    set_rc_params()

    link_delays = np.logspace(-4, -1, 1000)  # from 10us to 10ms
    switch_to_line = {x: [] for x in switches.keys()}

    for switch, (switch_ports, bw, _) in switches.items():
        line = []
        for delay in link_delays:
            bucket_size = needed_bucket_ring_size(delay, bw, packet_size)
            memory = bucket_size_to_memory(
                bucket_size, cell_cost, switch_ports)
            # right now memory in KB
            line.append((delay, memory / 1000))
        switch_to_line[switch] = line[:]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xscale("log")
    # ax.set_yscale("log")

    max_y = 500
    ax.set_ylim([0, max_y])

    c = ['b', 'r', 'k', 'g', 'm']
    ls = [':', '--', '-', '-.', '--']

    #line_styles = [('b', '--'), ('g', "--"), ("k", "-")]

    i = 0
    for switch, data in switch_to_line.items():
        ports, bw, memory = switches[switch]
        x = [x[0] for x in data]
        y = [x[1] / 1000 for x in data]
        # add line
        ax.plot(
            x, y, label='{}-ports x {}Gbps'.format(ports, bw),
            color=c[i],
            ls=ls[i])
        #s = ('{} Tbps Switch'.format((ports * bw)/1000))
        # if i == 0:
        #    s = " " + s
        # print(s)
        #ax.plot(x, y, label=s, color=c[i], ls=ls[i])

        # add x and y bars
        # Not used anymore?
        intersect_delay, intersect_memory = find_memory_intersect(
            data, memory * 1000)
        # back to mb
        intersect_memory = intersect_memory / 1000

        # instead of vertical line
        #ax.plot([0, intersect_delay], [intersect_memory, intersect_memory], linewidth=0.5, color=c[i], ls=ls[i])
        #ax.axvline(x=intersect_delay, ymin=0, ymax=intersect_memory/max_y, linewidth=0.5, color=c[i], ls=ls[i])

        # ax.axvline()
        # ax.axhline()

        i += 1

    #ax.plot([0, 1e-1], [15, 15], linewidth=0.5, color='grey', ls='--', label="Memory per pipeline")
    #ax.axhline(y=100, xmin=0, xmax=1, linewidth=0.5, color='r', ls='-')
    #ax.axvline(x=1e-3, ymin=0, ymax=1, linewidth=0.5, color='r', ls='--')
    #ax.axvline(x=1e-2, ymin=0, ymax=1, linewidth=0.5, color='r', ls='--')

    #ax.set_title("NetSeer Memory usage for a {}-port switch and {}B packets".format(switch_ports, packet_size))
    ax.margins(x=0, y=0)
    # ax.set_yticks([20, , 100, 150, 200, 300, 400])
    #ax.set_yticklabels(["10us", "100us", "1ms", "10ms"])

    ax.set_xticks([1e-4, 1e-3, 1e-2, 1e-1])
    ax.set_xticklabels(["100us", "1ms", "10ms", "100ms"])

    ax.set_xlabel("Inter-Switch Link Latency (log scale)")
    ax.set_ylabel("Required Memory (MB)")

    legend = plt.legend(loc=2)
    for t in legend.get_texts():
        t.set_ha('right')

    plt.savefig(out_name)


def plot_and_crop(
        file_name="netseer_memory_usage.pdf",
        dst="/Users/edgar/p4-offloading/paper/current/figures/"):
    import os
    plot_netseer_memory_requirements(file_name, switch_descriptions)
    # crop
    os.system("pdfcrop {}".format(file_name))
    # send to paper figures
    crop_name = file_name.replace(".pdf", "-crop.pdf")
    os.system("cp {} {}".format(crop_name, dst))


if __name__ == "__main__":
    """Instructions to plot from cmd.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--plot', help="What to plot",
        type=str, required=False, default="")
    parser.add_argument(
        '--output', help="Where to save the plot (including name)",
        type=str, required=False, default="")
    args = parser.parse_args()

    if args.plot == "memory_requirements":
        avg_pkt_size = 1204
        bytes_per_packet = 13
        plot_netseer_memory_requirements(
            args.output, switch_descriptions, avg_pkt_size, bytes_per_packet)
    elif args.plot == "operational":
        buffer_size = 1000
        avg_pkt_size = 1024
        plot_netseer_operational_latex(args.output, buffer_size, avg_pkt_size)
    else:
        # just imports
        pass
