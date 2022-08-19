import os
import sys
import ipdb
import time
import socket

sys.path.append("../../bfrt_helper/")
sys.path.append("../scripts/")
sys.path.append("../../../eval")

from send_traffic import *
from bfrt_grpc_helper import BfRtAPI, gc

# command server to send remote commands
from server import TofinoCommandServer

# Loads constants from the p4 file such that i dont have to edit them in both places
import subprocess
from utils import get_constant_cmds, ip2int, int2ip, bcolors
from crc import Crc


# CONFIGURATION
# paths to constants
path_to_constants = "../includes/constants.p4"

args = sys.argv

# model enabled?
MODEL = False
if len(args) > 1:
    if args[1].lower() == "model":
        MODEL = True

# load all constants
cmds = get_constant_cmds(path_to_constants, MODEL)
for cmd in cmds:
    # make variable global
    exec(cmd)

STARTING_DST_IP = "11.0.2.1"

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

# register cell mapping for dedicated counter entries
port_to_id = {
    PORT0: PORT0_ID,
    PORT1: PORT1_ID,
    PORT2: PORT2_ID,
    PORT3: PORT3_ID,
    PORT4: PORT4_ID,
    PORT5: PORT5_ID,
    PORT6: PORT6_ID
}

port_to_type = {
    PORT0: HOST,
    PORT1: FANCY_SWITCH,
    PORT2: FANCY_SWITCH,
    PORT3: HOST,
    PORT4: HOST,
    PORT5: HOST,
    PORT6: FANCY_SWITCH
}

# SOME DEBUGGING FUNCTIONS
sender_state = {
    0: "SENDER_IDLE",
    1: "SENDER_START_ACK",
    2: "SENDER_COUNTING",
    3: "SENDER_WAIT_COUNTER_RECEIVE"
}

receiver_state = {
    0: "RECEIVER_IDLE",
    1: "RECEIVER_COUNTING",
    2: "RECEIVER_WAIT_COUNTER_SEND",
    3: "RECEIVER_COUNTER_ACK"
}


def get_hashes():
    hash_functions = []
    hash_functions.append(
        Crc(16, 0x11021, False, 0xffff, False, 0x0000))  # crc_ccitt
    hash_functions.append(Crc(16, 0x10589, False, 0x0001,
                          False, 0x0001))  # crc 16 dect
    # crc 16 dnp (in the pdf this is different)
    hash_functions.append(Crc(16, 0x13D65, True, 0x0000, True, 0xffff))
    return hash_functions


def get_hash_ip(ip, hashes=None, modulo=8):
    if not hashes:
        hashes = get_hashes()
    indexes = []
    for hash in hashes:
        _ip = socket.inet_aton(ip)
        index = (hash.bit_by_bit_fast(_ip) % modulo)
        indexes.append(index)
    return indexes


def build_ips_to_pkts(ips, pkts):
    return {ip: pkts for ip in ips}


def compute_counters_difference(ingress_counters, egress_counters):
    return [y - x for x, y in zip(ingress_counters, egress_counters)]


class FancyController():
    def __init__(self):
        self.controller = BfRtAPI(client_id=1)
        self.prev_sender_count = SENDER_COUNTING_COUNT

    def clear_state(self):
        self.controller.clear_all()

    def get_match_keys(self, key_names, rule):

        _key = []
        for key_name, key_param in zip(key_names, rule):
            if type(key_param) != tuple:
                key_param = (key_param,)
            _key.append((key_name,) + key_param)

        return _key

    def get_action_values(self, rule, action_param_names):
        _value = []
        for value_name, value_param in zip(action_param_names, rule):
            _value.append((value_name, value_param))
        return _value

    def add_ternary_rules(self, table_name, key_names, rules,
                          action_param_names, action):
        keys = []
        values = []

        key_values = [x[0] for x in rules]
        action_values = [x[1] for x in rules]

        for rule in key_values:
            keys.append(self.get_match_keys(key_names, rule))

        for value in action_values:
            values.append(self.get_action_values(value, action_param_names))

        for key, value in zip(keys, values):
            self.controller.entry_add(
                table_name, key, value, action)

    # Dedicated Controller
    ######################
    def set_next_state_in(self):

        table = self.controller.bfrt_info.table_get("table_next_state_in")
        key_names = list(table.info.key_dict.keys())
        # due to a problem with python3.5 with ord dicts I put it static
        key_names = [
            'meta.fancy.current_state', 'meta.fancy.current_counter',
            'hdr.fancy.action_value', 'hdr.fancy.ack', 'hdr.fancy.$valid',
            '$MATCH_PRIORITY']

        # keys, if tuple ternary, prio, data params
        receiver_state_machine = [
            [(RECEIVER_IDLE, (0, 0), (START, 2**5 - 1), (0, 1), (1, 1), 1), (RECEIVER_COUNTING, 0)],
            [(RECEIVER_COUNTING, (0, 0), (START, 2**5 - 1), (0, 1), (1, 1), 1), (RECEIVER_COUNTING, 0)],
            [(RECEIVER_COUNTING, (0, 0), (STOP, 2**5 - 1), (0, 1), (1, 1), 1), (RECEIVER_COUNTER_ACK, 0)],
            [(RECEIVER_WAIT_COUNTER_SEND, (RECEIVER_WAIT_COUNTER_SEND_COUNT, -1), (0, 0), (0, 0), (0, 0), 1), (RECEIVER_COUNTER_ACK, 1)],
            [(RECEIVER_COUNTER_ACK, (0, 0), (STOP, 2**5 - 1), (0, 1), (1, 1), 1), (RECEIVER_COUNTER_ACK, 0)],
            [(RECEIVER_COUNTER_ACK, (0, 0), (COUNTER, 2**5 - 1), (1, 1), (1, 1), 1), (RECEIVER_IDLE, 0)],
            [(RECEIVER_COUNTER_ACK, (0, 0), (START, 2**5 - 1), (0, 1), (1, 1), 1), (RECEIVER_COUNTING, 0)],
            [(RECEIVER_COUNTER_ACK, (RECEIVER_COUNTER_ACK_COUNT, -1), (0, 0), (0, 0), (0, 0), 2), (RECEIVER_COUNTER_ACK, 1)]
        ]

        self.add_ternary_rules(
            "table_next_state_in", key_names, receiver_state_machine,
            ["next_state", "counter_type"],
            "set_next_state_in")

    def set_next_state_out(self):

        table = self.controller.bfrt_info.table_get("table_next_state_out")
        key_names = list(table.info.key_dict.keys())
        # due to a problem with python3.5 with ord dicts I put it static
        key_names = [
            'meta.fancy.current_state', 'meta.fancy.current_counter',
            'hdr.fancy.action_value', 'hdr.fancy.ack', 'hdr.fancy.fsm',
            'hdr.fancy.$valid', '$MATCH_PRIORITY']

        # keys, if tuple ternary, prio, data params
        receiver_state_machine = [
            [(SENDER_IDLE, (SENDER_IDLE_COUNT, -1), (0, 0), (0, 0), (0, 0), (0, 0), 2), (SENDER_START_ACK, 1)],
            [(SENDER_IDLE, (0, 0), (COUNTER, 2**5 - 1), (0, 0), (1, 1), (1, 1), 1), (SENDER_IDLE, 0)],
            [(SENDER_START_ACK, (0, 0), (COUNTER, 2**5 - 1), (0, 1), (1, 1), (1, 1), 1), (SENDER_START_ACK, 0)],
            [(SENDER_START_ACK, (0, 0), (START, 2**5 - 1), (1, 1), (1, 1), (1, 1), 1), (SENDER_COUNTING, 0)],
            [(SENDER_START_ACK, (SENDER_START_ACK_COUNT, -1), (0, 0), (0, 0), (0, 0), (0, 0), 2), (SENDER_START_ACK, 1)],
            [(SENDER_COUNTING, (SENDER_COUNTING_COUNT, -1), (0, 0), (0, 0), (0, 0), (0, 0), 1), (SENDER_WAIT_COUNTER_RECEIVE, 1)],
            [(SENDER_WAIT_COUNTER_RECEIVE, (SENDER_WAIT_COUNTER_RECEIVE_COUNT, -1), (0, 0), (0, 0), (0, 0), (0, 0), 2), (SENDER_WAIT_COUNTER_RECEIVE, 1)],
            [(SENDER_WAIT_COUNTER_RECEIVE, (0, 0), (COUNTER, 2**5 - 1), (0, 1), (1, 1), (1, 1), 1), (SENDER_IDLE, 0)]
        ]

        self.add_ternary_rules(
            "table_next_state_out", key_names, receiver_state_machine,
            ["next_state", "counter_type"],
            "set_next_state_out")

        # reset counter
        self.prev_sender_count = SENDER_COUNTING_COUNT

    def set_special_tables(self):
        """Special tables that have to add or not FANCY headers."""
        print("Done with constant entries in the P4 code")
        # Done with constant entries

    def set_forwarding_table(self):
        """Sets the forwarding table accordingly to the README description"""

        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT4)],
            [("port", PORT1)],
            "set_port")
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT1)],
            [("port", PORT4)],
            "set_port")
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT2)],
            [("port", PORT5)],
            "set_port")
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT5)],
            [("port", PORT2)],
            "set_port")
        # return path after failure
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT6)],
            [("port", PORT4)],
            "set_port")

    def configure_port_mirrorings(self):
        # adds a mirroring id for both directions... this should work mirroring id
        # has to be at least 1, 0 does not work. Source:
        # /home/tofino/bf-sde-9.1.0/pkgsrc/p4-examples/ptf-tests/mirror_test/test.py
        # L50
        for port in port_to_id.keys():
            self.controller.add_mirroring(port, port + 1, "BOTH")

    def set_dedicated_rerouting(self, num_pipes=2):
        """Sets rerouting mirroring info"""
        for pipe in range(num_pipes):
            pipe_offset = pipe * 128  # not used because of the slice
            recirc_port = pipe_offset + 68

            self.controller.entry_add(
                "clone_to_recirculation",
                [("eg_intr_md.egress_port[8:7]", pipe)],
                [("mirror_id", 100 + pipe)],
                "_clone_to_recirculation")

            # adds the mirroring rule to recirc port!
            self.controller.add_mirroring(recirc_port, 100 + pipe, "EGRESS")

        for port, id in port_to_id.items():
            self.controller.entry_add(
                "failed_port_to_reroute_address_set",
                [("hdr.fancy_pre.port", port)],
                [("address_offset", id)],
                "set_reroute_address")

            self.controller.entry_add(
                "read_reroute_register",
                [("ig_tm_md.ucast_egress_port", port)],
                [("address_offset", id)],
                "read_reroute_address")
        # set reroute table
        # Hardcoded rerotuing from PORT1 to 6 from our constants.p4
        self.controller.entry_add(
            "dedicated_reroute", [("ig_tm_md.ucast_egress_port", PORT1)],
            [("port", PORT6)],
            "set_port")

    def configure_port_info(self):
        """configure port types"""
        for port, _type in port_to_type.items():
            port_id = port_to_id[port]

            self.controller.entry_add(
                "ingress_port_info",
                [("ig_intr_md.ingress_port", port)],
                [("address_offset", port_id), ("ingress_type", _type)],
                "set_ingress_port_info")

            self.controller.entry_add(
                "egress_port_info",
                [("eg_intr_md.egress_port", port)],
                [("address_offset", port_id), ("egress_type", _type)],
                "set_egress_port_info")

    def fill_top_prefixes_table(self, start_ip, num=10):
        start = ip2int(start_ip)
        for i in range(num):
            self.controller.entry_add(
                "packet_to_id", [("hdr.ipv4.dst_addr", i + start)],
                [("packet_id", i)],
                "set_packet_id_dedicated")

    # ZOOMING CONTROLLER
    ####################

    def set_in_port_offsets(self, ports):
        """Configures ports to register offsets where the tree is stored"""
        table = self.controller.bfrt_info.table_get("in_port_to_offsets")
        # due to a problem with python3.5 with ord dicts I put it static
        key_names = [
            'hdr.fancy_pre.$valid',
            'ig_intr_md.ingress_port', 'hdr.fancy_pre.port', '$MATCH_PRIORITY']

        for port in ports:
            i = port_to_index[port]
            rules = [[(0, (port, 2**9 - 1), (port, 0), 1),
                      (COUNTER_NODE_WIDTH * i, i)]]

            self.add_ternary_rules(
                "in_port_to_offsets", key_names, rules,
                ["counter_offset", "simple_offset"],
                "set_ingress_address_offsets_normal")

            rules1 = [[(1, (port, 0), (port, 2**9 - 1), 1),
                      (COUNTER_NODE_WIDTH * i, i)]]

            self.add_ternary_rules(
                "in_port_to_offsets", key_names, rules1,
                ["counter_offset", "simple_offset"],
                "set_ingress_address_offsets_recirc")

    def set_out_port_offsets(self, ports):
        """Configures ports to register offsets where the tree is stored"""
        table = self.controller.bfrt_info.table_get("out_port_to_offsets")
        key_names = [
            'hdr.fancy_pre.$valid', 'eg_intr_md.egress_port',
            'hdr.fancy_pre.port', '$MATCH_PRIORITY']

        for port in ports:
            i = port_to_index[port]
            rules = [[(0, (port, 2**9 - 1), (port, 0), 1),
                      (COUNTER_NODE_WIDTH * i, i)]]

            self.add_ternary_rules(
                "out_port_to_offsets", key_names, rules,
                ["counter_offset", "simple_offset"],
                "set_egress_address_offsets_normal")

            rules1 = [[(1, (port, 0), (port, 2**9 - 1), 1),
                      (COUNTER_NODE_WIDTH * i, i)]]

            self.add_ternary_rules(
                "out_port_to_offsets", key_names, rules1,
                ["counter_offset", "simple_offset"],
                "set_egress_address_offsets_recirc")

    def set_zooming_reroute(self):
        # set reroute table
        # Hardcoded rerotuing from PORT1 to 6 from our constants.p4
        self.controller.entry_add(
            "zooming_reroute", [("ig_tm_md.ucast_egress_port", PORT1)],
            [("port", PORT6)],
            "set_port")

    def set_update_zoom_max_table(self):
        for i in range(MAX_ZOOM + 1):
            self.controller.entry_add(
                "set_fancy_pre_type_to_update",
                [("hdr.fancy_counters_length._length", 0),
                 ("meta.fancy.zooming_stage", i)],
                [("_type", UPDATE_OFFSET + i + 4)], "_set_fancy_pre_type")

    def set_default_reroute(self):
        self.controller.default_entry_set(
            "zooming_reroute", [("port", PORT6)], "set_port")

    def set_initial_state(self):
        # set egress and ingress to counting states
        self.controller.register_entry_add(
            "in_state", port_to_index[PORT2],
            RECEIVER_COUNTING)

        self.controller.register_entry_add(
            "out_state", port_to_index[PORT1],
            SENDER_COUNTING)

    def modify_num_packet_count(self, new_count):
        key_names = [
            'meta.fancy.current_state', 'meta.fancy.current_counter',
            'hdr.fancy.action_value', 'hdr.fancy.ack', 'hdr.fancy.fsm',
            'hdr.fancy.$valid', '$MATCH_PRIORITY']

        rule = (SENDER_COUNTING, (self.prev_sender_count, -1),
                (0, 0), (0, 0), (0, 0), (0, 0), 1)
        key = self.get_match_keys(key_names, rule)

        self.controller.entry_del("table_next_state_out", keys=key)
        match_action = [
            (SENDER_COUNTING, (new_count, -1),
             (0, 0),
             (0, 0),
             (0, 0),
             (0, 0),
             1),
            (SENDER_WAIT_COUNTER_RECEIVE, 1)]

        self.add_ternary_rules(
            "table_next_state_out", key_names, [match_action],
            ["next_state", "counter_type"],
            "set_next_state_out")

        # update count
        self.prev_sender_count = new_count

    def configure_all(self):

        # clean all
        self.controller.clear_all()

        # configures the ingress state machine
        self.set_next_state_in()

        # configures the ingress state machine
        # we use the handler to modify a specific entry if needed.
        self.set_next_state_out()

        # sets port forwarding rules
        self.set_forwarding_table()

        # Configures port mirrorings, so we can do e2e mirroring for the egress statemachine
        self.configure_port_mirrorings()

        self.set_dedicated_rerouting()

        self.configure_port_info()

        self.fill_top_prefixes_table("11.0.2.1", 10)

        # ZOOMING STUFF

        self.set_in_port_offsets([PORT0, PORT1, PORT2, PORT3, PORT4, PORT5])

        self.set_zooming_reroute()

        self.set_out_port_offsets([PORT0, PORT1, PORT2, PORT3, PORT4, PORT5])

        self.set_update_zoom_max_table()

        # set registers to counting state.
        # Just for the case study
        self.set_initial_state()

        # I believe not needed?
        # self.set_default_reroute()

    ##################################################################
    # Testing Functions (not needed for case study)
    ##################################################################

    # DEDICATED
    def check_system_state(self, addresses_to_check, ids, pipe=1):

        for address_out, address_in in addresses_to_check:
            for id in ids:
                addr = address_out + id
                real_counter = self.controller.register_entry_get(
                    "pkt_counters_out",
                    addr)
                state_counter = self.controller.register_entry_get(
                    "counters_out",
                    addr)
                state = self.controller.register_entry_get("state_out", addr)

                port = int(addr / 512)

                print(
                    "{:<15} {:<4} {:<30} {:<10} {:<10}".format(
                        "Port {}(out)".format(port),
                        id, sender_state[state[pipe]],
                        state_counter[pipe],
                        real_counter[pipe]))

                addr = address_in + id
                port = int(addr / 512)
                real_counter = self.controller.register_entry_get(
                    "pkt_counters_in",
                    addr)
                state_counter = self.controller.register_entry_get(
                    "counters_in",
                    addr)
                state = self.controller.register_entry_get("state_in", addr)

                print(
                    "{:<15} {:<4} {:<30} {:<10} {:<10}".format(
                        "Port {}(in)".format(port),
                        id, receiver_state[state[pipe]],
                        state_counter[pipe],
                        real_counter[pipe]))
                print("")

    # ZOOMING TEST FUNCTIONS

    def read_status_port(self, port_id, direction, pipe=0):

        # gets indexes
        start_index = COUNTER_NODE_WIDTH * port_to_index[port_id]
        normal_index = port_to_index[port_id]

        # initial values when not read
        zooming_stage = max_0 = max_1 = -1

        print("Registers state of port {}; direction {}".format(
            port_to_index[port_id], direction))

        counters = []
        if direction == "in":
            counters = self.controller.register_entry_range_get(
                "in_counters", start_index, start_index + COUNTER_NODE_WIDTH)
        elif direction == "out":
            counters = self.controller.register_entry_range_get(
                "out_counters", start_index, start_index + COUNTER_NODE_WIDTH)

        counters = [x[pipe] for x in counters]
        print("Counter values:")
        print(counters)

        if direction == "out":
            zooming_stage = self.controller.register_entry_get(
                "zooming_stage", normal_index)[pipe]
            max_0 = self.controller.register_entry_get(
                "max_0", normal_index)[pipe]
            max_1 = self.controller.register_entry_get(
                "max_1", normal_index)[pipe]

            current_state = sender_state[self.controller.register_entry_get(
                "out_state", normal_index)[pipe]]
        elif direction == "in":
            current_state = receiver_state[self.controller.register_entry_get(
                "in_state", normal_index)[pipe]]

        print("zoom: {} max_0: {} max_1: {}".format(
            zooming_stage, max_0, max_1))
        print("Current state: {}".format(current_state))

        return counters, zooming_stage, max_0, max_1

    def fill_register_counters(self, direction, port_id, values):
        start_index = COUNTER_NODE_WIDTH * port_to_index[port_id]

        for value in values[:COUNTER_NODE_WIDTH]:
            if direction == "in":
                self.controller.register_entry_add(
                    "in_counters", start_index, value)
            elif direction == "out":
                self.controller.register_entry_add(
                    "out_counters", start_index, value)
            start_index += 1

    def set_test_counters(self, width=32):
        self.fill_register_counters("in", PORT0, range(0, width))
        self.fill_register_counters("in", PORT1, range(width, 2 * width))
        self.fill_register_counters("in", PORT2, range(2 * width, 3 * width))

        self.fill_register_counters("out", PORT0, range(0, width))
        self.fill_register_counters("out", PORT2, range(width, 2 * width))
        self.fill_register_counters("out", PORT1, range(2 * width, 3 * width))

    def test_status(self, current_status, expected_status):
        if current_status == expected_status:
            print(bcolors.OKGREEN + "Test Passed" + bcolors.ENDC)
        else:
            print(bcolors.FAIL + "Test failed with: {} {}".format(current_status,
                                                                  expected_status) + bcolors.ENDC)
            # raise Exception

    def compute_counters_after_traffic(
            self, ips_to_pkt, maxes, width=8, hash_functions=None,
            zooming_stage=0):

        counters = [0 for _ in range(width)]

        if not hash_functions:
            hash_functions = get_hashes()

        for ip, num_pkts in ips_to_pkt.items():
            hash_indexes = get_hash_ip(ip, hash_functions, width)
            path = hash_indexes[:zooming_stage]
            if maxes[:zooming_stage] == path:
                index = hash_indexes[zooming_stage]
                counters[index] += num_pkts

        return counters

    def test_zooming(
            self, ips, fail_ips, pkts=5, width=4, zooms=2, pipe=0):
        # for model ports pipe 0 and num pipes 4
        # for tofino ports pipe 1 and num pipes 2

        # ips = ["10.0.1.1" , "10.0.1.2", "10.0.1.3"]
        # fail_ips = ["10.0.1.1"]

        # reset all and configure
        self.configure_all()

        # hash functions
        hash_functions = get_hashes()

        time.sleep(3)

        good_ips = list(set(ips).difference(set(fail_ips)))

        # read status
        print("Reading status")
        status = self.read_status_port(PORT1, "out", pipe)
        self.test_status(status, ([0] * width, 0, 0, 0))

        status = self.read_status_port(PORT2, "in", pipe)
        self.test_status(status, ([0] * width, -1, -1, -1))

        maxes = [0 for _ in range(zooms)]

        for zoom in range(zooms + 1):
            print("Sending traffic...")
            for ip in ips:
                send_packet("veth8", addr=ip, count=pkts, delay=0.2)

            time.sleep(pkts * len(ips) * 0.3)

            # reading status
            print("Reading status after traffic...")
            status = self.read_status_port(PORT1, "out", pipe)
            # simulated status
            egress_counters = self.compute_counters_after_traffic(
                build_ips_to_pkts(ips, pkts),
                maxes, width, hash_functions, zoom)
            self.test_status(
                status, (egress_counters, zoom, maxes[0], maxes[1]))

            status = self.read_status_port(PORT2, "in", pipe)
            ingress_counters = self.compute_counters_after_traffic(
                build_ips_to_pkts(good_ips, pkts),
                maxes, width, hash_functions, zoom)
            self.test_status(status, (ingress_counters, -1, -1, -1))

            # send stop to ingress
            send_fancy_packet("veth4", actions['STOP'], 0, 0, 1, id=511)

            time.sleep(width * 0.3)

            # reading status
            print("Reading status after stop")
            if zoom != MAX_ZOOM:
                status = self.read_status_port(PORT1, "out", pipe)

                # update max
                counters_diff = compute_counters_difference(
                    ingress_counters, egress_counters)
                max_index = counters_diff.index(max(counters_diff))
                maxes[zoom] = max_index
                self.test_status(status, ([0] * width, (zoom + 1) %
                                          (MAX_ZOOM + 1), maxes[0], maxes[1]))

        status = self.read_status_port(PORT2, "in", pipe)
        self.test_status(status, ([0] * width, -1, -1, -1))


if __name__ == "__main__":
    print("Starts Fancy Switch Controller....")
    # adds ports
    print("Setting switch ports...")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true',
                        required=False, default=False)
    parser.add_argument('--server_port', help="Port to listen",
                        type=int, default=5000)

    args = parser.parse_args()

    # get controller
    controller = FancyController()

    # configure ports
    controller.configure_all()

    if args.server:
        s = TofinoCommandServer(int(args.server_port), controller)
        print("Start command server")
        s.run()


def a():
    b = 7
    exec("t = b")
    print(locals()["t"])
