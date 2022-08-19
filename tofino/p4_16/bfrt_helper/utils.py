import subprocess
import struct
import socket
import os.path
import sys


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


def get_constant_cmds(constants_path, model=True):
    """Loads all the constants from our P4 file so we can share them
    Args:
        constants_path (_type_): _description_
        model (bool, optional): _description_. Defaults to True.
    Returns:
        _type_: _description_
    """
    cmds = []
    if os.path.isfile(constants_path):
        with open(constants_path, "r") as constants:
            for line in constants:
                # checks if the line starts with define
                if line.strip().startswith("#define"):
                    tmp = line.strip().split()

                    # for port numbers we do this special parsing
                    # thus ports have to end with _M for the model and
                    # _S for hardware
                    if model and tmp[1].endswith("_M"):
                        tmp[1] = tmp[1].replace("_M", "")
                    elif not model and tmp[1].endswith("_S"):
                        tmp[1] = tmp[1].replace("_S", "")

                    # prepare python commands
                    cmd = "{} = {}".format(tmp[1], tmp[2])
                    cmds.append(cmd)
    else:
        print("Constants file does not exist")
        exit(1)
    return cmds


def load_constants(constants_path, model=True):
    """Loads the Constants into the python namespace. 
    Warning: It does not work, has to be ran locally at the controller code.
    Args:
        constants_path (_type_): _description_
        model (bool, optional): _description_. Defaults to True.
    Returns:
        _type_: _description_
    """
    cmds = get_constant_cmds(constants_path, model)
    for cmd in cmds:
        # make variable global
        exec(cmd)


def load_scripts_path(paths):
    """Inserts all the paths into PYTHONPATH
    Args:
        paths (_type_): _description_
    """
    for path in paths:
        sys.path.insert(0, path)


# Thrift API helper to set Ports.

def set_ports(pal, ports_setting):
    """Enable switch ports.
    Args:
        pal (_type_): pal object from run_pd_rpc
        ports_setting (dict): ports setting dictionary {1: "10G", 4: "100G", 6: "100G"}
    """

    # adds ports
    for port, setting in ports_setting.items():

        if setting == "10G":
            for lane in range(4):
                dp = pal.port_front_panel_port_to_dev_port_get(port, lane)
                pal.port_add(dp, pal.port_speed_t.BF_SPEED_10G,
                             pal.fec_type_t.BF_FEC_TYP_NONE)
                pal.port_an_set(dp, pal.autoneg_policy_t.BF_AN_FORCE_DISABLE)
                pal.port_enable(dp)

        elif setting == "100G":
            dp = pal.port_front_panel_port_to_dev_port_get(port, 0)
            pal.port_add(dp, pal.port_speed_t.BF_SPEED_100G,
                         pal.fec_type_t.BF_FEC_TYP_NONE)
            pal.port_an_set(dp, pal.autoneg_policy_t.BF_AN_FORCE_DISABLE)
            pal.port_enable(dp)
