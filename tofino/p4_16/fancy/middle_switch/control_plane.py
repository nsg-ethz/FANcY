import os
import sys
import time
import socket

sys.path.append("../../bfrt_helper/")
sys.path.append("../scripts/")
sys.path.append("../../../eval")

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


class DebuggingSwitchController():
    def __init__(self):
        self.controller = BfRtAPI(client_id=1)

    def clear_state(self):
        self.controller.clear_all()

    def set_forwarding_table(self):
        """Sets the forwarding table accordingly to the README description"""

        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT1)],
            [("port", PORT2)],
            "set_port")
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT2)],
            [("port", PORT1)],
            "set_port")
        self.controller.entry_add(
            "forward", [("ig_intr_md.ingress_port", PORT6)],
            [("port", PORT2)],
            "set_port")

    def set_forwarding_after_table(self):
        """Sets the forwarding table accordingly to the README description"""

        self.controller.entry_add(
            "forward_after", [("ig_intr_md.ingress_port", PORT1)],
            [("port", PORT2)],
            "set_port")
        self.controller.entry_add(
            "forward_after", [("ig_intr_md.ingress_port", PORT2)],
            [("port", PORT6)],
            "set_port")
        self.controller.entry_add(
            "forward_after", [("ig_intr_md.ingress_port", PORT6)],
            [("port", PORT2)],
            "set_port")

    def set_address_drop_rate(self, address, index, drop_rate):
        ip = ip2int(address)
        loss_rate = int(MAX32 * drop_rate)
        self.controller.entry_add("can_be_dropped", [("hdr.ipv4.dst_addr", ip)], [
            ("drop_prefix_index", index)], "enable_drop")
        # set register field
        self.controller.register_entry_add("loss_rates", index, loss_rate)
        print("Added IP to be dropped: {} loss_rate {}".format(address, drop_rate))

    def fill_drop_prefixes(self, start_ip="11.0.1.1", num=10, loss_rate=0.01):
        start = ip2int(start_ip)
        for i in range(num):
            addr = int2ip(start + i)
            self.set_address_drop_rate(addr, i, loss_rate)

    def configure_all(self, start_ip="11.0.2.1", num=5, loss_rate=0):
        """Inits the state of the switch"""
        self.clear_state()
        self.set_forwarding_table()
        self.set_forwarding_after_table()
        self.fill_drop_prefixes(start_ip, num, loss_rate)

    def set_loss_rate(self, start_ip, num, loss_rate):
        self.controller.clear_table("can_be_dropped")
        self.controller.clear_table("loss_rates")
        self.controller.clear_table("loss_count")
        self.fill_drop_prefixes(start_ip, num, loss_rate)


if __name__ == "__main__":
    print("Starts Middle Switch Controller....")
    # adds ports

    # get controller
    controller = DebuggingSwitchController()

    # Hardcoded parameters. I can not use the command line arguments since we call this
    # using the run_pd_rpc.py script.
    DST_IP = "11.0.2.2"
    SERVER_PORT = 5001

    # configure ports
    controller.configure_all(DST_IP, 3, 0)

    s = TofinoCommandServer(SERVER_PORT, controller)
    print("Start command server")
    s.run()
