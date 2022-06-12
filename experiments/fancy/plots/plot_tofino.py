from fancy.visualizations import *


def set_rc_params():
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.style.use(['science', 'ieee'])
    mpl.rcParams['xtick.labelsize'] = 11
    mpl.rcParams['ytick.labelsize'] = 11
    mpl.rcParams['legend.fontsize'] = 7
    mpl.rcParams['axes.labelsize'] = 12
    #mpl.rcParams['axes.linewidth'] = 1
    # we made it a bit bigger so it fits
    mpl.rcParams['figure.figsize'] = (3.5, 2.1)
    mpl.rcParams['axes.prop_cycle'] = (mpl.cycler(
        'color', ['k', 'r', 'b', 'g', 'm']) + mpl.cycler('ls', ['-', '--', ':', '-.', '--']))

# params


def parse_iperf_output(file_name):
    data = []
    with open(file_name, "r") as f:
        parse = False
        for line in f:
            if "SUM-cnt" in line:
                parse = True
                continue

            if parse:
                _line = line.split()
                ts = float(_line[1].split("-")[0])
                bw = float(_line[5])
                unit = (_line[6])
                losses = int(_line[7].split("=")[1].split(":")[0])

                data.append((ts, bw, unit, losses))
    return data


scale_formula = {
    ("bits/sec", "Gbits/sec"): (1 / 1000000000.),
    ("Kbits/sec", "Gbits/sec"): (1 / 1000000.),
    ("Mbits/sec", "Gbits/sec"): (1 / 1000.),
    ("bits/sec", "Mbits/sec"): (1 / 1000000.),
    ("Kbits/sec", "Mbits/sec"): (1 / 1000.),
    ("Gbits/sec", "Mbits/sec"): (1000),
}


def transform_bw(ip_data, max_bw):
    # max bw always in Mbitssec

    # up to 1G
    if max_bw <= 1000:
        bw_ref = "Mbits/sec"
        max_value = max_bw + (max_bw * 0.1)
    elif max_bw > 1000:
        bw_ref = "Gbits/sec"
        max_value = max_bw / 1000 + ((max_bw / 1000 * 0.1))

    # first pass set everything to a unified bw
    new_ip_data = []
    for time, bw, ref, loss in ip_data:
        # nothing
        if ref == bw_ref:
            if bw > max_value:
                bw = max_value
            new_ip_data.append((time, bw, ref, loss))
        # transform
        else:
            new_bw = scale_formula[(ref, bw_ref)] * bw
            if new_bw > max_value:
                new_bw = max_value
            new_ip_data.append((time, new_bw, bw_ref, loss))

    return new_ip_data


def parse_iperf_outputs(path_prefix, ips, bw, loss_rate, zooming_speed=None):
    ips_data = []
    for ip, port in ips:
        file_name = "{}/sender_tcp_{}_{}_{}_{}".format(
            path_prefix, ip, port, bw, loss_rate)
        if zooming_speed:
            file_name += "_{}.txt".format(zooming_speed)
        else:
            file_name += ".txt"
        data = parse_iperf_output(file_name)
        ips_data.append(data)
    return ips_data


"""
Tofino Zooming Part
"""


def plot_one_iperf_output(
        path_prefix, ips, bw, loss_rate, zooming_speed, out_name):
    """Used to plot the bw results of either zooming or dedicated counter entries

    Args:
        path_prefix ([type]): [description]
        ips ([type]): [description]
        bw ([type]): [description]
        loss_rate ([type]): [description]
        zooming_speed ([type]): [description]
        out_name ([type]): [description]
    """

    ips_data = parse_iperf_outputs(
        path_prefix, ips, bw, loss_rate, zooming_speed)
    # max bw always in Mbitssec
    # up to 1G
    if bw <= 1000:
        bw_ref = "Mbits/sec"
        max_value = bw + (bw * 0.2)
    elif bw > 1000:
        bw_ref = "Gbits/sec"
        max_value = bw / 1000 + ((bw / 1000 * 0.2))

    #import ipdb; ipdb.set_trace()
    fig, ax = plt.subplots()

    ax.set_title("Zooming {}, loss\_rate {}".format(zooming_speed, loss_rate))
    ax.set_ylabel('Bandwidth ({})'.format(bw_ref))
    ax.set_xlabel('Time (s)')

    plt.ylim(bottom=0, top=max_value)

    for i, prefix in enumerate(ips_data):
        prefix = transform_bw(prefix, bw)
        x = [x[0] for x in prefix][:-1]
        y = [x[1] for x in prefix][:-1]
        loss = [x[3] for x in prefix][:-1]
        ax.plot(x, y, label="Prefix {}".format(i))

    ax.legend(loc=0)

    fig.tight_layout()
    plt.savefig(out_name)


# "../plot_inputs/tofino/zooming_outputs/"


def many_plot_one_iperf_output(
        path_prefix, ips, bw_rates, loss_rates, zooming_speed):
    for bw in bw_rates:
        for loss_rate in loss_rates:
            out_name = "tofino_zooming_{}_{}.pdf".format(bw, loss_rate)
            plot_one_iperf_output(path_prefix, ips, bw,
                                  loss_rate, zooming_speed, out_name)


# Plot all together in one plot (zooming and dedicated counter entries)
bw = 50000
ips_setup = [("11.0.2.2", 31000)]
loss_rates = [1, 0.1, 0.01]
zooming_speed = 0.2


def plot_tofino_dedicated_zooming(
        path_to_inputs, ips, bw, loss_rates, zooming_speed,
        out_name, seed=""):
    """Plots tofino plot

    Args:
        path_to_dedicated (_type_): _description_
        path_to_zooming (_type_): _description_
        ips (_type_): _description_
        bw (_type_): _description_
        loss_rates (_type_): _description_
        zooming_speed (_type_): in seconds
        out_name (_type_): _description_
        seed (str): if we have multiple seeds we can look into the dir
    """
    # reset params
    set_rc_params()

    data_zooming_per_loss = {}
    data_dedicated_per_loss = {}

    path_to_zooming = f"{path_to_inputs}/zooming_outputs/"
    path_to_dedicated = f"{path_to_inputs}/dedicated_outputs/"

    # if seed
    if seed:
        path_to_zooming += f"{seed}/"
        path_to_dedicated += f"{seed}/"

    for loss_rate in loss_rates:
        data_zooming_per_loss[loss_rate] = parse_iperf_outputs(
            path_to_zooming, ips, bw, loss_rate, zooming_speed)
        data_dedicated_per_loss[loss_rate] = parse_iperf_outputs(
            path_to_dedicated, ips, bw, loss_rate, None)

    # max bw always in Mbitssec
    # up to 1G
    if bw <= 1000:
        bw_ref = "Mbits/sec"
        max_value = bw + (bw * 0.2)
    elif bw > 1000:
        bw_ref = "Gbits/sec"
        max_value = bw / 1000 + ((bw / 1000 * 0.2))

    # Create subplots (horitzontal placement)
    fig = plt.figure()

    #ax = fig.add_subplot(1, 1, 1)
    ax_dedicated = fig.add_subplot(2, 1, 1)
    ax_zooming = fig.add_subplot(2, 1, 2)

    fig.text(0.5, 0.01, 'Time (s)', ha='center', va='center', fontsize=11)
    fig.text(0.01, 0.5, 'Bandwidth ({})'.format(bw_ref), ha='center',
             va='center', rotation='vertical', fontsize=11)

    ax_dedicated.set_ylim(bottom=0, top=max_value)
    ax_dedicated.set_xlim(left=0, right=5)

    ax_dedicated.set_yticks([0, 25, 50])
    #ax_dedicated.set_yticklabels([0, 25, 50], fontweight='normal')

    props = dict(boxstyle='round', facecolor='white', alpha=1)
    # place a text box in upper left in axes coords
    ax_dedicated.text(0.65, 0.5, "Dedicated entry",
                      transform=ax_dedicated.transAxes, fontsize=8,
                      verticalalignment='top', bbox=props)

    for loss_rate, data in data_dedicated_per_loss.items():
        prefix = transform_bw(data[0], bw)
        x = [x[0] for x in prefix][:-1]
        y = [x[1] for x in prefix][:-1]
        loss = [x[3] for x in prefix][:-1]
        ax_dedicated.plot(
            x, y, linewidth=1, label="Loss {}\%".format(
                int(loss_rate * 100)))

    ax_dedicated.legend(loc=0)

    # Zooming subplot

    #ax_zooming.set_title("Zooming {}, loss\_rate {}".format(zooming_speed, loss_rate))
    #ax_zooming.set_ylabel('Bandwidth ({})'.format(bw_ref))

    ax_zooming.set_ylim(bottom=0, top=max_value)
    ax_zooming.set_xlim(left=0, right=5)

    ax_zooming.set_yticks([0, 25, 50])

    props = dict(boxstyle='round', facecolor='white', alpha=1)
    # place a text box in upper left in axes coords
    ax_zooming.text(0.65, 0.5, "Hash-based entry",
                    transform=ax_zooming.transAxes, fontsize=8,
                    verticalalignment='top', bbox=props)

    for loss_rate, data in data_zooming_per_loss.items():
        prefix = transform_bw(data[0], bw)
        x = [x[0] for x in prefix][:-1]
        y = [x[1] for x in prefix][:-1]
        loss = [x[3] for x in prefix][:-1]
        ax_zooming.plot(
            x, y, linewidth=1, label="Loss {}\%".format(
                int(loss_rate * 100)))

    ax_zooming.legend(loc=0)

    fig.tight_layout()
    plt.savefig(out_name)
