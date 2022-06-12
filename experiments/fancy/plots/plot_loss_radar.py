import matplotlib as mpl
import os
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import matplotlib.pyplot as plt
import csv


def set_rc_params():
    mpl.rcParams.update(mpl.rcParamsDefault)

# mpl.style.use(['modified_style.style'])
#mpl.rcParams['xtick.labelsize'] = 11
#mpl.rcParams['ytick.labelsize'] = 11
#mpl.rcParams['legend.fontsize'] = 9
#mpl.rcParams['axes.labelsize'] = 13
#mpl.rcParams['figure.figsize'] = (16, 4)
#mpl.rcParams['font.serif'] = 'Times New Roman'
#mpl.rcParams['font.family'] = 'serif'
#mpl.rcParams['text.usetex'] = True


def load_loss_rada_data(data_file="loss_radar_memory.csv"):
    """"Loads the precomputed loss radar reading speeds and memory file (from our excel sheet)
i
    Args:
        data_file (str, optional): _description_. Defaults to "loss_radar_memory.csv".

    Returns:
        _type_: data to plot
    """

    with open(data_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0

        data = []

        for row in csv_reader:
            if line_count < 2:
                line_count += 1
            else:
                data.append(row)
                line_count += 1
        return data


def plot_loss_radar_memory(data_file, output_file):
    """Plots loss radar memory needed for a given loss rate and packet size.

    Args:
        data_file (_type_): _description_
        output_file (_type_): _description_
    """
    set_rc_params()

    data = load_loss_rada_data(data_file)

    # parse the data and put it nice

    packet_sizes = [64, 128, 256, 512, 1024, 1500]
    parsed_data = {x: [] for x in packet_sizes}

    for row in data:
        # get interesting columns
        avg_pkt_size = int(row[0])
        loss_rate = float(row[3])
        memory_usage = float(row[7])

        total_time_32 = float(row[-1])
        total_time_64 = float(row[-4])

        parsed_data[avg_pkt_size].append(
            (loss_rate, memory_usage, total_time_32, total_time_64))

    # plot the thing

    fig = plt.figure()
    ax = fig.add_subplot(111)

    loss_rates = [x[0] for x in parsed_data[64]]

    ax.plot(loss_rates, [x[1] for x in parsed_data[64]], c='b',
            marker="^", ls='--', label='64', fillstyle='none')
    ax.plot(loss_rates, [x[1] for x in parsed_data[128]],
            c='g', marker=(8, 2, 0), ls='--', label='128')
    ax.plot(loss_rates, [x[1]
            for x in parsed_data[256]], c='k', ls='-', label='256')
    ax.plot(loss_rates, [x[1] for x in parsed_data[512]],
            c='r', marker="v", ls='-', label='512')
    ax.plot(loss_rates, [x[1] for x in parsed_data[1024]], c='m',
            marker="o", ls='--', label='1024', fillstyle='none')
    ax.plot(loss_rates, [x[1] for x in parsed_data[1500]],
            c='k', marker="+", ls=':', label='1500')

    ax.set_xlabel("Loss rate")
    ax.set_ylabel("Memory Size (MB)")

    plt.legend(loc=2)
    plt.savefig(output_file)


def plot_loss_radar_speed(data_file, output_file):
    """Plots loss radar time to read needed for a given loss rate and packet size.

    Args:
        data_file (_type_): _description_
        output_file (_type_): _description_
    """
    set_rc_params()

    # load loss radar data
    data = load_loss_rada_data(data_file)

    packet_sizes = [64, 128, 256, 512, 1024, 1500]
    parsed_data = {x: [] for x in packet_sizes}

    for row in data:
        # get interesting columns
        avg_pkt_size = int(row[0])
        loss_rate = float(row[3])
        memory_usage = float(row[7])

        total_time_32 = float(row[-1])
        total_time_64 = float(row[-4])

        parsed_data[avg_pkt_size].append(
            (loss_rate, memory_usage, total_time_32, total_time_64))

    # plot the thing

    fig = plt.figure()
    ax = fig.add_subplot(111)

    loss_rates = [x[0] for x in parsed_data[64]]

    ax.plot(loss_rates, [x[2] for x in parsed_data[64]], c='b',
            marker="^", ls='--', label='64', fillstyle='none')
    ax.plot(loss_rates, [x[2] for x in parsed_data[128]],
            c='g', marker=(8, 2, 0), ls='--', label='128')
    ax.plot(loss_rates, [x[2]
            for x in parsed_data[256]], c='k', ls='-', label='256')
    ax.plot(loss_rates, [x[2] for x in parsed_data[512]],
            c='r', marker="v", ls='-', label='512')
    ax.plot(
        loss_rates, [x[2] for x in parsed_data[1024]],
        c='m', marker="o", ls='--', label='1024', fillstyle='none')
    ax.plot(loss_rates, [x[2] for x in parsed_data[1500]],
            c='k', marker="+", ls=':', label='1500')

    ax.set_xlabel("Loss rate")
    ax.set_ylabel("Read Speed (s)")

    plt.legend(loc=2)
    plt.savefig(output_file)


# plot_loss_radar_memory("inputs/loss_radar_memory.csv", "loss_radar_memory.pdf")
# plot_loss_radar_speed("inputs/loss_radar_memory.csv", "loss_radar_speed.pdf")
