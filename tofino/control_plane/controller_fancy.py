
# Loads constants from the p4 file such that i dont have to edit them in both places
import subprocess
from utils import get_constant_cmds, set_ports, ip2int, int2ip, load_scripts_path

# add paths
# make sure you run the controller code from the controller dir.
paths = ["../eval", "../scripts"]
load_scripts_path(paths)
from server import ServerTCP, TofinoCommandServer


# CONFIGURATION
# paths to constants
path_to_constants = "../p4src/includes/constants.p4"
# model enabled?
MODEL = False
# load all constants
#load_constants(path_to_constants, MODEL)
cmds = get_constant_cmds(path_to_constants, MODEL)
for cmd in cmds:
    # make variable global
    exec(cmd)

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

# NOTE: you will find many constant variables in capital letters across the
#       document they are all imported from the constants.p4 using the function
#       `get_constant_cmds` and then loading them in the namespace using exec


# RECEIVER STATE MACHINE TABLE
# Configures the state transition table for the ingress machine
def set_next_state_in():
    """Configures the ingress state machine table with initial values."""
    # IDLE
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_IDLE, 0, 0, START, -1, 0, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTING, 0))

    # COUNTING
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTING, 0, 0, START, -1, 0, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTING, 0))

    # removed so we send the counter instantaneously
    #p4_pd.table_next_state_in_table_add_with_set_next_state_in(p4_pd.table_next_state_in_match_spec_t(RECEIVER_COUNTING, 0, 0, STOP, -1, 0, -1, 1, -1), 1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_WAIT_COUNTER_SEND,0))
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTING, 0, 0, STOP, -1, 0, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTER_ACK, 0))

    # WAIT TO SEND
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_WAIT_COUNTER_SEND, RECEIVER_WAIT_COUNTER_SEND_COUNT, -1,
            0, 0, 0, 0, 0, 0),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTER_ACK, 1))

    # COUNTER ACK
    # We give priority to the events with an action (2,1)
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTER_ACK, 0, 0, STOP, -1, 0, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTER_ACK, 0))
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTER_ACK, 0, 0, COUNTER, -1, 1, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_IDLE, 0))
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTER_ACK, 0, 0, START, -1, 0, -1, 1, -1),
        1, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTING, 0))
    p4_pd.table_next_state_in_table_add_with_set_next_state_in(
        p4_pd.table_next_state_in_match_spec_t(
            RECEIVER_COUNTER_ACK, RECEIVER_COUNTER_ACK_COUNT, -1, 0, 0, 0, 0,
            0, 0),
        2, p4_pd.set_next_state_in_action_spec_t(RECEIVER_COUNTER_ACK, 1))


def set_next_state_out():
    """Configures the egress state machine table with initial values."""

    # IDLE
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_IDLE, SENDER_IDLE_COUNT, -1, 0, 0, 0, 0, 0, 0, 0, 0),
        2, p4_pd.set_next_state_out_action_spec_t(SENDER_START_ACK, 1))
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_IDLE, 0, 0, COUNTER, -1, 0, 0, 1, -1, 1, -1),
        1, p4_pd.set_next_state_out_action_spec_t(SENDER_IDLE, 0))

    # START ACK
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_START_ACK, 0, 0, COUNTER, -1, 0, -1, 1, -1, 1, -1),
        1, p4_pd.set_next_state_out_action_spec_t(SENDER_START_ACK, 0))
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_START_ACK, 0, 0, START, -1, 1, -1, 1, -1, 1, -1),
        1, p4_pd.set_next_state_out_action_spec_t(SENDER_COUNTING, 0))
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_START_ACK, SENDER_START_ACK_COUNT, -1, 0, 0, 0, 0, 0, 0, 0,
            0),
        2, p4_pd.set_next_state_out_action_spec_t(SENDER_START_ACK, 1))

    # COUNTING
    handler = p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_COUNTING, SENDER_COUNTING_COUNT, -1, 0, 0, 0, 0, 0, 0, 0,
            0),
        1, p4_pd.set_next_state_out_action_spec_t(
            SENDER_WAIT_COUNTER_RECEIVE, 1))

    # WAIT COUNTER
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_WAIT_COUNTER_RECEIVE, SENDER_WAIT_COUNTER_RECEIVE_COUNT, -1,
            0, 0, 0, 0, 0, 0, 0, 0),
        2, p4_pd.set_next_state_out_action_spec_t(
            SENDER_WAIT_COUNTER_RECEIVE, 1))
    p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_WAIT_COUNTER_RECEIVE, 0, 0, COUNTER, -1, 0, -1, 1, -1, 1, -
            1),
        1, p4_pd.set_next_state_out_action_spec_t(SENDER_IDLE, 0))
    # p4_pd.table_next_state_out_table_add_with_set_next_state_out(p4_pd.table_next_state_out_match_spec_t(SENDER_WAIT_COUNTER_RECEIVE, 0, 0, COUNTER, -1, 0, -1), 2, p4_pd.set_next_state_out_action_spec_t(SENDER_START_ACK, 0))
    return handler


def set_special_tables():
    """Special tables that have to add or not FANCY headers."""

    # Send Start
    p4_pd.table_idle_to_start_ack_out_table_add_with_send_start(
        p4_pd.table_idle_to_start_ack_out_match_spec_t(0))
    p4_pd.table_idle_to_start_ack_out_table_add_with_send_start_already_fancy(
        p4_pd.table_idle_to_start_ack_out_match_spec_t(1))

    p4_pd.table_start_ack_to_start_ack_out2_table_add_with_send_start(
        p4_pd.table_start_ack_to_start_ack_out2_match_spec_t(0))
    p4_pd.table_start_ack_to_start_ack_out2_table_add_with_send_start_already_fancy(
        p4_pd.table_start_ack_to_start_ack_out2_match_spec_t(1))

    p4_pd.table_wait_counter_to_start_ack_table_add_with_send_start(
        p4_pd.table_wait_counter_to_start_ack_match_spec_t(0))
    p4_pd.table_wait_counter_to_start_ack_table_add_with_send_start_already_fancy(
        p4_pd.table_wait_counter_to_start_ack_match_spec_t(1))

    # Send Stop
    p4_pd.table_counting_to_wait_counter_table_add_with_send_stop(
        p4_pd.table_counting_to_wait_counter_match_spec_t(0))
    p4_pd.table_counting_to_wait_counter_table_add_with_send_stop_already_fancy(
        p4_pd.table_wait_counter_to_wait_counter_match_spec_t(1))

    p4_pd.table_wait_counter_to_wait_counter_table_add_with_send_stop(
        p4_pd.table_wait_counter_to_wait_counter_match_spec_t(0))
    p4_pd.table_wait_counter_to_wait_counter_table_add_with_send_stop_already_fancy(
        p4_pd.table_wait_counter_to_wait_counter_match_spec_t(1))


def sets_forwarding_table():
    """Sets the forwarding table accordingly to the README description"""
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

    # backup reverse path, in theory not used?
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT6),
        p4_pd.set_port_action_spec_t(PORT4))


# mirroing util
def mirror_session(
        mir_type=mirror.MirrorType_e.PD_MIRROR_TYPE_NORM,
        direction=mirror.Direction_e.PD_DIR_INGRESS, id=100, egr_port=1,
        egr_port_v=True, max_pkt_len=16384):
    return mirror.MirrorSessionInfo_t(
        mir_type=mir_type, direction=direction, mir_id=id, egr_port=egr_port,
        egr_port_v=egr_port_v, max_pkt_len=max_pkt_len)


def configure_port_mirrorings():
    # adds a mirroring id for both directions... this should work mirroring id
    # has to be at least 1, 0 does not work. Source:
    # /home/tofino/bf-sde-9.1.0/pkgsrc/p4-examples/ptf-tests/mirror_test/test.py
    # L50
    for port in [PORT0, PORT1, PORT2, PORT3, PORT4, PORT5, PORT6]:
        # Ingress cloning i2e table
        #p4_pd.table_counter_send_to_counter_ack_i2e_in_table_add_with_send_counter_i2e(p4_pd.table_counter_send_to_counter_ack_i2e_in_match_spec_t(port), p4_pd.send_counter_i2e_action_spec_t(port+1))
        p4_pd.table_counter_ack_to_counter_ack_i2e_in_table_add_with_send_counter_i2e(
            p4_pd.table_counter_ack_to_counter_ack_i2e_in_match_spec_t(port), p4_pd.send_counter_i2e_action_spec_t(port + 1))

        # Egress cloning e2e table
        p4_pd.table_mirror_to_update_table_add_with_action_mirror_to_update(
            p4_pd.table_mirror_to_update_match_spec_t(port),
            p4_pd.action_mirror_to_update_action_spec_t(port + 1))

        # Mirroring sessions
        mirror.session_create(
            mirror_session(
                id=1 + port, egr_port=port,
                direction=mirror.Direction_e.PD_DIR_BOTH))


def set_up_rerouting():
    """Set up rerouting tables"""
    try:
        # Set cloning to recirculation ports
        for pipe in range(2):
            pipe_offset = pipe * 128
            recirc_port = pipe_offset + 68

            p4_pd.clone_to_recirculation_table_add_with__clone_to_recirculation(
                p4_pd.clone_to_recirculation_match_spec_t(pipe_offset),
                p4_pd._clone_to_recirculation_action_spec_t(100 + pipe))

            mirror.session_create(
                mirror_session(
                    id=100 + pipe, egr_port=recirc_port,
                    direction=mirror.Direction_e.PD_DIR_EGRESS))

        # set port to reroute address set and port to reroute address read
        for port, id in port_to_id.items():
            p4_pd.port_to_reroute_address_set_table_add_with_set_reroute_address_set(
                p4_pd.port_to_reroute_address_set_match_spec_t(port), p4_pd.set_reroute_address_set_action_spec_t(id))

            p4_pd.port_to_reroute_address_read_table_add_with_set_reroute_address_read(
                p4_pd.port_to_reroute_address_read_match_spec_t(port), p4_pd.set_reroute_address_read_action_spec_t(id))

        # set reroute table
        # Hardcoded rerotuing from PORT1 to 6 from our constants.p4
        p4_pd.reroute_table_add_with_set_port(
            p4_pd.reroute_match_spec_t(PORT1),
            p4_pd.set_port_action_spec_t(PORT6))
    except:
        pass


def configure_port_types():
    # Ingress and egress types
    # The switch uses this to know if there is a running State machine or not
    # We have a table in both the ingress and egress

    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT0),
        p4_pd.set_ingress_type_action_spec_t(HOST))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT4),
        p4_pd.set_ingress_type_action_spec_t(HOST))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT5),
        p4_pd.set_ingress_type_action_spec_t(HOST))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT1),
        p4_pd.set_ingress_type_action_spec_t(SWITCH))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT2),
        p4_pd.set_ingress_type_action_spec_t(SWITCH))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT3),
        p4_pd.set_ingress_type_action_spec_t(HOST))
    p4_pd.ingress_fancy_enabled_table_add_with_set_ingress_type(
        p4_pd.ingress_fancy_enabled_match_spec_t(PORT6),
        p4_pd.set_ingress_type_action_spec_t(SWITCH))

    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT0),
        p4_pd.set_egress_type_action_spec_t(HOST))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT4),
        p4_pd.set_egress_type_action_spec_t(HOST))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT1),
        p4_pd.set_egress_type_action_spec_t(SWITCH))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT2),
        p4_pd.set_egress_type_action_spec_t(SWITCH))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT3),
        p4_pd.set_egress_type_action_spec_t(HOST))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT5),
        p4_pd.set_egress_type_action_spec_t(HOST))
    p4_pd.egress_fancy_enabled_table_add_with_set_egress_type(
        p4_pd.egress_fancy_enabled_match_spec_t(PORT6),
        p4_pd.set_egress_type_action_spec_t(SWITCH))


def set_port_to_id_table():
    # Populate port and ID tables
    for port, id in port_to_id.items():
        p4_pd.ingress_port_to_port_id_table_add_with_set_port_id(
            p4_pd.ingress_port_to_port_id_match_spec_t(port),
            p4_pd.set_port_id_action_spec_t(id))
        p4_pd.egress_port_to_port_id_table_add_with_set_port_id(
            p4_pd.egress_port_to_port_id_match_spec_t(port),
            p4_pd.set_port_id_action_spec_t(id))


def reset_registers():
    p4_pd.register_reset_all_counters_in()
    p4_pd.register_reset_all_pkt_counters_in()
    p4_pd.register_reset_all_state_in()
    p4_pd.register_reset_all_state_lock_in()

    p4_pd.register_reset_all_counters_out()
    p4_pd.register_reset_all_pkt_counters_out()
    p4_pd.register_reset_all_state_out()
    p4_pd.register_reset_all_state_lock_out()

    try:
        p4_pd.register_reset_all_reroute_register()
    except:
        pass


def fill_top_prefixes_table(start_ip="10.0.3.1", num=10):
    """Set ip to id for the dedicated state machine"""
    start = ip2int(start_ip)
    for i in range(num):
        p4_pd.packet_to_id_table_add_with_set_packet_id(
            p4_pd.packet_to_id_match_spec_t(i32(start + i)),
            p4_pd.set_packet_id_action_spec_t(i))
        print "Added packet ip to id: {} -> {}".format(int2ip(start + i), i)


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


def check_system_state(addresses_to_check, ids, pipe=1):

    for adress_out, address_in in addresses_to_check:
        for id in ids:
            addr = adress_out + id
            real_counter = p4_pd.register_read_pkt_counters_out(addr, from_hw)
            state_counter = p4_pd.register_read_counters_out(addr, from_hw)
            state = p4_pd.register_read_state_out(addr, from_hw)

            port = int(addr / 512)

            print(
                "{:<15} {:<4} {:<30} {:<10} {:<10}".format(
                    "Port {}(out)".format(port),
                    id, sender_state[state[pipe]],
                    state_counter[pipe],
                    real_counter[pipe]))

            addr = address_in + id
            port = int(addr / 512)
            real_counter = p4_pd.register_read_pkt_counters_in(addr, from_hw)
            state_counter = p4_pd.register_read_counters_in(addr, from_hw)
            state = p4_pd.register_read_state_in(addr, from_hw)

            print(
                "{:<15} {:<4} {:<30} {:<10} {:<10}".format(
                    "Port {}(in)".format(port),
                    id, receiver_state[state[pipe]],
                    state_counter[pipe],
                    real_counter[pipe]))
            print("")


def modify_num_packet_count(handler, new_pkt_count):
    p4_pd.table_next_state_out_table_delete(handler)
    handler = p4_pd.table_next_state_out_table_add_with_set_next_state_out(
        p4_pd.table_next_state_out_match_spec_t(
            SENDER_COUNTING, new_pkt_count, -1, 0, 0, 0, 0, 0, 0, 0, 0),
        1, p4_pd.set_next_state_out_action_spec_t(
            SENDER_WAIT_COUNTER_RECEIVE, 1))

    return handler


class DedicatedEntriesController(object):
    """Custom controller object we created to be able to run commands remotely 
    with some simple python server."""

    def __init__(self, controller, from_hw, initial_handler):

        self.controller = controller
        self.from_hw = from_hw
        self.handler = initial_handler

    def clear_state(self):
        self.controller.register_reset_all_counters_in()
        self.controller.register_reset_all_pkt_counters_in()
        self.controller.register_reset_all_state_in()
        self.controller.register_reset_all_state_lock_in()
        self.controller.register_reset_all_counters_out()
        self.controller.register_reset_all_pkt_counters_out()
        self.controller.register_reset_all_state_out()
        self.controller.register_reset_all_state_lock_out()
        self.controller.register_reset_all_reroute_register()

    def check_reroute_entries(self):
        self.controller.register_read_reroute_register(513, self.from_hw)
        self.controller.register_read_reroute_register(514, self.from_hw)

    def modify_num_packet_count(self, new_pkt_count):
        self.controller.table_next_state_out_table_delete(self.handler)
        self.handler = self.controller.table_next_state_out_table_add_with_set_next_state_out(p4_pd.table_next_state_out_match_spec_t(
            SENDER_COUNTING, new_pkt_count, -1, 0, 0, 0, 0, 0, 0, 0, 0), 1, p4_pd.set_next_state_out_action_spec_t(SENDER_WAIT_COUNTER_RECEIVE, 1))


if __name__ == "__main__":
    print("Starts Fancy Switch Controller....")
    # adds ports
    print("Setting switch ports...")

    # Hardcoded parameters. I can not use the command line arguments since we call this
    # using the run_pd_rpc.py script.
    SERVER_PORT = 5000
    STARTING_DST_IP = "11.0.2.1"

    # clear all state
    clear_all()

    # set ports
    set_ports(pal, {1: "10G", 3: "100G", 4: "100G",
                    5: "100G", 6: "100G", 7: "100G", 8: "100G"})

    # configures the ingress state machine
    set_next_state_in()

    # configures the ingress state machine
    # we use the handler to modify a specific entry if needed.
    handler = set_next_state_out()

    # configures some tables that have to add or not fancy headers
    set_special_tables()

    # sets port forwarding rules
    sets_forwarding_table()

    # Configures port mirrorings, so we can do e2e mirroring for the egress statemachine
    configure_port_mirrorings()

    # configure rerouting rules
    set_up_rerouting()

    # configure port types: HOST or SWITCH
    configure_port_types()

    # port to id mappings
    set_port_to_id_table()

    fill_top_prefixes_table(STARTING_DST_IP, 10)

    reset_registers()
    conn_mgr.complete_operations()

    controller = DedicatedEntriesController(p4_pd, from_hw, handler)
    s = TofinoCommandServer(SERVER_PORT, controller)
    print("Start command server")
    s.run()
