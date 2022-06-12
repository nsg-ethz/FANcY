# This is a control planed used for basic rules at the second switch the one we use
# as debugger and link with properties
from utils import get_constant_cmds, set_ports, load_scripts_path
import struct
import socket
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
cmds = get_constant_cmds(path_to_constants, MODEL)
for cmd in cmds:
    # make variable global
    exec(cmd)


class DebuggingSwitchController(object):
    """Custom controller object we created to be able to run commands remotely 
    with some simple python server."""

    def __init__(self, controller, from_hw):

        self.controller = controller
        self.from_hw = from_hw

    def fill_drop_prefixes(self, start_ip, num, loss_rate):

        start = ip2int(start_ip)
        for index in range(num):
            addr = int2ip(start + index)
            # set can be dropped table
            ip = ip2int(addr)
            loss_rate_int = int(MAX32 * loss_rate)
            self.controller.can_be_dropped_table_add_with_enable_drop(
                p4_pd.can_be_dropped_match_spec_t(i32(ip)),
                self.controller.enable_drop_action_spec_t(index))
            # set register field
            self.controller.register_write_loss_rates(index, loss_rate_int)
            print(
                "Added IP to be dropped: {} loss_rate {}".format(
                    addr, loss_rate))

    def set_loss_rate(self, start_ip, num, loss_rate):
        """Sets loss rate for traffic incoming from PORT1

        Args:
            start_ip (str): ip to start from
            num (int): how many ips get the same loss rate
            loss_rate (float): loss rate from 0 to 1 (100%)
        """

        # clear table can be dropped before we set the new loss rate
        clear_table("can_be_dropped")
        # clear counters
        self.controller.register_reset_all_loss_rates()
        self.controller.register_reset_all_loss_count()

        # set new rates
        self.fill_drop_prefixes(start_ip, num, loss_rate)


##############################
# MAIN HELPERS AND FUNCTIONS
##############################

def clear_state():
    """Resets all the state of this switch to default"""
    clear_all()
    p4_pd.register_reset_all_loss_rates()
    p4_pd.register_reset_all_loss_count()


# Populate packet id table
def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


def set_basic_tables():
    """Sets the forwaring rules as explained in the readme
    PORT1 <-> PORT2
    PORT6 (backup) -> PORT2 
    """

    # normal forwarding
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT1),
        p4_pd.set_port_action_spec_t(PORT2))
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT2),
        p4_pd.set_port_action_spec_t(PORT1))

    # backup path without loss or problems
    p4_pd.forward_table_add_with_set_port(
        p4_pd.forward_match_spec_t(PORT6),
        p4_pd.set_port_action_spec_t(PORT2))


# utility to setup mirroring sessions
def mirror_session(
        mir_type=mirror.MirrorType_e.PD_MIRROR_TYPE_NORM,
        direction=mirror.Direction_e.PD_DIR_INGRESS, id=100, egr_port=1,
        egr_port_v=True, max_pkt_len=16384):
    return mirror.MirrorSessionInfo_t(
        mir_type=mir_type, direction=direction, mir_id=id, egr_port=egr_port,
        egr_port_v=egr_port_v, max_pkt_len=max_pkt_len)


def set_address_drop_rate(address, index, drop_rate):
    """Sets the drop rate for a given address"""
    # set can be dropped table
    ip = ip2int(address)
    loss_rate = int(MAX32 * drop_rate)
    p4_pd.can_be_dropped_table_add_with_enable_drop(
        p4_pd.can_be_dropped_match_spec_t(i32(ip)),
        p4_pd.enable_drop_action_spec_t(index))
    # set register field
    p4_pd.register_write_loss_rates(index, loss_rate)
    print("Added IP to be dropped: {} loss_rate {}".format(address, drop_rate))


def fill_drop_prefixes(start_ip="11.0.1.1", num=10, loss_rate=0.01):
    start = ip2int(start_ip)
    for i in range(num):
        addr = int2ip(start + i)
        set_address_drop_rate(addr, i, loss_rate)


def init(start_ip="11.0.1.1", num=10, loss_rate=0.01):
    """Inits the state of the switch"""
    clear_state()
    set_basic_tables()
    fill_drop_prefixes(start_ip, num, loss_rate)


if __name__ == "__main__":
    print("Starts Middle Switch Controller....")
    # adds ports
    print("Setting switch ports...")
    set_ports(pal, {1: "10G", 3: "100G", 4: "100G",
                    5: "100G", 6: "100G"})

    # Set mirroring session for debugging
    # PORT0 or 128 is just a coincidence careful with this
    mirror.session_create(
        mirror_session(
            id=100, egr_port=PORT0,
            direction=mirror.Direction_e.PD_DIR_BOTH))

    # Hardcoded parameters. I can not use the command line arguments since we call this
    # using the run_pd_rpc.py script.
    DST_IP = "11.0.2.2"
    SERVER_PORT = 5001

    # configure all tables etc
    print("Setting default loss rates")
    init(DST_IP, 3, 0)

    controller = DebuggingSwitchController(p4_pd, from_hw)
    s = TofinoCommandServer(SERVER_PORT, controller)
    print("Start Command Server")
    s.run()
