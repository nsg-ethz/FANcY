from fancy.file_loader import *
import _pickle as pickle
import os.path
import multiprocessing
import glob
import random

WEAK_BIN = 1
STRONG_BIN = 5

"""
Frequency and zooming opportunities functions
"""


def get_empty_prefix_packet_frequency(ts_start, ts_end, slice_size):
    parsed_info = []
    while ts_start <= ts_end:
        parsed_info.append((ts_start, min(ts_start + slice_size, ts_end), 0))
        ts_start = ts_start + slice_size
    return parsed_info


def _get_prefix_packet_frequency(
        prefix_ts, ts_start, ts_end=None, slice_size=1, loss_rate=1):
    """
    This function gets time windows and counts from packet time stamps. For that you need to
    give the first and last timestamp and the time slice you want to consider in seconds.
    For example 5ms = 5/1000
    Args:
        prefixes_ts_file: dictionary with prefixes and timestamps
        ts_start: start timestamp to check
        ts_end: end timestamp to check
        slice_size: time slize we count (window size)

    Returns:

    """

    assert (slice_size > 0)
    assert (loss_rate <= 1 and loss_rate > 0)

    slice_size = Decimal(str(slice_size))

    if not prefix_ts and (not ts_start or not ts_end):
        print("Warning.. Prefix not found in trace. Please provide start and end ts")
        return [], 0

    parsed_info = []
    i = 0
    global_packet_counter = 0

    # for empty prefixes we make an list with 0s everywhere
    if not prefix_ts:
        parsed_info = get_empty_prefix_packet_frequency(
            ts_start, ts_end, slice_size)

    # normal case
    else:
        # just in case.
        if not ts_end:
            ts_end = prefix_ts[-1]

        if not ts_start:
            ts_start = prefix_ts[0]

        pkt_counter = 0
        while True:

            ts = prefix_ts[i]

            # stop running
            if ts_start >= ts_end:
                break
            # print(ts_start, ts_start+slice_size, ts)

            state2 = False

            # we are too far from the start
            if (ts_start) > ts:
                #parsed_info += (ts_start, ts_start + slice_size, 0)
                # no we should not count!!!
                i += 1

            # inside the slice
            elif ts_start <= ts and min((ts_start + slice_size), ts_end) >= ts:
                pkt_counter += 1
                i += 1
                global_packet_counter += 1
                state2 = True

            elif ts > min((ts_start + slice_size), ts_end):
                parsed_info.append(
                    (ts_start, min((ts_start + slice_size), ts_end), pkt_counter))
                pkt_counter = 0
                ts_start = min((ts_start + slice_size), ts_end)

            # all packets ?
            if i == len(prefix_ts):
                if state2:
                    parsed_info.append(
                        (ts_start, min((ts_start + slice_size), ts_end), pkt_counter))
                break

    if loss_rate < 1:
        parsed_info, global_packet_counter = apply_loss_rate_to_prefix_packet_frequency(
            parsed_info, loss_rate)

    return parsed_info, global_packet_counter


def apply_loss_rate_to_prefix_packet_frequency(
        prefix_packet_frequency, loss_rate=1):
    """
    Addapts the packet frequency to a packet loss.
    Args:
        prefix_packet_frequency:
        loss_rate:

    Returns:

    """
    # random.seed(1)
    new_prefix_frequency = []

    for start, end, pkt_count in prefix_packet_frequency:

        probabilities = [random.uniform(0, 1) for _ in range(pkt_count)]
        new_pkt_count = sum([1 for x in probabilities if x <= loss_rate])
        new_prefix_frequency.append((start, end, new_pkt_count))

    #previous_total_packets = sum([x[2] for x in prefix_packet_frequency])
    total_packets = sum([x[2] for x in new_prefix_frequency])

    #print(previous_total_packets, total_packets)
    return new_prefix_frequency, total_packets


def prefix_zooming_performance(
        packet_frequency, tree_depth=5, weak_threshold=1, strong_threshold=5):
    """
    Gets the performance given some packet frequencies, tree depth and others
    Args:
        packet_frequency:
        tree_depth:
        weak_threshold:
        strong_threshold:
        loss_rate:
    Returns:

    """

    weak_max_consecutive_bins = 0
    weak_zooming_opportunities = 0
    weak_current_consecutive_bins = 0
    weak_total_bins = 0
    weak_first_zooming_opportunity = -1

    strong_max_consecutive_bins = 0
    strong_zooming_opportunities = 0
    strong_current_consecutive_bins = 0
    strong_total_bins = 0
    strong_first_zooming_opportunity = -1

    for start_ts, end_ts, count in packet_frequency:
        if count >= weak_threshold:
            weak_current_consecutive_bins += 1
            weak_total_bins += 1
            if weak_current_consecutive_bins >= tree_depth:
                if weak_first_zooming_opportunity == -1:
                    weak_first_zooming_opportunity = start_ts
                weak_zooming_opportunities += 1

            if weak_current_consecutive_bins > weak_max_consecutive_bins:
                weak_max_consecutive_bins = weak_current_consecutive_bins

        else:
            weak_current_consecutive_bins = 0

        if count >= strong_threshold:
            strong_current_consecutive_bins += 1
            strong_total_bins += 1
            if strong_current_consecutive_bins >= tree_depth:
                strong_zooming_opportunities += 1
                if strong_first_zooming_opportunity == -1:
                    strong_first_zooming_opportunity = start_ts

            if strong_current_consecutive_bins > strong_max_consecutive_bins:
                strong_max_consecutive_bins = strong_current_consecutive_bins
        else:
            strong_current_consecutive_bins = 0

    return weak_total_bins, weak_max_consecutive_bins, weak_zooming_opportunities, weak_first_zooming_opportunity,\
        strong_total_bins, strong_max_consecutive_bins, strong_zooming_opportunities, strong_first_zooming_opportunity


def get_prefix_zooming_oportunity_range(
        prefix_ts, start_ts, end_ts, tree_depth, zooming_speeds,
        cached_frequencies=None, loss_rate=1):

    zooming_opportunities = []
    detection_time = []

    for speed in zooming_speeds:
        # milliseconds zooming speed
        _speed = Decimal(speed) / Decimal(1000)
        packet_frequency, num_packets = get_prefix_packet_frequency(
            prefix_ts, start_ts, end_ts, _speed, cached_frequencies, loss_rate)

        # we do not take it into account
        if num_packets < tree_depth:
            return [], 0

        # build a local cached frequencies to speed the thing up
        if ((not cached_frequencies) and ((num_packets / loss_rate) > 1000)):
            if not cached_frequencies:
                cached_frequencies = {
                    'num_packets': num_packets,
                    "frequencies": {_speed: packet_frequency}}

        elif cached_frequencies and (len(cached_frequencies["frequencies"]) < 2):
            cached_frequencies["frequencies"][_speed] = packet_frequency

        weak_total_bins, \
            weak_max_consecutive_bins, \
            weak_zooming_opportunities, \
            weak_first_zooming_opportunity, \
            strong_total_bins, \
            strong_max_consecutive_bins, \
            strong_zooming_opportunities, \
            strong_first_zooming_opportunity = prefix_zooming_performance(packet_frequency, tree_depth, WEAK_BIN, STRONG_BIN)

        zooming_opportunities.append(
            (_speed, weak_zooming_opportunities, strong_zooming_opportunities))
        detection_time.append((_speed, (speed * tree_depth)))

    return zooming_opportunities, detection_time


def get_prefix_best_zooming_speed(
        prefix_ts, start_ts, end_ts, tree_depth, zooming_speeds,
        cached_frequencies=None, loss_rate=1):
    """

    Args:
        prefix_ts:
        start_ts:
        end_ts:
        tree_depth:
        zooming_speeds:

    Returns:
    """

    zooming_opportunities, _ = get_prefix_zooming_oportunity_range(
        prefix_ts, start_ts, end_ts, tree_depth, zooming_speeds,
        cached_frequencies, loss_rate)
    if not zooming_opportunities:
        return (0, 0), (0, 0), get_empty_zooming_opportunities(zooming_speeds)
    weak_best = sorted(
        zooming_opportunities, key=lambda x: x[1],
        reverse=True)[0]
    strong_best = sorted(
        zooming_opportunities, key=lambda x: x[2],
        reverse=True)[0]
    return weak_best, strong_best, zooming_opportunities


def get_prefix_packet_frequency(
        prefix_ts, ts_start, ts_end=None, slice_size=1,
        cached_frequencies=None, loss_rate=1):

    # check if we can fast build the packet frequencies
    if cached_frequencies:  # {"frequencies": {}, "num_packets": int}
        res = get_modified_packet_frequency(
            cached_frequencies, ts_start, ts_end, slice_size)
        if res:
            return res[0], res[1]

    # otherwise we do it from 0
    return _get_prefix_packet_frequency(
        prefix_ts, ts_start, ts_end, slice_size, loss_rate)


"""
Zooming opportunities stuff
"""


def get_empty_zooming_opportunities(speeds):
    """
    Returns a list of empty zooming opportunities (used for consistency)
    Args:
        speeds:

    Returns:

    """

    return [(Decimal(x) / Decimal(1000), 0, 0) for x in speeds]


def speeds_to_ms_decimals(speeds):
    """
    Returns the decimals in miliseconds of a list of speeds
    Args:
        speeds:

    Returns:

    """
    if speeds and type(speeds[0]) == Decimal:
        return speeds

    return [Decimal(x) / Decimal(1000) for x in speeds]


def get_only_detectable_raw_opportunities(raw_opportunities):

    new_raw_opportunities = []

    for opportunities in raw_opportunities:
        # sums weak and strong?
        opp = sum(x[1] + x[2] for x in opportunities["zooming_opportunities"])
        if opp:
            new_raw_opportunities.append(opportunities)

    return new_raw_opportunities


def get_raw_zooming_opportunities(
        trace_base_path, prefix_list, tree_depth, speeds, duration=0,
        loss_rate=1):
    """
    Returns a list of dictionaries with prefix and zooming opportunities per zooming speed.
    Args:
        trace_base_path:
        prefix_list:
        tree_depth:
        speeds:
        duration:

    Returns:
    """

    trace_ts = load_trace_ts(trace_base_path + ".info".format(slice))
    prefixes_ts = load_prefixes_ts_raw(trace_base_path + ".ts".format(slice))

    start_ts = trace_ts[0]
    if not duration:
        end_ts = trace_ts[1]
    else:
        end_ts = start_ts + Decimal(duration)

    # load_prefixes_packet_frequency(trace_base_path, end_ts-start_ts, prefix_list, [5,10])
    cached_prefixes_packet_frequency = {}

    zooming_opportunities_data = []
    # print(len(prefix_list))
    for prefix in prefix_list:
        # print(i)
        prefix_ts = prefixes_ts.get(prefix, [])
        if prefix_ts:
            if type(prefix_ts) == dict:
                prefix_ts = prefix_ts['ts']

        # if there is not even dt
        #print("packets: {}".format(len(prefix_ts)))
        if len(prefix_ts) < tree_depth:
            # ADD THIS IF I WANT TO TAKE PREFIXES INTO ACCOUNT
            zooming_opportunities_data.append(
                {"prefix": prefix, "zooming_opportunities": get_empty_zooming_opportunities(speeds)})
            continue

        # here it gets cleared
        cached_frequencies = cached_prefixes_packet_frequency.get(prefix, None)
        #print(prefix, len(prefix_ts), bool(cached_frequencies))
        best_weak_zooming, best_strong_zooming, zooming_opportunities = get_prefix_best_zooming_speed(
            prefix_ts, start_ts, end_ts, tree_depth, zooming_speeds=speeds, cached_frequencies=cached_frequencies, loss_rate=loss_rate)
        # we add empty prefixes
        if zooming_opportunities:
            zooming_opportunities_data.append(
                {"prefix": prefix, "zooming_opportunities": zooming_opportunities})

    return zooming_opportunities_data


def get_zooming_opportunities_absolute(
        speed_to_detectable_prefixes, num_prefixes):
    """
    Returns the absolute number of prefixes per zooming speed.
    Args:
        speed_to_detectable_prefixes:

    Returns:

    """

    absolute_zooming_oportunities = OrderedDict()
    for speed, info in speed_to_detectable_prefixes.items():
        absolute_zooming_oportunities[speed] = {
            'weak': len(info['weak']) / num_prefixes,
            'strong': len(info['strong']) / num_prefixes}

    return absolute_zooming_oportunities


def get_zooming_opportunities_absolute2(
        zooming_opportunities, min_weak_opportunities=5,
        min_strong_opportunities=2):
    """
    For each speed it returns the absolute share of prefixes that are detectable
    Args:
        zooming_opportunities:  list of [{'prefix': x, 'zooming_opportunities' :[Decimal, weak, strong]}, {}]
        min_weak_opportunities: int
        min_strong_opportunities: int

    Returns:
    """

    absolute_zooming_oportunities = {
        x: {'weak': 0, 'strong': 0}
        for x
        in [y[0] for y in zooming_opportunities[0]["zooming_opportunities"]]}

    num_prefixes = len(zooming_opportunities)

    for zooming_opportunity in zooming_opportunities:
        _zooming_opportunities = zooming_opportunity["zooming_opportunities"]

        for speed, weak_op, strong_op in _zooming_opportunities:

            if weak_op >= min_weak_opportunities:
                absolute_zooming_oportunities[speed]["weak"] += (
                    1 / num_prefixes)

            if strong_op >= min_strong_opportunities:
                absolute_zooming_oportunities[speed]["strong"] += (
                    1 / num_prefixes)

    # just in case this is not python 3.7
    _absolute_zooming_oportunities = OrderedDict()
    for k, v in sorted(
            absolute_zooming_oportunities.items(),
            key=lambda x: x[0]):
        _absolute_zooming_oportunities[k] = v

    return _absolute_zooming_oportunities


def get_zooming_opportunities_only_topX(zooming_opportunities, topX=1):
    """
    Takes the zooming opportunities sorts them by weak and strong then just takes topX
    then builds a list with the same "time slots" and just counts +1 where there is a weak or strong.

    Args:
        zooming_opportunities:
        topX:

    Returns:

    """

    _new_zooming_opportunities = []

    if topX >= len(zooming_opportunities):
        topX = len(zooming_opportunities)

    weak_best = sorted(
        zooming_opportunities, key=lambda x: x[1],
        reverse=True)[
        : topX]
    strong_best = sorted(
        zooming_opportunities, key=lambda x: x[2],
        reverse=True)[
        : topX]

    for opportunity in zooming_opportunities:

        _speed, _, _ = opportunity
        current_weak = 0
        current_strong = 0

        # try to find that speed in weak_best and strong_best
        for _speed2, weak, strong in weak_best:
            if _speed2 == _speed:
                current_weak = 1

        for _speed2, weak, strong in strong_best:
            if _speed2 == _speed:
                current_strong = 1

        _new_zooming_opportunities.append(
            (_speed, current_weak, current_strong))

    return _new_zooming_opportunities


def get_zooming_opportunities_per_type_with_only_top_x(
        zooming_opportunities_data, topX=5):
    """
    Sums all the opportunities
    Args:
        zooming_opportunities_data:
        topX:

    Returns:

    """

    total_zooming_opportunities = []
    detected_zooming_opportunities = []
    not_detected_zooming_opportunities = []

    if topX >= len(zooming_opportunities_data[0]):
        topX = len(zooming_opportunities_data[0])

    for _zooming_opportunities in zooming_opportunities_data:

        detection_time, _type, zooming_opportunities = [
            _zooming_opportunities
            [x]
            for x
            in
            ["detection_time",
             "type",
             "zooming_opportunities"]]

        only_top_zooming_opportunities = get_zooming_opportunities_only_topX(
            zooming_opportunities,
            topX)

        if not total_zooming_opportunities:
            total_zooming_opportunities = [
                (0, 0, 0)] * len(only_top_zooming_opportunities)
        for i, element in enumerate(only_top_zooming_opportunities):

            total_zooming_opportunities[i] = (
                element[0],
                total_zooming_opportunities[i][1] + element[1],
                total_zooming_opportunities[i][2] + element[2])

        if detection_time == -1:
            if not not_detected_zooming_opportunities:
                not_detected_zooming_opportunities = [
                    (0, 0, 0)] * len(only_top_zooming_opportunities)
            for i, element in enumerate(only_top_zooming_opportunities):
                not_detected_zooming_opportunities[i] = (
                    element[0], not_detected_zooming_opportunities[i][1] + element[1],
                    not_detected_zooming_opportunities[i][2] + element[2])

        else:
            if not detected_zooming_opportunities:
                detected_zooming_opportunities = [
                    (0, 0, 0)] * len(only_top_zooming_opportunities)
            for i, element in enumerate(only_top_zooming_opportunities):
                detected_zooming_opportunities[i] = (
                    element[0], detected_zooming_opportunities[i][1] + element[1],
                    detected_zooming_opportunities[i][2] + element[2])

    return total_zooming_opportunities, detected_zooming_opportunities, not_detected_zooming_opportunities


def get_zooming_opportunities_per_type_with_cap(
        zooming_opportunities_data, cap=100):
    """
    counts the oportunities in each "zooming bin" however this ends up adding too much to the faster
    bins.
    Args:
        zooming_opportunities_data:
        cap:

    Returns:

    """

    total_zooming_opportunities = []
    detected_zooming_opportunities = []
    not_detected_zooming_opportunities = []

    if cap <= 0:
        cap = 10000000

    for _zooming_opportunities in zooming_opportunities_data:

        detection_time, _type, zooming_opportunities = [
            _zooming_opportunities
            [x]
            for x
            in
            ["detection_time",
             "type",
             "zooming_opportunities"]]

        if not total_zooming_opportunities:
            total_zooming_opportunities = [
                (0, 0, 0)] * len(zooming_opportunities)
        for i, element in enumerate(zooming_opportunities):
            weak = min(element[1], cap)
            strong = min(element[2], cap)
            total_zooming_opportunities[i] = (
                element[0],
                total_zooming_opportunities[i][1] + weak,
                total_zooming_opportunities[i][2] + strong)

        if detection_time == -1:
            if not not_detected_zooming_opportunities:
                not_detected_zooming_opportunities = [
                    (0, 0, 0)] * len(zooming_opportunities)
            for i, element in enumerate(zooming_opportunities):
                weak = min(element[1], cap)
                strong = min(element[2], cap)
                not_detected_zooming_opportunities[i] = (
                    element[0],
                    not_detected_zooming_opportunities[i][1] + weak,
                    not_detected_zooming_opportunities[i][2] + strong)

        else:
            if not detected_zooming_opportunities:
                detected_zooming_opportunities = [
                    (0, 0, 0)] * len(zooming_opportunities)
            for i, element in enumerate(zooming_opportunities):
                weak = min(element[1], cap)
                strong = min(element[2], cap)
                detected_zooming_opportunities[i] = (
                    element[0],
                    detected_zooming_opportunities[i][1] + weak,
                    detected_zooming_opportunities[i][2] + strong)

    return total_zooming_opportunities, detected_zooming_opportunities, not_detected_zooming_opportunities


"""
Save and Load Prefix Frequencies for a speed up.
"""


def get_modified_packet_frequency(
        original_frequencies, start_ts, end_ts, new_speed):
    """

    Args:
        original_frequencies:
        original_speed:
        new_speed:
        start_ts:
        end_ts:

    Returns:

    """

    # 1. find if there is any good divisor
    available_zooming_speeds = original_frequencies['frequencies'].keys()

    # do we already have this in the cache? do we have to trim it?
    if new_speed in available_zooming_speeds:
        # maybe a bad idea
        # if end_ts:
        #    new_frequencies, new_num_packets = trim_prefix_packet_frequency(original_frequencies['frequencies'][new_speed], start_ts, end_ts)
        #    return new_frequencies, new_num_packets
        return original_frequencies['frequencies'][new_speed], original_frequencies["num_packets"]

    # 2. Check if the available sizes can be used to build new size
    else:
        # find the largest divisor so we can enhance the list
        reference_zooming_speed = find_largest_divisor(
            new_speed, available_zooming_speeds)
        if reference_zooming_speed:
            # maybe bad idea to remove this
            # if end_ts:
            #    new_frequencies, new_num_packets = trim_prefix_packet_frequency(original_frequencies['frequencies'][reference_zooming_speed], start_ts, end_ts)
            #    new_frequencies = transform_prefix_packet_frequency(new_frequencies, reference_zooming_speed, new_speed)
            #    return new_frequencies, new_num_packets
            #
            # else: # we do not trim we just transform
            new_frequencies = transform_prefix_packet_frequency(
                original_frequencies['frequencies'][reference_zooming_speed],
                reference_zooming_speed, new_speed)
            return new_frequencies, original_frequencies["num_packets"]

        else:
            return None

    return None


def trim_prefix_packet_frequency(original_frequencies, start_ts, end_ts):
    """
    Takes packet frequencies and only keeps the bins within some times
    Args:
        original_frequencies:
        start_ts:
        end_ts:

    Returns:

    """

    trimmed_frequencies = []
    packets = 0
    for start, end, count in original_frequencies:
        if start >= start_ts and end <= end_ts:
            trimmed_frequencies.append((start, end, count))
            packets += count

    return trimmed_frequencies, packets


def transform_prefix_packet_frequency(
        original_frequencies, original_speed, new_speed):
    """
    Transforms the frequencies. New speed needs to be bigger and a multiple of original speed.
    Args:
        original_frequencies:
        original_speed:
        new_speed:

    Returns:

    """

    assert(new_speed > original_speed)
    assert(new_speed % original_speed == 0)

    transform_factor = int(new_speed / original_speed)

    transformed_frequencies = []

    for i in range(0, len(original_frequencies), transform_factor):

        sub_list = original_frequencies[i: i + transform_factor]
        new_pkt_count = sum([x[-1] for x in sub_list])
        # takes first time stamp and last, and packet count in that period
        transformed_frequencies.append(
            (sub_list[0][0], sub_list[-1][1], new_pkt_count))

    return transformed_frequencies


def find_largest_divisor(number, candidates):
    """
    Finds biggest divisor
    Args:
        number:
        candidates:

    Returns:

    """
    candidates = sorted(candidates, reverse=True)
    for candidate in candidates:
        if number % candidate == 0:
            return candidate

    return None


def load_prefixes_packet_frequency(
        inputs_dir_base, send_duration, prefix_list, zooming_speeds):
    """
    Loads the precomputed prefixes packet frequencies file. loads it for a list of prefixes

    1) Only loads the desired prefixes into memory
    2) Adapts the frequencies to a specific duration
    3) Only keeps the desired zooming speeds. If they dont exist it tries to compute them

    Args:
        info_file:
        prefix_list:
        zooming_speeds:

    Returns:

    """

    trace_ts = load_trace_ts(inputs_dir_base + ".info")
    start_ts = trace_ts[0]
    end_ts = start_ts + Decimal(send_duration)

    if os.path.isfile(inputs_dir_base + ".frequencies"):
        pre_prefixes_pkt_freq = pickle.load(
            open(inputs_dir_base + ".frequencies", "rb"))
    else:
        pre_prefixes_pkt_freq = {}

    loaded_prefixes_pkt_freq = {}

    for prefix in prefix_list:
        all_frequencies = pre_prefixes_pkt_freq.get(prefix, None)
        if all_frequencies:  # may include multiple zooming speeds
            # trim frequencies to from beginning to start+duration
            loaded_prefixes_pkt_freq[prefix] = {
                'frequencies': {}, 'num_packets': 0}
            for zooming_speed, frequencies in all_frequencies['frequencies'].items():
                new_frequencies, new_num_packets = trim_prefix_packet_frequency(
                    frequencies, start_ts, end_ts)
                loaded_prefixes_pkt_freq[prefix]['frequencies'][
                    zooming_speed] = new_frequencies
                loaded_prefixes_pkt_freq[prefix]['num_packets'] = new_num_packets

            # add new zooming speed if they are multiple of the current ones
            for new_zooming_speed in zooming_speeds:
                _speed = Decimal(new_zooming_speed) / Decimal(1000)
                available_zooming_speeds = loaded_prefixes_pkt_freq[prefix][
                    'frequencies'].keys()
                if _speed not in available_zooming_speeds:
                    # find the largest divisor so we can enhance the list
                    reference_zooming_speed = find_largest_divisor(
                        _speed, available_zooming_speeds)
                    # if we find a divisor we add the transformed list
                    if reference_zooming_speed:
                        transformed_frequencies = transform_prefix_packet_frequency(
                            loaded_prefixes_pkt_freq[prefix]['frequencies'][reference_zooming_speed], reference_zooming_speed, _speed)

                        loaded_prefixes_pkt_freq[prefix]['frequencies'][
                            _speed] = transformed_frequencies

    return loaded_prefixes_pkt_freq


def precompute_prefixes_packet_frequency(
        trace_path, zooming_speeds, top_max=0):
    """
    Stores the packet frequencies for some prefixes. This is typically used only for
    top prefixes, otherwise it is not even worth to use.
    Args:
        trace_path:
        zooming_speeds:
        top_max:

    Returns:

    """

    prefixes_ts = load_prefixes_ts_raw("{}.ts".format(trace_path))
    start_ts, end_ts = load_trace_ts("{}.info".format(trace_path))

    if top_max:
        top_prefixes = list(load_top_prefixes_dict(
            "{}.top".format(trace_path)).keys())[:top_max]

    prefixes_packet_frequency = {}

    for prefix, timestamps in prefixes_ts.items():
        if top_max and prefix in top_prefixes:
            prefixes_packet_frequency[prefix] = {
                'frequencies': {}, 'num_packets': 0}
            for zooming_speed in zooming_speeds:
                _speed = Decimal(zooming_speed) / Decimal(1000)
                packet_frequency, num_packets = _get_prefix_packet_frequency(
                    timestamps,
                    start_ts,
                    end_ts,
                    _speed)
                prefixes_packet_frequency[prefix]['frequencies'][_speed] = packet_frequency
                prefixes_packet_frequency[prefix]['num_packets'] = num_packets

    pickle.dump(prefixes_packet_frequency, open(
        "{}.frequencies".format(trace_path), "wb"))


def precompute_prefixes_frequencies_many(
        traces_path, zooming_speeds, top_max=0, num_processes=10):
    """
    Preocumputes the frequencies for all the slices we find in the traces_path directory
    Args:
        traces_path:
        zooming_speeds:
        top_max:
        num_processes:

    Returns:

    """

    pool = multiprocessing.Pool(num_processes)
    traces = glob.glob(traces_path)

    for trace in traces:
        trace_name = trace.split("/")[-1]
        slices = [x.replace(".ts", "")
                  for x in glob.glob(trace + "/" + "*_*.ts")]
        for slice in slices:
            print(slice)
            pool.apply_async(
                precompute_prefixes_packet_frequency,
                (slice, zooming_speeds, top_max),
                {})


"""
Deprecated Stuff
"""


@deprecated(reason="deprecated in favour of get_prefix_packet_frequency")
def packets_sent_in_time_frame(packet_frequencies, start_ts, end_ts):
    """
    Returns the number of packets between start and end. It is better to use
    get_prefix_packet_frequency.
    Args:
        packet_frequencies:
        start_ts:
        end_ts:

    Returns:

    """
    packets = 0
    for start, end, count in packet_frequencies:
        if start >= start_ts and end <= end_ts:
            packets += count

    return packets


"""
Timestamps modifiers
"""


def prefixes_ts_to_flat_ts(prefixes_ts):
    """
    Loads all the timestamps in flat. We get them from a prefixes_ts file
    Args:
        prefixes_ts:

    Returns:

    """

    ts = []
    for v in prefixes_ts.values():
        ts += v

    return sorted(ts)


def scale_prefixes_ts(prefixes_ts, first_ts, scale_factor):
    """
    Computes the prefixes timestamps for a scaled trace. It gets an
    approximation of the real sent timestamps. Getting the real values is
    very very hard.
    Args:
        prefixes_ts:
        scale_factor:

    Returns:

    """

    scaled_prefixes_ts = {}
    scale_factor = Decimal(str(scale_factor))
    for prefix, timestamps in prefixes_ts.items():
        scaled_timestamps = [(first_ts + ((x - first_ts) * scale_factor))
                             for x in timestamps]
        scaled_prefixes_ts[prefix] = scaled_timestamps

    return scaled_prefixes_ts


def find_last_ts_before(prefix_ts, last_time):
    """
    Finds less valid timestamp for a given prefix
    before before some other time
    Args:
        prefix_ts:
        last_time:

    Returns:

    """
    last_ts = -1
    for ts in prefix_ts:
        if ts <= last_time:
            last_ts = ts
        else:
            break

    return last_ts
