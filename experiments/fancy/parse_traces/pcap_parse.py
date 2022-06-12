import multiprocessing
import struct
import socket
import _pickle as cPickle
from decimal import Decimal
import math
import random
import numpy as np

from scapy.all import RawPcapReader, DLT_EN10MB, DLT_RAW_ALT, DLT_PPP

from fancy.utils import LimitedSizeDict, run_cmd, find_files_in_dir, check_memory
from fancy.logger import log


TH_FIN = 0b1
TH_SYN = 0b10
TH_RST = 0b100
TH_PUSH = 0b1000
TH_ACK = 0b10000
TH_URG = 0b100000
TH_ECE = 0b1000000
TH_CWR = 0b10000000

# constants
IP_LEN = 20
IPv6_LEN = 40
UDP_LEN = 8
TCP_LEN = 14


all_traces = [
    'equinix-chicago.dirB.20140619', 'equinix-nyc.dirA.20180419',
    'equinix-nyc.dirB.20180816', 'equinix-nyc.dirB.20190117']

"""Helpers"""


def get_inter_packet_arrivals(timestamps):

    inter_packet_arrivals = []
    for i, ts in enumerate(timestamps):
        if i == len(timestamps) - 1:
            break
        inter_packet_arrivals.append(timestamps[i + 1] - ts)
    return inter_packet_arrivals


def takes_spread_elements(sequence, num):
    """

    Args:
        sequence:
        num:
        extra:

    Returns:

    """

    length = float(len(sequence))
    for i in range(num):
        yield sequence[int(math.ceil(i * length / num))]


def get_cdf_points(data, num_points_in_cdf):
    """
    From a list of sorted elements we get a CDF of X points
    Args:
        column:
        num_points_in_cdf:
        extra:

    Returns:
    """

    data = sorted(data)

    if num_points_in_cdf > len(data):
        return data

    elements = list(takes_spread_elements(data, num_points_in_cdf))
    #elements[0] = data[0]
    #elements[-1] = data[-1]
    return elements


def compress_prefix_data(prefix_data, compression_value=10000):
    """
    Compresses all the timestamp diff collected (inter-packet times),
    adds them to the CDF and compresses the CDF.
    Args:
        prefix_data: data  to compress
        compression_value:  compression of the CDF

    Returns:

    """

    for element in prefix_data:
        num_ts = len(prefix_data[element]['ts'])
        if num_ts > 1:
            compress_by = min(num_ts, compression_value)
            intervals = get_inter_packet_arrivals(prefix_data[element]['ts'])
            prefix_data[element]['interpacket'] += intervals
            prefix_data[element]['ts'] = []
            # inter packet CDF
            prefix_data[element]['interpacket'] = get_cdf_points(
                prefix_data[element]['interpacket'], compress_by)


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


def prefixes_to_top_prefixes(prefixes):
    return sorted(
        prefixes.items(),
        key=lambda x: x[1]["packets_num"],
        reverse=True)


def get_timestamp(meta, format="pcap"):
    if format == "pcap":
        return meta.sec + meta.usec / 1000000.
    elif format == "pcapng":
        return ((meta.tshigh << 32) | meta.tslow) / float(meta.tsresol)


def read_bin_file(in_file):

    filein = open(in_file, "rb")
    prefixes = set()
    while True:
        packet = filein.read(14)
        if not packet:
            break

        #import ipdb; ipdb.set_trace()
        prefixes.add(struct.unpack("BBBB", packet[8:12][::-1])[0:3])
    return prefixes


def save_prefixes_ts_raw(prefixes_ts, out_file, prefix_type="str"):

    out = open(out_file, "wb")
    # number of prefixes in the file
    out.write(struct.pack("I", len(prefixes_ts)))
    for prefix, info in prefixes_ts.items():
        ts_len = struct.pack("I", len(info['ts']))
        if prefix_type == "str":
            packed_prefix = struct.pack(
                "BBBB", *[int(x) for x in prefix.split(".")])
        if prefix_type == "int":
            packed_prefix = struct.pack("!I", prefix)

        out.write(packed_prefix)
        out.write(ts_len)
        for ts in info['ts']:
            # sec to nano sec
            out.write(struct.pack("Q", int(ts * 1000000000)))

    out.close()


def read_flows_dist(dist_file):

    prefixes = {}
    current_prefix = ""
    with open(dist_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                current_prefix = line.split()[1]
                prefixes[current_prefix] = {
                    'packets': [],
                    'bytes': [],
                    'durations': [],
                    "rtts": []}
            elif not line.strip():
                continue
            else:
                start_time, packets, duration, bytes, rtt, proto = line.split()
                prefixes[current_prefix]["packets"].append(int(packets))
                prefixes[current_prefix]["bytes"].append(int(bytes))
                prefixes[current_prefix]["durations"].append(float(duration))
                prefixes[current_prefix]["rtts"].append(float(rtt))
    return prefixes


def flow_dist_to_top_prefixes(dist_file, out_file):

    prefixes = read_flows_dist(dist_file)

    prefixes = sorted(
        prefixes.items(),
        key=lambda x: sum(x[1]["packets"]),
        reverse=True)

    with open(out_file, "w") as f:
        for prefix, info in prefixes:
            f.write(
                "{} {} {}\n".format(
                    prefix, sum(info['bytes']),
                    sum(info['packets'])))


"""
Main parsing functions
"""

# gets the basic time slices with stateless packets


def get_pcap_slice_info(
        pcap_file, ts_file, out_file_base, time_slice, jump_after_slice,
        max_slices=0):

    # constants
    packet_count = 0
    precise_timestamps = open(ts_file, "r")
    default_packet_offset = 0
    file = RawPcapReader(pcap_file)
    packet, meta = next(file)
    if hasattr(meta, 'usec'):
        pcap_format = "pcap"
        link_type = file.linktype
    elif hasattr(meta, 'tshigh'):
        pcap_format = "pcapng"
        link_type = meta.linktype
    file.close()

    # check first layer
    if link_type == DLT_EN10MB:
        default_packet_offset += 14
    elif link_type == DLT_RAW_ALT:
        default_packet_offset += 0
    elif link_type == DLT_PPP:
        default_packet_offset += 2

    first_packet = True
    skiping_face = False

    slice = 0

    # binary file with the pcap to re-inject
    out = open(out_file_base + "_{}.bin".format(slice), "wb")
    # first and last timestamp of this slice
    ts_reference_file = open(out_file_base + "_{}.info".format(slice), "w")

    prefix_ts = {}

    with RawPcapReader(pcap_file) as _pcap_reader:
        for packet, meta in _pcap_reader:

            packet_count += 1
            packet = packet[default_packet_offset:]
            real_ts = Decimal(precise_timestamps.readline())

            if first_packet:
                first_ts = real_ts
                first_packet = False
                ts_reference_file.write("{}\n".format(first_ts))
                prefix_ts.clear()

            ts = int((real_ts - first_ts) * 1000000000)

            if skiping_face:
                if ts >= ((time_slice + jump_after_slice) * 1000000000):
                    skiping_face = False
                    first_packet = True

                continue

            if not packet:
                print("Bad Packet 1: ", packet_count)
                continue

            # IP LAYER Parsing
            packet_offset = 0
            version = packet[0]
            ip_version = version >> 4
            if ip_version != 4:
                continue
                # filter if the packet does not even have 20+14 bytes
                # get the normal ip fields. If there are options we remove it later
                #prefix = struct.unpack("!I", packet[16:20])[0]
                # prefix = '{0:d}.{1:d}.{2:d}.0'.format(ip_header[0],
                #                                       ip_header[1],
                #                                       ip_header[2])
            size = meta.wirelen

            # save the pcap data in the maximum compression as possible
            # we pack in bytes
            # timestamps are in nanoseconds (*e9)
            out.write(struct.pack("Q", ts))
            #out.write(struct.pack("I", prefix))
            # we do not need to unpack anymore
            out.write(packet[16:20][::-1])
            out.write(struct.pack("H", size))
            # print(packet_count)
            # out.close()
            # return

            # save per prefix data
            prefix = (struct.unpack("!I", packet[16:20])[0] & 0xffffff00)

            if prefix not in prefix_ts:
                prefix_ts[prefix] = {'bytes_num': size,
                                     'packets_num': 1, 'ts': [real_ts]}
            else:
                prefix_ts[prefix]['bytes_num'] += size
                prefix_ts[prefix]['packets_num'] += 1
                prefix_ts[prefix]['ts'].append(real_ts)

            if ts >= (time_slice * 1000000000):
                # close current file
                print("slice: {}, length={}, skip={}".format(
                    slice, time_slice, jump_after_slice))
                print(packet_count)
                out.close()
                skiping_face = True
                ts_reference_file.write("{}\n".format(real_ts))
                ts_reference_file.close()

                # safe time stamps file
                save_prefixes_ts_raw(
                    prefix_ts, out_file_base + "_{}.ts".format(slice),
                    "int")

                # safe top prefixes file
                print(len(prefix_ts))
                top_prefixes = prefixes_to_top_prefixes(prefix_ts)
                with open(out_file_base + "_{}.top".format(slice), "w") as f:
                    for prefix, data in top_prefixes:
                        prefix = struct.unpack(
                            "BBBB", struct.pack("!I", prefix))
                        prefix = '{0:d}.{1:d}.{2:d}.0'.format(prefix[0],
                                                              prefix[1],
                                                              prefix[2],
                                                              prefix[3])

                        f.write(
                            "{} {} {}\n".format(
                                prefix, data['bytes_num'],
                                data['packets_num']))

                if (max_slices != 0 and (max_slices == slice + 1)):
                    break

                # new file
                packet_count = 0
                slice += 1
                out = open(out_file_base + "_{}.bin".format(slice), "wb")
                ts_reference_file = open(
                    out_file_base + "_{}.info".format(slice), "w")

# new function to parse at per flow level for the worst case scenario


def get_pcap_slice_info_per_flow(
        pcap_file, ts_file, out_file_base, time_slice, jump_after_slice,
        max_slices=0):

    # constants
    packet_count = 0
    precise_timestamps = open(ts_file, "r")
    default_packet_offset = 0
    file = RawPcapReader(pcap_file)
    packet, meta = next(file)
    if hasattr(meta, 'usec'):
        pcap_format = "pcap"
        link_type = file.linktype
    elif hasattr(meta, 'tshigh'):
        pcap_format = "pcapng"
        link_type = meta.linktype
    file.close()

    # check first layer
    if link_type == DLT_EN10MB:
        default_packet_offset += 14
    elif link_type == DLT_RAW_ALT:
        default_packet_offset += 0
    elif link_type == DLT_PPP:
        default_packet_offset += 2

    first_packet = True
    skiping_face = False

    slice = 0

    # binary file with the pcap to re-inject
    #out = open(out_file_base + "_{}.bin".format(slice), "wb")
    # first and last timestamp of this slice
    ts_reference_file = open(
        out_file_base + "_per_flow_{}.info".format(slice), "w")

    prefix_ts = {}

    REACTIVE_UDP_PORTS = {443, 80}

    with RawPcapReader(pcap_file) as _pcap_reader:
        for packet, meta in _pcap_reader:

            packet_count += 1
            packet = packet[default_packet_offset:]
            real_ts = Decimal(precise_timestamps.readline())

            if first_packet:
                first_ts = real_ts
                first_packet = False
                ts_reference_file.write("{}\n".format(first_ts))
                prefix_ts.clear()

            ts = int((real_ts - first_ts) * 1000000000)

            if skiping_face:
                if ts >= ((time_slice + jump_after_slice) * 1000000000):
                    skiping_face = False
                    first_packet = True

                continue

            if not packet:
                print("Bad Packet 1: ", packet_count)
                continue

            # IP LAYER Parsing
            packet_offset = 0
            version = packet[0]
            ip_version = version >> 4

            # ipv4
            if ip_version == 4:
                if len(packet) < (IP_LEN + UDP_LEN):
                    #print("small packet found {}".format(packet_count))
                    continue

                src = packet[12:16]
                #src = "{}.{}.{}.{}".format(*src)
                dst = packet[16:20]
                #prefix = "{}.{}.{}.0".format(*dst)
                #dst = "{}.{}.{}.{}".format(*dst)

                packet_offset = (packet[0] & 0x0f) * 4
                protocol = packet[9]

                # tcp
                if protocol == 6:
                    sport = int.from_bytes(
                        packet[packet_offset: packet_offset + 2],
                        byteorder='big')
                    dport = int.from_bytes(
                        packet[packet_offset + 2: packet_offset + 4],
                        byteorder='big')
                # udp
                elif protocol == 17:
                    sport = int.from_bytes(
                        packet[packet_offset: packet_offset + 2],
                        byteorder='big')
                    dport = int.from_bytes(
                        packet[packet_offset + 2: packet_offset + 4],
                        byteorder='big')
                elif protocol == 1:
                    sport = 0
                    dport = 0
                else:
                    continue
            # ignore ipv6, traces have 1-5% of traffic max
            else:
                continue

            # debugging
            #print("{} -> {} {}/{}".format(src, dst, sport, dport))
            # save flow
            flow = (src, dst, protocol, sport, dport)

            #import ipdb; ipdb.set_trace()
            #size = meta.wirelen
            # save the pcap data in the maximum compression as possible
            # we pack in bytes
            # timestamps are in nanoseconds (*e9)
            #out.write(struct.pack("Q", ts))
            #out.write(struct.pack("I", prefix))
            # we do not need to unpack anymore
            # out.write(packet[16:20][::-1])
            #out.write(struct.pack("H", size))
            # print(packet_count)
            # out.close()
            # return

            # save per prefix data
            # prefix id
            # TO CHANGE
            prefix = (struct.unpack("!I", dst)[0] & 0xffffff00)

            # Save the information we need

            if prefix not in prefix_ts:
                prefix_ts[prefix] = {'ts': [real_ts], 'flows': set([flow])}
            else:
                if protocol == 6:
                    if flow not in prefix_ts[prefix]['flows']:
                        # add timestamp
                        prefix_ts[prefix]['ts'].append(real_ts)
                        # add flow
                        prefix_ts[prefix]['flows'].add(flow)

                elif protocol == 17 and dport in REACTIVE_UDP_PORTS:
                    if flow not in prefix_ts[prefix]['flows']:
                        # add timestamp
                        prefix_ts[prefix]['ts'].append(real_ts)
                        # add flow
                        prefix_ts[prefix]['flows'].add(flow)

                # inconditional add
                else:
                    # add timestamp
                    prefix_ts[prefix]['ts'].append(real_ts)
                    # add flow
                    prefix_ts[prefix]['flows'].add(flow)

            # save to files and start new slice
            if ts >= (time_slice * 1000000000):

                # close current file
                print("slice: {}, length={}, skip={}".format(
                    slice, time_slice, jump_after_slice))
                print(packet_count)
                # out.close()
                skiping_face = True
                ts_reference_file.write("{}\n".format(real_ts))
                ts_reference_file.close()

                # safe time stamps file
                save_prefixes_ts_raw(
                    prefix_ts, out_file_base + "_per_flow_{}.ts".format(slice),
                    "int")

                if (max_slices != 0 and (max_slices == slice + 1)):
                    break

                # new file
                packet_count = 0
                slice += 1
                #out = open(out_file_base + "_{}.bin".format(slice), "wb")
                ts_reference_file = open(
                    out_file_base + "_per_flow_{}.info".format(slice), "w")

# new function to parse at per flow level for the worst case scenario


def get_pcap_slice_info_per_flow_retrans(
        pcap_file, ts_file, out_file_base, time_slice, jump_after_slice,
        max_slices=0, rto=0.2, max_retrans=5):

    # constants
    packet_count = 0
    precise_timestamps = open(ts_file, "r")
    default_packet_offset = 0
    file = RawPcapReader(pcap_file)
    packet, meta = next(file)
    if hasattr(meta, 'usec'):
        pcap_format = "pcap"
        link_type = file.linktype
    elif hasattr(meta, 'tshigh'):
        pcap_format = "pcapng"
        link_type = meta.linktype
    file.close()

    # check first layer
    if link_type == DLT_EN10MB:
        default_packet_offset += 14
    elif link_type == DLT_RAW_ALT:
        default_packet_offset += 0
    elif link_type == DLT_PPP:
        default_packet_offset += 2

    first_packet = True
    skiping_face = False

    slice = 0

    # binary file with the pcap to re-inject
    #out = open(out_file_base + "_{}.bin".format(slice), "wb")
    # first and last timestamp of this slice
    ts_reference_file = open(
        out_file_base + "_per_flow_retrans_{}.info".format(slice), "w")

    prefix_ts = {}

    REACTIVE_UDP_PORTS = {443, 80}

    with RawPcapReader(pcap_file) as _pcap_reader:
        for packet, meta in _pcap_reader:

            packet_count += 1
            packet = packet[default_packet_offset:]
            real_ts = Decimal(precise_timestamps.readline())

            if first_packet:
                first_ts = real_ts
                first_packet = False
                ts_reference_file.write("{}\n".format(first_ts))
                prefix_ts.clear()

            ts = int((real_ts - first_ts) * 1000000000)

            if skiping_face:
                if ts >= ((time_slice + jump_after_slice) * 1000000000):
                    skiping_face = False
                    first_packet = True

                continue

            if not packet:
                print("Bad Packet 1: ", packet_count)
                continue

            # IP LAYER Parsing
            packet_offset = 0
            version = packet[0]
            ip_version = version >> 4

            # ipv4
            if ip_version == 4:
                if len(packet) < (IP_LEN + UDP_LEN):
                    #print("small packet found {}".format(packet_count))
                    continue

                src = packet[12:16]
                #src = "{}.{}.{}.{}".format(*src)
                dst = packet[16:20]
                #prefix = "{}.{}.{}.0".format(*dst)
                #dst = "{}.{}.{}.{}".format(*dst)

                packet_offset = (packet[0] & 0x0f) * 4
                protocol = packet[9]

                # tcp
                if protocol == 6:
                    sport = int.from_bytes(
                        packet[packet_offset: packet_offset + 2],
                        byteorder='big')
                    dport = int.from_bytes(
                        packet[packet_offset + 2: packet_offset + 4],
                        byteorder='big')
                # udp
                elif protocol == 17:
                    sport = int.from_bytes(
                        packet[packet_offset: packet_offset + 2],
                        byteorder='big')
                    dport = int.from_bytes(
                        packet[packet_offset + 2: packet_offset + 4],
                        byteorder='big')
                elif protocol == 1:
                    sport = 0
                    dport = 0
                # remove the rest which is small % of traffic
                else:
                    continue
            # ignore ipv6, traces have 1-5% of traffic max
            else:
                continue

            flow = (src, dst, protocol, sport, dport)

            prefix = (struct.unpack("!I", dst)[0] & 0xffffff00)

            # Save the information we need

            # first packet for prefix enters inconditionally
            if prefix not in prefix_ts:
                prefix_ts[prefix] = {'ts': [real_ts], 'flows': set([flow])}
                # add retransmissions
                if protocol == 6:
                    retransmission_ts = Decimal(0)
                    for i in range(0, max_retrans):
                        retransmission_ts += Decimal(rto * 2**i)
                        prefix_ts[prefix]['ts'].append(
                            real_ts + retransmission_ts)

            else:
                if protocol == 6:
                    if flow not in prefix_ts[prefix]['flows']:
                        # add timestamp
                        prefix_ts[prefix]['ts'].append(real_ts)
                        # add retransmissions
                        retransmission_ts = Decimal(0)
                        for i in range(0, max_retrans):
                            retransmission_ts += Decimal(rto * 2**i)
                            prefix_ts[prefix]['ts'].append(
                                real_ts + retransmission_ts)

                        # add flow
                        prefix_ts[prefix]['flows'].add(flow)

                elif protocol == 17 and dport in REACTIVE_UDP_PORTS:
                    if flow not in prefix_ts[prefix]['flows']:
                        # add timestamp
                        prefix_ts[prefix]['ts'].append(real_ts)
                        # add flow
                        prefix_ts[prefix]['flows'].add(flow)

                # inconditional add
                else:
                    # add timestamp
                    prefix_ts[prefix]['ts'].append(real_ts)
                    # add flow
                    prefix_ts[prefix]['flows'].add(flow)

            # save to files and start new slice
            if ts >= (time_slice * 1000000000):

                # close current file
                print("slice: {}, length={}, skip={}".format(
                    slice, time_slice, jump_after_slice))
                print(packet_count)
                # out.close()
                skiping_face = True
                ts_reference_file.write("{}\n".format(real_ts))
                ts_reference_file.close()

                # sort ts and filter start + slice duration
                sorted_prefix_ts = {}
                for prefix, info in prefix_ts.items():
                    ts = [x for x in info['ts'] if (
                        (x - first_ts) <= time_slice)]
                    ts.sort()
                    sorted_prefix_ts[prefix] = {'ts': ts}

                # safe time stamps file
                save_prefixes_ts_raw(
                    sorted_prefix_ts, out_file_base + "_per_flow_retrans_{}.ts".format(slice), "int")

                if (max_slices != 0 and (max_slices == slice + 1)):
                    break

                # new file
                packet_count = 0
                slice += 1
                #out = open(out_file_base + "_{}.bin".format(slice), "wb")
                ts_reference_file = open(
                    out_file_base + "_per_flow_retrans_{}.info".format(slice), "w")


def pcap_to_top_prefixes(pcap_file, top_file):
    """Simply counts packets and bytes for each prefix and saves it into a

    Args:
        pcap_file ([type]): [description]
        top_file ([type]): [description]
    """

    # constants
    packet_count = 0
    default_packet_offset = 0
    file = RawPcapReader(pcap_file)
    packet, meta = next(file)
    if hasattr(meta, 'usec'):
        pcap_format = "pcap"
        link_type = file.linktype
    elif hasattr(meta, 'tshigh'):
        pcap_format = "pcapng"
        link_type = meta.linktype
    file.close()

    # check first layer
    if link_type == DLT_EN10MB:
        default_packet_offset += 14
    elif link_type == DLT_RAW_ALT:
        default_packet_offset += 0
    elif link_type == DLT_PPP:
        default_packet_offset += 2

    prefix_data = {}

    with RawPcapReader(pcap_file) as _pcap_reader:
        for packet, meta in _pcap_reader:

            packet_count += 1
            packet = packet[default_packet_offset:]

            if not packet:
                print("Bad Packet 1: ", packet_count)
                continue

            # IP LAYER Parsing
            packet_offset = 0
            version = packet[0]
            ip_version = version >> 4
            if ip_version != 4:
                continue
                # filter if the packet does not even have 20+14 bytes
                # get the normal ip fields. If there are options we remove it later
                #prefix = struct.unpack("!I", packet[16:20])[0]
                # prefix = '{0:d}.{1:d}.{2:d}.0'.format(ip_header[0],
                #                                       ip_header[1],
                #                                       ip_header[2])
            size = meta.wirelen

            prefix = (struct.unpack("!I", packet[16:20])[0] & 0xffffff00)

            if prefix not in prefix_data:
                prefix_data[prefix] = {'bytes_num': size, 'packets_num': 1}
            else:
                prefix_data[prefix]['bytes_num'] += size
                prefix_data[prefix]['packets_num'] += 1

    # close current file
    print("Packets processed: ", packet_count)

    # safe top prefixes file
    print("Number of prefixes found: ", len(prefix_data))
    top_prefixes = prefixes_to_top_prefixes(prefix_data)

    with open(top_file, "w") as f:
        for prefix, data in top_prefixes:
            prefix = struct.unpack("BBBB", struct.pack("!I", prefix))
            prefix = '{0:d}.{1:d}.{2:d}.0'.format(prefix[0],
                                                  prefix[1],
                                                  prefix[2],
                                                  prefix[3])

            f.write(
                "{} {} {}\n".format(
                    prefix, data['bytes_num'],
                    data['packets_num']))


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


# new function resubmit
def get_pcap_slice_prefix_info(
        pcap_file, ts_file, out_file_base, time_slice, jump_after_slice,
        max_slices=0):
    """
    Gets prefix flow information and RTT per flow information
    """
    # constants
    packet_count = 0
    precise_timestamps = open(ts_file, "r")
    default_packet_offset = 0
    file = RawPcapReader(pcap_file)
    packet, meta = next(file)
    if hasattr(meta, 'usec'):
        pcap_format = "pcap"
        link_type = file.linktype
    elif hasattr(meta, 'tshigh'):
        pcap_format = "pcapng"
        link_type = meta.linktype
    file.close()

    # check first layer
    if link_type == DLT_EN10MB:
        default_packet_offset += 14
    elif link_type == DLT_RAW_ALT:
        default_packet_offset += 0
    elif link_type == DLT_PPP:
        default_packet_offset += 2

    first_packet = True
    skiping_face = False

    slice = 0

    # info of each prefix
    prefixes_info = {}

    # info of each flow
    flows_info = {}

    # we count RTTs here
    starting_flows = LimitedSizeDict(size_limit=100000)

    # we count flows per sec here
    new_flows_per_sec_count = 0
    new_syn_flows_per_sec_count = 0
    # per intervals
    flows_per_sec = []
    # used to save the flows per sec counters
    flows_per_sec_reference = 1

    rtts_found = []

    with RawPcapReader(pcap_file) as _pcap_reader:
        for packet, meta in _pcap_reader:

            packet_count += 1
            packet = packet[default_packet_offset:]
            real_ts = Decimal(precise_timestamps.readline())

            if first_packet:
                first_ts = real_ts
                first_packet = False

                # clear things
                prefixes_info.clear()
                flows_info.clear()
                starting_flows.clear()
                flows_per_sec.clear()
                new_flows_per_sec_count = 0
                new_syn_flows_per_sec_count = 0
                rtts_found = []
                flows_per_sec_reference = 1

            # nanosecond cast
            ts = int((real_ts - first_ts) * 1000000000)

            if skiping_face:
                if ts >= ((time_slice + jump_after_slice) * 1000000000):
                    skiping_face = False
                    first_packet = True

                continue

            if not packet:
                print("Bad Packet 1: ", packet_count)
                continue

            total_size = meta.wirelen
            # IP LAYER Parsing

            packet_offset = 0
            version = packet[0]
            ip_version = version >> 4

            # we skip ipv6 traffic for now
            if ip_version != 4:
                continue

            # ipv4
            src_ip = struct.unpack("!I", packet[12:16])[0]
            dst_ip = struct.unpack("!I", packet[16:20])[0]
            proto = packet[9]

            packet_offset += (packet[0] & 0x0f) * 4
            #prefix = dst_ip & 0xffffff00

            # tcp
            if proto == 6:
                # parse TCP header
                # filter if the packet does not even have 20+14 bytes
                if len(packet) < (packet_offset + TCP_LEN):
                    continue

                tcp_header = struct.unpack(
                    "!HHLLBB", packet
                    [packet_offset: packet_offset + TCP_LEN])
                sport = tcp_header[0]
                dport = tcp_header[1]
                pkt_seq = tcp_header[2]
                flags = tcp_header[5]
                syn_flag = flags & TH_SYN != 0
                ack_flag = flags & TH_ACK != 0

                # update data structures
                flow = (src_ip, sport, dst_ip, dport, proto)

                # if the syn flag is found we save the flow
                if syn_flag and not ack_flag:
                    new_syn_flows_per_sec_count += 1
                    starting_flows[flow] = (ts, pkt_seq)
                # if ack flag is found and the flow is tracked, the SEQ number is +1 we save the timestamp difference
                elif ack_flag and flow in starting_flows:
                    saved_ts, seq = starting_flows.pop(flow)
                    # check if its consequent ack
                    if pkt_seq == seq + 1:
                        # real RTT for this flow
                        # in nanoseconds
                        rtt = (ts) - (saved_ts)

                        # save the rtt in the flow
                        flows_info[flow]["rtt"] = rtt
                        # some flows get the RTT rewritten but it is very rare
                        rtts_found.append(rtt)
            # udp
            elif proto == 17:
                # if there is fragmentation offset we skip
                frag_off = struct.unpack("!H", packet[6:8])[0] & 0x1fff
                if frag_off > 0:
                    continue

                if len(packet) < (packet_offset + 8):
                    continue
                udp_header = struct.unpack(
                    "!HHHH", packet[packet_offset: packet_offset + 8])

                sport = udp_header[0]
                dport = udp_header[1]
                flow = (src_ip, sport, dst_ip, dport, proto)
            else:
                continue

            if flow not in flows_info:
                new_flows_per_sec_count += 1
                flows_info[flow] = {
                    "rtt": None, "duration": [ts, -1],
                    "bytes": total_size, "packets": 1, "protocol": proto,
                    "start_time": ts}
            else:
                # put last seen time stamp
                flows_info[flow]['duration'][-1] = ts
                # update sizes
                flows_info[flow]['bytes'] += total_size
                flows_info[flow]["packets"] += 1

            # one sec measurements
            if ts >= (flows_per_sec_reference * 1000000000):
                flows_per_sec.append(
                    (new_flows_per_sec_count, new_syn_flows_per_sec_count))
                new_flows_per_sec_count = 0
                new_syn_flows_per_sec_count = 0
                flows_per_sec_reference += 1

            if ts >= (time_slice * 1000000000):
                # close current file
                print("trace: {}, slice: {}, length={}, skip={}, packet_count={}".format(
                    pcap_file.split("/")[-1], slice, time_slice, jump_after_slice, packet_count))

                # Process and save the flows per prefix data structure
                mean_rtt = np.mean(rtts_found)
                max_rtt = 0.5
                min_flows_prefix_without_rtt = 2

                prefixes_info = aggregate_and_fix_flows_info(
                    flows_info, rtts_found, max_rtt,
                    min_flows_prefix_without_rtt)

                # generate outputs
                # 1 ) flows per prefix
                top_prefixes_info = sorted(
                    prefixes_info.items(),
                    key=lambda x: sum([y["packets"] for y in x[1]]),
                    reverse=True)
                with open("{}_{}.dist".format(out_file_base, slice), "w") as f:
                    for prefix, flows in top_prefixes_info:
                        f.write("### {0} ###\n".format(int2ip(prefix)))
                        for flow in flows:
                            f.write(
                                "{0} {1} {2} {3} {4} {5}\n".format(
                                    flow["start_time"] / 1000000000,
                                    flow['packets'],
                                    flow['duration'] / 1000000000,
                                    flow['bytes'],
                                    flow['rtt'] / 1000000000, flow
                                    ["protocol"]))
                        f.write("\n")

                # 2) RTTs and RTT CDF
                rtts = []
                for prefix, flows in prefixes_info.items():
                    rtts += [x["rtt"] / 1000000000 for x in flows]
                rtts = sorted(rtts)
                with open("{}_{}.rtts".format(out_file_base, slice), "w") as f:
                    for rtt in rtts:
                        f.write("{}\n".format(rtt))

                # 3) Flows per second
                with open("{}_{}.freq".format(out_file_base, slice), "w") as f:
                    for new_per_sec, new_per_sec_sync in flows_per_sec:
                        f.write("{} {}\n".format(
                            new_per_sec, new_per_sec_sync))
                skiping_face = True

                if (max_slices != 0 and (max_slices == slice + 1)):
                    break

                # new file
                packet_count = 0
                slice += 1


def aggregate_and_fix_flows_info(flows_info, original_rtts, max_rtt,
                                 min_flows_prefix_without_rtt=2) -> dict:
    """
    This function takes all the flow and prefix data. Aggregates it and then
    since there is incomplete RTT and duration info it tries to fix that.

    1) First it takes all the prefixes for which there is at least one RTT and
       assigns all the flows without RTTs one from the given ones.

    2) For all prefixes with 0 RTTs, removes them if they have less than
       min_flows. For the rest, it tries to find a prefix with the similar
       number of flows, and picks RTTs from there.

    Of course this could be done better or different, but should be good enough.

    """

    prefixes_info = {}
    # some variables to count stats
    prefixes_with_rtts = 0
    all_original_rtts = []
    max_given_rtt_accepted = max_rtt * 1000000000  # ns

    mean_rtt = np.mean(original_rtts)

    good_prefix_to_num_flows = {}

    # first pass we classify flows per prefix
    for flow, info in flows_info.items():
        prefix = flow[2] & 0xffffff00  # dst/24
        #proto = flow[4]

        if prefix not in prefixes_info:
            _info = info.copy()
            #_info["proto"] = proto
            prefixes_info[prefix] = [_info]
        else:
            _info = info.copy()
            #_info["proto"] = proto
            prefixes_info[prefix].append(_info)

    #original_prefixes_info = copy.deepcopy(prefixes_info)

    # For each prefix we will try to enhance the RTTs using the other Rtts
    # Also for all flows without duration or a duration smaller than RTT, we set duration
    # to at least 1 RTT. Our sender will handle the rest.
    for prefix, flows in prefixes_info.items():
        # gets only the valid RTTs
        #prefix_rtts = [x["rtt"] for x in flows if ((x["rtt"] is not None) and (x["rtt"] < max_rtt_accepted))]
        prefix_rtts = [x["rtt"] for x in flows if ((x["rtt"] is not None))]
        # move to next prefix
        if not prefix_rtts:
            continue

        all_original_rtts += prefix_rtts
        prefixes_with_rtts += 1

        for flow in flows:
            # flow has rtt
            if flow["rtt"]:
                duration = flow["duration"][1] - flow["duration"][0]
                if (flow["rtt"] > duration):
                    duration = flow["rtt"] * 1.1
                flow["duration"] = duration
            else:
                # sample rtt
                rtt = random.choice(prefix_rtts)
                # To remove 10ms rtt
                # if below 300ms, we set it to 10-20ms
                if rtt < 300000000:
                    rtt = random.randint(10000000, 20000000)

                # if the rtt we want to transfer is too big we assign the trace mean
                if rtt > max_given_rtt_accepted:
                    rtt = mean_rtt

                flow["rtt"] = rtt

                # if we do not have duration we set it as rtt
                if flow["duration"][1] == -1:
                    flow["duration"] = rtt

                # else we compute and see if its big enough
                else:
                    duration = flow["duration"][1] - flow["duration"][0]
                    if (flow["rtt"] > duration):
                        duration = flow["rtt"] * 1.1
                    flow["duration"] = duration

        good_prefix_to_num_flows[prefix] = len(flows)

    # Last iteration. For all prefixes that have 0 RTTs. We get them from other
    # prefixes.
    prefixes_to_delete = []
    for prefix, flows in prefixes_info.items():
        prefix_rtts = [x["rtt"] for x in flows if x["rtt"] is not None]

        # if prefix has nothing
        if not prefix_rtts:
            # if very few flows and packets
            packets = sum([x["packets"] for x in flows])
            if len(flows) < min_flows_prefix_without_rtt and packets < 50:
                prefixes_to_delete.append(prefix)
                continue

            # we try to get RTTs from other prefixes
            candidate_found = False
            num_flows_margin = 2
            prefix_num_flows = len(flows)
            while not candidate_found:
                for candidate_prefix, candidate_num_flows in good_prefix_to_num_flows.items():
                    if abs(prefix_num_flows - candidate_num_flows) <= num_flows_margin:
                        candidate_found = True
                        # continue from here
                        candidate_rtts = [x["rtt"]
                                          for x in prefixes_info
                                          [candidate_prefix]]
                        break
                    else:
                        continue

                num_flows_margin *= 2

            # now we assign the stuff
            for flow in flows:
                # sample rtt
                rtt = random.choice(candidate_rtts)
                # To remove 10ms rtt
                # if below 300ms, we set it to 10-20ms
                if rtt < 300000000:
                    rtt = random.randint(10000000, 40000000)

                # if the rtt we want to transfer is too big we assign the trace mean
                if rtt > max_given_rtt_accepted:
                    rtt = mean_rtt

                flow["rtt"] = rtt

                # if we do not have duration we set it as rtt
                if flow["duration"][1] == -1:
                    flow["duration"] = rtt * 1.1

                # else we compute and see if its big enough
                else:
                    duration = flow["duration"][1] - flow["duration"][0]
                    if (flow["rtt"] > duration):
                        duration = flow["rtt"] * 1.1
                    flow["duration"] = duration

    # remove useless small prefixes
    for prefix in prefixes_to_delete:
        del(prefixes_info[prefix])

    # verify all is good
    #erification = True
    #inal_rtts = []
    # or prefix, flows in prefixes_info.items():
    #   for flow in flows:
    #       if not flow["rtt"]:
    #           verification = False
    #       elif flow["duration"] < flow["rtt"]:
    #           verification = False
    #
    #       final_rtts.append(flow["rtt"])

    #       if not verification:
    #           import ipdb; ipdb.set_trace()

    return prefixes_info


"""
Mains 
"""


# this is the good one at this point: Main function that computes *bin, *cdf, *info and top
def main_pcap_info(
        traces_base_dir, files, slice_size=20, skip_after=40, slices=10,
        processes=1):

    pool = multiprocessing.Pool(processes)
    url_base = "{}/{}/{}.{}"
    for file in files:
        pool.apply_async(
            get_pcap_slice_info,
            (url_base.format(traces_base_dir, file, file, "pcap"),
             url_base.format(traces_base_dir, file, file, "times"),
             "{}/{}/{}".format(traces_base_dir, file, file),
             slice_size, skip_after, slices),
            {})


# this is the good one at this point: does the same but only keeps one packet per flow after the failure. It just does the timestamps
def main_pcap_info_per_flow(
        traces_base_dir, files, slice_size=20, skip_after=40, slices=10,
        processes=1):

    pool = multiprocessing.Pool(processes)
    url_base = "{}/{}/{}.{}"
    for file in files:
        pool.apply_async(
            get_pcap_slice_info_per_flow,
            (url_base.format(traces_base_dir, file, file, "pcap"),
             url_base.format(traces_base_dir, file, file, "times"),
             "{}/{}/{}".format(traces_base_dir, file, file),
             slice_size, skip_after, slices),
            {})


# this is the good one at this point, the same but adds retransmissions
def main_pcap_info_per_flow_retrans(
        traces_base_dir, files, slice_size=20, skip_after=40, slices=10,
        processes=1):

    pool = multiprocessing.Pool(processes)
    url_base = "{}/{}/{}.{}"
    for file in files:
        pool.apply_async(
            get_pcap_slice_info_per_flow_retrans,
            (url_base.format(traces_base_dir, file, file, "pcap"),
             url_base.format(traces_base_dir, file, file, "times"),
             "{}/{}/{}".format(traces_base_dir, file, file),
             slice_size, skip_after, slices, 0.2, 5),
            {})


# computes the top file for the entire trace
def main_pcap_to_top_file(traces_base_dir, files, processes=1):

    pool = multiprocessing.Pool(processes)
    url_base = "{}/{}/{}.{}"
    for file in files:
        pool.apply_async(
            pcap_to_top_prefixes,
            (url_base.format(traces_base_dir, file, file, "pcap"),
             url_base.format(traces_base_dir, file, file, "top")),
            {})


# this is the good one at this point: Main function that computes *bin, *cdf, *info and top
def main_pcap_prefix_info(
        traces_base_dir, files, slice_size=30, skip_after=30, slices=10,
        processes=1):

    pool = multiprocessing.Pool(processes)
    url_base = "{}/{}/{}.{}"
    for file in files:
        pool.apply_async(
            get_pcap_slice_prefix_info,
            (url_base.format(traces_base_dir, file, file, "pcap"),
             url_base.format(traces_base_dir, file, file, "times"),
             "{}/{}/{}".format(traces_base_dir, file, file),
             slice_size, skip_after, slices),
            {})

    pool.close()
    pool.join()


def get_rtt_cdf(input_file, outout_file, cdf_size=100):
    with open(input_file, "r") as f:
        rtts = f.readlines()
        rtts = [float(x) for x in rtts]
        rtts = sorted(rtts)

        cdf = get_cdf_points(rtts, cdf_size - 6)

        # add 5 points form the upper last 1%.
        index = int(99.5 / 100 * len(rtts))
        last_rtts = rtts[index:]
        last_mile_rtts = get_cdf_points(last_rtts, 5) + [rtts[-1]]

        # complete
        cdf = cdf + last_mile_rtts

    with open(outout_file, "w") as f:
        for rtt in cdf:
            f.write("{}\n".format(rtt))


def get_rtts_cdfs(traces_base_dir, cdf_size=100):

    url_base = "{}/{}/{}_{}.{}"
    slices = 10
    for trace in all_traces:
        for slice in range(slices):
            rtts_file = url_base.format(
                traces_base_dir, trace, trace, slice, "rtts")
            out_file = url_base.format(
                traces_base_dir, trace, trace, str(slice) + "_rtt_cdfs", "txt")
            get_rtt_cdf(rtts_file, out_file, cdf_size)
