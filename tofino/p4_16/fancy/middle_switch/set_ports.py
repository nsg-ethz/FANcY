
# usage:
# ~/tools/run

sys.path.append("../../bfrt_helper/")

# Loads constants from the p4 file such that i dont have to edit them in both places
import subprocess
from utils import set_ports

# App config
# Fixed API


if __name__ == "__main__":

    #import argparse
    #parser = argparse.ArgumentParser()
    # parser.add_argument('--traffic_gen', action='store_true',
    #                    required=False, default=False)
    # parser.add_argument('--period', help="Packet gen period time in ms",
    #                    type=int, default=200, required=False)
    #
    #args = parser.parse_args()

    print("Configure switch with the Fixed API....")
    # adds ports

    print("Setting switch ports...")
    set_ports(pal, {1: "10G", 3: "100G", 4: "100G",
                    5: "100G", 6: "100G"})
