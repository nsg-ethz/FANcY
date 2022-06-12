# This is a control planed used for basic rules at the second switch the one we use
# as debugger and link with properties
from utils import get_constant_cmds, set_ports, load_scripts_path, ip2int, int2ip, bcolors
import struct
import socket

# add paths
paths = ["../eval", "../scripts"]
load_scripts_path(paths)
# import utilities
from send_traffic import *
from crc import Crc
from server import ServerTCP, TofinoCommandServer


# CONFIGURATION
# paths to constants
path_to_constants = "../p4src/includes/constants.p4"
# model enabled?
MODEL = False
# load all constants
cmds = get_constant_cmds(path_to_constants, MODEL)
for cmd in cmds:
    # make variable global
    exec(cmd)


# constants
port_to_index = {
    PORT0: 0,
    PORT1: 1,
    PORT2: 2,
    PORT3: 3,
    PORT4: 4,
    PORT5: 5,
    PORT6: 6
}

port_to_id = {
    PORT0: PORT0_ID,
    PORT1: PORT1_ID,
    PORT2: PORT2_ID,
    PORT3: PORT3_ID,
    PORT4: PORT4_ID,
    PORT5: PORT5_ID,
    PORT6: PORT6_ID
}


def clean_bloom_filters():
    p4_pd.register_reset_all_bloom_filter_1()
    p4_pd.register_reset_all_bloom_filter_2()


def check_bloom_entries():
    return sum(p4_pd.register_range_read_bloom_filter_1(0, 65635, from_hw))


def clear_registers_ingress():
    p4_pd.register_reset_all_in_counters()
    p4_pd.register_reset_all_in_state()
    clean_bloom_filters()


def clear_registers_egress():
    p4_pd.register_reset_all_max_0()
    p4_pd.register_reset_all_max_1()
    p4_pd.register_reset_all_out_counters()
    p4_pd.register_reset_all_out_state()
    p4_pd.register_reset_all_zooming_stage()


class ZoomingController(object):
    """Custom controller object we created to be able to run commands remotely
    with some simple python server."""

    def __init__(self, controller, from_hw):

        self.controller = controller
        self.from_hw = from_hw

    def clear_state(self):
        self.controller.register_reset_all_in_counters()
        self.controller.register_reset_all_max_0()
        self.controller.register_reset_all_max_1()
        self.controller.register_reset_all_out_counters()
        self.controller.register_reset_all_out_state()
        self.controller.register_reset_all_zooming_stage()

    def clean_bloom_filters(self):
        self.controller.register_reset_all_bloom_filter_1()
        self.controller.register_reset_all_bloom_filter_2()

    def check_bloom_entries(self):
        print(sum(self.controller.register_range_read_bloom_filter_1(
            0, 65635, self.from_hw)))


def set_in_port_to_offsets(ports):
    """Configures ports to register offsets where the tree is stored"""
    for port in ports:
        i = port_to_index[port]
        p4_pd.in_port_to_offsets_table_add_with_set_ingress_address_offsets_normal(p4_pd.in_port_to_offsets_match_spec_t(
            0, port, -1, port, 0), 1, p4_pd.set_ingress_address_offsets_normal_action_spec_t(COUNTER_NODE_WIDTH * i, i))
        p4_pd.in_port_to_offsets_table_add_with_set_ingress_address_offsets_recirc(p4_pd.in_port_to_offsets_match_spec_t(
            1, port, 0, port, -1), 1, p4_pd.set_ingress_address_offsets_recirc_action_spec_t(COUNTER_NODE_WIDTH * i, i))


def set_out_port_to_offsets(ports):
    """Configures ports to register offsets where the tree is stored"""
    for port in ports:
        i = port_to_index[port]
        p4_pd.out_port_to_offsets_table_add_with_set_egress_address_offsets_normal(p4_pd.out_port_to_offsets_match_spec_t(
            0, port, -1, port, 0), 1, p4_pd.set_egress_address_offsets_normal_action_spec_t(COUNTER_NODE_WIDTH * i, i))
        p4_pd.out_port_to_offsets_table_add_with_set_egress_address_offsets_recirc(p4_pd.out_port_to_offsets_match_spec_t(
            1, port, 0, port, -1), 1, p4_pd.set_egress_address_offsets_recirc_action_spec_t(COUNTER_NODE_WIDTH * i, i))


def set_forward_table():
    """Configures the forwarding table as we have described in our README"""

    # 100g
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT4),
        p4_pd.set_port_action_spec_t(PORT1))
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT1),
        p4_pd.set_port_action_spec_t(PORT4))
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT2),
        p4_pd.set_port_action_spec_t(PORT5))
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT5),
        p4_pd.set_port_action_spec_t(PORT2))

    # reverse path from reroute port in theory not even used?
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT6),
        p4_pd.set_port_action_spec_t(PORT4))


def set_update_zoom_max_table():

    for i in range(MAX_ZOOM + 1):
        p4_pd.set_fancy_pre_type_to_update_table_add_with__set_fancy_pre_type(
            p4_pd.set_fancy_pre_type_to_update_match_spec_t(0, i),
            p4_pd._set_fancy_pre_type_action_spec_t(UPDATE_OFFSET + i + 4))


def set_default_reroute():
    p4_pd.reroute_set_default_action_set_port(
        p4_pd.set_port_action_spec_t(PORT6))


##################################################################
# Testing Functions (not needed for case study)
##################################################################

def read_status_port(port_id, direction, pipe=0, num_pipes=4):

    # read counters
    start = COUNTER_NODE_WIDTH * port_to_index[port_id]
    normal_index = port_to_index[port_id]

    # initial values when not read
    zooming_stage = max_0 = max_1 = -1

    print("Registers state of port {}; direction {}".format(
        port_to_index[port_id], direction))

    if direction == "in":
        counters = p4_pd.register_range_read_in_counters(
            start, COUNTER_NODE_WIDTH, from_hw)
    elif direction == "out":
        counters = p4_pd.register_range_read_out_counters(
            start, COUNTER_NODE_WIDTH, from_hw)
    counters = counters[pipe::num_pipes]
    print("Counter values:")
    print(counters)

    if direction == "out":
        # print zooming, and max, etc
        zooming_stage = p4_pd.register_read_zooming_stage(
            normal_index, from_hw)[pipe]
        max_0 = p4_pd.register_read_max_0(normal_index, from_hw)[pipe]
        max_1 = p4_pd.register_read_max_1(normal_index, from_hw)[pipe]
        print("zoom: {} max_0: {} max_1: {}".format(
            zooming_stage, max_0, max_1))

    return counters, zooming_stage, max_0, max_1


def fill_register_counters(direction, port_num, values):
    start_index = port_num * COUNTER_NODE_WIDTH
    for value in values[:COUNTER_NODE_WIDTH]:
        if direction == "in":
            p4_pd.register_write_in_counters(start_index, value)
        elif direction == "out":
            p4_pd.register_write_out_counters(start_index, value)
        start_index += 1


def set_test_counters():
    fill_register_counters("in", 0, range(0, 32))
    fill_register_counters("in", 1, range(32, 64))
    fill_register_counters("in", 2, range(64, 96))

    fill_register_counters("out", 0, range(0, 32))
    fill_register_counters("out", 2, range(32, 64))
    fill_register_counters("out", 1, range(64, 96))


def build_ips_to_pkts(ips, pkts):
    return {ip: pkts for ip in ips}


def compute_counters_after_traffic(
        ips_to_pkt, maxes, modulo=8, hash_functions=None, zooming_stage=0):

    counters = [0 for _ in range(modulo)]

    if not hash_functions:
        hash_functions = get_hashes()

    for ip, num_pkts in ips_to_pkt.items():
        hash_indexes = get_hash_ip(ip, hash_functions, modulo)
        path = hash_indexes[:zooming_stage]
        if maxes[:zooming_stage] == path:
            index = hash_indexes[zooming_stage]
            counters[index] += num_pkts

    return counters


def compute_counters_difference(ingress_counters, egress_counters):
    return [y - x for x, y in zip(ingress_counters, egress_counters)]


def test_status(current_status, expected_status):
    if current_status == expected_status:
        print(bcolors.OKGREEN + "Test Passed" + bcolors.ENDC)
    else:
        print(bcolors.FAIL + "Test failed with: {} {}".format(current_status,
              expected_status) + bcolors.ENDC)
        # raise Exception


def test_zoom(
        ips, fail_ips, pkts=5, modulo=4, zooms=2, ports_pipe=0, num_pipes=4):

    # for model ports pipe 0 and num pipes 4
    # for tofino ports pipe 1 and num pipes 2

    # ips = ["10.0.1.1" , "10.0.1.2", "10.0.1.3"]
    # fail_ips = ["10.0.1.1"]

    # reset all and configure
    configure_all()
    hash_functions = get_hashes()

    time.sleep(3)

    good_ips = list(set(ips).difference(set(fail_ips)))

    # reading status
    print("Reading status")
    status = read_status_port(PORT1, "out", ports_pipe, num_pipes)
    test_status(status, ([0] * modulo, 0, 0, 0))

    status = read_status_port(PORT2, "in", ports_pipe, num_pipes)
    test_status(status, ([0] * modulo, -1, -1, -1))

    maxes = [0 for _ in range(zooms)]

    for zoom in range(zooms + 1):
        # send some packets at veth0
        print("Sending traffic...")
        for ip in ips:
            send_packet("veth0", addr=ip, count=pkts, delay=0.2)

        time.sleep(pkts * len(ips) * 0.3)

        # reading status
        print("Reading status after traffic...")
        status = read_status_port(PORT1, "out", ports_pipe, num_pipes)
        egress_counters = compute_counters_after_traffic(
            build_ips_to_pkts(ips, pkts),
            maxes, modulo, hash_functions, zoom)
        test_status(status, (egress_counters, zoom, maxes[0], maxes[1]))

        status = read_status_port(PORT2, "in", ports_pipe, num_pipes)
        ingress_counters = compute_counters_after_traffic(
            build_ips_to_pkts(good_ips, pkts),
            maxes, modulo, hash_functions, zoom)
        test_status(status, (ingress_counters, -1, -1, -1))

        # send stop to ingress
        send_fancy_packet("veth4", actions['STOP'], 0, 0, 1)

        time.sleep(modulo * 0.3)

        # reading status
        print("Reading status after stop")
        if zoom != MAX_ZOOM:
            status = read_status_port(PORT1, "out", ports_pipe, num_pipes)

            # update max
            counters_diff = compute_counters_difference(
                ingress_counters, egress_counters)
            max_index = counters_diff.index(max(counters_diff))
            maxes[zoom] = max_index
            test_status(status, ([0] * modulo, (zoom + 1) %
                        (MAX_ZOOM + 1), maxes[0], maxes[1]))

        status = read_status_port(PORT2, "in", ports_pipe, num_pipes)
        test_status(status, ([0] * modulo, -1, -1, -1))


def test_many_ips(num, start="10.0.1.1"):

    start_int = ip2int(start)
    for i in range(num):
        send_packet(
            "veth0", addr=int2ip(start_int + (1 * i)),
            count=1, delay=0.3)


def get_hashes():
    hash_functions = []
    hash_functions.append(
        Crc(16, 0x11021, False, 0xffff, False, 0x0000))  # crc_ccitt
    hash_functions.append(Crc(16, 0x10589, False, 0x0001,
                          False, 0x0001))  # crc 16 dect
    # crc 16 dnp (in the pdf this is different)
    hash_functions.append(Crc(16, 0x13D65, True, 0x0000, True, 0xffff))
    return hash_functions


def get_32_hashes():

    hash_functions = []
    hash_functions.append(
        Crc(32, 0x104C11DB7, True, 0x00000000, True, 0xFFFFFFFF))  # crc_32
    hash_functions.append(
        Crc(32, 0x11EDC6F41, True, 0x00000000, True, 0xFFFFFFFF))  # crc_32_c
    return hash_functions


def test_hash_ip(ip, modulo=8):
    print(get_hash_ip(ip, modulo))


def get_hash_path_indexes(hash_path, hashes=None, modulo=65536):
    if not hashes:
        hashes = get_32_hashes()

    indexes = []
    for hash in hashes:
        index = hash.bit_by_bit_fast(struct.pack("!HHH", *hash_path)) % modulo
        indexes.append(index)

    return indexes


def get_hash_ip(ip, hashes=None, modulo=8):
    if not hashes:
        hashes = get_hashes()
    indexes = []
    for hash in hashes:
        _ip = socket.inet_aton(ip)
        index = (hash.bit_by_bit_fast(_ip) % modulo)
        indexes.append(index)
    return indexes


##############
# INIT CONFIG
##############

def configure_basic_tables():
    """Initializes all tables and registers."""
    # clear all tables
    clear_all()
    clear_registers_ingress()

    # ingress
    set_in_port_to_offsets([PORT0, PORT1, PORT2, PORT3, PORT4, PORT5])

    set_forward_table()

    # egress
    clear_registers_egress()
    set_out_port_to_offsets([PORT0, PORT1, PORT2, PORT3, PORT4, PORT5])
    set_update_zoom_max_table()


def configure_all():
    """Configures everything for a test."""
    configure_basic_tables()

    print("clearing registers")
    time.sleep(2)

    # set egress and ingress to counting states
    p4_pd.register_write_in_state(port_to_index[PORT2], RECEIVER_COUNTING)
    p4_pd.register_write_out_state(port_to_index[PORT1], SENDER_COUNTING)

    set_default_reroute()
    time.sleep(1)


if __name__ == "__main__":

    print("Starts Fancy Zooming Switch Controller....")
    # adds ports
    print("Setting switch ports...")

    # Hardcoded parameters. I can not use the command line arguments since we call this
    # using the run_pd_rpc.py script.
    SERVER_PORT = 5000

    # sets tofino ports
    set_ports(pal, {1: "10G", 3: "100G", 4: "100G",
                    5: "100G", 6: "100G", 7: "100G", 8: "100G"})

    # configure all tables etc
    configure_all()

    controller = ZoomingController(p4_pd, from_hw)
    s = TofinoCommandServer(SERVER_PORT, controller)
    print("Start command server")
    s.run()
