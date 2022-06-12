from fancy.visualizations import *
import pickle


def precompute_uniform_drops(
        input_dir, output_dir, loss_rates=[1, 0.75, 0.5, 0.1, 0.01, 0.001],
        zooming_speeds=[200],
        switch_delays=[1000, 5000, 10000],
        num_prefixes=[1000, 10000]):

    os.system("mkdir -p {}".format(output_dir))

    data = {}
    for zooming_speed in zooming_speeds:
        for switch_delay in switch_delays:
            for num_prefix in num_prefixes:
                eval_key = (zooming_speed, switch_delay, num_prefix)
                data[eval_key] = {}
                for loss_rate in loss_rates:

                    data[eval_key][loss_rate] = {
                        "tpr": 0, "avg_detection_time": 0, "detection_times": [],
                        "faulty_entries": []}

                    specs = {
                        "ProbingTimeZoomingMs": ("%6.6f" % zooming_speed).strip(),
                        "FailDropRate": ("%6.6f" % loss_rate).strip(),
                        "SwitchDelay": str(switch_delay),
                        "NumPrefixes": str(num_prefix)
                    }

                    experiment_runs = get_specific_tests_info(input_dir, specs)

                    for run in experiment_runs:
                        sim_info = load_sim_info_file(run)
                        fail_time = float(sim_info["FailTime"])
                        outputs_dir_base = sim_info["OutDirBase"]
                        sim_out = load_simulation_out(
                            outputs_dir_base + "_s1.json")

                        if sim_out['uniform_failures']:
                            detection_time = sim_out['uniform_failures'][0][
                                'timestamp'] - fail_time
                            data[eval_key][loss_rate]["detection_times"].append(
                                detection_time)
                            data[eval_key][loss_rate]["faulty_entries"].append(
                                sim_out['uniform_failures'][0]['faulty_entries'])

                    # compute stats

                    data[eval_key][loss_rate]["tpr"] = len(
                        data[eval_key][loss_rate]["detection_times"]) / len(experiment_runs)

                    data[eval_key][loss_rate]["avg_detection_time"] = np.mean(
                        data[eval_key][loss_rate]["detection_times"])

    output_file = "{}/fancy_uniform.pickle".format(
        output_dir)
    pickle.dump(data, open(output_file, "wb"))

    return data


def print_uniform_random_drops_table(
        input_file, output_file=""):
    """Gracefully prints the output of uniform drops experiments

    Args:
        input_file (_type_): _description_
        output_file (_type_): _description_
    """

    # import uniform loss data
    data = pickle.load(open(input_file, "rb"))

    # table heading
    heading = "{:>8} {:>14} {:>14}"

    # output string to save and print
    out_str = ""

    for params, info in data.items():
        # the columns we want to see
        columns = ['tpr', 'avg_detection_time']

        zooming_speed, switch_delay, num_prefixes = params

        headers = [""] + columns
        out_str += "Uniform random loss. Zooming: {}, Num Prefixes: {}".format(
            zooming_speed, num_prefixes) + "\n"

        heading_str = heading.format(*headers)
        out_str += heading_str + "\n"

        # print the run info
        for loss, run_info in info.items():
            # get the fields we want
            _values = [run_info[x] for x in columns]
            headers = [loss] + [round(x, 5) for x in _values]
            heading_str = heading.format(*headers)
            out_str += heading_str + "\n"
        out_str += "\n"
    out_str += "\n"

    # print table
    print(out_str)

    # save table
    if output_file:
        with open(output_file, "w") as fp:
            fp.write(out_str)
